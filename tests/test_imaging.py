"""Tests for safe new-image imaging, interruption/resume, bad sector map."""
import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.imaging import (create_image, sidecar_path, ImagingError,
                                  _recover_read, describe_bad_ranges)


class BadSectorFile:
    def __init__(self, data, damaged_start, damaged_end):
        self.data = data
        self.position = 0
        self.a, self.b = damaged_start, damaged_end
        self.requests = []

    def seek(self, position):
        self.position = position

    def read(self, size):
        start = self.position
        self.requests.append((start, size))
        if start < self.b and start + size > self.a:
            raise OSError(errno.EIO, 'Simulierter Lesefehler')
        self.position += size
        return self.data[start:start+size]


class ImagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source.raw'
        self.dst = self.root / 'copy.img'
        self.data = bytes((i * 7 + 11) % 256 for i in range(3 * 1024 * 1024 + 321))
        self.src.write_bytes(self.data)

    def test_image_copy_exact_and_metadata(self):
        events = []
        state = create_image(str(self.src), str(self.dst), progress=events.append)
        self.assertEqual(self.dst.read_bytes(), self.data)
        self.assertEqual(self.src.read_bytes(), self.data)
        self.assertEqual(state['state'], 'complete')
        self.assertEqual(state['unreadable_bytes'], 0)
        self.assertTrue(os.path.isfile(sidecar_path(self.dst)))
        self.assertEqual(events[-1].processed, len(self.data))
        self.assertEqual(events[-1].total, len(self.data))
        self.assertIn('Nicht lesbare Bytes', describe_bad_ranges(state))

    def test_existing_destination_is_never_overwritten(self):
        self.dst.write_bytes(b'NOT MY DATA')
        with self.assertRaises(ImagingError):
            create_image(str(self.src), str(self.dst))
        self.assertEqual(self.dst.read_bytes(), b'NOT MY DATA')

    def test_no_imaging_to_same_file(self):
        with self.assertRaises(ImagingError):
            create_image(str(self.src), str(self.src))
        self.assertEqual(self.src.read_bytes(), self.data)

    def test_pause_then_resume_with_manifest(self):
        cancel = [False]
        def after_block(e):
            if e.processed >= 1024 * 1024:
                cancel[0] = True
        first = create_image(str(self.src), str(self.dst),
                             cancel=lambda: cancel[0], progress=after_block)
        self.assertEqual(first['state'], 'paused')
        self.assertEqual(first['processed'], 1024 * 1024)
        self.assertEqual(self.dst.stat().st_size, 1024 * 1024)
        second = create_image(str(self.src), str(self.dst), resume=True)
        self.assertEqual(second['state'], 'complete')
        self.assertEqual(self.dst.read_bytes(), self.data)

    def test_resume_rejects_changed_source_without_touching_destination(self):
        cancel = [False]
        create_image(str(self.src), str(self.dst), cancel=lambda: cancel[0],
                     progress=lambda e: cancel.__setitem__(0, e.processed >= 1024 * 1024))
        before = self.dst.read_bytes()
        self.src.write_bytes(self.data[:-1] + b'X')
        with self.assertRaises(ImagingError):
            create_image(str(self.src), str(self.dst), resume=True)
        self.assertEqual(self.dst.read_bytes(), before)

    def test_resume_rejects_tampered_image(self):
        canceled = [False]
        create_image(str(self.src), str(self.dst), cancel=lambda: canceled[0],
                     progress=lambda e: canceled.__setitem__(0, e.processed >= 1024 * 1024))
        with open(self.dst, 'r+b') as f:
            f.seek(200)
            f.write(b'TAMPERED')
        before = self.dst.read_bytes()
        with self.assertRaises(ImagingError):
            create_image(str(self.src), str(self.dst), resume=True)
        self.assertEqual(self.dst.read_bytes(), before)

    def test_resume_rejects_bad_manifest(self):
        self.dst.write_bytes(b'existing')
        Path(sidecar_path(self.dst)).write_text('{"format": 1}', encoding='utf-8')
        with self.assertRaises(ImagingError):
            create_image(str(self.src), str(self.dst), resume=True)
        self.assertEqual(self.dst.read_bytes(), b'existing')

    def test_resume_after_early_interrupted_uncommitted_tail(self):
        canceled = [False]
        create_image(str(self.src), str(self.dst), cancel=lambda: canceled[0],
                     progress=lambda e: canceled.__setitem__(0, e.processed >= 1024 * 1024))
        with open(self.dst, 'ab') as f:
            f.write(b'UNCOMMITTED' * 100)
        self.assertEqual(create_image(str(self.src), str(self.dst), resume=True)['state'], 'complete')
        self.assertEqual(self.dst.read_bytes(), self.data)

    def test_bad_sector_split_and_ranges(self):
        data = bytes([0x77]) * 8192 + bytes([0x33]) * 4096 + bytes([0x66]) * 8192
        f = BadSectorFile(data, 8192, 12288)
        errors = []
        result = _recover_read(f, 0, len(data), 4096, errors)
        self.assertEqual(result, data[:8192] + bytes(4096) + data[12288:])
        self.assertEqual(errors, [[8192, 4096]])
        self.assertTrue(all(start % 4096 == 0 for start, count in f.requests))

    def test_bad_sector_integration(self):
        from contextlib import contextmanager
        data = self.data
        bad = BadSectorFile(data, 4096, 8192)
        @contextmanager
        def fake_reader(source):
            yield bad
        with patch('recoverydesk.imaging.open_source', fake_reader):
            result = create_image(str(self.src), str(self.dst), block_size=1024 * 1024)
        expected = self.data[:4096] + bytes(4096) + self.data[8192:]
        self.assertEqual(self.dst.read_bytes(), expected)
        self.assertEqual(result['unreadable_bytes'], 4096)
        self.assertEqual(result['bad_ranges'], [[4096, 4096]])

    def test_different_block_sizes(self):
        result = create_image(str(self.src), str(self.dst), block_size=4 * 1024 * 1024)
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(self.dst.read_bytes(), self.data)

    def test_reject_symlink_destination(self):
        if not hasattr(os, 'symlink'):
            self.skipTest('Symlink unavailable')
        try:
            os.symlink(self.src, self.dst)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        with self.assertRaises(ImagingError):
            create_image(str(self.src), str(self.dst))
        self.assertEqual(self.src.read_bytes(), self.data)

    def test_gui_still_two_tabs_and_accent_button(self):
        import inspect
        from recoverydesk.gui import RecoveryDeskApp
        source = inspect.getsource(RecoveryDeskApp)
        self.assertIn('text="Image erstellen / fortsetzen"', source)
        self.assertIn("bg=self._palette()['accent']", source)
        self.assertIn('self.tabs.add(self.partition_tab, text="Partitionen")', source)
        self.assertIn('self.tabs.add(self.ntfs_tab, text="Dateien & Ordner")', source)
        self.assertNotIn('text="Signatursuche"', source)

if __name__ == '__main__':
    unittest.main()

class ShortWriteTests(unittest.TestCase):
    def test_partial_writes_are_retried(self):
        from recoverydesk.imaging import _write_all
        class ShortWriter:
            def __init__(self): self.buf = bytearray()
            def write(self, data):
                n = min(len(data), 3)
                self.buf.extend(data[:n])
                return n
        writer = ShortWriter()
        _write_all(writer, b'1234567890')
        self.assertEqual(writer.buf, b'1234567890')

    def test_zero_write_is_rejected(self):
        from recoverydesk.imaging import _write_all
        class FullDisk:
            def write(self, data): return 0
        with self.assertRaises(ImagingError):
            _write_all(FullDisk(), b'a')

class DeviceDestinationSafetyTests(unittest.TestCase):
    def test_raw_device_destinations_are_rejected_before_open(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'src.img'
            src.write_bytes(bytes(8192))
            for bad in [r'\\.\PhysicalDrive0', r'\\?\PhysicalDrive0',
                        '//./PhysicalDrive0', 'NUL', 'CON.img', 'COM1.bin']:
                with self.subTest(bad=bad):
                    with self.assertRaises(ImagingError):
                        create_image(str(src), bad)
