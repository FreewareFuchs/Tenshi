"""Regression tests for Windows Access Denied on .recovery.json replacement."""
import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.imaging import create_image, sidecar_path, journal_path, ImagingError, _read_journal


class WindowsCheckpointAccessDeniedTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.source = Path(self.d.name) / 'input.raw'
        self.target = Path(self.d.name) / 'image.img'
        self.data = bytes(range(256)) * (16384 + 256)
        self.source.write_bytes(self.data)

    @staticmethod
    def locked_replace(*args):
        raise PermissionError(errno.EACCES, 'Access denied')

    def test_fallback_journal_produces_complete_byte_exact_image(self):
        with patch('recoverydesk.imaging.os.replace', side_effect=self.locked_replace), \
             patch('recoverydesk.imaging.time.sleep'):
            state = create_image(str(self.source), str(self.target))
        self.assertEqual(state['state'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)
        side = Path(sidecar_path(str(self.target)))
        self.assertTrue(side.is_file())
        self.assertTrue(Path(journal_path(str(side))).is_file())
        self.assertEqual(json.loads(side.read_text())['processed'], 0)
        latest, _ = _read_journal(journal_path(str(side)))
        self.assertEqual(latest['processed'], len(self.data))

    def test_paused_journal_resume_preserves_image_and_checkpoint(self):
        canceled = [False]
        def progress(p):
            if p.processed >= 1024 * 1024:
                canceled[0] = True
        with patch('recoverydesk.imaging.os.replace', side_effect=self.locked_replace), \
             patch('recoverydesk.imaging.time.sleep'):
            state = create_image(str(self.source), str(self.target),
                                 cancel=lambda: canceled[0], progress=progress)
        self.assertEqual(state['state'], 'paused')
        resumed = create_image(str(self.source), str(self.target), resume=True)
        self.assertEqual(resumed['state'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_truncated_journal_tail_is_discarded_on_resume(self):
        canceled = [False]
        with patch('recoverydesk.imaging.os.replace', side_effect=self.locked_replace), \
             patch('recoverydesk.imaging.time.sleep'):
            create_image(str(self.source), str(self.target),
                cancel=lambda: canceled[0], progress=lambda p: canceled.__setitem__(0, p.processed >= 1024*1024))
        j = Path(journal_path(sidecar_path(str(self.target))))
        with j.open('ab') as f:
            f.write(b'{"checkpoint":{')
        complete = create_image(str(self.source), str(self.target), resume=True)
        self.assertEqual(complete['state'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertTrue(j.read_bytes().endswith(b'\n'))
        final, _ = _read_journal(str(j))
        self.assertEqual(final['state'], 'complete')
        self.assertEqual(final['verification']['status'], 'verified')

    def test_tampered_committed_journal_record_rejected(self):
        canceled = [False]
        with patch('recoverydesk.imaging.os.replace', side_effect=self.locked_replace), \
             patch('recoverydesk.imaging.time.sleep'):
            create_image(str(self.source), str(self.target),
                cancel=lambda: canceled[0], progress=lambda p: canceled.__setitem__(0, p.processed >= 1024*1024))
        j = Path(journal_path(sidecar_path(str(self.target))))
        data = j.read_bytes().replace(b'"processed":1048576', b'"processed":1048575')
        self.assertNotEqual(j.read_bytes(), data)
        j.write_bytes(data)
        before = self.target.read_bytes()
        with self.assertRaises(ImagingError):
            create_image(str(self.source), str(self.target), resume=True)
        self.assertEqual(self.target.read_bytes(), before)

    def test_transient_access_denied_recovers_without_journal(self):
        import os
        normal_replace = os.replace
        failures = [0]
        def transient_replace(src, dst):
            if failures[0] < 2:
                failures[0] += 1
                raise PermissionError(errno.EACCES, 'temporarily locked')
            return normal_replace(src, dst)
        with patch('recoverydesk.imaging.os.replace', side_effect=transient_replace), \
             patch('recoverydesk.imaging.time.sleep'):
            result = create_image(str(self.source), str(self.target))
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertFalse(Path(journal_path(sidecar_path(str(self.target)))).exists())

    def test_fallback_cannot_write_journal_raises_actionable_error(self):
        def denied(*args, **kwargs):
            raise ImagingError('Windows verweigert das Schreiben der Imaging-Prüfpunkte.')
        with patch('recoverydesk.imaging.os.replace', side_effect=self.locked_replace), \
             patch('recoverydesk.imaging._append_journal', side_effect=denied), \
             patch('recoverydesk.imaging.time.sleep'):
            with self.assertRaisesRegex(ImagingError, 'Windows verweigert'):
                create_image(str(self.source), str(self.target))
        self.assertTrue(self.source.is_file())
        self.assertTrue(Path(sidecar_path(str(self.target))).is_file())

if __name__ == '__main__':
    unittest.main()
