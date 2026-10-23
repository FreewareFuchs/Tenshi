"""Wrong-sized sources must be rejected before reading original sample offsets."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from recoverydesk.session_store import fingerprint_image, check_fingerprint, SessionError

class ReplacementSizeTests(unittest.TestCase):
    def test_smaller_and_larger_replacements_report_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp)/'original.img'
            replacement = Path(tmp)/'replacement.img'
            original.write_bytes(bytes(2*1024*1024))
            saved = fingerprint_image(str(original))
            for size in (1024*1024, 3*1024*1024):
                replacement.write_bytes(bytes(size))
                with patch('recoverydesk.session_store.fingerprint_image') as reader:
                    with self.assertRaisesRegex(SessionError, 'Größe des Quell-Images'):
                        check_fingerprint(str(replacement), saved)
                    reader.assert_not_called()
    def test_same_size_wrong_contents_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp)/'original.img'
            replacement = Path(tmp)/'replacement.img'
            original.write_bytes(bytes(1024*1024))
            saved = fingerprint_image(str(original))
            replacement.write_bytes(b'X'+bytes(1024*1024-1))
            with self.assertRaisesRegex(SessionError, 'Inhaltsprüfung'):
                check_fingerprint(str(replacement), saved)
