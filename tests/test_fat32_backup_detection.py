import struct
import tempfile
import unittest
from pathlib import Path
from recoverydesk.partition_scan import analyze_image

class FAT32BackupTests(unittest.TestCase):
    def scan(self, table=True, backup_sector=6, different=False):
        raw = bytearray(4*1024*1024)
        start = 2048*512
        boot = bytearray(512)
        boot[:3] = b'\xeb\x58\x90'
        struct.pack_into('<H', boot, 11, 512)
        boot[13] = 1
        struct.pack_into('<HB', boot, 14, 32, 2)
        struct.pack_into('<I', boot, 32, 4096)
        struct.pack_into('<I', boot, 36, 32)
        struct.pack_into('<I', boot, 44, 2)
        struct.pack_into('<H', boot, 50, backup_sector)
        boot[82:90] = b'FAT32   '
        boot[510:] = b'\x55\xaa'
        if table:
            raw[450] = 0x0c
            struct.pack_into('<II', raw, 454, 2048, 4096)
            raw[510:512] = b'\x55\xaa'
        raw[start:start+512] = boot
        if different:
            struct.pack_into('<I', boot, 67, 12345)
        raw[start+6*512:start+7*512] = boot
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fat.img'
            path.write_bytes(raw)
            return analyze_image(str(path))
    def test_mbr_backup_not_offered(self):
        self.assertEqual([p.offset_bytes for p in self.scan().partitions], [1048576])
    def test_heuristic_primary_also_suppresses_backup(self):
        self.assertEqual([p.offset_bytes for p in self.scan(table=False).partitions], [1048576])
    def test_different_bpb_is_not_suppressed(self):
        self.assertEqual(len(self.scan(different=True).partitions), 2)
    def test_disabled_backup_field_does_not_hide_candidate(self):
        self.assertEqual(len(self.scan(backup_sector=0).partitions), 2)
