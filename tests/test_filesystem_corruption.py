"""Bounded malformed-metadata regressions using synthetic bytes, never raw devices."""
import io
import struct
import unittest

from recoverydesk.filesystems import FAT32, ExFAT, FileSystemError
from recoverydesk.ntfs import (NTFSError, parse_boot_sector, parse_runlist,
                              apply_update_sequence, attributes)
from test_fat32_active_fat import active_fat_image
from test_exfat_active_fat import dual_fat_image
from test_ntfs import make_image, file_record, resident_attr, nonresident_attr


class BudgetReader(io.BytesIO):
    """Fail immediately on excessive I/O, instead of waiting for a hung CI job."""
    def __init__(self, raw, reads=24):
        super().__init__(raw)
        self.remaining_reads = reads

    def read(self, size=-1):
        if not 0 <= size <= 1024 * 1024:
            raise AssertionError(f'Unexpected read size: {size}')
        self.remaining_reads -= 1
        if self.remaining_reads < 0:
            raise AssertionError('Corrupt metadata exhausted the read budget')
        return super().read(size)


class CorruptFatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fat = bytes(active_fat_image())
        cls.exfat = bytes(dual_fat_image())

    def fixtures(self):
        return ((FAT32, self.fat, (32 + 524) * 512, 0x0FFFFFF7, 0x0FFFFFFF),
                (ExFAT, self.exfat, 26 * 512, 0xFFFFFFF7, 0xFFFFFFFF))

    def test_self_and_two_cluster_cycles_stop_within_read_budget(self):
        for kind, original, table, _, _ in self.fixtures():
            for links in (((3, 3),), ((3, 6), (6, 3))):
                with self.subTest(fs=kind.__name__, links=links):
                    raw = bytearray(original)
                    for cluster, following in links:
                        struct.pack_into('<I', raw, table + cluster * 4, following)
                    stream = BudgetReader(raw)
                    volume = kind(stream, 0)
                    with self.assertRaises(FileSystemError):
                        list(volume.clusters(stream, 3))
                    self.assertEqual(stream.getvalue(), raw)

    def test_free_reserved_bad_and_out_of_volume_pointers_rejected(self):
        for kind, original, table, bad, _ in self.fixtures():
            for following in (0, 1, bad, 1000000):
                with self.subTest(fs=kind.__name__, following=following):
                    raw = bytearray(original)
                    struct.pack_into('<I', raw, table + 3 * 4, following)
                    stream = BudgetReader(raw)
                    volume = kind(stream, 0)
                    with self.assertRaises(FileSystemError):
                        list(volume.clusters(stream, 3))

    def test_directory_cycles_without_end_marker_stop(self):
        for kind, original, table, _, _ in self.fixtures():
            with self.subTest(fs=kind.__name__):
                raw = bytearray(original)
                struct.pack_into('<I', raw, table + 2 * 4, 2)
                stream = BudgetReader(raw)
                volume = kind(stream, 0)
                locator = (2,) if kind is FAT32 else (2, False, None)
                with self.assertRaises(FileSystemError):
                    volume.list_directory(stream, locator)

    def test_truncated_boot_and_fat_entry_raise_domain_errors(self):
        for kind, original, table, _, _ in self.fixtures():
            with self.subTest(fs=kind.__name__, location='boot'):
                with self.assertRaises(FileSystemError):
                    kind(BudgetReader(original[:511]), 0)
            with self.subTest(fs=kind.__name__, location='FAT'):
                stream = BudgetReader(original[:table + 3 * 4 + 2])
                volume = kind(stream, 0)
                with self.assertRaises(FileSystemError):
                    list(volume.clusters(stream, 3))

    def test_truncated_data_and_early_chain_end_do_not_return_complete_file(self):
        for kind, original, table, _, end in self.fixtures():
            for truncated in (False, True):
                with self.subTest(fs=kind.__name__, truncated=truncated):
                    raw = bytearray(original)
                    stream = BudgetReader(raw)
                    volume = kind(stream, 0)
                    if truncated:
                        stream = BudgetReader(raw[:volume.cluster_offset(3) + 17])
                    else:
                        struct.pack_into('<I', raw, table + 3 * 4, end)
                        stream = BudgetReader(raw)
                    iterator = (volume._bytes(stream, 3, 1024) if kind is FAT32
                                else volume._bytes(stream, 3, 1024, False))
                    with self.assertRaises(FileSystemError):
                        b''.join(iterator)


class CorruptNtfsTests(unittest.TestCase):
    def test_truncated_boot_and_mft_outside_volume(self):
        raw = bytearray(make_image())
        with self.assertRaises(NTFSError):
            parse_boot_sector(BudgetReader(raw[:511]))
        struct.pack_into('<Q', raw, 48, 2**63)
        with self.assertRaises(NTFSError):
            parse_boot_sector(BudgetReader(raw))

    def test_invalid_runlist_widths_truncation_and_volume_bounds(self):
        cases = (b'', b'\x11', b'\x11\x01', b'\x11\x01\x02',
                 b'\x10\x01\x00', b'\x91\x01' + bytes(9),
                 b'\x11\x00\x01\x00', b'\x11\x01\xff\x00',
                 b'\x21\x01\xff\x7f\x00')
        for raw in cases:
            with self.subTest(runlist=raw), self.assertRaises(NTFSError):
                parse_runlist(raw, 512)
        # Valid signed deltas remain supported: LCN 40, then LCN 20.
        runs = parse_runlist(b'\x11\x01\x28\x11\x01\xec\x00', 512)
        self.assertEqual([run.lcn for run in runs], [40, 20])

    def test_torn_records_and_invalid_attribute_lengths(self):
        raw = file_record([resident_attr(0x80, b'original')])
        for length in (0, 47, 511, 1023):
            with self.subTest(length=length), self.assertRaises(NTFSError):
                apply_update_sequence(raw[:length], 512)
        for length in (0, 8, 23, 2**32 - 1):
            damaged = bytearray(raw)
            struct.pack_into('<I', damaged, 0x38 + 4, length)
            with self.subTest(attribute_length=length), self.assertRaises(NTFSError):
                list(attributes(damaged))

    def test_nonresident_runlist_offsets_cannot_escape_record(self):
        raw = file_record([nonresident_attr(0x80, b'\x11\x01\x28\x00', 512, 0)])
        for offset in (0, 24, 63, 65535):
            damaged = bytearray(raw)
            struct.pack_into('<H', damaged, 0x38 + 32, offset)
            with self.subTest(offset=offset), self.assertRaises(NTFSError):
                list(attributes(damaged))
