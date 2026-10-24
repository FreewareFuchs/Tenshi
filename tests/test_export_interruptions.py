"""Inject deterministic interruptions into real exporters using synthetic sources."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk import batch_export
from recoverydesk.batch_export import export_batch, plan_selection
from recoverydesk.filesystems import scan_tree
from recoverydesk.ntfs_browser import scan_ntfs_tree
from test_browser import image_with_folders
from test_filesystems import fat_img


class ExportInterruptionTests(unittest.TestCase):
    def fixture(self, root, ntfs):
        source = root / 'source.raw'
        source.write_bytes(image_with_folders() if ntfs else fat_img())
        index = scan_ntfs_tree(str(source)) if ntfs else scan_tree(str(source))
        entry = next(e for e in index.entries if e.name == ('bericht.txt' if ntfs else 'README.TXT'))
        target = root / 'out'
        target.mkdir()
        relative = plan_selection(index, [entry])[0].path
        return source, index, entry, target, relative, b'FIRST' if ntfs else b'HELLO'

    def run_export(self, fixture, **kwargs):
        source, index, entry, target, _, _ = fixture
        return export_batch(str(source), index, [entry], str(target), **kwargs)

    def test_cancel_at_each_write_boundary_then_restart_and_verify(self):
        for ntfs in (False, True):
            for boundary in (0, 2, 4, 5):
                with self.subTest(ntfs=ntfs, boundary=boundary), tempfile.TemporaryDirectory() as temporary:
                    f = self.fixture(Path(temporary), ntfs)
                    before = f[0].read_bytes()
                    written = 0
                    def progress(count):
                        nonlocal written
                        written += count
                    with patch('recoverydesk.export_io.CHUNK_SIZE', 2):
                        first = self.run_export(f, cancel=lambda: written >= boundary, byte_progress=progress)
                    self.assertTrue(first.cancelled)
                    output = Path(first.root) / 'files' / f[4]
                    self.assertFalse(output.exists())
                    state = json.loads(Path(first.manifest).read_text(encoding='utf-8'))
                    self.assertNotEqual(state['results'].get(f[4], {}).get('status'), 'Erfolgreich')
                    resumed = self.run_export(f)
                    self.assertTrue(resumed.resumed)
                    self.assertEqual(resumed.exported, 1)
                    self.assertEqual(resumed.verified_existing, 0)
                    self.assertEqual(output.read_bytes(), f[5])
                    self.assertEqual(self.run_export(f).verified_existing, 1)
                    self.assertEqual(f[0].read_bytes(), before)

    def test_write_error_after_partial_block_removes_output_and_retries(self):
        for ntfs in (False, True):
            with self.subTest(ntfs=ntfs), tempfile.TemporaryDirectory() as temporary:
                f = self.fixture(Path(temporary), ntfs)
                module = 'recoverydesk.ntfs_browser' if ntfs else 'recoverydesk.filesystems'
                import importlib
                real_open = importlib.import_module(module).open_regular_output
                @contextmanager
                def failing_output(*args, **kwargs):
                    with real_open(*args, **kwargs) as output:
                        class Writer:
                            def write(self, data):
                                output.write(data[:1])
                                raise OSError(28, 'simulated target full')
                        yield Writer()
                with patch(module + '.open_regular_output', side_effect=failing_output):
                    first = self.run_export(f)
                self.assertEqual(first.failed, 1)
                output = Path(first.root) / 'files' / f[4]
                self.assertFalse(output.exists())
                state = json.loads(Path(first.manifest).read_text(encoding='utf-8'))
                self.assertEqual(state['results'][f[4]]['status'], 'Fehler')
                self.assertNotIn('sha256', state['results'][f[4]])
                self.assertEqual(self.run_export(f).exported, 1)
                self.assertEqual(output.read_bytes(), f[5])

    def test_lost_completion_checkpoint_does_not_trust_or_overwrite_output(self):
        for ntfs in (False, True):
            with self.subTest(ntfs=ntfs), tempfile.TemporaryDirectory() as temporary:
                f = self.fixture(Path(temporary), ntfs)
                real_checkpoint = batch_export._atomic_json
                calls = 0
                def checkpoint(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise OSError('simulated checkpoint failure after file completion')
                    return real_checkpoint(*args, **kwargs)
                with patch.object(batch_export, '_atomic_json', side_effect=checkpoint):
                    with self.assertRaisesRegex(OSError, 'checkpoint failure'):
                        self.run_export(f)
                root = next(f[3].glob('Tenshi_Export_*'))
                output = root / 'files' / f[4]
                self.assertEqual(output.read_bytes(), f[5])
                state = json.loads((root / batch_export.MANIFEST).read_text(encoding='utf-8'))
                self.assertNotIn(f[4], state['results'])
                with patch.object(batch_export, 'export_ntfs_file') as ntfs_writer, \
                     patch.object(batch_export, 'export_other_file') as other_writer:
                    resumed = self.run_export(f)
                ntfs_writer.assert_not_called()
                other_writer.assert_not_called()
                self.assertEqual(resumed.failed, 1)
                self.assertEqual(resumed.verified_existing, 0)
                self.assertEqual(output.read_bytes(), f[5])
