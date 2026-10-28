"""Queue events, deterministic progress and GUI regression coverage."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recoverydesk.export_queue import QueueProgress, readable_bytes, readable_duration
from recoverydesk.batch_export import export_batch
from recoverydesk.ntfs_browser import scan_ntfs_tree
from test_browser import image_with_folders


class ExportQueueTests(unittest.TestCase):
    def test_speed_remaining_and_pending_are_not_falsely_final(self):
        q = QueueProgress()
        q.handle({'type': 'plan', 'total': 2, 'total_bytes': 1000, 'items': [
            {'path': 'one', 'size': 800, 'directory': False},
            {'path': 'two', 'size': 200, 'directory': False}],
            'root': '/tmp/target', 'log': '/tmp/target/log'}, now=1)
        self.assertEqual(q.remaining_bytes, 1000)
        q.handle({'type': 'start', 'path': 'one'}, now=1)
        q.handle({'type': 'bytes', 'path': 'one', 'delta': 200}, now=2)
        q.handle({'type': 'bytes', 'path': 'one', 'delta': 200}, now=3)
        self.assertEqual(q.written_bytes, 400)
        self.assertEqual(q.remaining_bytes, 600)
        self.assertAlmostEqual(q.speed(3), 200)
        self.assertAlmostEqual(q.eta(3), 3)
        q.handle({'type': 'done', 'path': 'one', 'size': 800, 'status': 'Erfolgreich'}, now=3)
        self.assertEqual(q.remaining_bytes, 200)
        self.assertEqual(q.done_count, 1)
        self.assertEqual(q.visible_items['one']['status'], 'Erfolgreich')
        q.handle({'type': 'start', 'path': 'two'}, now=4)
        q.handle({'type': 'done', 'path': 'two', 'size': 200, 'status': 'Bereits verifiziert'}, now=4)
        q.handle({'type': 'complete', 'cancelled': False}, now=4)
        self.assertEqual(q.remaining_bytes, 0)
        self.assertEqual(q.item_fraction, 1)
        self.assertIsNone(q.eta(4))

    def test_cancel_preserves_pending_and_rate_expires(self):
        q = QueueProgress()
        q.handle({'type': 'plan', 'total': 1, 'total_bytes': 500,
                  'items': [{'path': 'a', 'size': 500}]}, now=0)
        q.handle({'type': 'start', 'path': 'a'}, now=1)
        q.handle({'type': 'bytes', 'path': 'a', 'delta': 100}, now=1)
        q.handle({'type': 'bytes', 'path': 'a', 'delta': 100}, now=2)
        self.assertEqual(q.speed(9), 0)
        q.handle({'type': 'done', 'path': 'a', 'size': 500,
                  'status': 'Abgebrochen', 'detail': 'Unvollständig entfernt'}, now=9)
        q.handle({'type': 'complete', 'cancelled': True}, now=9)
        self.assertTrue(q.cancelled)
        self.assertEqual(q.overall_fraction, 0)
        self.assertEqual(q.visible_items['a']['status'], 'Abgebrochen')
        self.assertIn('200 B', q.summary(now=9))
        self.assertEqual(readable_bytes(1024), '1.0 KiB')
        self.assertEqual(readable_duration(None), '–')

    def test_live_export_resume_and_error_events(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            image = root / 'ntfs.raw'
            image.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(image))
            folder = next(f for f in index.list_dir(5) if f.name == 'Dokumente')
            output = root / 'output'; output.mkdir()
            events = []
            report = export_batch(str(image), index, [folder], str(output), event=events.append)
            self.assertEqual(events[0]['type'], 'plan')
            self.assertEqual(events[-1]['type'], 'complete')
            self.assertEqual(events[0]['total'], 5)
            self.assertEqual(len([e for e in events if e['type'] == 'done']), 5)
            self.assertEqual(sum(e['delta'] for e in events if e['type'] == 'bytes'), report.bytes_written)
            q = QueueProgress()
            for n, event in enumerate(events):
                q.handle(event, now=n / 5)
            self.assertEqual(q.done_count, 5)
            self.assertEqual(q.item_fraction, 1)
            self.assertEqual(q.remaining_bytes, 0)
            self.assertGreater(q.written_bytes, 0)
            # The second run reports previously verified files, not newly exported.
            events2 = []
            second = export_batch(str(image), index, [folder], str(output), event=events2.append)
            self.assertTrue(second.resumed)
            self.assertEqual(second.exported, 0)
            self.assertEqual(len([e for e in events2 if e.get('status') == 'Bereits verifiziert']), 3)
            self.assertEqual(sum(e['delta'] for e in events2 if e['type'] == 'bytes'), 0)
            # A tampered target must be shown as an explicit error, never overwritten.
            bad = Path(report.root) / 'files' / 'Dokumente' / 'bericht.txt'
            bad.write_bytes(b'OTHER')
            events3 = []
            third = export_batch(str(image), index, [folder], str(output), event=events3.append)
            self.assertEqual(third.failed, 1)
            failure = next(e for e in events3 if e.get('status') == 'Fehler')
            self.assertIn('existiert', failure['detail'])
            self.assertEqual(bad.read_bytes(), b'OTHER')

    def test_gui_end_to_end_starts_export_and_shows_result(self):
        import time
        from recoverydesk.gui import RecoveryDeskApp
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            image = root / 'ntfs.raw'
            image.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(image))
            folder = next(f for f in index.list_dir(5) if f.name == 'Dokumente')
            target = root / 'out'; target.mkdir()
            app = RecoveryDeskApp()
            app.withdraw()
            app.change_language('de')
            try:
                app.browser_source = str(image)
                app.browser_index = index
                app.browser_entries_visible = {'selected-folder': folder}
                app.file_tree.insert('', 'end', iid='selected-folder', text=folder.name)
                app.file_tree.selection_set('selected-folder')
                with patch('recoverydesk.gui.filedialog.askdirectory', return_value=str(target)), \
                     patch('recoverydesk.gui.messagebox.askyesno', return_value=True):
                    app.export_browser_selection()
                    limit = time.monotonic() + 5
                    while app.export_running and time.monotonic() < limit:
                        app.update()
                        time.sleep(.02)
                self.assertFalse(app.export_running)
                self.assertIsNotNone(app.export_result)
                self.assertEqual(app.export_result.exported, 3)
                self.assertEqual(app.export_progress.done_count, 5)
                self.assertEqual(len(app.export_progress.visible_items), 5)
                app._export_progress_window.refresh_display()
                self.assertEqual(str(app._export_progress_window.report_button.cget('state')), 'normal')
                with patch('recoverydesk.gui.filedialog.askdirectory', return_value=str(target)), \
                     patch('recoverydesk.gui.messagebox.askyesno', return_value=True):
                    app.export_browser_selection()
                    limit = time.monotonic() + 5
                    while app.export_running and time.monotonic() < limit:
                        app.update()
                        time.sleep(.02)
                self.assertFalse(app.export_running)
                self.assertEqual(app.export_result.verified_existing, 3)
                statuses = [row['status'] for row in app.export_progress.visible_items.values()]
                self.assertIn('Bereits verifiziert', statuses)
                # A modified target must raise a visible warning, not a full success bar.
                bad = Path(app.export_result.root) / 'files' / 'Dokumente' / 'bericht.txt'
                bad.write_bytes(b'changed target')
                with patch('recoverydesk.gui.filedialog.askdirectory', return_value=str(target)), \
                     patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                     patch('recoverydesk.gui.messagebox.showwarning') as warning:
                    app.export_browser_selection()
                    limit = time.monotonic() + 5
                    while app.export_running and time.monotonic() < limit:
                        app.update()
                        time.sleep(.02)
                    self.assertFalse(app.export_running)
                    warning.assert_called_once()
                    self.assertIn('1 Fehler', warning.call_args.args[1])
                self.assertEqual(app.export_result.failed, 1)
                view=app._show_export_progress()
                self.assertEqual(view.labels['phase'].cget('text'), 'Beendet mit Fehlern')
                self.assertLess(app.export_blocks.confirmed_fraction,1)
                self.assertIn('error',app.export_blocks.cell_states())
                self.assertEqual(bad.read_bytes(), b'changed target')
                # A later clean run must clear the failure state.
                fresh = root / 'fresh'; fresh.mkdir()
                with patch('recoverydesk.gui.filedialog.askdirectory', return_value=str(fresh)), \
                     patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                     patch('recoverydesk.gui.messagebox.showwarning') as warning:
                    app.export_browser_selection()
                    limit = time.monotonic() + 5
                    while app.export_running and time.monotonic() < limit:
                        app.update()
                        time.sleep(.02)
                    self.assertFalse(app.export_running)
                    warning.assert_not_called()
                self.assertEqual(app.export_blocks.confirmed_fraction,1)
                self.assertEqual(app._show_export_progress().labels['phase'].cget('text'),'Beendet')
            finally:
                app.destroy()

    def test_main_window_has_reopen_and_preflight_actions_without_a_queue(self):
        from recoverydesk.gui import RecoveryDeskApp
        app=RecoveryDeskApp()
        try:
            app.change_language('de')
            app.tabs.select(app.ntfs_tab);app.update()
            self.assertEqual(len(app.tabs.tabs()),2)
            self.assertEqual([app.tabs.tab(i,'text') for i in app.tabs.tabs()],['Partitionen','Dateien & Ordner'])
            self.assertNotIn('export_queue_tree',app.__dict__)
            self.assertNotIn('export_queue_bar',app.__dict__)
            self.assertNotIn('export_queue_frame',app.__dict__)
            self.assertTrue(app.export_progress_button.winfo_ismapped())
            self.assertTrue(app.export_preflight_button.winfo_ismapped())
            app.export_progress_button.invoke()
            first=app._export_progress_window
            first.destroy()
            app.export_progress_button.invoke()
            self.assertIsNot(first,app._export_progress_window)
            self.assertFalse(app.export_cancel.is_set())
        finally:
            app.destroy()


if __name__ == '__main__':
    unittest.main()
