"""Synthetic sysfs backing-disk tests: dm-crypt/LVM/mdraid-like stacked paths.

All /dev names are mocked. No real devices are opened, mounted or altered.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from recoverydesk import linux_devices


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux sysfs only')
class StackedTopologyTests(unittest.TestCase):
    def _topology(self, root: Path):
        sysblock = root / 'sys' / 'dev' / 'block'
        sysblock.mkdir(parents=True)
        for major_minor, name in (('8:1', 'sda'), ('8:17', 'sdb')):
            disk = root / 'sys' / 'devices' / ('pci-' + name) / 'block' / name
            part = disk / (name + '1')
            part.mkdir(parents=True)
            (part / 'partition').write_text('1', encoding='ascii')
            (disk / 'device').mkdir()
            (sysblock / major_minor).symlink_to(part, target_is_directory=True)
        dm = root / 'sys' / 'devices' / 'virtual' / 'block' / 'dm-0'
        (dm / 'slaves').mkdir(parents=True)
        (dm / 'slaves' / 'sda1').touch()
        (dm / 'slaves' / 'sdb1').touch()
        (sysblock / '253:0').symlink_to(dm, target_is_directory=True)
        return sysblock, dm

    def _patch_paths(self, sysblock, extra=None):
        original_path = Path
        original_stat = os.stat
        mapping = {'/dev/sda1': os.makedev(8, 1),
                   '/dev/sdb1': os.makedev(8, 17)}
        if extra:
            mapping.update(extra)

        def fake_stat(path, *args, **kwargs):
            device = mapping.get(os.fspath(path))
            if device is not None:
                return SimpleNamespace(st_rdev=device)
            return original_stat(path, *args, **kwargs)

        return (
            mock.patch.object(linux_devices, 'Path',
                side_effect=lambda path: original_path(str(path).replace(
                    '/sys/dev/block', str(sysblock), 1))),
            mock.patch.object(linux_devices.os, 'stat', side_effect=fake_stat)
        )

    def test_stacked_device_reports_all_physical_backing_disks(self):
        with tempfile.TemporaryDirectory() as folder:
            sysblock, _ = self._topology(Path(folder))
            p1, p2 = self._patch_paths(sysblock)
            with p1, p2:
                roots = linux_devices._backing_disks(os.makedev(253, 0))
                one = linux_devices._backing_disks(os.makedev(8, 1))
                two = linux_devices._backing_disks(os.makedev(8, 17))
            self.assertEqual(len(roots), 2)
            self.assertEqual(roots, one | two)
            self.assertFalse(one & two)

    def test_missing_slave_sysfs_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            sysblock, _ = self._topology(Path(folder))
            (sysblock / '8:17').unlink()
            p1, p2 = self._patch_paths(sysblock)
            with p1, p2:
                with self.assertRaisesRegex(ValueError, 'nicht auflösbar'):
                    linux_devices._backing_disks(os.makedev(253, 0))

    def test_stacked_members_are_snapshotted_once(self):
        with tempfile.TemporaryDirectory() as folder:
            sysblock, dm = self._topology(Path(folder))
            members = list((dm / 'slaves').iterdir())
            original_iterdir = Path.iterdir
            reads = []

            def changing_members(path):
                if path == dm / 'slaves':
                    reads.append(path)
                    return iter(members if len(reads) == 1 else [])
                return original_iterdir(path)

            p1, p2 = self._patch_paths(sysblock)
            with p1, p2, mock.patch.object(Path, 'iterdir', changing_members):
                roots = linux_devices._backing_disks(os.makedev(253, 0))
                expected = (linux_devices._backing_disks(os.makedev(8, 1))
                            | linux_devices._backing_disks(os.makedev(8, 17)))
            self.assertEqual(roots, expected)
            self.assertEqual(len(reads), 1)

    def test_disconnected_member_aborts_instead_of_accepting_partial_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            sysblock, _ = self._topology(Path(folder))
            p1, p2 = self._patch_paths(sysblock)
            with p1, p2:
                mapped_stat = linux_devices.os.stat

                def disconnected(path, *args, **kwargs):
                    if os.fspath(path) == '/dev/sdb1':
                        raise FileNotFoundError('simulated unplug')
                    return mapped_stat(path, *args, **kwargs)

                with mock.patch.object(linux_devices.os, 'stat', side_effect=disconnected), \
                        mock.patch.object(linux_devices.os, 'open',
                                          side_effect=AssertionError('No device access')) as opened:
                    with self.assertRaisesRegex(FileNotFoundError, 'simulated unplug'):
                        linux_devices._backing_disks(os.makedev(253, 0))
                    opened.assert_not_called()

    def test_cycle_in_virtual_device_backing_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            sysblock, dm0 = self._topology(Path(folder))
            for child in (dm0 / 'slaves').iterdir():
                child.unlink()
            (dm0 / 'slaves' / 'dm-1').touch()
            dm1 = Path(folder) / 'sys' / 'devices' / 'virtual' / 'block' / 'dm-1'
            (dm1 / 'slaves').mkdir(parents=True)
            (dm1 / 'slaves' / 'dm-0').touch()
            (sysblock / '253:1').symlink_to(dm1, target_is_directory=True)
            p1, p2 = self._patch_paths(sysblock, {
                '/dev/dm-0': os.makedev(253, 0),
                '/dev/dm-1': os.makedev(253, 1),
            })
            with p1, p2:
                with self.assertRaisesRegex(ValueError, 'Zyklische'):
                    linux_devices._backing_disks(os.makedev(253, 0))


if __name__ == '__main__':
    unittest.main()
