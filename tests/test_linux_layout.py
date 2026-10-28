"""Linux/X11 layout regressions; empty application, no source/device access."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.i18n import LANGUAGES, save_language
from recoverydesk.ui_preferences import save_ui_preferences


@unittest.skipUnless(sys.platform.startswith('linux') and os.environ.get('DISPLAY'),
                     'Linux/X11 required')
class LinuxLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def assert_visible(self, app, widget, name):
        self.assertTrue(widget.winfo_ismapped(), name + ' is hidden')
        self.assertGreater(widget.winfo_width(), 1, name)
        self.assertGreater(widget.winfo_height(), 1, name)
        left, top = widget.winfo_rootx(), widget.winfo_rooty()
        right = left + widget.winfo_width()
        bottom = top + widget.winfo_height()
        parent = widget.master
        while parent is not None:
            self.assertGreaterEqual(left, parent.winfo_rootx(), name + ': left clipping')
            self.assertGreaterEqual(top, parent.winfo_rooty(), name + ': top clipping')
            self.assertLessEqual(right, parent.winfo_rootx() + parent.winfo_width(),
                                 name + ': right clipping')
            self.assertLessEqual(bottom, parent.winfo_rooty() + parent.winfo_height(),
                                 name + ': bottom clipping')
            parent = parent.master

    def check_layout(self, width, height, scaling, theme='light'):
        # Apply scaling before application styles and widgets are created.
        class App(RecoveryDeskApp):
            def _setup_style(self):
                self.tk.call('tk', 'scaling', scaling)
                super()._setup_style()

            def report_callback_exception(self, exc_type, exc, tb):
                self.callback_errors.append((exc_type.__name__, str(exc)))

        for language in LANGUAGES:
            with self.subTest(size=(width, height), scaling=scaling, language=language):
                settings = Path(self.temp.name) / (language + '.json')
                with patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(settings),
                                              'TENSHI_LOG_DIR': str(Path(self.temp.name) / 'logs')}):
                    save_language(language)
                    save_ui_preferences({'theme': theme})
                    # Actions are inspected, never invoked; discovering devices is
                    # also forbidden if startup behavior changes in the future.
                    with patch('recoverydesk.gui.list_physical_sources',
                               side_effect=AssertionError('Unexpected device enumeration')):
                        app = App()
                        app.callback_errors = []
                        try:
                            self.assertGreaterEqual(app.winfo_screenwidth(), width)
                            self.assertGreaterEqual(app.winfo_screenheight(), height)
                            app.geometry(f'{width}x{height}+0+0')
                            app.update()
                            self.assertEqual((app.winfo_width(), app.winfo_height()),
                                             (width, height))
                            self.assertEqual(app.language, language)
                            self.assertAlmostEqual(float(app.tk.call('tk', 'scaling')),
                                                   scaling, delta=0.03)
                            for name in ('help_button', 'error_log_button',
                                         'theme_button', '_language_button', 'session_menu_button'):
                                self.assert_visible(app, getattr(app, name), name)
                            source_actions = app.session_menu_button.master.winfo_children()
                            self.assertEqual(len(source_actions), 4)
                            for button in source_actions:
                                self.assert_visible(app, button, str(button.cget('text')))
                                self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth(),
                                                        str(button.cget('text')) + ': compressed action')
                            for key, button in app._nav_buttons.items():
                                self.assert_visible(app, button, key)
                            for tab in ('partition', 'files'):
                                app._select_main_tab(tab)
                                app.update()
                                self.assertGreaterEqual(app.tabs.winfo_height(), 100)
                            self.assert_visible(app, app.file_tree, 'file browser')
                            app.ntfs_scanning = True
                            app.status.set('MFT: 123,456 / 987,654 Datensätze geprüft …')
                            app.update()
                            self.assert_visible(app, app.status_label, 'live scan progress')
                            self.assertGreaterEqual(app.status_label.winfo_height(),
                                                    app.status_label.winfo_reqheight())
                            self.assertGreaterEqual(app.file_tree.winfo_height(), 70)
                            self.assert_visible(app, app.export_button, 'export action')
                            self.assertNotIn('export_queue_tree',app.__dict__)
                            self.assertNotIn('export_queue_bar',app.__dict__)
                            self.assert_visible(app,app.export_progress_button,'progress/result action')
                            self.assert_visible(app,app.export_preflight_button,'preflight action')
                            browser_height=app.file_tree.winfo_height()
                            app.export_progress_button.invoke()
                            app.update()
                            app._export_progress_window.destroy()
                            app.update()
                            self.assertEqual(app.file_tree.winfo_height(),browser_height)
                            self.assert_visible(app,app.status_label,'live status after closing export view')
                            self.assertEqual(app.callback_errors, [])
                        finally:
                            app.destroy()

    def test_compact_1024x650(self):
        for theme in ('light', 'dark'):
            self.check_layout(1024, 650, 4 / 3, theme)

    def test_laptop_1280x720(self):
        for theme in ('light', 'dark'):
            self.check_layout(1280, 720, 4 / 3, theme)

    def test_medium_height_1024x750(self):
        for theme in ('light', 'dark'):
            self.check_layout(1024, 750, 4 / 3, theme)

    def test_full_hd_1920x1080(self):
        for theme in ('light', 'dark'):
            self.check_layout(1920, 1080, 4 / 3, theme)

    def test_full_hd_with_larger_text(self):
        for theme in ('light', 'dark'):
            self.check_layout(1920, 1080, 2.0, theme)


if __name__ == '__main__':
    unittest.main()
