"""Synthetic, non-sensitive RAW images for sector sizes, tables and search."""
from __future__ import annotations
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from recoverydesk.partition_scan import analyze_image, scan_partitions


def ntfs_vbr(bps=512, sectors=4096, mft_lcn=4):
    raw = bytearray(512)
    raw[:3] = b"\xeb\x52\x90"
    raw[3:11] = b"NTFS    "
    struct.pack_into("<H", raw, 11, bps)
    raw[13] = 8 if bps == 512 else 1
    struct.pack_into("<Q", raw, 40, sectors)
    struct.pack_into("<Q", raw, 48, mft_lcn)
    raw[64] = 0xf6  # -10: 1024 bytes per FILE record
    raw[510:512] = b"\x55\xaa"
    return bytes(raw)


def write_mbr(img: bytearray, start=2048, size=4096, typ=0x07):
    img[446+4] = typ
    struct.pack_into("<II", img, 446+8, start, size)
    img[510:512] = b"\x55\xaa"


def write_gpt(raw: bytearray, ss=512, bad_primary=False):
    length = len(raw) // ss
    entries = bytearray(128 * 128)
    entries[:16] = bytes(range(1, 17))
    struct.pack_into("<QQ", entries, 32, 40, 600)
    entries[56:56+len("Data".encode("utf-16le"))] = "Data".encode("utf-16le")
    entries_crc = zlib.crc32(entries)
    def header(lba, other, table_lba):
        h = bytearray(ss)
        h[:8] = b"EFI PART"
        struct.pack_into("<I", h, 8, 0x00010000)
        struct.pack_into("<I", h, 12, 92)
        struct.pack_into("<QQQQ", h, 24, lba, other, 34, length-34)
        struct.pack_into("<Q", h, 72, table_lba)
        struct.pack_into("<III", h, 80, 128, 128, entries_crc)
        struct.pack_into("<I", h, 16, zlib.crc32(h[:92]))
        return h
    first_table_lba = 2
    backup_table_lba = length - 1 - len(entries)//ss
    raw[first_table_lba*ss:first_table_lba*ss+len(entries)] = entries
    raw[backup_table_lba*ss:backup_table_lba*ss+len(entries)] = entries
    primary = header(1, length-1, first_table_lba)
    if bad_primary:
        primary[16] ^= 0xff
    raw[ss:2*ss] = primary
    raw[(length-1)*ss:length*ss] = header(length-1, 1, backup_table_lba)
    # protective MBR
    write_mbr(raw, 1, min(length-1, 0xffffffff), 0xee)
    raw[40*ss:40*ss+512] = ntfs_vbr(bps=ss, sectors=500)


def exfat_vbr():
    raw = bytearray(512)
    raw[:3] = b"\xeb\x76\x90"
    raw[3:11] = b"EXFAT   "
    struct.pack_into("<Q", raw, 72, 1200)
    struct.pack_into("<IIIII", raw, 80, 24, 8, 32, 100, 2)
    raw[108] = 9
    raw[109] = 3
    raw[510:512] = b"\x55\xaa"
    return bytes(raw)


