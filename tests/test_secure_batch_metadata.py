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


if __name__ == '__main__':
    unittest.main()
