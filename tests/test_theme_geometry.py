"""Switching appearance preserves compact metrics and user geometry."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tkinter import ttk
from recoverydesk.gui import RecoveryDeskApp

@unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt', 'Display required')
class ThemeGeometryTests(unittest.TestCase):
    def test_native_surfaces_keep_dark_colors_focus_and_table_selection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'TENSHI_SETTINGS_FILE': str(Path(tmp)/'settings.json')}):
            app = RecoveryDeskApp()
            try:
                style = ttk.Style(app)
                entry = ttk.Entry(app)
                entry.insert(0, 'Source image')
                combo = ttk.Combobox(app, values=('NTFS', 'FAT32'), state='readonly')
                combo.set('NTFS')
                app.file_tree.insert('', 'end', iid='resize-test', text='example.txt')
                app.file_tree.selection_set('resize-test')
                from recoverydesk.appearance import palette
                for mode in ('dark', 'light', 'dark'):
                    app.change_theme(mode)
                    colors = palette(mode)
                    self.assertEqual(style.theme_use(), 'sun-valley-' + mode)
                    for name in ('TEntry', 'TCombobox'):
                        self.assertEqual(style.lookup(name, 'fieldbackground', ('readonly',)), colors['input'])
                        self.assertEqual(style.lookup(name, 'bordercolor', ('focus',)), colors['accent'])
                        self.assertEqual(style.lookup(name, 'bordercolor', ('invalid',)), colors['warning'])
                    self.assertEqual(entry.get(), 'Source image')
                    self.assertEqual(combo.get(), 'NTFS')
                    self.assertEqual(app.file_tree.selection(), ('resize-test',))
                    self.assertEqual(style.lookup('Treeview', 'background', ('selected',)), colors['inactive'])
            finally:
                app.destroy()

    def test_switch_preserves_geometry_sash_and_widget_sizes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'TENSHI_SETTINGS_FILE':str(Path(tmp)/'settings.json')}):
            app=RecoveryDeskApp()
            try:
                for geometry in ('1024x650+0+0', '1340x830+0+0'):
                    app.geometry(geometry);app._select_main_tab('files');app.update()
                    app.browser_paned.sashpos(0,300);app.update()
                    before=app.geometry();sash=app.browser_paned.sashpos(0)
                    widgets=(app.help_button,app.error_log_button,app.theme_button,app._language_button)
                    sizes=[(w.winfo_width(),w.winfo_height()) for w in widgets]
                    style=ttk.Style(app);metrics=(style.lookup('TButton','padding'),style.lookup('Treeview','rowheight'))
                    for theme in ('light','dark','light'):
                        app.change_theme(theme);app.update()
                        self.assertEqual(app.geometry(),before)
                        self.assertEqual(app.browser_paned.sashpos(0),sash)
                        self.assertEqual([(w.winfo_width(),w.winfo_height()) for w in widgets],sizes)
                        self.assertEqual((style.lookup('TButton','padding'),style.lookup('Treeview','rowheight')),metrics)
            finally:app.destroy()
