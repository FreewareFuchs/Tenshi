"""Tests for the three high-contrast primary navigation buttons."""
import os
import unittest
from recoverydesk.gui import RecoveryDeskApp

class MainTabs180Tests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
    def test_active_tab_is_high_contrast_and_switchable(self):
        app = RecoveryDeskApp()
        try:
            app.update()
            self.assertEqual(len(app.tabs.tabs()), 3)
            self.assertEqual(set(app._nav_buttons), {'partition', 'files', 'signatures'})
            part = app._nav_buttons['partition']
            files = app._nav_buttons['files']
            signatures = app._nav_buttons['signatures']
            self.assertEqual(part.cget('bg'), app._palette()['nav'])
            self.assertEqual(part.cget('fg'), '#ffffff')
            app._select_main_tab('files')
            app.update()
            self.assertEqual(app.tabs.select(), str(app.ntfs_tab))
            self.assertEqual(files.cget('bg'), app._palette()['nav'])
            self.assertEqual(part.cget('bg'), app._palette()['inactive'])
            app._select_main_tab('signatures')
            app.update()
            self.assertEqual(app.tabs.select(), str(app.signature_tab))
            self.assertEqual(signatures.cget('bg'), app._palette()['nav'])
            self.assertEqual(files.cget('bg'), app._palette()['inactive'])
            app.tabs.select(app.partition_tab)  # existing internal navigation also updates buttons
            app.update()
            self.assertEqual(part.cget('bg'), app._palette()['nav'])
            self.assertEqual(files.cget('bg'), app._palette()['inactive'])
            self.assertEqual(signatures.cget('bg'), app._palette()['inactive'])
            self.assertEqual(app.export_button.cget('bg'),app._palette()['accent'])
        finally:
            app.destroy()

if __name__ == '__main__':unittest.main()
