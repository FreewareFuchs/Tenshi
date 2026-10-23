"""Linux port regression tests (no physical disk is opened)."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from recoverydesk import sources
from recoverydesk import linux_devices

REAL_STAT = os.stat


class LinuxDeviceTests(unittest.TestCase):
    def test_windows_path_is_not_linux_device(self):
        self.assertFalse(linux_devices.block_path(r'\\.\PhysicalDrive0'))

    def test_image_is_not_device(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=False):
            self.assertFalse(sources.is_device_source('/tmp/example.img'))

    def test_destination_unverifiable_fails_closed(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices, '_backing_disks', side_effect=ValueError('unknown')), \
             mock.patch.object(linux_devices.os, 'stat', side_effect=lambda path, *a, **k: (SimpleNamespace(st_rdev=2048, st_dev=2049) if str(path) == '/dev/sda' else REAL_STAT(path, *a, **k))):
            with self.assertRaises(ValueError):
                linux_devices.ensure_separate_device('/dev/sda', '/tmp/tenshi-test.img')

    def test_same_physical_disk_is_rejected(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices, '_backing_disks', return_value={'/sys/devices/mock-disk'}), \
             mock.patch.object(linux_devices.os, 'stat', side_effect=lambda path, *a, **k: (SimpleNamespace(st_rdev=2048, st_dev=2049) if str(path) == '/dev/sda' else REAL_STAT(path, *a, **k))):
            with self.assertRaisesRegex(ValueError, 'demselben'):
                linux_devices.ensure_separate_device('/dev/sda', '/tmp/tenshi-test.img')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux-specific fcntl/ioctl test')
    def test_linux_block_info_permission_denial_is_actionable(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices.os, 'open',
                               side_effect=PermissionError(13, 'Permission denied')) as opened:
            with self.assertRaises(PermissionError) as caught:
                linux_devices.block_info('/dev/fake-test-device')
        self.assertIn('Linux-Blockgerät', str(caught.exception))
        self.assertIn('Geräteberechtigungen', str(caught.exception))
        self.assertNotIn('Windows', str(caught.exception))
        opened.assert_called_once()
        self.assertEqual(opened.call_args.args[1] & os.O_ACCMODE, os.O_RDONLY)

    def test_windows_import_still_available(self):
        self.assertTrue(hasattr(sources, 'open_source'))


if __name__ == '__main__':
    unittest.main()
