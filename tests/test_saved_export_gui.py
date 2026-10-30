"""Fresh-app saved-job UI, explicit consent, cancellation and normal export controls."""
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import prepare_saved_export as real_prepare
from recoverydesk.ntfs_browser import ScanCancelled
from recoverydesk.i18n import LANGUAGES,translate
import test_batch_export
import test_export_pause


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class SavedExportGuiTests(unittest.TestCase):
    setUp=test_export_pause.ExportPauseGuiTests.setUp
    stop_worker=test_export_pause.ExportPauseGuiTests.stop_worker
    pump=test_export_pause.ExportPauseGuiTests.pump

    def fixture(self):
        source,index,parent,target=test_batch_export.BatchExportTests().fixture(self.root)
        stop=False
        def event(data):
            nonlocal stop
            if data['type']=='done' and data['status']=='Erfolgreich':stop=True
        first=export_batch(str(source),index,[parent],str(target),cancel=lambda:stop,event=event)
        self.assertTrue(first.cancelled)
        real_thread=threading.Thread
        def thread(*args,**kwargs):
            worker=real_thread(*args,**kwargs);self.threads.append(worker);return worker
        self.stack.enter_context(patch('recoverydesk.gui.threading.Thread',side_effect=thread))
        self.stack.enter_context(patch('recoverydesk.gui.filedialog.askdirectory',return_value=first.root))
        self.error=self.stack.enter_context(patch('recoverydesk.gui.messagebox.showerror'))
        self.warning=self.stack.enter_context(patch('recoverydesk.gui.messagebox.showwarning'))
        return source,index,first

    def snapshot(self,root):
        return {p.relative_to(root):p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}

    def test_new_app_opens_job_without_browser_selection_and_uses_one_worker(self):
        source,index,first=self.fixture();before=source.read_bytes();app=self.app
        self.assertIsNone(app.browser_index)
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True) as ask, \
             patch.object(app,'_selected_browser_entries',side_effect=AssertionError('New selection requested')):
            app.export_open_job_button.invoke();self.pump(lambda:not app.export_running)
        self.assertEqual(len(self.threads),1);ask.assert_called_once()
        self.assertEqual(app.export_result.root,first.root)
        self.assertEqual((app.export_result.verified_existing,app.export_result.exported,app.export_result.failed),(1,2,0))
        self.assertIsNone(app.browser_index)
        self.assertEqual(source.read_bytes(),before)
        self.error.assert_not_called();self.warning.assert_not_called()

    def test_declining_source_consent_never_prepares_or_changes_job(self):
        source,index,first=self.fixture();before=self.snapshot(first.root)
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=False), \
             patch('recoverydesk.gui.prepare_saved_export') as prepare:
            self.app.export_open_job_button.invoke();self.pump(lambda:not self.app.export_running)
        prepare.assert_not_called();self.assertEqual(self.snapshot(first.root),before)
        self.assertIsNone(self.app.export_result);self.assertFalse(self.app._export_target_reviewing)
        self.error.assert_not_called()

    def test_source_review_is_translated_and_preserves_paths(self):
        source,index,first=self.fixture();ui_thread=threading.get_ident()
        def decline(title,text,**kwargs):
            self.assertEqual(threading.get_ident(),ui_thread)
            self.assertIn(os.path.normcase(str(source)),text)
            self.assertIn(first.root,text)
            if self.app.language!='de':self.assertNotIn('Gespeicherten Export fortsetzen?',text)
            return False
        with patch('recoverydesk.gui._messagebox.askyesno',side_effect=decline) as ask:
            for language in LANGUAGES:
                self.app.change_language(language)
                self.assertEqual(self.app.export_open_job_button.cget('text'),translate('Exportauftrag öffnen',language))
                self.app.export_open_job_button.invoke();self.pump(lambda:not self.app.export_running)
        self.assertEqual(ask.call_count,6);self.error.assert_not_called()

    def test_cancel_during_rescan_preserves_checkpoint_and_previous_ui(self):
        source,index,first=self.fixture();before=self.snapshot(first.root)
        reached=threading.Event()
        def prepare(saved,**kwargs):
            def scan(*args,**options):
                options['progress'](1,123)
                reached.set();self.release.wait(5)
                if options['cancel']():raise ScanCancelled('cancel')
                return index
            with patch('recoverydesk.export_resume.scan_ntfs_tree',side_effect=scan):
                return real_prepare(saved,**kwargs)
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
             patch('recoverydesk.gui.prepare_saved_export',side_effect=prepare):
            self.app.export_open_job_button.invoke();self.pump(reached.is_set)
            self.pump(lambda:bool(self.app._export_restore_status))
            view=self.app._export_progress_window;view.refresh_display()
            self.assertIn('1 / 123',view.labels['verification'].cget('text'))
            self.assertEqual(str(view.pause_button.cget('state')),'disabled')
            view.cancel_button.invoke();self.release.set();self.pump(lambda:not self.app.export_running)
        self.assertEqual(self.snapshot(first.root),before);self.assertIsNone(self.app.export_result)
        self.error.assert_not_called()

    def test_changed_source_is_reported_without_mutating_destination(self):
        source,index,first=self.fixture();before=self.snapshot(first.root);stamp=source.stat()
        os.utime(source,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+1000000000))
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True):
            self.app.export_open_job_button.invoke();self.pump(lambda:not self.app.export_running)
        self.assertEqual(self.snapshot(first.root),before);self.error.assert_called_once()
        self.assertFalse(self.app._export_restoring)

    def test_existing_export_button_reopens_restore_view_without_another_worker(self):
        source,index,first=self.fixture();reached=threading.Event()
        def prepare(saved,**kwargs):
            reached.set();self.release.wait(5)
            return real_prepare(saved,**kwargs)
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
             patch('recoverydesk.gui.prepare_saved_export',side_effect=prepare):
            self.app.export_open_job_button.invoke();self.pump(reached.is_set)
            self.app._export_progress_window.destroy();self.app.export_button.invoke()
            self.assertEqual(len(self.threads),1)
            self.assertTrue(self.app._export_progress_window.winfo_exists())
            self.release.set();self.pump(lambda:not self.app.export_running)
        self.error.assert_not_called();self.assertEqual(self.app.export_result.failed,0)

    def test_main_window_close_cancels_pending_restore_and_waits_for_worker(self):
        source,index,first=self.fixture();before=self.snapshot(first.root);reached=threading.Event()
        def prepare(saved,**kwargs):
            reached.set();self.release.wait(5)
            return real_prepare(saved,**kwargs)
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
             patch('recoverydesk.gui.prepare_saved_export',side_effect=prepare):
            self.app.export_open_job_button.invoke();self.pump(reached.is_set)
            self.app._request_close();self.assertTrue(self.app._exit_requested)
            self.assertFalse(self.app._closing)
            self.release.set();self.pump(lambda:self.app._closing)
        self.assertEqual(self.snapshot(first.root),before)
        self.error.assert_not_called()
