"""Branding regression tests: GUI branding must be bundled and visible."""
import unittest
from pathlib import Path

from recoverydesk.branding import asset_path
from recoverydesk.gui import RecoveryDeskApp, APP_NAME


class BrandingTests(unittest.TestCase):
    def test_app_name(self):
        self.assertEqual(APP_NAME, 'Tenshi')

    def test_logo_assets_exist(self):
        for name in ('tenshi_logo.png', 'tenshi_icon.png', 'tenshi.ico'):
            self.assertTrue(asset_path(name).is_file(), name)

    def test_disallow_unrelated_asset_paths(self):
        with self.assertRaises(ValueError):
            asset_path('../README.md')

    def test_gui_branding_and_tabs(self):
        app = RecoveryDeskApp()
        try:
            app.update_idletasks()
            self.assertIn('Tenshi', app.title())
            self.assertIsNotNone(app.brand_logo)
            self.assertEqual(app.tabs.tabs().__len__(), 2)
            self.assertEqual(app.tabs.tab(app.tabs.tabs()[0], 'text'), 'Partitionen')
            self.assertEqual(app.tabs.tab(app.tabs.tabs()[1], 'text'), 'Dateien & Ordner')
            self.assertTrue(app.brand_logo.width() >= 200)
        finally:
            app.destroy()

    def test_windows_build_includes_icon_and_assets(self):
        build = (Path(__file__).resolve().parents[1] / 'build_windows.bat').read_text(encoding='utf-8')
        self.assertIn('--name Tenshi', build)
        self.assertIn('--icon "recoverydesk/assets/tenshi.ico"', build)
        self.assertIn('--add-data "recoverydesk/assets;recoverydesk/assets"', build)


if __name__ == '__main__':
    unittest.main()
