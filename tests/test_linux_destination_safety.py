"""No-hardware regression tests for Linux source/destination safety.

All fake block devices use mocks. No test opens /dev/sd* or /dev/nvme*.
"""
from __future__ import annotations

import builtins
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from recoverydesk import batch_export, imaging, linux_devices, sources

_REAL_STAT = os.stat
_DEVICE = '/dev/sda'


def _stat_without_device_access(path, *args, **kwargs):
    if os.fspath(path) == _DEVICE:
        return SimpleNamespace(st_rdev=2048, st_dev=2048)
    return _REAL_STAT(path, *args, **kwargs)


class DestinationSeparationTests(unittest.TestCase):
    def _check(self, destination, source_roots, target_roots):
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices.os, 'stat', side_effect=_stat_without_device_access), \
             mock.patch.object(linux_devices, '_backing_disks',
                               side_effect=[source_roots, target_roots]) as resolve:
            linux_devices.ensure_separate_device(_DEVICE, destination)
            self.assertEqual(resolve.call_count, 2)

    def test_separate_physical_disk_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            self._check(os.path.join(folder, 'new-image.img'), {'diskA'}, {'diskB'})

    def test_same_physical_disk_is_rejected_even_for_other_partition(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'demselben physischen'):
                self._check(os.path.join(folder, 'target.img'), {'diskA'}, {'diskA'})

    def test_multidisk_overlap_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'demselben physischen'):
                self._check(os.path.join(folder, 'target.img'), {'diskA', 'diskB'},
                            {'diskB', 'diskC'})

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux block device policy')
    def test_block_device_destination_rejected_without_file_creation(self):
        with mock.patch.object(linux_devices, 'block_path',
                               side_effect=lambda p: p in (_DEVICE, '/dev/sda1')), \
             mock.patch.object(linux_devices, '_backing_disks',
                               side_effect=AssertionError('no raw disk topology needed')):
            with self.assertRaisesRegex(ValueError, 'niemals als Ausgabeziel'):
                linux_devices.ensure_separate_device(_DEVICE, '/dev/sda1')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux block device policy')
    def test_symlink_to_block_device_destination_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            alias = os.path.join(folder, 'image.img')
            os.symlink('/dev/sda1', alias)
            with mock.patch.object(linux_devices, 'block_path',
                                   side_effect=lambda p: p in (_DEVICE, '/dev/sda1')), \
                 mock.patch.object(linux_devices, '_backing_disks',
                                   side_effect=AssertionError('no raw disk topology needed')):
                with self.assertRaisesRegex(ValueError, 'niemals als Ausgabeziel'):
                    linux_devices.ensure_separate_device(_DEVICE, alias)
            self.assertTrue(os.path.islink(alias))

    def test_unresolved_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices.os, 'stat', side_effect=_stat_without_device_access), \
             mock.patch.object(linux_devices, '_backing_disks',
                               side_effect=ValueError('unknown mapping')):
            with self.assertRaisesRegex(ValueError, 'unknown mapping'):
                linux_devices.ensure_separate_device(_DEVICE, folder)

    def test_imaging_denied_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = os.path.join(folder, 'image.img')
            with mock.patch.object(imaging, 'validate_source', return_value=_DEVICE), \
                 mock.patch.object(imaging, 'is_device_source',
                                   side_effect=lambda path: path == _DEVICE), \
                 mock.patch.object(imaging, 'ensure_safe_destination',
                                   side_effect=ValueError('same physical disk')) as guard:
                with self.assertRaisesRegex(ValueError, 'same physical disk'):
                    imaging.create_image(_DEVICE, dest)
                guard.assert_called_once()
            self.assertFalse(os.path.lexists(dest))
            self.assertFalse(os.path.lexists(imaging.sidecar_path(dest)))

    def test_export_denied_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(batch_export, 'ensure_safe_destination',
                                   side_effect=ValueError('same physical disk')) as guard:
                with self.assertRaisesRegex(ValueError, 'same physical disk'):
                    batch_export.export_batch(_DEVICE, None, (), folder)
                guard.assert_called_once_with(_DEVICE, folder)
            self.assertEqual(list(Path(folder).iterdir()), [])



class SysfsTopologyTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux sysfs only')
    def test_partition_maps_to_same_physical_disk_as_whole_device(self):
        # Exercise the REAL ancestry resolver against a temporary fake sysfs.
        # No /dev device is opened or examined.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            block = root / 'sys' / 'dev' / 'block'
            disk = root / 'sys' / 'devices' / 'pci-test' / 'block' / 'sda'
            partition = disk / 'sda1'
            block.mkdir(parents=True)
            partition.mkdir(parents=True)
            (disk / 'device').mkdir()
            (partition / 'partition').write_text('1', encoding='ascii')
            (block / '8:0').symlink_to(disk, target_is_directory=True)
            (block / '8:1').symlink_to(partition, target_is_directory=True)
            original_path = Path
            with mock.patch.object(linux_devices, 'Path',
                  side_effect=lambda path: original_path(str(path).replace(
                      '/sys/dev/block', str(block), 1))):
                whole = linux_devices._backing_disks(os.makedev(8, 0))
                part = linux_devices._backing_disks(os.makedev(8, 1))
            self.assertEqual(whole, {str(disk.resolve())})
            self.assertEqual(whole, part)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux sysfs only')
    def test_virtual_device_without_physical_backing_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            block = root / 'sys' / 'dev' / 'block'
            virtual = root / 'sys' / 'devices' / 'virtual' / 'block' / 'loop0'
            block.mkdir(parents=True)
            virtual.mkdir(parents=True)
            (block / '7:0').symlink_to(virtual, target_is_directory=True)
            original_path = Path
            with mock.patch.object(linux_devices, 'Path',
                  side_effect=lambda path: original_path(str(path).replace(
                      '/sys/dev/block', str(block), 1))):
                with self.assertRaisesRegex(ValueError, 'Virtueller Datenträger'):
                    linux_devices._backing_disks(os.makedev(7, 0))

class ReadOnlyOpenTests(unittest.TestCase):
    def test_regular_raw_image_reader_cannot_write(self):
        with tempfile.TemporaryDirectory() as folder:
            image = os.path.join(folder, 'tiny.img')
            with open(image, 'wb') as output:
                output.write(b'original-bytes')
            with sources.open_source(image) as reader:
                self.assertFalse(reader.writable())
                self.assertEqual(reader.read(), b'original-bytes')
            with open(image, 'rb') as check:
                self.assertEqual(check.read(), b'original-bytes')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux ioctl only')
    def test_linux_block_metadata_uses_readonly_flags(self):
        import fcntl
        import struct
        with mock.patch.object(linux_devices, 'block_path', return_value=True), \
             mock.patch.object(linux_devices.os, 'open', return_value=77) as opened, \
             mock.patch.object(linux_devices.os, 'close') as closed, \
             mock.patch.object(fcntl, 'ioctl',
                               side_effect=[struct.pack('Q', 4096), struct.pack('I', 512)]):
            self.assertEqual(linux_devices.block_info(_DEVICE), (4096, 512))
        flags = opened.call_args.args[1]
        self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
        self.assertTrue(flags & os.O_CLOEXEC)
        closed.assert_called_once_with(77)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux guidance only')
    def test_linux_permission_error_does_not_suggest_windows_admin(self):
        with mock.patch.object(sources, 'validate_source', return_value=_DEVICE), \
             mock.patch.object(sources, 'is_device_source', return_value=True), \
             mock.patch.object(builtins, 'open', side_effect=PermissionError('denied')), \
             mock.patch.object(sources, 'log_issue'):
            with self.assertRaisesRegex(PermissionError, 'Linux-Datenträger'):
                with sources.open_source(_DEVICE):
                    pass


if __name__ == '__main__':
    unittest.main()
