"""TOCTOU regression tests for Linux outputs without physical device access."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from recoverydesk import secure_target, imaging


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux dirfd defenses only')
class LinuxDestinationHandleTests(unittest.TestCase):
    def test_checksum_cleanup_stays_in_open_parent_after_directory_swap(self):
        from contextlib import contextmanager
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.img';source.write_bytes(b'protected')
            parent=root/'checksums';parent.mkdir();path=parent/'file.sha256';path.write_bytes(b'owned')
            meta=path.stat();expected=(meta.st_dev,meta.st_ino)
            original=secure_target.secure_parent
            @contextmanager
            def swapped(*args):
                with original(*args) as fd:
                    parent.rename(root/'old');parent.mkdir()
                    (parent/path.name).write_bytes(b'foreign')
                    yield fd
            with mock.patch.object(secure_target,'secure_parent',swapped):
                secure_target.remove_owned_output(str(path),str(source),expected,b'owned')
            self.assertEqual(path.read_bytes(),b'foreign')
            self.assertFalse((root/'old'/path.name).exists())
            self.assertEqual(source.read_bytes(),b'protected')

    def test_checksum_cleanup_rejects_symlink_to_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.img';source.write_bytes(b'protected')
            path=root/'file.sha256';path.symlink_to(source)
            meta=source.stat()
            with self.assertRaises((OSError,ValueError)):
                secure_target.remove_owned_output(str(path),str(source),(meta.st_dev,meta.st_ino),b'protected')
            self.assertTrue(path.is_symlink());self.assertEqual(source.read_bytes(),b'protected')

    def test_new_file_is_regular_exclusive_and_pinned(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'new.img'
            source = Path(folder) / 'source.raw'
            source.write_bytes(b'source-unmodified')
            with secure_target.open_regular_output(str(path), 'xb', str(source)) as output:
                output.write(b'expected')
                identity = os.fstat(output.fileno())
                self.assertTrue(path.is_file())
                self.assertEqual((identity.st_dev, identity.st_ino),
                                 (path.stat().st_dev, path.stat().st_ino))
            with self.assertRaises(FileExistsError):
                with secure_target.open_regular_output(str(path), 'xb', str(source)):
                    pass
            self.assertEqual(path.read_bytes(), b'expected')
            self.assertEqual(source.read_bytes(), b'source-unmodified')

    def test_final_component_symlink_never_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.raw'
            source.write_bytes(b'protected')
            dest = root / 'copy.img'
            dest.symlink_to(source)
            with self.assertRaises(OSError):
                with secure_target.open_regular_output(str(dest), 'r+b', str(source)):
                    pass
            self.assertEqual(source.read_bytes(), b'protected')

    def test_swapped_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.raw'
            source.write_bytes(b'protected')
            external = root / 'external'
            external.mkdir()
            trap = root / 'trap'
            trap.symlink_to(external, target_is_directory=True)
            with self.assertRaises(OSError):
                with secure_target.open_regular_output(str(trap / 'new.img'), 'xb',
                                                      str(source)):
                    pass
            self.assertFalse((external / 'new.img').exists())

    def test_fifo_is_never_used_for_existing_imaging_output(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFOs unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.raw'
            source.write_bytes(b'protected')
            special = root / 'special.img'
            os.mkfifo(special)
            with self.assertRaisesRegex(ValueError, 'reguläre'):
                with secure_target.open_regular_output(str(special), 'r+b',
                                                      str(source)):
                    pass

    def test_resume_rejects_replaced_regular_inode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.raw'
            source.write_bytes(bytes(range(256)) * 32768)
            dest = root / 'dest.img'
            original_opener = imaging.open_regular_output
            replaced = root / 'untracked'
            replaced.write_bytes(b'protect-me')

            from contextlib import contextmanager
            @contextmanager
            def malicious_open(path, mode, src, **kwargs):
                if mode == 'r+b':
                    # Swap filename AFTER its exclusive creation, before reopen.
                    dest.unlink()
                    os.link(replaced, dest)
                with original_opener(path, mode, src, **kwargs) as handle:
                    yield handle

            with mock.patch.object(imaging, 'open_regular_output',
                                   side_effect=malicious_open):
                with self.assertRaisesRegex(ValueError, 'ausgetauscht'):
                    imaging.create_image(str(source), str(dest))
            self.assertEqual(source.read_bytes(), bytes(range(256)) * 32768)
            self.assertEqual(replaced.read_bytes(), b'protect-me')

    def test_open_parent_fd_checked_against_source_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            src = '/dev/fake-raw-device'
            dest = str(Path(folder) / 'out.img')
            real_stat = os.stat
            class FakeStat:
                st_rdev = os.makedev(8, 0)

            def fake_stat(path, *args, **kwargs):
                if path == src:
                    return FakeStat()
                return real_stat(path, *args, **kwargs)

            with mock.patch('recoverydesk.linux_devices.block_path',
                            side_effect=lambda p: p == src), \
                 mock.patch('recoverydesk.secure_target.os.stat',
                            side_effect=fake_stat), \
                 mock.patch('recoverydesk.linux_devices._backing_disks',
                            return_value={'same-physical-drive'}):
                with self.assertRaisesRegex(ValueError, 'demselben physischen'):
                    with secure_target.open_regular_output(dest, 'xb', src):
                        pass
            self.assertFalse(Path(dest).exists())


if __name__ == '__main__':
    unittest.main()
