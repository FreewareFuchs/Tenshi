"""Checkpoint rename cannot escape a verified Linux directory fd."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from recoverydesk.secure_target import atomic_json_checkpoint


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux dirfd atomic update only')
class LinuxCheckpointRenameTests(unittest.TestCase):
    def test_symlink_checkpoint_destination_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            image = root / 'source.img'
            image.write_bytes(b'original')
            victim = root / 'important.txt'
            victim.write_text('unchanged', encoding='utf-8')
            checkpoint = root / 'checkpoint.json'
            checkpoint.symlink_to(victim)
            with self.assertRaisesRegex(ValueError, 'Statusziel'):
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


if __name__ == '__main__':
    unittest.main()
