"""Metadata-only diagnostics from synthetic RAW partitions (no personal data)."""
from __future__ import annotations
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recoverydesk.partition_health import inspect_partition, format_partition_details
from recoverydesk.partition_scan import Partition


class PartitionHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'probe.raw'
        self.data = bytearray(2 * 1024 * 1024)
        self.off = 512 * 64

    def probe(self, fs, part_bytes=1024*1024):
        self.path.write_bytes(self.data)
        p = Partition(1, 'MBR', self.off//512, part_bytes//512, '0x83', filesystem=fs)
        before = self.path.read_bytes()
        details = inspect_partition(str(self.path), p)
        self.assertEqual(self.path.read_bytes(), before, 'Diagnose darf kein RAW-Image schreiben')
        return p, details

    def test_fat32_fsinfo_free_clusters(self):
        b = self.data
        start = self.off
        b[start:start+3] = b'\xeb\x58\x90'
        b[start+82:start+90] = b'FAT32   '
        struct.pack_into('<H', b, start+11, 512)
        b[start+13] = 1
        struct.pack_into('<H', b, start+14, 32)
        b[start+16] = 2
        struct.pack_into('<I', b, start+36, 32)
        struct.pack_into('<I', b, start+32, 2048)
        struct.pack_into('<H', b, start+48, 1)
        b[start+510:start+512] = b'\x55\xaa'
        at = start+512
        struct.pack_into('<I',b,at,0x41615252)
        struct.pack_into('<I',b,at+484,0x61417272)
        struct.pack_into('<I',b,at+488,200)
        struct.pack_into('<I',b,at+508,0xAA550000)
        p,d = self.probe('FAT32')
        self.assertEqual(d.free_bytes, 200*512)
        self.assertGreater(d.used_bytes,0)
        self.assertIn('FSInfo', d.usage_basis)
        self.assertEqual(d.status, 'Keine offensichtlichen Fehler')
        self.assertIn('Originalquelle nicht verändert',format_partition_details(p,d,str(self.path)))

    def test_fat32_corrupt_fsinfo_is_not_used(self):
        self.data[self.off+82:self.off+90] = b'FAT32   '
        struct.pack_into('<H', self.data, self.off+11, 512)
        self.data[self.off+13] = 1
        struct.pack_into('<H',self.data,self.off+14,32)
        self.data[self.off+16] = 2
        struct.pack_into('<I',self.data,self.off+36,32)
        struct.pack_into('<I',self.data,self.off+32,2048)
        struct.pack_into('<H',self.data,self.off+48,1)
        self.data[self.off+510:self.off+512] = b'\x55\xaa'
        p,d = self.probe('FAT32')
        self.assertIsNone(d.used_bytes)
        self.assertTrue(any('FSInfo' in x for x in d.warnings))

    def test_exfat_percentage_is_not_full_volume_usage(self):
        b = self.data
        start = self.off
        b[start+3:start+11] = b'EXFAT   '
        b[start+108], b[start+109] = 9, 3
        b[start+112] = 75
        struct.pack_into('<Q',b,start+72,2048)
        struct.pack_into('<I',b,start+92,100)
        b[start+510:start+512] = b'\x55\xaa'
        p,d = self.probe('exFAT')
        self.assertEqual(d.used_bytes, 75*100*4096//100)
        self.assertAlmostEqual(d.used_percent, 75.0)
        self.assertIn('Clusterbereich',d.usage_basis)
        self.data[start+112] = 0xFF
        _, d2 = self.probe('exFAT')
        self.assertIsNone(d2.used_percent)

    def test_ext4_dirty_and_error_flag(self):
        b = self.data
        start = self.off+1024
        struct.pack_into('<H',b,start+56,0xEF53)
        struct.pack_into('<I',b,start+4,512)
        struct.pack_into('<I',b,start+12,128)
        struct.pack_into('<I',b,start+24,2)
        struct.pack_into('<H',b,start+58,0x2)
        _,d = self.probe('ext4',2*1024*1024)
        self.assertEqual(d.used_bytes,(512-128)*4096)
        self.assertEqual(d.status,'Auffällig')
        self.assertTrue(any('Dateisystemfehler' in w for w in d.warnings))

    def test_btrfs_multidevice_warning(self):
        start=self.off+65536
        b=self.data
        b[start+0x40:start+0x48] = b'_BHRfS_M'
        struct.pack_into('<Q',b,start+0x70,1024*1024)
        struct.pack_into('<Q',b,start+0x78,256*1024)
        struct.pack_into('<Q',b,start+0x88,2)
        _,d = self.probe('Btrfs')
        self.assertEqual(d.used_percent,25.0)
        self.assertTrue(any('Mehrgeräte' in w for w in d.warnings))

    def test_xfs_usage_is_reported_as_metadata(self):
        b=self.data
        start=self.off
        b[start:start+4]=b'XFSB'
        struct.pack_into('>I',b,start+4,4096)
        struct.pack_into('>Q',b,start+8,256)
        struct.pack_into('>Q',b,start+144,64)
        _,d = self.probe('XFS')
        self.assertEqual(d.used_percent,75.0)
        self.assertIn('fdblocks',d.usage_basis)

    def test_ntfs_no_invented_free_space(self):
        b=self.data
        start=self.off
        b[start+3:start+11]=b'NTFS    '
        struct.pack_into('<H',b,start+11,512)
        b[start+13]=8
        struct.pack_into('<Q',b,start+40,2048)
        b[start+510:start+512]=b'\x55\xaa'
        _,d = self.probe('NTFS')
        self.assertIsNone(d.free_bytes)
        self.assertIsNone(d.used_percent)
        self.assertIn('Bitmap', ' '.join(d.notes))

    def test_invalid_partition_offset_returns_warning(self):
        self.path.write_bytes(bytes(512))
        p = Partition(1,'MBR',12345,200,'0x07',filesystem='NTFS')
        d = inspect_partition(str(self.path),p)
        self.assertEqual(d.status,'Auffällig')


class PartitionHealthGuiTests(unittest.TestCase):
    def test_two_tabs_and_diagnostic_column(self):
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        app.withdraw()
        try:
            self.assertEqual(len(app.tabs.tabs()),2)
            self.assertIn('usage', app.part_tree['columns'])
            self.assertIn('health', app.part_tree['columns'])
            self.assertTrue(app.detail_btn.winfo_exists())
            app.partition_details[0]='stale'
            app._reset_analysis_for_source()
            self.assertEqual(app.partition_details,{})
        finally:
            app.destroy()


if __name__ == '__main__':
    unittest.main()

class PartitionReportGuiTests(unittest.TestCase):
    def test_partition_report_no_overwrite_and_source_change(self):
        from recoverydesk.gui import RecoveryDeskApp
        from recoverydesk.partition_health import PartitionDetails
        app = RecoveryDeskApp()
        app.withdraw()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp)/'disk.raw'
                target = Path(tmp)/'diagnose.txt'
                source.write_bytes(bytes(1024*1024))
                part = Partition(1,'MBR',0,2048,'0x83', filesystem='ext4')
                app.source_path.set(str(source))
                app.partitions = [part]
                app.partition_source = str(source)
                app.part_tree.insert('', 'end',iid='0',values=(1,'MBR',0,'1 GiB','ext4','—','Nicht geprüft',512,'0x83',''))
                app.part_tree.selection_set('0')
                app.partition_details[0] = PartitionDetails('ext4',0,1024*1024,status='Keine offensichtlichen Fehler')
                with patch('recoverydesk.gui.filedialog.asksaveasfilename', return_value=str(target)), \
                     patch('recoverydesk.gui.messagebox.showinfo'), \
                     patch('recoverydesk.gui.messagebox.showerror') as err:
                    app.save_partition_details()
                    self.assertTrue(target.exists())
                    self.assertIn('schreibgeschützter Partitionsbericht',target.read_text(encoding='utf-8'))
                    app.save_partition_details()
                    err.assert_called_once()
                app._reset_analysis_for_source()
                self.assertEqual(app.partition_details,{})
                self.assertFalse(app.part_tree.get_children())
        finally:
            app.destroy()
