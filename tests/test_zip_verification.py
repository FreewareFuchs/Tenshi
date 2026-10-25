"""Real ZIP streams: CRC, limits, cancellation and no extraction/source writes."""
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from recoverydesk.zip_verification import verify_zip


class ZipVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'export.zip'

    def make_zip(self, compression=zipfile.ZIP_STORED):
        with zipfile.ZipFile(self.path, 'w', compression=compression) as archive:
            archive.writestr('nested/', b'')
            archive.writestr('nested/Grüne.txt', 'Referenz\n'.encode())
            archive.writestr('../not-extracted.bin', b'UNIQUE_PAYLOAD_FOR_CRC' + bytes(range(256)) * 1000)
        return self.path.read_bytes()

    def test_valid_archives_crc_and_content_are_read_without_extraction(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA):
            with self.subTest(compression=compression):
                before = self.make_zip(compression)
                result = verify_zip(self.path)
                self.assertEqual(result.status, 'passed', result)
                self.assertEqual(result.files, 2)
                self.assertGreater(result.checked_bytes, 256000)
                self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(), hashlib.sha256(before).digest())
                self.assertEqual(list(self.root.iterdir()), [self.path])
        with zipfile.ZipFile(self.path, 'w'):
            pass
        result = verify_zip(self.path)
        self.assertEqual((result.status, result.files, result.checked_bytes), ('passed', 0, 0))

    def test_crc_corruption_and_truncation_never_pass(self):
        valid = self.make_zip()
        corrupted = valid.replace(b'UNIQUE_PAYLOAD_FOR_CRC', b'WRONG__PAYLOAD_FOR_CRC', 1)
        self.assertEqual(len(corrupted), len(valid))
        for payload in (corrupted, valid[:-30], b'not a zip'):
            self.path.write_bytes(payload)
            self.assertEqual(verify_zip(self.path).status, 'failed')
            self.assertEqual(self.path.read_bytes(), payload)

    def test_limits_and_cancellation_are_not_success(self):
        before = self.make_zip()
        for options in ({'max_archive_bytes': len(before)-1}, {'max_expanded_bytes': 10}, {'max_members': 2}):
            with self.subTest(options=options):
                self.assertEqual(verify_zip(self.path, **options).status, 'incomplete')
        self.assertEqual(verify_zip(self.path, cancel=lambda: True).status, 'cancelled')
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            return calls > 6
        self.assertEqual(verify_zip(self.path, cancel=cancel).status, 'cancelled')
        self.assertEqual(self.path.read_bytes(), before)

    def test_encryption_and_unsupported_methods_are_not_corruption_claims(self):
        valid = self.make_zip()
        for encrypted in (False, True):
            raw = bytearray(valid)
            local = raw.index(b'PK\x03\x04')
            central = raw.index(b'PK\x01\x02')
            if encrypted:
                struct.pack_into('<H', raw, local+6, 1)
                struct.pack_into('<H', raw, central+8, 1)
            else:
                struct.pack_into('<H', raw, local+8, 99)
                struct.pack_into('<H', raw, central+10, 99)
            self.path.write_bytes(raw)
            self.assertEqual(verify_zip(self.path).status, 'incomplete')

    def test_changed_file_or_missing_input_is_not_confirmed(self):
        self.make_zip()
        before = self.path.stat()
        calls = 0
        def change_metadata():
            nonlocal calls
            calls += 1
            if calls == 2:
                os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
            return False
        result = verify_zip(self.path, cancel=change_metadata)
        self.assertEqual(result.status, 'incomplete')
        self.assertIn('geändert', result.message)
        self.assertEqual(verify_zip(self.root / 'missing.zip').status, 'incomplete')
