"""Device access diagnostics use metadata only and preserve read-only failures."""
import errno
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from recoverydesk import linux_devices, sources
from recoverydesk.i18n import LANGUAGES, translate

REAL_STAT = os.stat


class DiagnosticMessageTests(unittest.TestCase):
    def test_message_preserves_error_type_and_device_in_all_languages(self):
        path = '/dev/disk/by-id/usb-Test_SSD-part1'
        details = {'path': path, 'model': 'TEST SSD', 'size_bytes': 128000000000, 'address': '8:1'}
        with patch.object(linux_devices, 'device_access_details', return_value=details):
            error = linux_devices.LinuxReadAccessError(path)
        self.assertIsInstance(error, PermissionError)
        self.assertEqual(error.errno, errno.EACCES)
        self.assertEqual(error.filename, path)
        for language in LANGUAGES:
            text = translate(str(error), language)
            for value in (path, 'TEST SSD', '128000000000', '8:1'):
                self.assertIn(value, text)
            if language != 'de':
                self.assertNotIn(linux_devices.ACCESS_HEADER, text)
                self.assertNotIn(linux_devices.ACCESS_HINT, text)
            self.assertIn('sudo', text)
        self.assertNotIn('chmod', str(error))
        self.assertNotIn('usermod', str(error))

    def test_unavailable_metadata_does_not_invent_model_or_size(self):
        with patch.object(linux_devices.os, 'stat', side_effect=FileNotFoundError):
            error = linux_devices.LinuxReadAccessError('/dev/disconnected-test')
        text = str(error)
        self.assertIn('/dev/disconnected-test', text)
        self.assertIn(linux_devices.ACCESS_ALTERNATIVE, text)
        self.assertNotIn('Modell:', text)
        self.assertNotIn('Gerätegröße (Bytes):', text)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux metadata/access integration')
class LinuxAccessIntegrationTests(unittest.TestCase):
    def test_partition_metadata_uses_parent_model_without_opening_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disk = root / 'devices/sda'
            partition = disk / 'sda1'
            partition.mkdir(parents=True)
            (partition / 'partition').write_text('1', encoding='ascii')
            (partition / 'size').write_text('1000', encoding='ascii')
            (disk / 'device').mkdir()
            (disk / 'device/model').write_text('TEST SSD\n' + 'x' * 300, encoding='ascii')
            sysfs = root / 'sysfs'
            sysfs.mkdir()
            (sysfs / '8:1').symlink_to(partition, target_is_directory=True)
            def metadata_stat(path, *args, **kwargs):
                if str(path) == '/dev/diagnostic-test':
                    return SimpleNamespace(st_mode=stat.S_IFBLK | 0o600, st_rdev=os.makedev(8, 1))
                return REAL_STAT(path, *args, **kwargs)
            with patch.object(linux_devices.os, 'stat', side_effect=metadata_stat), \
                 patch.object(linux_devices.os, 'open', side_effect=AssertionError('No device open')):
                details = linux_devices.device_access_details('/dev/diagnostic-test', sysfs_root=sysfs)
            self.assertEqual(details['address'], '8:1')
            self.assertEqual(details['size_bytes'], 512000)
            self.assertTrue(details['model'].startswith('TEST SSD '))
            self.assertLessEqual(len(details['model']), 256)
            self.assertNotIn('\n', details['model'])

    def test_both_read_paths_return_same_diagnostic_and_do_not_retry_writable(self):
        path = '/dev/diagnostic-test'
        with patch.object(linux_devices, 'device_access_details', return_value={'path': path}), \
             patch.object(linux_devices, 'block_path', return_value=True), \
             patch.object(linux_devices.os, 'open', side_effect=PermissionError(errno.EACCES, 'denied')) as opened:
            with self.assertRaises(linux_devices.LinuxReadAccessError) as info_error:
                linux_devices.block_info(path)
            opened.assert_called_once()
            self.assertEqual(opened.call_args.args[1] & os.O_ACCMODE, os.O_RDONLY)
        with patch.object(sources, 'validate_source', return_value=path), \
             patch.object(sources, 'is_device_source', return_value=True), \
             patch.object(linux_devices, 'device_access_details', return_value={'path': path}), \
             patch('builtins.open', side_effect=PermissionError(errno.EACCES, 'denied')) as opened, \
             patch.object(sources, 'log_issue'):
            with self.assertRaises(linux_devices.LinuxReadAccessError) as stream_error:
                with sources.open_source(path):
                    self.fail('Access denial must prevent entering the source context')
            opened.assert_called_once_with(path, 'rb', buffering=0)
        self.assertEqual(str(info_error.exception), str(stream_error.exception))


if __name__ == '__main__':
    unittest.main()
