"""FAT short-name case flags must not be confused with long-name records."""
import io
from pathlib import Path
import tempfile
import unittest
from recoverydesk.explorer import SearchCriteria, search_entries
from recoverydesk.filesystems import FAT32, scan_tree
from recoverydesk.session_store import load_session, save_session
from test_filesystems import fat_img, fat_short


def deleted_name_image(name, *, bad_checksum=False, missing_tail=False):
    raw = bytearray(fat_img())
    short = bytearray(fat_short('REPORT~1TXT', 0x20, 3, 5))
    checksum = 0
    for byte in short[:11]:
        checksum = (((checksum >> 1) | ((checksum & 1) << 7)) + byte) & 0xFF
    short[0] = 0xE5
    encoded = name.encode('utf-16le') + b'\0\0'
    fragments = [encoded[i:i+26].ljust(26, b'\xff') for i in range(0, len(encoded), 26)]
    records = []
    for fragment in reversed(fragments):
        record = bytearray(32)
        record[0] = 0xE5
        record[11] = 0x0F
        record[13] = checksum ^ int(bad_checksum and not records)
        record[1:11], record[14:26], record[28:32] = fragment[:10], fragment[10:22], fragment[22:]
        records.append(record)
    if missing_tail:
        records.pop(0)
    directory = b''.join(records) + short + bytes(32)
    raw[48*512:48*512+len(directory)] = directory
    raw[32*512+12:32*512+16] = bytes(4)  # The original data cluster is free.
    return bytes(raw)


class Fat32NameCaseTests(unittest.TestCase):
    def test_deleted_hint_is_searchable_and_survives_a_saved_session(self):
        name = 'Grüner Bericht 2026.txt'
        raw = deleted_name_image(name)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'fat32.img'
            session = Path(temporary) / 'name.tenshi-session'
            source.write_bytes(raw)
            index = scan_tree(str(source))
            entry, = index.list_dir(index.root)
            self.assertEqual(entry.name, '?EPORT~1.TXT')
            self.assertEqual(entry.possible_original_name, name)
            self.assertEqual(search_entries([entry], SearchCriteria(name='grüner*2026.txt')), [entry])
            self.assertEqual(search_entries([entry], SearchCriteria(name='EPORT~1')), [entry])
            save_session(str(session), str(source), index=index)
            restored = load_session(str(session)).index
            self.assertEqual(restored.list_dir(restored.root)[0].possible_original_name, name)
            self.assertEqual(source.read_bytes(), raw)

    def test_ambiguous_and_invalid_fragments_keep_only_the_short_name(self):
        for raw in (deleted_name_image('Grüner Bericht 2026.txt', bad_checksum=True),
                    deleted_name_image('Grüner Bericht 2026.txt', missing_tail=True),
                    deleted_name_image('Grüner/Bericht 2026.txt')):
            stream = io.BytesIO(raw)
            volume = FAT32(stream, 0)
            row, = volume.list_directory(stream, (2,))
            self.assertEqual(row[0], '?EPORT~1.TXT')
            self.assertIsNone(row[-1])

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
