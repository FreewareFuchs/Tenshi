"""Post-imaging integrity verification without opening physical devices."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from recoverydesk import imaging


class FullImagingVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.src = Path(self.temp.name) / 'source.raw'
        self.dest = Path(self.temp.name) / 'output.img'
        self.payload = (bytes(range(256)) * (4 * 4096)) + b'footer'
        self.src.write_bytes(self.payload)

    def _state(self):
        return json.loads(Path(imaging.sidecar_path(str(self.dest))).read_text(encoding='utf-8'))

    def test_regular_image_auto_verified_after_full_reread(self):
        states = []
        result = imaging.create_image(str(self.src), str(self.dest),
                                      progress=lambda progress: states.append(progress.state))
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(result['verification'], {'status': 'verified',
                                                   'checked': len(self.payload)})
        self.assertEqual(self._state()['verification']['status'], 'verified')
        self.assertIn('verifying', states)
        self.assertEqual(states[-1], 'complete')
        self.assertEqual(self.dest.read_bytes(), self.payload)

    def test_wrong_interior_byte_before_verification_is_detected_and_persisted(self):
        corrupt_offset = 300_002
        open_verified = imaging.open_regular_input

        @contextmanager
        def injected_corruption(path, source):
            # The source is never touched, only disposable test output.
            with open(path, 'r+b') as target:
                target.seek(corrupt_offset)
                target.write(b'X')
            with open_verified(path, source) as reader:
                yield reader

        with mock.patch.object(imaging, 'open_regular_input',
                               side_effect=injected_corruption):
            with self.assertRaisesRegex(imaging.ImagingError, 'INTEGRITÄTSFEHLER.*Byteoffset'):
                imaging.create_image(str(self.src), str(self.dest))
        state = self._state()
        self.assertEqual(state['state'], 'integrity_failed')
        self.assertEqual(state['verification']['status'], 'failed')
        self.assertNotEqual(self.dest.read_bytes(), self.payload)
        self.assertEqual(self.src.read_bytes(), self.payload)

    def test_resume_already_complete_rechecks_unsampled_interior_corruption(self):
        imaging.create_image(str(self.src), str(self.dest), block_size=65536)
        # First and last checkpoint digests remain valid. An interior
        # modification would have passed the old checkpoint-only test.
        at = 200_002
        with self.dest.open('r+b') as image:
            image.seek(at)
            image.write(b'X')
        with self.assertRaisesRegex(imaging.ImagingError, 'INTEGRITÄTSFEHLER'):
            imaging.create_image(str(self.src), str(self.dest), resume=True)
        self.assertEqual(self._state()['state'], 'integrity_failed')
        self.assertEqual(self.src.read_bytes(), self.payload)

    def test_cancel_verification_persists_pause_and_resume_reverifies(self):
        cancel = [False]
        def progress(item):
            if item.state == 'verifying':
                cancel[0] = True
        before = imaging.create_image(str(self.src), str(self.dest),
                                      progress=progress, cancel=lambda: cancel[0])
        self.assertEqual(before['state'], 'paused')
        self.assertEqual(before['processed'], len(self.payload))
        self.assertEqual(before['verification']['status'], 'interrupted')
        after = imaging.create_image(str(self.src), str(self.dest), resume=True)
        self.assertEqual(after['state'], 'complete')
        self.assertEqual(after['verification']['status'], 'verified')
        self.assertEqual(self.dest.read_bytes(), self.payload)

    def test_explicit_opt_out_records_unverified(self):
        result = imaging.create_image(str(self.src), str(self.dest), verify=False)
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(result['verification']['status'], 'not_requested')
        self.assertEqual(self.dest.read_bytes(), self.payload)

    def test_physical_device_like_source_does_not_auto_reread(self):
        # Models the control flow of a physical source using a regular
        # temporary file; no /dev device is opened.
        # Real block devices have a size divisible by the logical sector;
        # the general fixture intentionally has a 6-byte trailing footer.
        aligned_payload = self.payload + bytes((-len(self.payload)) % 512)
        self.src.write_bytes(aligned_payload)
        source = str(self.src)
        with mock.patch.object(imaging, 'is_device_source',
                               side_effect=lambda path: str(path) == source), \
             mock.patch.object(imaging, 'physical_sector_size', return_value=512), \
             mock.patch.object(imaging, 'ensure_safe_destination') as guard, \
             mock.patch.object(imaging, '_verify_full_copy',
                               side_effect=AssertionError('unexpected extra physical read')):
            result = imaging.create_image(source, str(self.dest), block_size=65536)
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(result['verification']['status'], 'not_requested')
        guard.assert_called_once()
        self.assertEqual(self.dest.read_bytes(), aligned_payload)


if __name__ == '__main__':
    unittest.main()
