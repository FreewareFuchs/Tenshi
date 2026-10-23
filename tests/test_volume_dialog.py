"""Regression tests: select a Windows logical drive and inspect raw volume read-only."""
import contextlib
import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from recoverydesk import sources
from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.i18n import LANGUAGES, translate
try:
    from tkinter import ttk
except ImportError:
    ttk = None


class VolumeSourceTests(unittest.TestCase):
    def test_exact_volume_path_accepted(self):
        self.assertEqual(sources.raw_volume_path('d:\\'), r'\\.\D:')
        self.assertTrue(sources.is_volume(r'\\.\C:'))
        self.assertEqual(sources.volume_letter(r'\\.\z:'), 'Z')
        self.assertTrue(sources.is_device_source(r'\\.\C:'))
        self.assertTrue(sources.is_device_source(r'\\.\PhysicalDrive0'))
        for bad in ('D:', 'D:\\Folder', r'\\.\D:\\', r'\\.\PhysicalDrive0\\', '../d:'):
            with self.subTest(bad=bad):
                if bad.startswith('\\\\.'):
                    self.assertFalse(sources.is_volume(bad))
                else:
                    with self.assertRaises(ValueError):
                        sources.raw_volume_path(bad)

    def test_windows_validation(self):
        with patch.object(sources.os, 'name', 'nt'):
            self.assertEqual(sources.validate_source(r'\\.\D:'), r'\\.\D:')
        with patch.object(sources.os, 'name', 'posix'):
            with self.assertRaises(ValueError):
                sources.validate_source(r'\\.\D:')

    def test_source_size_and_aligned_reader_volume(self):
        source = r'\\.\D:'
        with patch.object(sources.os, 'name', 'nt'), \
             patch.object(sources, '_device_ioctl', return_value=(8192).to_bytes(8, 'little')) as ioctl:
            self.assertEqual(sources.source_size(source), 8192)
            ioctl.assert_called_once()
        disk = io.BytesIO(bytes(range(256)) * 32)
        with patch.object(sources.os, 'name', 'nt'), \
             patch.object(sources, 'source_size', return_value=8192), \
             patch.object(sources, 'physical_sector_size', return_value=512), \
             patch('builtins.open', return_value=disk):
            with sources.open_source(source) as reader:
                reader.seek(11)
                self.assertEqual(reader.read(25), bytes(range(11, 36)))
                self.assertFalse(reader.writable())

    def test_destination_requires_distinct_physical_disk(self):
        source = r'\\.\D:'
        with patch.object(sources, 'volume_disk_numbers', return_value={1, 2}), \
             patch.object(sources, 'disk_numbers_of_destination', return_value={2}):
            with self.assertRaisesRegex(ValueError, 'denselben physischen'):
                sources.ensure_safe_destination(source, 'X:\\recovery\\file.bin')
        with patch.object(sources, 'volume_disk_numbers', return_value={1, 2}), \
             patch.object(sources, 'disk_numbers_of_destination', return_value={3}):
            sources.ensure_safe_destination(source, 'X:\\recovery\\file.bin')
        with patch.object(sources, 'volume_disk_numbers', return_value=None), \
             patch.object(sources, 'disk_numbers_of_destination', return_value={3}):
            with self.assertRaisesRegex(ValueError, 'nicht sicher zugeordnet'):
                sources.ensure_safe_destination(source, 'X:\\recovery\\file.bin')


@unittest.skipUnless(ttk and (os.name == 'nt' or os.environ.get('DISPLAY')),
                     'No GUI display')
class VolumeDialogTests(unittest.TestCase):
    def setUp(self):
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.volumes = [
            SimpleNamespace(path='C:\\', label='System', filesystem='NTFS',
                            total_bytes=100*1024**3, free_bytes=20*1024**3),
            SimpleNamespace(path='D:\\', label='Daten', filesystem='NTFS',
                            total_bytes=200*1024**3, free_bytes=150*1024**3),
        ]

    def tearDown(self):
        self.app.destroy()

    def widgets(self, dialog):
        def visit(w):
            for child in w.winfo_children():
                yield child
                yield from visit(child)
        widgets = list(visit(dialog))
        tree = next(w for w in widgets if isinstance(w, ttk.Treeview))
        # UITranslator updates dialog captions asynchronously and can run in
        # any of the six supported languages when tests share a process.
        expected = {
            translate('Auswahl übernehmen (nur lesen)', lang)
            for lang in LANGUAGES
        }
        buttons = [w for w in widgets if isinstance(w, ttk.Button)]
        button = next((w for w in buttons if str(w.cget('text')) in expected), None)
        self.assertIsNotNone(
            button, f'Confirm button missing; found captions: '
                    f'{[str(w.cget("text")) for w in buttons]!r}')
        return tree, button

    def test_confirm_button_is_locatable_in_all_supported_languages(self):
        """The UI translates captions asynchronously; selection must survive."""
        dlg = self.app._show_volume_dialog(self.volumes)
        for lang in LANGUAGES:
            with self.subTest(language=lang):
                self.app._i18n.set_language(lang)
                tree, button = self.widgets(dlg)
                self.assertEqual(str(button.cget('text')),
                                 translate('Auswahl übernehmen (nur lesen)', lang))
                self.assertEqual(tuple(tree.selection()), (self.volumes[0].path,))
        dlg.destroy()

    def test_confirm_selection_sets_volume_and_byte_offset_zero(self):
        dlg = self.app._show_volume_dialog(self.volumes)
        self.app.update()
        tree, button = self.widgets(dlg)
        self.assertEqual(tuple(tree.selection()), ('C:\\',))
        self.assertEqual(str(button.cget('state')), 'normal')
        self.app.ntfs_byte_offset.set('1048576')
        tree.selection_set('D:\\')
        self.app.update()
        @contextlib.contextmanager
        def fake_reader(_source):
            yield io.BytesIO(b'NTFS' + bytes(508))
        with patch('recoverydesk.gui.open_source', side_effect=fake_reader) as fake_open, \
             patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
             patch.object(self.app, 'scan_partitions') as scan:
            button.invoke()
        fake_open.assert_called_once_with(r'\\.\D:')
        self.assertEqual(self.app.source_path.get(), r'\\.\D:')
        self.assertEqual(self.app.ntfs_byte_offset.get(), '0')
        self.assertEqual(str(self.app.tabs.select()), str(self.app.partition_tab))
        scan.assert_called_once_with(False)
        self.assertFalse(dlg.winfo_exists())

    def test_access_denied_retains_original_source_and_dialog(self):
        dlg = self.app._show_volume_dialog(self.volumes)
        self.app.update()
        _, button = self.widgets(dlg)
        self.app.source_path.set('test.raw')
        with patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
             patch('recoverydesk.gui.open_source', side_effect=PermissionError('Access denied')), \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            button.invoke()
        self.assertEqual(self.app.source_path.get(), 'test.raw')
        self.assertTrue(dlg.winfo_exists())
        error.assert_called_once()

    def test_cancel_and_disabled_empty_selection(self):
        dlg = self.app._show_volume_dialog(self.volumes)
        self.app.update()
        tree, button = self.widgets(dlg)
        tree.selection_remove(*tree.selection())
        self.app.update()
        self.assertEqual(str(button.cget('state')), 'disabled')
        tree.selection_set('C:\\')
        self.app.update()
        self.assertEqual(str(button.cget('state')), 'normal')
        with patch('recoverydesk.gui.messagebox.askyesno', return_value=False):
            button.invoke()
        self.assertEqual(self.app.source_path.get(), '')
        self.assertTrue(dlg.winfo_exists())

if __name__ == '__main__':
    unittest.main()
