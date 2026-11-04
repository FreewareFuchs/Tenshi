"""Checkpoint rename cannot escape a verified Linux directory fd."""
from __future__ import annotations

import json
import errno
import stat
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from recoverydesk.secure_target import atomic_json_checkpoint


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux dirfd atomic update only')
class LinuxCheckpointRenameTests(unittest.TestCase):
    def test_shared_directory_rejecting_fsync_still_saves_complete_json(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.img';source.write_bytes(b'protected')
            target=root/'search.json';target.write_text('{"previous":true}')
            real_sync=os.fsync;calls=[]
            def shared_sync(fd):
                directory=stat.S_ISDIR(os.fstat(fd).st_mode)
                calls.append(directory)
                if directory:raise OSError(errno.EINVAL,'Unsupported directory sync')
                real_sync(fd)
            with mock.patch('recoverydesk.secure_target.os.fsync',side_effect=shared_sync):
                atomic_json_checkpoint(str(target),{'saved':'complete'},str(source))
            self.assertEqual(json.loads(target.read_text()),{'saved':'complete'})
            self.assertEqual(calls,[False,True])
            self.assertEqual(source.read_bytes(),b'protected')
            self.assertFalse(list(root.glob('.tenshi-checkpoint-*.tmp')))

    def test_file_flush_failure_preserves_previous_json_and_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.img';source.write_bytes(b'protected')
            target=root/'search.json';target.write_bytes(b'{"previous":true}')
            with mock.patch('recoverydesk.secure_target.os.fsync',side_effect=OSError(errno.EINVAL,'File flush failed')):
                with self.assertRaises(OSError):atomic_json_checkpoint(str(target),{'new':True},str(source))
            self.assertEqual(target.read_bytes(),b'{"previous":true}')
            self.assertFalse(list(root.glob('.tenshi-checkpoint-*.tmp')))

    def test_directory_media_error_after_rename_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.img';source.write_bytes(b'protected')
            target=root/'search.json';real_sync=os.fsync
            def failed_sync(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError(errno.EIO,'Media error')
                real_sync(fd)
            with mock.patch('recoverydesk.secure_target.os.fsync',side_effect=failed_sync):
                with self.assertRaises(OSError):atomic_json_checkpoint(str(target),{'new':True},str(source))

    def test_symlink_checkpoint_destination_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            image = root / 'source.img'
            image.write_bytes(b'original')
            victim = root / 'important.txt'
            victim.write_text('unchanged', encoding='utf-8')
            checkpoint = root / 'checkpoint.json'
            checkpoint.symlink_to(victim)
            with self.assertRaisesRegex(ValueError, 'umgeleitet'):
                atomic_json_checkpoint(str(checkpoint), {'state': 'paused'}, str(image))
            self.assertEqual(victim.read_text(encoding='utf-8'), 'unchanged')
            self.assertTrue(checkpoint.is_symlink())

    def test_parent_replaced_before_rename_does_not_redirect_checkpoint(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            image = root / 'source.img'
            image.write_bytes(b'original')
            live = root / 'live'
            outside = root / 'outside'
            renamed = root / 'original-live'
            live.mkdir()
            outside.mkdir()
            checkpoint = live / 'checkpoint.json'
            (outside / 'checkpoint.json').write_text('outside-protected', encoding='utf-8')

            real_replace = os.replace
            performed = []

            def swap_before_replace(src, dest, **kwargs):
                if not performed:
                    live.rename(renamed)
                    live.symlink_to(outside, target_is_directory=True)
                    performed.append(True)
                return real_replace(src, dest, **kwargs)

            with mock.patch('recoverydesk.secure_target.os.replace',
                            side_effect=swap_before_replace):
                atomic_json_checkpoint(str(checkpoint), {'state': 'paused'}, str(image))
            self.assertTrue(performed)
            self.assertEqual(json.loads((renamed / 'checkpoint.json').read_text()), {'state': 'paused'})
            self.assertEqual((outside / 'checkpoint.json').read_text(), 'outside-protected')
            self.assertFalse((outside / 'checkpoint.json').is_symlink())


class LinuxImageCheckpointDispatchTests(LinuxCheckpointRenameTests):
    """Exercise the imaging entry point with an ordinary image source."""

    def setUp(self):
        from recoverydesk.imaging import _atomic_json
        dispatch = lambda path, state, source: _atomic_json(path, state, source=source)
        patcher = mock.patch(__name__ + '.atomic_json_checkpoint', side_effect=dispatch)
        patcher.start()
        self.addCleanup(patcher.stop)


if __name__ == '__main__':
    unittest.main()
