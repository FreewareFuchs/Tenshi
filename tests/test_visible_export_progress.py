"""Regression for the main-window batch progress being clipped by the browser."""
import unittest

from recoverydesk.export_queue import QueueProgress


class ProgressVisibilityTests(unittest.TestCase):
    def test_live_single_file_bytes_advance_the_fraction(self):
        q = QueueProgress()
        q.handle({'type':'plan', 'total':1, 'total_bytes':4000,
                  'items':[{'path':'huge.bin','size':4000,'directory':False}]})
        q.handle({'type':'start','path':'huge.bin'})
        q.handle({'type':'bytes', 'path':'huge.bin','delta':1000})
        self.assertAlmostEqual(q.item_fraction,0)
        self.assertAlmostEqual(q.overall_fraction,0.25)
        q.handle({'type':'bytes','path':'huge.bin','delta':1000})
        self.assertAlmostEqual(q.overall_fraction,0.5)
        q.handle({'type':'done','path':'huge.bin','size':4000,'status':'Erfolgreich'})
        self.assertEqual(q.overall_fraction,1)

    def test_only_directories_use_item_percentage(self):
        q = QueueProgress()
        q.handle({'type':'plan','total':2,'total_bytes':0,
                  'items':[{'path':'d1','size':0,'directory':True},
                           {'path':'d2','size':0,'directory':True}]})
        q.handle({'type':'done','path':'d1','size':0,'status':'Ordner erstellt'})
        self.assertAlmostEqual(q.overall_fraction,.5)

    def test_bar_visible_in_main_window_on_multiple_sizes(self):
        from recoverydesk.gui import RecoveryDeskApp
        for geometry in ('1340x830','1024x650'):
            with self.subTest(geometry=geometry):
                app = RecoveryDeskApp()
                try:
                    app.geometry(geometry)
                    app.tabs.select(app.ntfs_tab)
                    app.update()
                    self.assertTrue(app.export_queue_bar.winfo_ismapped(), 'Fortschrittsbalken fehlt')
                    self.assertTrue(app.file_tree.winfo_ismapped(), 'Dateibrowser verschwunden')
                    self.assertLess(app.export_queue_bar.winfo_rooty() + app.export_queue_bar.winfo_height(),
                                    app.winfo_rooty() + app.winfo_height())
                    self.assertEqual(app.export_queue_percent.get(), '0 %')
                    self.assertFalse(app.export_queue_details_open)
                    # Users can opt into the file-level details, then collapse again.
                    app._toggle_export_details()
                    self.assertTrue(app.export_queue_details_open)
                    app._toggle_export_details()
                    self.assertFalse(app.export_queue_details_open)
                finally:
                    app.destroy()

    def test_display_progress_updates_on_byte_event_without_finished_file(self):
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        try:
            app.tabs.select(app.ntfs_tab)
            app._handle_export_event({'type':'plan','total':1,'total_bytes':2000,
                                     'items':[{'path':'groß.dat', 'size':2000, 'directory':False}]})
            app._handle_export_event({'type':'start','path':'groß.dat'})
            app._handle_export_event({'type':'bytes','path':'groß.dat','delta':500})
            app._paint_export_progress()
            app.update_idletasks()
            self.assertEqual(app.export_queue_percent.get(),'25.0 %')
            self.assertAlmostEqual(float(app.export_queue_bar.cget('value')),25.)
        finally:
            app.destroy()

if __name__ == '__main__':
    unittest.main()
