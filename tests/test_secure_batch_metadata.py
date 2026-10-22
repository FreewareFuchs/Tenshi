"""Linux block-source batch metadata writes: dirfd-bound and symlink safe.

The 'block' source is a mocked regular file under TemporaryDirectory.
No physical disk or /dev node is ever opened.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from recoverydesk import batch_export


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux dirfd tests only')
class SafeBatchMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'fake-source.raw'
        self.source.write_bytes(b'original-source-content')
        self.target = self.root / 'output'
        self.target.mkdir()

    @contextmanager
    def simulated_block(self):
        name = str(self.source)
        is_source = lambda path: os.fspath(path) == name
        with mock.patch('recoverydesk.batch_export.block_path', side_effect=is_source), \
             mock.patch('recoverydesk.linux_devices.block_path', side_effect=is_source), \
             mock.patch('recoverydesk.linux_devices._backing_disks',
                        side_effect=lambda dev: {'source-disk'} if dev == 0 else {'target-disk'}):
            yield

    def _write_log(self, path):
        state = {'identity': {'source': str(self.source), 'filesystem': 'ext4'},
                 'results': {}}
        result = batch_export.BatchResult(root=str(self.target))
        batch_export._write_log(path, state, result)

    def test_manifest_and_log_use_pinned_atomic_writer(self):
        manifest = self.target / batch_export.MANIFEST
        report = self.target / batch_export.LOG_NAME
        with self.simulated_block(), \
             mock.patch('recoverydesk.batch_export.atomic_json_checkpoint',
                        wraps=batch_export.atomic_json_checkpoint) as json_writer, \
             mock.patch('recoverydesk.batch_export.atomic_bytes_checkpoint',
                        wraps=batch_export.atomic_bytes_checkpoint) as report_writer:
            batch_export._atomic_json(manifest, {'schema': 1}, source=str(self.source))
            self._write_log(report)
            json_writer.assert_called_once()
            report_writer.assert_called_once()
        self.assertEqual(json.loads(manifest.read_text())['schema'], 1)
        self.assertIn('Tenshi Exportbericht', report.read_text())
        self.assertEqual(self.source.read_bytes(), b'original-source-content')

    def test_symlinked_manifest_and_report_never_overwrite_other_file(self):
        victim = self.root / 'victim.txt'
        victim.write_text('keep-this', encoding='utf-8')
        manifest = self.target / batch_export.MANIFEST
        report = self.target / batch_export.LOG_NAME
        manifest.symlink_to(victim)
        report.symlink_to(victim)
        with self.simulated_block():
            with self.assertRaisesRegex(ValueError, 'umgeleitet'):
                batch_export._atomic_json(manifest, {'schema': 1}, source=str(self.source))
            with self.assertRaisesRegex(ValueError, 'umgeleitet'):
                self._write_log(report)
        self.assertEqual(victim.read_text(), 'keep-this')
        self.assertTrue(manifest.is_symlink())
        self.assertTrue(report.is_symlink())

    def test_batch_report_parent_swap_stays_inside_original_directory(self):
        outside = self.root / 'unrelated'
        outside.mkdir()
        original = self.root / 'moved-out'
        report = self.target / batch_export.LOG_NAME
        (outside / batch_export.LOG_NAME).write_text('protected', encoding='utf-8')
        regular_replace = os.replace
        swaps = []

        def swap_parent(src, dest, **kwargs):
            if not swaps:
                self.target.rename(original)
                self.target.symlink_to(outside, target_is_directory=True)
                swaps.append(True)
            return regular_replace(src, dest, **kwargs)

        with self.simulated_block(), \
             mock.patch('recoverydesk.secure_target.os.replace',
                        side_effect=swap_parent):
            self._write_log(report)
        self.assertEqual(swaps, [True])
        self.assertIn('Tenshi Exportbericht',
                      (original / batch_export.LOG_NAME).read_text())
        self.assertEqual((outside / batch_export.LOG_NAME).read_text(), 'protected')


    def test_manifest_reader_rejects_final_symlink(self):
        from recoverydesk.secure_target import open_regular_input
        victim = self.root / 'secret.txt'
        victim.write_text('protected-content', encoding='utf-8')
        manifest = self.target / batch_export.MANIFEST
        manifest.symlink_to(victim)
        with self.simulated_block():
            with self.assertRaises(OSError):
                with open_regular_input(str(manifest), str(self.source)) as source:
                    source.read()
        self.assertEqual(victim.read_text(), 'protected-content')

    def test_manifest_reader_pins_parent_before_path_swap(self):
        from recoverydesk.secure_target import open_regular_input
        old = self.root / 'former-output'
        outside = self.root / 'outside'
        outside.mkdir()
        manifest = self.target / batch_export.MANIFEST
        manifest.write_text('{"schema": 1}', encoding='utf-8')
        (outside / batch_export.MANIFEST).write_text('{"schema": 999}', encoding='utf-8')
        original_open = os.open
        swaps = []

        def swap_before_manifest_open(name, flags, *args, **kwargs):
            if name == batch_export.MANIFEST and kwargs.get('dir_fd') is not None and not swaps:
                self.target.rename(old)
                self.target.symlink_to(outside, target_is_directory=True)
                swaps.append(True)
            return original_open(name, flags, *args, **kwargs)

        with self.simulated_block(), \
             mock.patch('recoverydesk.secure_target.os.open',
                        side_effect=swap_before_manifest_open):
            with open_regular_input(str(manifest), str(self.source)) as source:
                state = json.load(source)
        self.assertEqual(swaps, [True])
        self.assertEqual(state, {'schema': 1})
        self.assertEqual((outside / batch_export.MANIFEST).read_text(), '{"schema": 999}')

    def test_real_batch_resume_invokes_pinned_manifest_reader(self):
        from recoverydesk.filesystems import scan_tree
        from test_filesystems import fat_img
        source = self.root / 'fat-source.img'
        source.write_bytes(fat_img())
        index = scan_tree(str(source))
        selected = next(item for item in index.list_dir(5)
                        if item.name == 'README.TXT')
        first = batch_export.export_batch(str(source), index, [selected], str(self.target))
        self.assertEqual(first.exported, 1)
        is_fake_source = lambda p: os.fspath(p) == str(source)
        with mock.patch('recoverydesk.batch_export.block_path', side_effect=is_fake_source), \
             mock.patch('recoverydesk.batch_export.open_regular_input',
                        wraps=batch_export.open_regular_input) as pinned_reader:
            second = batch_export.export_batch(str(source), index, [selected], str(self.target))
        self.assertTrue(second.resumed)
        self.assertEqual(second.verified_existing, 1)
        opened = [call.args[0] for call in pinned_reader.call_args_list]
        self.assertEqual(len(opened), 2)
        self.assertIn(first.manifest, opened)
        self.assertIn(str(Path(first.root) / 'files' / 'README.TXT'), opened)
        self.assertEqual(source.read_bytes(), fat_img())


    def test_export_hash_rejects_symlink_to_unrelated_file(self):
        import hashlib
        victim = self.root / 'unrelated.bin'
        victim.write_bytes(b'do-not-use')
        target = self.target / 'recovered.bin'
        target.symlink_to(victim)
        with self.simulated_block():
            with self.assertRaises(OSError):
                batch_export._hash_file(target, source=str(self.source))
        self.assertEqual(victim.read_bytes(), b'do-not-use')

    def test_export_hash_uses_original_parent_handle_after_swap(self):
        import hashlib
        outside = self.root / 'outside-hash'
        outside.mkdir()
        original = self.root / 'original-output'
        expected = b'correct-recovered-file'
        other = b'unrelated-file'
        target = self.target / 'recovered.bin'
        target.write_bytes(expected)
        (outside / target.name).write_bytes(other)
        open_original = os.open
        swapped = []

        def swap_before_file_open(name, flags, *args, **kwargs):
            if name == target.name and kwargs.get('dir_fd') is not None and not swapped:
                self.target.rename(original)
                self.target.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return open_original(name, flags, *args, **kwargs)

        with self.simulated_block(), \
             mock.patch('recoverydesk.secure_target.os.open',
                        side_effect=swap_before_file_open):
            digest = batch_export._hash_file(target, source=str(self.source))
        self.assertEqual(swapped, [True])
        self.assertEqual(digest, hashlib.sha256(expected).hexdigest())
        self.assertEqual((outside / target.name).read_bytes(), other)


if __name__ == '__main__':
    unittest.main()
