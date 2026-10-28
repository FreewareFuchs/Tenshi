"""Regression coverage for the initial Files & Folders pane split."""
import os
import unittest
import tempfile
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class FolderPaneLayoutTests(unittest.TestCase):
    def setUp(self):
        self._settings = tempfile.TemporaryDirectory()
        self._settings_patch = patch.dict(os.environ, {
            'TENSHI_SETTINGS_FILE': os.path.join(self._settings.name, 'settings.json')})
        self._settings_patch.start()
        self.app = RecoveryDeskApp()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self._settings_patch.stop()
        self._settings.cleanup()

    def show_files(self):
        self.app._select_main_tab('files')
        self.app.update()

    def test_tree_is_wide_enough_when_first_shown(self):
        self.assertFalse(self.app._browser_sash_initialized)
        self.show_files()
        pane = self.app.browser_paned
        self.assertTrue(self.app._browser_sash_initialized)
        self.assertGreaterEqual(self.app.folder_tree.winfo_width(), 300)
        self.assertGreater(self.app.file_tree.winfo_width(), 320)
        self.assertGreaterEqual(pane.sashpos(0), 330)
        self.assertLessEqual(abs(pane.sashpos(0) / pane.winfo_width() - 0.38), 0.06)

    def test_manual_sash_drag_is_not_overwritten_by_tab_changes(self):
        self.show_files()
        pane = self.app.browser_paned
        pane.sashpos(0, 370)
        self.app.update()
        self.app._select_main_tab('partition')
        self.app.update()
        self.app._select_main_tab('files')
        self.app.update()
        self.assertAlmostEqual(pane.sashpos(0), 370, delta=10)

    def test_resize_does_not_force_default_split_again(self):
        self.show_files()
        pane = self.app.browser_paned
        pane.sashpos(0, 410)
        self.app.update()
        self.app.geometry('1500x920')
        self.app.update()
        self.assertAlmostEqual(pane.sashpos(0), 410, delta=18)

    def test_existing_tabs_and_accent_export_button_remain(self):
        self.show_files()
        self.assertEqual(len(self.app.tabs.tabs()), 2)
        self.assertEqual(self.app.export_button.cget('bg'), self.app._palette()['accent'])


if __name__ == '__main__':
    unittest.main()
