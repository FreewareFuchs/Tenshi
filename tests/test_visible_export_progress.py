"""Separate progress remains visible without taking space from the browser."""
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

    def test_cancelled_batch_never_claims_confirmation_after_last_item_done(self):
        from types import SimpleNamespace
        from recoverydesk.gui import RecoveryDeskApp
        for written in (0, 1000, 4000):
            with self.subTest(written=written):
                app = RecoveryDeskApp()
                try:
                    app._handle_export_event({'type': 'plan', 'total': 1, 'total_bytes': 4000,
                        'items': [{'path': 'huge.bin', 'size': 4000, 'directory': False}]})
                    app.change_language('de')
                    app._handle_export_event({'type': 'start', 'path': 'huge.bin','size':4000})
                    app._handle_export_event({'type': 'bytes', 'path': 'huge.bin', 'delta': written})
                    app._handle_export_event({'type': 'done', 'path': 'huge.bin', 'size': 4000,
                        'status': 'Abgebrochen', 'detail': 'Unvollständige Datei entfernt'})
                    app._handle_export_event({'type': 'complete', 'cancelled': True})
                    app._handle_export_event({'type': 'run_finish', 'result': SimpleNamespace(
                        cancelled=True, exported=0, verified_existing=0, failed=0,
                        skipped=0, bytes_written=written)})
                    view=app._show_export_progress()
                    self.assertEqual(view.labels['phase'].cget('text'),'Abgebrochen')
                    self.assertEqual(app.export_blocks.confirmed_fraction,0)
                    self.assertNotIn('confirmed',app.export_blocks.cell_states())
                    self.assertTrue(app.export_progress.cancelled)
                finally:
                    app.destroy()

    def test_progress_reopens_without_consuming_main_browser_space(self):
        from recoverydesk.gui import RecoveryDeskApp
        for geometry in ('1340x830','1024x650'):
            with self.subTest(geometry=geometry):
                app = RecoveryDeskApp()
                try:
                    app.geometry(geometry)
                    app.tabs.select(app.ntfs_tab)
                    app.update()
                    self.assertNotIn('export_queue_bar',app.__dict__)
                    self.assertNotIn('export_queue_tree',app.__dict__)
                    self.assertTrue(app.export_progress_button.winfo_ismapped())
                    height=app.file_tree.winfo_height()
                    view=app._show_export_progress();app.update()
                    self.assertTrue(view.grid_view.winfo_ismapped())
                    self.assertTrue(app.file_tree.winfo_ismapped(), 'Dateibrowser verschwunden')
                    self.assertEqual(app.file_tree.winfo_height(),height)
                    view.destroy();app.update()
                    app.export_progress_button.invoke();app.update()
                    self.assertTrue(app._export_progress_window.grid_view.winfo_ismapped())
                    self.assertEqual(app.file_tree.winfo_height(),height)
                finally:
                    app.destroy()

    def test_display_progress_updates_on_byte_event_without_finished_file(self):
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        try:
            app.export_running=True
            app.tabs.select(app.ntfs_tab)
            app._handle_export_event({'type':'plan','total':1,'total_bytes':2000,
                                     'items':[{'path':'groß.dat', 'size':2000, 'directory':False}]})
            app._handle_export_event({'type':'start','path':'groß.dat','size':2000})
            app._handle_export_event({'type':'bytes','path':'groß.dat','delta':500})
            view=app._show_export_progress()
            app.update_idletasks()
            view.refresh_display()
            self.assertEqual(app.export_blocks.cell_states().count('copied'),25)
            self.assertEqual(app.export_blocks.confirmed_fraction,0)
            self.assertAlmostEqual(app.export_progress.overall_fraction,.25)
        finally:
            app.destroy()

if __name__ == '__main__':
    unittest.main()
