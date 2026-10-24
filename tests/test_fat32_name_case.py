"""FAT short-name case flags must not be confused with long-name records."""
import io
import unittest
from recoverydesk.filesystems import FAT32
from test_filesystems import fat_img


class Fat32NameCaseTests(unittest.TestCase):
    def test_base_and_extension_case_bits_are_independent(self):
        for flags, expected in ((0, 'README.TXT'), (8, 'readme.TXT'),
                                (16, 'README.txt'), (24, 'readme.txt')):
            with self.subTest(flags=flags):
                raw = bytearray(fat_img())
                raw[48 * 512 + 32 + 12] = flags
                stream = io.BytesIO(raw)
                volume = FAT32(stream, 0)
                rows = volume.list_directory(stream, (2,))
                self.assertEqual(rows[1][0], expected)
                self.assertEqual(stream.getvalue(), raw)
