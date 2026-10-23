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
