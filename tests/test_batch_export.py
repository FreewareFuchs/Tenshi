"""End-to-end regression checks for the resumable batch export (synthetic images)."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recoverydesk.batch_export import export_batch, plan_selection, MANIFEST, LOG_NAME
from recoverydesk.ntfs_browser import scan_ntfs_tree, FileEntry
from recoverydesk.filesystems import scan_tree
from test_browser import image_with_folders
from test_filesystems import fat_img


class BatchExportTests(unittest.TestCase):
    def fixture(self, folder):
        src = folder / 'ntfs.raw'
        src.write_bytes(image_with_folders())
        index = scan_ntfs_tree(str(src))
        parent = next(i for i in index.list_dir(5) if i.name == 'Dokumente')
        target = folder / 'rescued'
        target.mkdir()
        return src, index, parent, target

    def test_folder_tree_and_second_run_verifies_existing(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, target = self.fixture(Path(temp))
            first = export_batch(str(src), index, [parent], str(target))
            self.assertEqual(first.exported, 3)
            self.assertEqual(first.directories, 2)
            self.assertFalse(first.resumed)
            self.assertEqual((Path(first.root) / 'files' / 'Dokumente' / 'bericht.txt').read_bytes(), b'FIRST')
            self.assertEqual((Path(first.root) / 'files' / 'Dokumente' / 'unterordner' / 'bild.irgendwas').read_bytes(), b'NOT-A-JPEG')
            self.assertTrue(Path(first.manifest).exists())
            self.assertTrue(Path(first.log).exists())
            original = src.read_bytes()
            second = export_batch(str(src), index, [parent], str(target))
            self.assertEqual(second.root, first.root)
            self.assertTrue(second.resumed)
            self.assertEqual(second.exported, 0)
            self.assertEqual(second.verified_existing, 3)
            self.assertEqual(src.read_bytes(), original)

    def test_cancel_then_resume_remaining_without_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            src, idx, parent, dest = self.fixture(Path(temp))
            stop = {'value': False}
            def on_progress(number, total, name, status):
                if status == 'Erfolgreich':
                    stop['value'] = True
            first = export_batch(str(src), idx, [parent], str(dest),
                                 cancel=lambda: stop['value'], progress=on_progress)
            self.assertTrue(first.cancelled)
            self.assertEqual(first.exported, 1)
            second = export_batch(str(src), idx, [parent], str(dest))
            self.assertTrue(second.resumed)
            self.assertEqual(second.exported, 2)
            self.assertEqual(second.verified_existing, 1)
            third = export_batch(str(src), idx, [parent], str(dest))
            self.assertEqual(third.verified_existing, 3)
            self.assertEqual(third.exported, 0)

    def test_tampered_prior_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            one = export_batch(str(src), index, [parent], str(dest))
            corrupted = Path(one.root) / 'files' / 'Dokumente' / 'bericht.txt'
            corrupted.write_bytes(b'OTHER')
            result = export_batch(str(src), index, [parent], str(dest))
            self.assertGreaterEqual(result.failed, 1)
            self.assertEqual(corrupted.read_bytes(), b'OTHER')
            self.assertIn('bericht.txt', Path(result.log).read_text(encoding='utf-8'))

    def test_untracked_existing_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            one = export_batch(str(src), index, [parent], str(dest))
            out = Path(one.root) / 'files' / 'Dokumente' / 'bericht.txt'
            out.unlink()
            manifest = Path(one.manifest)
            state = json.loads(manifest.read_text(encoding='utf-8'))
            state['results'].pop('Dokumente/bericht.txt')
            manifest.write_text(json.dumps(state), encoding='utf-8')
            out.write_bytes(b'OTHER')
            two = export_batch(str(src), index, [parent], str(dest))
            self.assertGreaterEqual(two.failed, 1)
            self.assertEqual(out.read_bytes(), b'OTHER')

    def test_selection_parent_and_child_not_duplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            file = next(e for e in index.list_dir(parent.record_number) if e.name == 'bericht.txt')
            plan = plan_selection(index, [parent, file, file])
            self.assertEqual(sum(1 for item in plan if item.entry.record_number == file.record_number), 1)
            outcome = export_batch(str(src), index, [parent, file], str(dest))
            self.assertEqual(outcome.exported, 3)

    def test_cancel_mid_file_removes_incomplete_output_then_resumes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / 'fat.raw'; src.write_bytes(fat_img())
            index = scan_tree(str(src))
            chosen = next(i for i in index.list_dir(5) if i.name == 'README.TXT')
            dest = root / 'out'; dest.mkdir()
            flag = {'cancel': False}
            def copied(amount):
                flag['cancel'] = True
            first = export_batch(str(src), index, [chosen], str(dest),
                                 byte_progress=copied, cancel=lambda: flag['cancel'])
            self.assertTrue(first.cancelled)
            self.assertFalse((Path(first.root) / 'files' / 'README.TXT').exists())
            second = export_batch(str(src), index, [chosen], str(dest))
            self.assertEqual(second.exported, 1)
            self.assertEqual((Path(second.root) / 'files' / 'README.TXT').read_bytes(), b'HELLO')

    def test_same_length_corruption_is_caught_by_sha256(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            first = export_batch(str(src), index, [parent], str(dest))
            filename = Path(first.root) / 'files' / 'Dokumente' / 'bericht.txt'
            filename.write_bytes(b'OTHER')  # same length as FIRST
            second = export_batch(str(src), index, [parent], str(dest))
            self.assertEqual(second.failed, 1)
            self.assertEqual(filename.read_bytes(), b'OTHER')

    def test_preexisting_symlink_in_export_path_is_not_followed(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, idx, folder, target = self.fixture(root)
            outcome = export_batch(str(src), idx, [folder], str(target))
            link = Path(outcome.root) / 'files' / 'Dokumente' / 'unterordner'
            (link / 'bild.irgendwas').unlink()
            link.rmdir()
            outside = root / 'external'
            outside.mkdir()
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symbolische Links auf dieser Plattform nicht verfügbar')
            with self.assertRaises(ValueError):
                export_batch(str(src), idx, [folder], str(target))
            self.assertFalse(list(outside.iterdir()))

    def test_fat32_export_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root/'fat.raw'
            src.write_bytes(fat_img())
            index = scan_tree(str(src))
            entry = next(i for i in index.list_dir(5) if i.name == 'README.TXT')
            dest = root / 'out'; dest.mkdir()
            first = export_batch(str(src), index, [entry], str(dest))
            self.assertEqual(first.exported, 1)
            self.assertEqual((Path(first.root)/'files'/'README.TXT').read_bytes(), b'HELLO')
            second = export_batch(str(src), index, [entry], str(dest))
            self.assertEqual(second.verified_existing, 1)
            self.assertEqual(second.exported, 0)

    def test_source_change_separates_job_and_prevents_wrong_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            first = export_batch(str(src), index, [parent], str(dest))
            # Use an independent image with a different name but equivalent metadata.
            other = Path(temp)/'other.raw'
            other.write_bytes(src.read_bytes())
            second = export_batch(str(other), index, [parent], str(dest))
            self.assertNotEqual(second.root, first.root)
            self.assertFalse(second.resumed)

    def test_existing_untracked_batch_dir_without_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            first = export_batch(str(src), index, [parent], str(dest))
            Path(first.manifest).unlink()
            with self.assertRaises(FileExistsError):
                export_batch(str(src), index, [parent], str(dest))

    def test_changed_source_same_path_requires_new_job(self):
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            first = export_batch(str(src), index, [parent], str(dest))
            src.write_bytes(src.read_bytes() + b'1')
            second = export_batch(str(src), index, [parent], str(dest))
            self.assertNotEqual(second.root, first.root)

    def test_unsafe_names_and_collision(self):
        from recoverydesk.ntfs_browser import FileIndex
        from recoverydesk.ntfs import NTFSInfo
        with tempfile.TemporaryDirectory() as temp:
            src, index, parent, dest = self.fixture(Path(temp))
            # Fake two entries identical name but different records in same directory.
            a = FileEntry(100, 1, '../evil.txt', 5, 1, False, False, 3, 'resident', 3, resident_data=b'aaa')
            b = FileEntry(101, 1, '../evil.txt', 5, 1, False, False, 3, 'resident', 3, resident_data=b'bbb')
            paths = [i.path for i in plan_selection(index, [a, b])]
            self.assertEqual(len(paths), 2)
            self.assertNotEqual(paths[0], paths[1])
            self.assertTrue(all('/' not in s for s in paths))
            self.assertTrue(all('..' not in s for s in paths))

    def test_gui_button_is_present_without_restoring_removed_tabs(self):
        import tkinter as tk
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        try:
            self.assertEqual(app.tabs.tabs().__len__(), 2)
            labels = []
            def gather(widget):
                try:
                    labels.append(widget.cget('text'))
                except tk.TclError:
                    pass
                for child in widget.winfo_children():
                    gather(child)
            gather(app)
            self.assertIn('Stapel-Export / fortsetzen', labels)
            self.assertNotIn('Sektor / Hex-Editor', labels)
        finally:
            app.destroy()

if __name__ == '__main__': unittest.main()