class RAWPartitionTests(unittest.TestCase):
    def _temp_image(self, data: bytes, deep=False, mb=0):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"image.raw"
            path.write_bytes(data)
            return analyze_image(str(path), deep_scan=deep, max_scan_mb=mb)

    def test_ntfs_raw_volume_without_partition_table(self):
        image = bytearray(2 * 1024 * 1024)
        image[:512] = ntfs_vbr()
        report = self._temp_image(image)
        self.assertEqual(report.table_type, "keine")
        self.assertEqual(len(report.partitions), 1)
        p = report.partitions[0]
        self.assertEqual((p.scheme, p.offset_bytes, p.filesystem), ("Volume", 0, "NTFS"))
        self.assertIn("Kandidaten", " ".join(report.warnings))

    def test_mbr_and_ntfs_partition(self):
        image = bytearray(4 * 1024 * 1024)
        write_mbr(image, start=2048, size=4096)
        image[2048*512:2048*512+512] = ntfs_vbr()
        report = self._temp_image(image)
        self.assertEqual(report.table_type, "MBR")
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].filesystem, "NTFS")
        self.assertEqual(report.partitions[0].offset_bytes, 1024*1024)

    def test_4kn_primary_gpt(self):
        image = bytearray(4 * 1024 * 1024)
        write_gpt(image, ss=4096)
        report = self._temp_image(image)
        self.assertEqual(report.table_type, "GPT")
        self.assertEqual(report.sector_size, 4096)
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].offset_bytes, 40*4096)
        self.assertEqual(report.partitions[0].filesystem, "NTFS")

    def test_gpt_backup_when_primary_missing(self):
        image = bytearray(4 * 1024 * 1024)
        write_gpt(image)
        image[512:1024] = bytes(512)
        report = self._temp_image(image)
        self.assertEqual(report.table_type, "GPT")
        self.assertEqual(report.partitions[0].scheme, "GPT Backup")

    def test_backup_preferred_over_bad_primary_crc(self):
        image = bytearray(4 * 1024 * 1024)
        write_gpt(image, bad_primary=True)
        report = self._temp_image(image)
        self.assertEqual(report.partitions[0].scheme, "GPT Backup")
        self.assertIn("CRC", " ".join(report.warnings))

    def test_ntfs_found_by_deep_search_beyond_64mb(self):
        # Sparse file avoids holding 70+ MiB in RAM.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"disk.raw"
            pos = 68 * 1024 * 1024
            with path.open("wb") as f:
                f.truncate(pos + 4 * 1024 * 1024)
            with path.open("r+b") as f:
                f.seek(pos)
                f.write(ntfs_vbr())
            quick = analyze_image(str(path))
            self.assertFalse(quick.partitions)
            deep = analyze_image(str(path), deep_scan=True, max_scan_mb=0)
            self.assertEqual(len(deep.partitions), 1)
            self.assertEqual(deep.partitions[0].offset_bytes, pos)
            self.assertEqual(deep.partitions[0].filesystem, "NTFS")

    def test_exfat_vbr_found(self):
        image = bytearray(2 * 1024 * 1024)
        image[512*64:512*64+512] = exfat_vbr()
        report = self._temp_image(image)
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].filesystem, "exFAT")

    def test_string_ntfs_alone_is_not_valid_partition(self):
        image = bytearray(2 * 1024 * 1024)
        image[512*100+3:512*100+11] = b"NTFS    "
        report = self._temp_image(image)
        self.assertEqual(report.partitions, [])

    def test_invalid_sector_size_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"x.raw"
            path.write_bytes(bytes(512))
            with self.assertRaises(ValueError):
                analyze_image(str(path), sector_size=1024)


if __name__ == "__main__":
    unittest.main()

# Additional scenarios tested by unittest discovery; integration tests above use
# a full synthetic, non-personal RAW disk image.
class MBRLayoutTests(unittest.TestCase):
    def test_mbr_with_4096_byte_logical_sectors(self):
        image = bytearray(8 * 1024 * 1024)
        write_mbr(image, start=256, size=1024)
        image[256*4096:256*4096+512] = ntfs_vbr(bps=4096, sectors=1024)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"4096.raw"
            path.write_bytes(image)
            report = analyze_image(str(path))
        self.assertEqual(report.table_type, "MBR")
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].sector_size, 4096)
        self.assertEqual(report.partitions[0].offset_bytes, 1048576)
        self.assertEqual(report.partitions[0].filesystem, "NTFS")

    def test_ebr_logical_partition(self):
        image = bytearray(4 * 1024 * 1024)
        write_mbr(image, start=64, size=512, typ=0x0f)
        # first EBR at LBA 64, contains a logical partition at 64+1
        ebr = bytearray(512)
        ebr[446+4] = 0x07
        struct.pack_into("<II", ebr, 446+8, 1, 300)
        ebr[510:512] = b"\x55\xaa"
        image[64*512:65*512] = ebr
        image[65*512:66*512] = ntfs_vbr()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"logical.raw"
            path.write_bytes(image)
            report = analyze_image(str(path))
        self.assertEqual(report.table_type, "MBR")
        self.assertEqual(len(report.partitions), 1)
        self.assertEqual(report.partitions[0].scheme, "MBR logisch")
        self.assertEqual(report.partitions[0].offset_bytes, 65*512)

    def test_ntfs_backup_sector_not_double_counted(self):
        image = bytearray(4 * 1024 * 1024)
        volume_sectors = 2048
        image[0:512] = ntfs_vbr(sectors=volume_sectors)
        image[(volume_sectors-1)*512:volume_sectors*512] = ntfs_vbr(sectors=volume_sectors)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"volume.raw"
            path.write_bytes(image)
            report = analyze_image(str(path))
        self.assertEqual(len(report.partitions), 1)

class OtherVolumeTests(unittest.TestCase):
    def test_fat32_volume_image(self):
        boot = bytearray(512)
        boot[:3] = b'\xeb\x58\x90'
        boot[82:90] = b'FAT32   '
        struct.pack_into('<H', boot, 11, 512)
        boot[13] = 8
        struct.pack_into('<HB', boot, 14, 32, 2)
        struct.pack_into('<I', boot, 32, 8192)
        struct.pack_into('<I', boot, 36, 64)
        struct.pack_into('<I', boot, 44, 2)
        boot[510:512] = b'\x55\xaa'
        raw = bytearray(4 * 1024 * 1024)
        raw[:512] = boot
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'fat32.raw'
            p.write_bytes(raw)
            result = analyze_image(str(p))
        self.assertEqual(len(result.partitions), 1)
        self.assertEqual(result.partitions[0].filesystem, 'FAT32')
