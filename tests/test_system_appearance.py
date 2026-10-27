"""OS preference parsing, fallbacks and GUI-thread application."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from recoverydesk import appearance
from recoverydesk.ui_preferences import clean_ui_preferences, load_ui_preferences


class SystemDetectionTests(unittest.TestCase):
    def test_new_default_and_existing_explicit_preferences(self):
        self.assertEqual(clean_ui_preferences({})['theme'], 'system')
        for mode in ('system', 'light', 'dark'):
            self.assertEqual(clean_ui_preferences({'theme': mode})['theme'], mode)

    def test_portal_precedes_desktop_and_flatpak_does_not_use_host_fallback(self):
        with patch.object(appearance.sys, 'platform', 'linux'), patch.dict(
                os.environ, {'FLATPAK_ID': 'test'}), patch.object(appearance, '_command') as command:
            for value, expected in ((1, 'dark'), (2, 'light'), (0, None)):
                command.reset_mock()
                command.return_value = f'(<uint32 {value}>,)'
                self.assertEqual(appearance.detect_system_theme(), expected)
                self.assertEqual(command.call_count, 1)
            command.return_value = 'garbage'
            self.assertIsNone(appearance.detect_system_theme())

    def test_cinnamon_xfce_and_gnome(self):
        with patch.object(appearance.sys, 'platform', 'linux'), patch.dict(os.environ, {}, clear=True):
            for desktop, values, expected in (
                ('X-Cinnamon', ['', "'Mint-Y-Dark-Aqua'"], 'dark'),
                ('X-Cinnamon', ['', "'Mint-Y-Aqua'"], 'light'),
                ('XFCE', ['', 'Adwaita-dark'], 'dark'),
                ('GNOME', ['', "'prefer-dark'"], 'dark'),
                ('GNOME', ['', "'default'", "'Adwaita'"], 'light'),
                ('GNOME', ['', '', ''], None)):
                with self.subTest(desktop=desktop, values=values), patch.dict(
                        os.environ, {'XDG_CURRENT_DESKTOP': desktop}), patch.object(
                        appearance, '_command', side_effect=values):
                    self.assertEqual(appearance.detect_system_theme(), expected)

    def test_windows_app_preference_and_missing_value(self):
        registry = MagicMock()
        with patch.object(appearance.sys, 'platform', 'win32'), patch.dict('sys.modules', {'winreg': registry}):
            for value, expected in ((0, 'dark'), (1, 'light'), (7, None), (['dark'], None)):
                registry.QueryValueEx.return_value = (value, 4)
                self.assertEqual(appearance.detect_system_theme(), expected)
            registry.OpenKey.side_effect = OSError()
            self.assertIsNone(appearance.detect_system_theme())

    def test_missing_or_hanging_command_is_bounded(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('gdbus', 2)):
            with patch.object(appearance.subprocess, 'run', side_effect=error) as run:
                self.assertEqual(appearance._command(['gdbus']), '')
                self.assertEqual(run.call_args.kwargs['timeout'], 2)


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Display required')
class SystemAppearanceGuiTests(unittest.TestCase):
    def test_auto_changes_preserve_system_choice_manual_override_and_fonts(self):
        from recoverydesk.gui import RecoveryDeskApp
        from tkinter import ttk
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'TENSHI_SETTINGS_FILE': str(Path(tmp) / 'settings.json')}), patch(
                'recoverydesk.gui.detect_system_theme', return_value='light'):
            app = RecoveryDeskApp()
            try:
                app.update()
                self.assertEqual(app.theme_mode, 'system')
                style = ttk.Style(app)
                before_font = str(style.lookup('TLabel', 'font'))
                app._system_appearance_changed('dark')
                app.update()
                self.assertEqual(style.theme_use(), 'sun-valley-dark')
                self.assertEqual(app.theme_mode, 'system')
                app._save_display_preferences()
                self.assertEqual(load_ui_preferences()['theme'], 'system')
                app.change_theme('light')
                app._system_appearance_changed('dark')
                self.assertEqual(style.theme_use(), 'sun-valley-light')
                self.assertEqual(load_ui_preferences()['theme'], 'light')
                app.change_theme('system')
                self.assertEqual(style.theme_use(), 'sun-valley-dark')
                self.assertEqual(str(style.lookup('TLabel', 'font')), before_font)
                self.assertEqual(str(app.export_button.cget('font')), '{Segoe UI} 10 bold')
                app._system_appearance_changed(None)
                self.assertEqual(app.theme, 'light')
                self.assertEqual(app.theme_mode, 'system')
            finally:
                app.destroy()
            self.assertTrue(app._appearance_stop.is_set())
