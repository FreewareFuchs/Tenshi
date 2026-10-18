"""Tests for the two high-contrast primary navigation buttons."""
import os
import unittest
from recoverydesk.gui import RecoveryDeskApp

class MainTabs180Tests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
    def test_active_tab_is_high_contrast_and_switchable(self):
        app = RecoveryDeskApp()
        try:
            app.update()
            self.assertEqual(len(app.tabs.tabs()), 2)
            self.assertEqual(set(app._nav_buttons), {'partition', 'files'})
            part = app._nav_buttons['partition']
            files = app._nav_buttons['files']
            self.assertEqual(part.cget('bg'), '#103e70')
            self.assertEqual(part.cget('fg'), '#ffffff')
            app._select_main_tab('files')
            app.update()
            self.assertEqual(app.tabs.select(), str(app.ntfs_tab))
            self.assertEqual(files.cget('bg'), '#103e70')
            self.assertEqual(part.cget('bg'), '#e1e9f3')
            app.tabs.select(app.partition_tab)  # existing internal navigation also updates buttons
            app.update()
            self.assertEqual(part.cget('bg'), '#103e70')
            self.assertEqual(files.cget('bg'), '#e1e9f3')
            self.assertEqual(app.export_button.cget('bg'),'#16803c')
        finally:
            app.destroy()

if __name__ == '__main__':unittest.main()
