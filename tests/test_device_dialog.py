"""Regression tests for GUI device confirmation (no physical disks needed)."""
import os
import unittest
from unittest.mock import patch

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.i18n import LANGUAGES, translate


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


@unittest.skipUnless(tk and (os.name == 'nt' or os.environ.get('DISPLAY')),
                     'Tk graphical display is unavailable')
class DeviceDialogTests(unittest.TestCase):
    def setUp(self):
        self.app = RecoveryDeskApp()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()

    def _parts(self, dialog):
        widgets = list(descendants(dialog))
        tree = next(w for w in widgets if isinstance(w, ttk.Treeview))
        # Dialog captions may be translated on the next Tk event loop pass.
        expected = {
            translate('Auswahl übernehmen (nur lesen)', lang)
            for lang in LANGUAGES
        }
        buttons = [w for w in widgets if isinstance(w, ttk.Button)]
        ok = next((w for w in buttons if str(w.cget('text')) in expected), None)
        self.assertIsNotNone(
            ok, f'Confirm button missing; found captions: '
                f'{[str(w.cget("text")) for w in buttons]!r}')
        return tree, ok

    def test_first_disk_is_selected_and_button_sets_source(self):
        dlg = self.app._show_device_dialog([
            (r'\\.\PhysicalDrive0', 100 * 1024**3),
            (r'\\.\PhysicalDrive1', 200 * 1024**3),
        ])
        self.app.update()
        tree, ok = self._parts(dlg)
        self.assertEqual(tuple(tree.selection()), (r'\\.\PhysicalDrive0',))
        self.assertEqual(str(ok.cget('state')), 'normal')
        tree.selection_set(r'\\.\PhysicalDrive1')
        self.app.update()
        with patch('recoverydesk.gui.messagebox.askyesno', return_value=True) as prompt, \
             patch.object(self.app, 'scan_partitions') as scan:
            ok.invoke()
        prompt.assert_called_once()
        scan.assert_called_once_with(False)
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))
        self.assertEqual(self.app.source_path.get(), r'\\.\PhysicalDrive1')
        self.assertIn('PhysicalDrive1', self.app.status.get())
        self.assertFalse(dlg.winfo_exists())

    def test_empty_selection_is_visibly_disabled_then_recovers(self):
        dlg = self.app._show_device_dialog([(r'\\.\PhysicalDrive3', 500 * 1024**3)])
        self.app.update()
        tree, ok = self._parts(dlg)
        tree.selection_remove(*tree.selection())
        self.app.update()
        self.assertEqual(str(ok.cget('state')), 'disabled')
        tree.selection_set(r'\\.\PhysicalDrive3')
        self.app.update()
        self.assertEqual(str(ok.cget('state')), 'normal')

    def test_rejected_confirmation_keeps_dialog_and_source_unchanged(self):
        dlg = self.app._show_device_dialog([(r'\\.\PhysicalDrive2', 80 * 1024**3)])
        self.app.update()
        _, ok = self._parts(dlg)
        with patch('recoverydesk.gui.messagebox.askyesno', return_value=False):
            ok.invoke()
        self.assertEqual(self.app.source_path.get(), '')
        self.assertTrue(dlg.winfo_exists())


if __name__ == '__main__':
    unittest.main()
