"""Read-only, reproducible export preflight and GUI integration."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from recoverydesk.recovery_preflight import inspect_selection, inspect_metadata, _orphan_reason
from recoverydesk.ntfs_browser import scan_ntfs_tree, FileEntry
from recoverydesk.ntfs import DataRun
from recoverydesk.filesystems import scan_tree
from recoverydesk.batch_export import export_batch
from recoverydesk.i18n import LANGUAGES, translate
from test_browser import image_with_folders
from test_filesystems import fat_img


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.src = Path(self.temp.name) / 'volume.raw'
        self.src.write_bytes(image_with_folders())
        self.index = scan_ntfs_tree(str(self.src))

    def get(self, name):
        return next(e for e in self.index.entries if e.name == name)

    def test_recursively_assesses_same_export_plan(self):
        folder = self.get('Dokumente')
        rep = inspect_selection(self.index, [folder], filesystem='NTFS')
        self.assertEqual(rep.folders, 2)
        self.assertEqual(rep.files, 3)
        self.assertEqual(rep.warnings, 1)  # deleted entry
        self.assertEqual(rep.ready, 2)
        self.assertEqual(rep.blocked, 0)
        self.assertIn('Dokumente/unterordner/bild.irgendwas', [row.path for row in rep.items])
        self.assertIn('Metadatenprüfung', rep.as_text())
        self.assertEqual(rep.expected_bytes, len(b'FIRST') + len(b'RECOVER') + len(b'NOT-A-JPEG'))
        self.assertEqual(self.src.read_bytes(), image_with_folders())

    def test_orphan_finds_disconnected_ancestry(self):
        orphan = self.get('orphan.dat')
        rep = inspect_selection(self.index, [orphan])
        self.assertEqual(rep.warnings, 1)
        self.assertIn('Elternverzeichnis', rep.items[0].details[0])

    def test_no_original_checksum_claim(self):
        rep = inspect_selection(self.index, [self.get('bericht.txt')])
        self.assertEqual(rep.items[0].state, 'Bereit')
        self.assertIn('ungeprüft', rep.as_text())
        self.assertNotIn('Datei ist intakt', rep.as_text())

    def test_invalid_resident_stream_blocked_without_io(self):
        item = self.get('bericht.txt')
        item.size += 3
        before = self.src.read_bytes()
        row = inspect_metadata(self.index, item.name, item)
        self.assertEqual(row.state, 'Gesperrt')
        self.assertIn('Residente', row.details[0])
        self.assertEqual(before, self.src.read_bytes())

    def test_invalid_ntfs_data_runs_blocked_before_export(self):
        item = self.get('bericht.txt')
        item.data_kind = 'nonresident'
        item.size = 1024
        item.initialized_size = 1024
        item.resident_data = None
        item.data_runs = [DataRun(1, 1)]
        row = inspect_metadata(self.index, item.name, item)
        self.assertEqual(row.state, 'Gesperrt')
        target = Path(self.temp.name) / 'export'
        target.mkdir()
        result = export_batch(str(self.src), self.index, [item], str(target))
        self.assertEqual(result.exported, 0)
        self.assertEqual(result.skipped, 1)
        self.assertIn('Clusterzuordnung', result.errors[0])

    def test_invalid_extent_beyond_volume_blocked(self):
        item = self.get('bericht.txt')
        item.data_kind, item.size, item.initialized_size = 'nonresident', 512, 512
        item.data_runs = [DataRun(10**12, 1)]
        self.assertEqual(inspect_metadata(self.index, item.name, item).state, 'Gesperrt')

    def test_metadata_only_hint_cannot_export(self):
        item = FileEntry(91, 1, 'suspected.dat', 5, 0, False, False,
                         metadata_only=True, unsupported_reason='Nur Indexmetadaten')
        rep = inspect_selection(self.index, [item])
        self.assertEqual(rep.items[0].state, 'Gesperrt')

    def test_generic_fat_still_works_and_is_not_ntfs(self):
        fatpath = Path(self.temp.name) / 'fat.raw'
        fatpath.write_bytes(fat_img())
        index = scan_tree(str(fatpath))
        entry = next(e for e in index.entries if not e.is_directory and e.recoverable)
        report = inspect_selection(index, [entry], filesystem='FAT32')
        self.assertEqual(report.ready, 1)
        self.assertEqual(report.blocked, 0)

    def test_nonexistent_parent_and_cycle_are_explained(self):
        entry = FileEntry(90, 1, 'missing.ext', 6789, 1, False, False,
                          size=2, data_kind='resident', resident_data=b'OK')
        self.assertIn('Elternverzeichnis fehlt', _orphan_reason(self.index, entry))
        e1 = FileEntry(500, 1, 'x', 501, 1, True, False)
        e2 = FileEntry(501, 1, 'y', 500, 1, True, False)
        self.index.by_record[500] = e1
        self.index.by_record[501] = e2
        self.assertIn('Zyklische', _orphan_reason(self.index, e1))

    def test_language_entries_present(self):
        for label in ['Export prüfen', 'Export-Vorabprüfung', 'Prüfbericht speichern', 'Bewertung']:
            for language in LANGUAGES:
                self.assertTrue(translate(label, language))
                if language != 'de':
                    self.assertNotEqual(translate(label, language), label)


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'GUI display required')
class PreflightGuiTests(unittest.TestCase):
    def test_button_in_main_window_and_dialog_has_results(self):
        from recoverydesk.gui import RecoveryDeskApp
        import tkinter as tk
        app = RecoveryDeskApp()
        try:
            app.update()
            self.assertEqual(app.export_preflight_button.cget('text'), 'Export prüfen')
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / 'disk.raw'
                path.write_bytes(image_with_folders())
                index = scan_ntfs_tree(str(path))
                entry = next(e for e in index.entries if e.name == 'bericht.txt')
                app.browser_source = str(path)
                app.browser_index = index
                app.browser_fs = 'NTFS'
                with patch.object(app, '_selected_browser_entries', return_value=[entry]):
                    app.preflight_selection()
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline:
                    app.update()
                    windows = [child for child in app.winfo_children() if isinstance(child, tk.Toplevel)]
                    if windows:
                        all_trees = []
                        def walk(widget):
                            if isinstance(widget, __import__('tkinter').ttk.Treeview):
                                all_trees.append(widget)
                            for child in widget.winfo_children():
                                walk(child)
                        walk(windows[-1])
                        if all_trees and all_trees[0].get_children():
                            self.assertIn('bericht.txt', all_trees[0].item(all_trees[0].get_children()[0])['text'])
                            break
                    time.sleep(0.02)
                else:
                    self.fail('Vorabprüfungsdialog zeigt keine Einträge')
        finally:
            app.destroy()
