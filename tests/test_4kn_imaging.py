"""Complete imaging workflows against a strict, memory-only 4-KiB device.

Physical classification, geometry and separation are simulated. Real output
files are created only in a temporary directory; no device nodes are used.
"""
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk import imaging, sources

SECTOR = 4096
BLOCK = 4 * SECTOR


class Imaging4KnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'simulated-source.raw'
        self.target = self.root / 'copy.img'
        # Distinct content in every sector detects shifts by a full sector too.
        self.data = b''.join(hashlib.shake_256(str(i).encode()).digest(SECTOR)
                             for i in range(33))
        self.source.write_bytes(self.data)
        self.reads = []
        self.handles = []

    @contextmanager
    def device(self):
        owner = self

        class StrictReadOnlyDisk(io.BytesIO):
            def read(self, count=-1):
                offset = self.tell()
                owner.reads.append((offset, count))
                if offset % SECTOR or count <= 0 or count % SECTOR:
                    raise AssertionError('Unaligned underlying device read')
                return super().read(count)

            def write(self, payload):
                raise AssertionError('Source write attempted')

        @contextmanager
        def open_simulated(path):
            self.assertEqual(path, str(self.source))
            raw = StrictReadOnlyDisk(self.data)
            self.handles.append(raw)
            try:
                yield sources.AlignedDeviceReader(raw, len(self.data), SECTOR)
            finally:
                raw.close()

        with patch.object(imaging, 'is_device_source',
                          side_effect=lambda path: os.fspath(path) == str(self.source)), \
                patch.object(imaging, 'physical_sector_size', return_value=SECTOR), \
                patch.object(imaging, 'source_size', return_value=len(self.data)), \
                patch.object(imaging, 'ensure_safe_destination') as separation, \
                patch.object(imaging, 'open_source', open_simulated):
            yield separation
        self.assertTrue(all(handle.closed for handle in self.handles))
        self.assertEqual(self.source.read_bytes(), self.data)

    def create(self, **kwargs):
        options = dict(block_size=BLOCK, verify=True, bad_sector_policy='stop')
        options.update(kwargs)
        return imaging.create_image(str(self.source), str(self.target), **options)

    def pause(self):
        stopped = [False]

        def progress(event):
            if event.processed >= BLOCK:
                stopped[0] = True

        result = self.create(cancel=lambda: stopped[0], progress=progress)
        self.assertEqual(result['state'], 'paused')
        self.assertEqual(result['processed'], BLOCK)
        self.assertEqual(self.target.read_bytes(), self.data[:BLOCK])
        return result

    def test_complete_copy_verifies_every_byte_including_final_single_sector(self):
        with self.device() as separation:
            state = self.create()
        self.assertEqual(state['state'], 'complete')
        self.assertEqual(state['source']['sector_size'], SECTOR)
        self.assertTrue(state['source']['device'])
        self.assertEqual(state['verification'], {'status': 'verified', 'checked': len(self.data)})
        self.assertEqual(state['unreadable_bytes'], 0)
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertIn((len(self.data) - SECTOR, SECTOR), self.reads)
        separation.assert_called_once_with(str(self.source), str(self.root))

    def test_pause_resume_preserves_checkpoint_and_finishes_full_verification(self):
        with self.device() as separation:
            paused = self.pause()
            resumed = self.create(resume=True)
        self.assertEqual(resumed['state'], 'complete')
        self.assertEqual(resumed['first'], paused['first'])
        self.assertEqual(resumed['verification']['status'], 'verified')
        self.assertEqual(resumed['verification']['checked'], len(self.data))
        self.assertEqual(resumed['bad_ranges'], [])
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(separation.call_count, 2)

    def test_changed_checkpoint_bytes_refuse_resume_without_overwriting_them(self):
        with self.device():
            self.pause()
            damaged = bytearray(self.target.read_bytes())
            damaged[SECTOR + 17] ^= 0xff
            self.target.write_bytes(damaged)
            with self.assertRaises(imaging.ImagingError):
                self.create(resume=True)
        self.assertEqual(self.target.read_bytes(), damaged)

    def test_changed_sector_geometry_refuses_resume_before_opening_source(self):
        with self.device():
            self.pause()
            previous = self.target.read_bytes()
            opened = len(self.handles)
            with patch.object(imaging, 'physical_sector_size', return_value=512):
                with self.assertRaises(imaging.ImagingError):
                    self.create(resume=True)
            self.assertEqual(len(self.handles), opened)
        self.assertEqual(self.target.read_bytes(), previous)

    def test_full_verification_detects_middle_damage_outside_resume_checkpoints(self):
        with self.device():
            self.create()
            damaged = bytearray(self.target.read_bytes())
            damaged[16 * SECTOR + 11] ^= 0xff
            self.target.write_bytes(damaged)
            with self.assertRaises(imaging.ImagingError):
                self.create(resume=True)
        self.assertEqual(self.target.read_bytes(), damaged)
        state = json.loads(Path(imaging.sidecar_path(self.target)).read_text(encoding='utf-8'))
        self.assertEqual(state['state'], 'integrity_failed')
        self.assertEqual(state['verification']['status'], 'failed')

    def test_invalid_source_size_and_block_alignment_create_no_output(self):
        for size, block in [(len(self.data) - 1, BLOCK),
                            (len(self.data), BLOCK + 512)]:
            with self.subTest(size=size, block=block), self.device():
                with patch.object(imaging, 'source_size', return_value=size):
                    with self.assertRaises(imaging.ImagingError):
                        self.create(block_size=block)
            self.assertFalse(self.target.exists())
            self.assertFalse(Path(imaging.sidecar_path(self.target)).exists())
            self.assertFalse(self.handles)


if __name__ == '__main__':
    unittest.main()
