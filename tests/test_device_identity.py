"""Simulated replacement at the same path; never access physical hardware."""
from contextlib import contextmanager
import copy
import hashlib
import io
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from recoverydesk import device_identity as device
from recoverydesk.batch_export import export_batch
from recoverydesk.filesystems import scan_tree
from test_filesystems import fat_img


class DeviceIdentityTests(unittest.TestCase):
    def test_windows_serial_is_bounded_hashed_and_query_is_read_only(self):
        raw = bytearray(64)
        struct.pack_into('<I', raw, 4, len(raw))
        struct.pack_into('<I', raw, 24, 40)
        raw[40:47] = b'SERIAL\0'
        with patch.object(device, '_device_ioctl', return_value=bytes(raw)) as ioctl:
            self.assertEqual(device.windows_serial('device'), hashlib.sha256(b'SERIAL').hexdigest())
            ioctl.assert_called_once_with('device', 0x002D1400, 4096, bytes(12))
        for malformed in (b'', bytes(36), bytes(raw[:43]), bytes(raw[:24])):
            with self.subTest(raw=malformed), patch.object(device, '_device_ioctl', return_value=malformed):
                self.assertIsNone(device.windows_serial('device'))
        with patch.object(device, '_device_ioctl', side_effect=OSError('unsupported')):
            self.assertIsNone(device.windows_serial('device'))

    @unittest.skipUnless(hasattr(os, 'major'), 'Linux device numbers required')
    def test_linux_disk_sequence_detects_replug_even_with_same_serial(self):
        with tempfile.TemporaryDirectory() as temporary:
            node = Path(temporary)
            (node / 'device').mkdir()
            (node / 'device' / 'serial').write_text('same serial')
            (node / 'diskseq').write_text('42')
            real_stat = os.stat
            def stat(path, *args, **kwargs):
                return SimpleNamespace(st_rdev=2048) if path == '/dev/mock' else real_stat(path, *args, **kwargs)
            with patch.object(device.os, 'stat', side_effect=stat), \
                    patch.object(device, 'Path', return_value=node):
                before = device.linux_identity('/dev/mock')
                (node / 'diskseq').write_text('43')
                after = device.linux_identity('/dev/mock')
            self.assertNotEqual(before, after)
            self.assertEqual(before['device/serial'], after['device/serial'])
            self.assertNotIn('same serial', str(before))

    def test_stable_volume_id_ignores_live_allocation_counters(self):
        boot = bytearray(512)
        boot[3:11] = b'EXFAT   '
        boot[510:512] = b'\x55\xaa'
        boot[100:104] = b'ABCD'
        before = device._volume_id(boot)
        boot[106:108] = b'\x01\x00'
        boot[112] = 73
        self.assertEqual(device._volume_id(boot), before)
        boot[100:104] = b'EFGH'
        self.assertNotEqual(device._volume_id(boot), before)

    def test_capture_is_bounded_and_compares_offset_identity(self):
        boot = bytearray(512)
        boot[3:11] = b'NTFS    '
        boot[510:512] = b'\x55\xaa'
        boot[72:80] = b'abcdefgh'
        stream = io.BytesIO(bytes(512) + boot)
        @contextmanager
        def opened(_):
            yield stream
        with patch.object(device, 'is_device_source', return_value=True), \
                patch.object(device, 'source_size', return_value=1024), \
                patch.object(device, 'physical_sector_size', return_value=512), \
                patch.object(device, 'open_source', side_effect=opened), \
                patch.object(device, 'windows_serial', return_value=None):
            snapshot = device.capture_device_identity('mock', 512)
        self.assertEqual(snapshot['volume_ids'], [[0, None], [512, 'NTFS:6162636465666768']])
        for actual in (None, dict(snapshot, size=2048), dict(snapshot, volume_ids=[])):
            with patch.object(device, 'capture_device_identity', return_value=actual):
                with self.assertRaises(device.DeviceSourceChanged):
                    device.check_device_identity('mock', snapshot)
        with patch.object(device, 'capture_device_identity', side_effect=OSError('disconnected')):
            with self.assertRaises(device.DeviceSourceChanged):
                device.check_device_identity('mock', snapshot)
        with patch.object(device, 'capture_device_identity', return_value=copy.deepcopy(snapshot)):
            device.check_device_identity('mock', snapshot)

    def test_image_sources_do_not_gain_device_queries(self):
        with patch.object(device, 'is_device_source', return_value=False), \
                patch.object(device, 'open_source') as opened:
            self.assertIsNone(device.capture_device_identity('image'))
            opened.assert_not_called()

    def test_replacement_between_scan_and_batch_refuses_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.img'
            source.write_bytes(fat_img())
            index = scan_tree(str(source))
            selected = [e for e in index.entries if e.name == 'README.TXT']
            index._device_identity = {'offset': 0, 'serial': 'first'}
            target = root / 'out'
            target.mkdir()
            with patch('recoverydesk.batch_export.is_device_source', return_value=True), \
                    patch('recoverydesk.batch_export.capture_device_identity', return_value={'offset': 0, 'serial': 'second'}):
                with self.assertRaises(device.DeviceSourceChanged):
                    export_batch(str(source), index, selected, str(target))
            self.assertEqual(list(target.iterdir()), [])

    def test_geometry_or_missing_path_after_scan_reports_source_loss(self):
        from recoverydesk import batch_export
        index = SimpleNamespace(_device_identity={'offset': 0, 'serial': 'known'})
        for failure in (OSError('Nicht unterstützte Datenträgergeometrie.'),
                        ValueError('Die Quelle muss eine vorhandene RAW-Image-Datei sein.')):
            with self.subTest(failure=str(failure)), \
                    patch.object(batch_export, 'source_size', side_effect=failure):
                with self.assertRaisesRegex(device.DeviceSourceChanged, 'Quelle nicht mehr erreichbar') as caught:
                    batch_export._identity('missing-source', index)
                self.assertIs(caught.exception.__cause__, failure)
        unbound = SimpleNamespace()
        with patch.object(batch_export, 'source_size', side_effect=OSError('Nicht unterstützte Datenträgergeometrie.')):
            with self.assertRaisesRegex(OSError, 'Nicht unterstützte Datenträgergeometrie') as caught:
                batch_export._identity('new-source', unbound)
            self.assertNotIsInstance(caught.exception, device.DeviceSourceChanged)

    def test_failure_during_snapshot_capture_is_normalized(self):
        from recoverydesk import batch_export
        index = SimpleNamespace(_device_identity={'offset': 0, 'serial': 'known'})
        with patch.object(batch_export, 'source_size', return_value=1024), \
                patch.object(batch_export, 'is_device_source', return_value=True), \
                patch.object(batch_export, 'capture_device_identity', side_effect=OSError('geometry lost')):
            with self.assertRaisesRegex(device.DeviceSourceChanged, 'Quelle nicht mehr erreichbar'):
                batch_export._identity('device', index)

    def test_replacement_during_write_removes_partial_and_retry_then_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.img'
            original = fat_img()
            source.write_bytes(original)
            index = scan_tree(str(source))
            selected = [e for e in index.entries if e.name == 'README.TXT']
            snapshot = {'offset': 0, 'serial': 'first'}
            index._device_identity = snapshot
            target = root / 'out'
            target.mkdir()
            clock = [0.]
            with patch('recoverydesk.batch_export.is_device_source', return_value=True), \
                    patch('recoverydesk.batch_export.capture_device_identity', return_value=snapshot), \
                    patch('recoverydesk.batch_export.time.monotonic', side_effect=lambda: clock[0]), \
                    patch('recoverydesk.export_io.CHUNK_SIZE', 2), \
                    patch('recoverydesk.batch_export.check_device_identity', side_effect=device.DeviceSourceChanged('replaced')):
                def first_block(_):
                    clock[0] = 1.
                failed = export_batch(str(source), index, selected, str(target), byte_progress=first_block)
            self.assertEqual(failed.failed, 1)
            self.assertEqual(failed.exported, 0)
            self.assertFalse((Path(failed.root) / 'files' / 'README.TXT').exists())
            with patch('recoverydesk.batch_export.is_device_source', return_value=True), \
                    patch('recoverydesk.batch_export.capture_device_identity', return_value=snapshot), \
                    patch('recoverydesk.batch_export.check_device_identity'):
                retried = export_batch(str(source), index, selected, str(target))
                self.assertEqual(retried.exported, 1, retried.errors)
                self.assertEqual((Path(retried.root) / 'files' / 'README.TXT').read_bytes(), b'HELLO')
                resumed = export_batch(str(source), index, selected, str(target))
                self.assertEqual(resumed.verified_existing, 1, resumed.errors)
            self.assertEqual(source.read_bytes(), original)
