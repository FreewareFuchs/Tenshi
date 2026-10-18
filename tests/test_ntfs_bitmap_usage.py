"""NTFS $Bitmap coverage uses entirely synthetic images; no disk is modified."""
from __future__ import annotations

import os
import struct
import tempfile
import unittest
from pathlib import Path

from recoverydesk.ntfs_usage import inspect_ntfs_bitmap, BitmapUnavailable
from recoverydesk.partition_health import inspect_partition
from recoverydesk.partition_scan import Partition

RECORD_BYTES = 1024
SECTOR = 512
MFT_START_CLUSTER = 4


def _align8(n):
    return (n + 7) & ~7


def _data_attr(runlist, real_size, last_vcn):
    buf = bytearray(_align8(64 + len(runlist)))
    struct.pack_into('<II', buf, 0, 0x80, len(buf))
    buf[8] = 1
    struct.pack_into('<QQ', buf, 16, 0, last_vcn)
    struct.pack_into('<H', buf, 32, 64)
    struct.pack_into('<QQQ', buf, 40, (last_vcn+1)*SECTOR, real_size, real_size)
    buf[64:64+len(runlist)] = runlist
    return buf


def _record(attr, in_use=True):
    buf = bytearray(RECORD_BYTES)
    buf[:4] = b'FILE'
    struct.pack_into('<HH', buf, 4, 0x30, 3)
    struct.pack_into('<HH', buf, 20, 0x38, int(in_use))
    buf[0x38:0x38+len(attr)] = attr
    struct.pack_into('<I', buf, 0x38+len(attr), 0xFFFFFFFF)
    buf[0x30:0x32] = b'\xaa\xbb'
    for i in range(1, 3):
        pos = i * SECTOR - 2
        buf[0x30+2*i:0x32+2*i] = buf[pos:pos+2]
        buf[pos:pos+2] = b'\xaa\xbb'
    return buf


