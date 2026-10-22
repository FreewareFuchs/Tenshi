"""Linux port regression tests (no physical disk is opened)."""
import os
import unittest
from unittest import mock

from recoverydesk import sources
from recoverydesk import linux_devices


class LinuxDeviceTests(unittest.TestCase):
    def test_windows_path_is_not_linux_device(self):
        self.assertFalse(linux_devices.block_path(r'\\.\PhysicalDrive0'))

    def test_image_is_not_device(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=False):
            self.assertFalse(sources.is_device_source('/tmp/example.img'))

    def test_destination_unverifiable_fails_closed(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices, '_backing_disks', side_effect=ValueError('unknown')), \
             mock.patch.object(os, 'stat') as fake_stat:
            fake_stat.return_value.st_rdev = os.makedev(8, 0)
            with self.assertRaises(ValueError):
                linux_devices.ensure_separate_device('/dev/sda', '/tmp/tenshi-test.img')

    def test_same_physical_disk_is_rejected(self):
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices, '_backing_disks', return_value={'/sys/devices/mock-disk'}), \
             mock.patch.object(os, 'stat') as fake_stat:
            fake_stat.return_value.st_rdev = os.makedev(8, 0)
            fake_stat.return_value.st_dev = os.makedev(8, 1)
            with self.assertRaisesRegex(ValueError, 'demselben'):
                linux_devices.ensure_separate_device('/dev/sda', '/tmp/tenshi-test.img')

    def test_windows_import_still_available(self):
        self.assertTrue(hasattr(sources, 'open_source'))


if __name__ == '__main__':
    unittest.main()