def make_volume(*, cluster_count=512, used_clusters=100, bitmap_size=None,
                broken_record=False, corrupt_run=False, missing_bitmap=False, wrong_name=False):
    size = cluster_count * SECTOR
    raw = bytearray(size)
    boot = bytearray(SECTOR)
    boot[3:11] = b'NTFS    '
    struct.pack_into('<H', boot, 11, SECTOR)
    boot[13] = 1
    struct.pack_into('<Q', boot, 40, cluster_count)
    struct.pack_into('<Q', boot, 48, MFT_START_CLUSTER)
    struct.pack_into('<b', boot, 64, -10)
    boot[510:512] = b'\x55\xaa'
    raw[0:SECTOR] = boot
    mft_data = _data_attr(b'\x11\x10\x04\x00', 16*SECTOR, 15)
    rec0 = _record(mft_data)
    raw[4*SECTOR:4*SECTOR+RECORD_BYTES] = rec0
    if not missing_bitmap:
        bitmap_bytes = (cluster_count + 7) // 8
        bitmap = bytearray(bitmap_bytes)
        for i in range(used_clusters):
            bitmap[i//8] |= (1 << (i % 8))
        if cluster_count % 8:
            bitmap[-1] |= ((0xFF << (cluster_count % 8)) & 0xFF)
        run = b'\x11\x01\x64\x00' if not corrupt_run else b'\x01\x01\x00'
        bitmap_data = _data_attr(run, bitmap_bytes if bitmap_size is None else bitmap_size, 0)
        filename = '$NotBitmap' if wrong_name else '$Bitmap'
        filename_payload = bytearray(66 + 2 * len(filename))
        filename_payload[64] = len(filename)
        filename_payload[65] = 1
        filename_payload[66:] = filename.encode('utf-16le')
        filename_attr = bytearray(_align8(24 + len(filename_payload)))
        struct.pack_into('<II', filename_attr, 0, 0x30, len(filename_attr))
        struct.pack_into('<I', filename_attr, 16, len(filename_payload))
        struct.pack_into('<H', filename_attr, 20, 24)
        filename_attr[24:24+len(filename_payload)] = filename_payload
        rec6 = _record(filename_attr + bitmap_data)
        if broken_record:
            rec6[SECTOR-2] = 0
        raw[(4+12)*SECTOR:(4+12)*SECTOR+RECORD_BYTES] = rec6
        raw[100*SECTOR:100*SECTOR+bitmap_bytes] = bitmap
    return bytes(raw)


class BitmapUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'volume.raw'

    def _inspect(self, *, volume=None):
        volume = volume if volume is not None else make_volume()
        self.source.write_bytes(volume)
        before = self.source.read_bytes()
        p = Partition(1, 'Volume', 0, len(volume)//512, '0x07', filesystem='NTFS')
        d = inspect_partition(str(self.source), p)
        self.assertEqual(self.source.read_bytes(), before, 'Die Quelle wurde verändert.')
        return d

    def test_bitmap_usage_exact_clusters(self):
        d = self._inspect()
        self.assertEqual(d.volume_bytes, 512*512)
        self.assertEqual(d.used_bytes, 100*512)
        self.assertEqual(d.free_bytes, 412*512)
        self.assertAlmostEqual(d.used_percent, 100*100/512)
        self.assertIn('$Bitmap', d.usage_basis)

    def test_padding_bits_not_counted(self):
        d = self._inspect(volume=make_volume(cluster_count=509, used_clusters=7))
        self.assertEqual(d.used_bytes, 7*SECTOR)
        self.assertEqual(d.free_bytes, 502*SECTOR)

    def test_missing_bitmap_remains_unknown(self):
        d = self._inspect(volume=make_volume(missing_bitmap=True))
        self.assertIsNone(d.used_percent)
        self.assertTrue(any('Bitmap' in msg for msg in d.notes))

    def test_corrupt_record_unavailable_not_guess(self):
        d = self._inspect(volume=make_volume(broken_record=True))
        self.assertIsNone(d.used_bytes)
        self.assertIsNone(d.free_bytes)

    def test_short_bitmap_unavailable(self):
        d = self._inspect(volume=make_volume(bitmap_size=8))
        self.assertIsNone(d.used_percent)

    def test_bad_runlist_unavailable(self):
        d = self._inspect(volume=make_volume(corrupt_run=True))
        self.assertIsNone(d.used_percent)

    def test_wrong_bitmap_filename_not_misinterpreted(self):
        d = self._inspect(volume=make_volume(wrong_name=True))
        self.assertIsNone(d.used_bytes)
        self.assertIn('unbekannt', ' '.join(d.notes))

    def test_tight_scan_limit_yields_unknown(self):
        self.source.write_bytes(make_volume())
        with open(self.source, 'rb') as f, self.assertRaises(BitmapUnavailable):
            inspect_ntfs_bitmap(f, 0, max_bitmap_bytes=8)


class ExfatFlagsTests(unittest.TestCase):
    def test_dirty_and_media_failure_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = bytearray(2*1024*1024)
            raw[3:11] = b'EXFAT   '
            raw[108], raw[109] = 9, 3
            raw[112] = 0xFF
            struct.pack_into('<H', raw, 106, 0x0006)
            struct.pack_into('<Q', raw, 72, 4096)
            struct.pack_into('<I', raw, 92, 256)
            raw[510:512] = b'\x55\xaa'
            path = Path(tmp)/'exfat.raw'
            path.write_bytes(raw)
            part = Partition(1,'Volume',0,4096,'exFAT',filesystem='exFAT')
            d = inspect_partition(str(path), part)
            self.assertTrue(any('VolumeDirty' in w for w in d.warnings))
            self.assertTrue(any('MediaFailure' in w for w in d.warnings))


class UsageBarTests(unittest.TestCase):
    def test_graphic_updates_and_resets(self):
        from recoverydesk.gui import RecoveryDeskApp
        from recoverydesk.partition_health import PartitionDetails
        app = RecoveryDeskApp()
        app.geometry('1024x650')
        app.update()
        try:
            self.assertEqual(len(app.tabs.tabs()), 2)
            self.assertTrue(app.usage_canvas.winfo_exists())
            self.assertTrue(app.usage_canvas.winfo_ismapped())
            self.assertGreaterEqual(app.usage_canvas.winfo_width(), 200)
            self.assertLess(app.usage_canvas.winfo_rooty() + app.usage_canvas.winfo_height(),
                            app.winfo_rooty() + app.winfo_height())
            details = PartitionDetails('NTFS', 0, 262144, volume_bytes=262144,
                                       used_bytes=131072, free_bytes=131072)
            app._draw_usage_bar(details)
            self.assertIn('50.0 %', app.usage_caption.get())
            self.assertGreaterEqual(len(app.usage_canvas.find_all()), 2)
            app._reset_analysis_for_source()
            self.assertIn('unbekannt', app.usage_caption.get())
        finally:
            app.destroy()


if __name__ == '__main__':
    unittest.main()
