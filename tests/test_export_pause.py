"""Pause the actual writer/hash loop without restarting its file or worker."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from recoverydesk.batch_export import export_batch
from recoverydesk.export_pause import ExportPause
from recoverydesk.export_queue import QueueProgress
import test_export_interruptions


class ExportPauseTests(unittest.TestCase):
    def test_pause_withdrawn_before_worker_boundary_does_not_block(self):
        events=[];control=ExportPause(threading.Event(),events.append)
        control.request(True);control.request(False)
        self.assertFalse(control.check_cancel());self.assertEqual(events,[])

    def test_cancel_releases_paused_worker_without_resume(self):
        cancelled=threading.Event();paused=threading.Event();finished=threading.Event();result=[]
        control=ExportPause(cancelled,lambda event:paused.set() if event['type']=='paused' else None)
        control.request(True)
        def worker():result.append(control.check_cancel());finished.set()
        thread=threading.Thread(target=worker);thread.start()
        try:
            self.assertTrue(paused.wait(3));self.assertFalse(finished.is_set())
            cancelled.set();self.assertTrue(finished.wait(3));self.assertEqual(result,[True])
        finally:
            cancelled.set();control.request(False);thread.join(3)

    def test_actual_partial_files_keep_the_same_identity_and_digest_when_resumed(self):
        for ntfs in (False,True):
            with self.subTest(ntfs=ntfs),tempfile.TemporaryDirectory() as folder:
                fixture=test_export_interruptions.ExportInterruptionTests().fixture(Path(folder),ntfs)
                source,index,entry,target,relative,expected=fixture
                cancelled=threading.Event();paused=threading.Event();finished=threading.Event()
                events=[];results=[];errors=[];written=0
                def event(item):
                    events.append(item)
                    if item['type']=='paused':paused.set()
                control=ExportPause(cancelled,event)
                def progress(count):
                    nonlocal written
                    written+=count
                    if written==2:control.request(True)
                def worker():
                    try:results.append(export_batch(str(source),index,[entry],str(target),
                        byte_progress=progress,cancel=control.check_cancel,event=event))
                    except Exception as exc:errors.append(exc)
                    finally:finished.set()
                thread=threading.Thread(target=worker)
                with patch('recoverydesk.export_io.CHUNK_SIZE',2):
                    thread.start()
                    try:
                        self.assertTrue(paused.wait(5));self.assertFalse(finished.wait(.1))
                        export_root=next(target.glob('Tenshi_Export_*'));output=export_root/'files'/relative
                        self.assertEqual(output.read_bytes(),expected[:2])
                        identity=(output.stat().st_dev,output.stat().st_ino)
                        self.assertFalse(list(export_root.rglob('*.sha256')))
                        control.request(False);self.assertTrue(finished.wait(5))
                    finally:
                        cancelled.set();control.request(False);thread.join(5)
                self.assertFalse(errors);result=results[0]
                self.assertFalse(result.cancelled);self.assertFalse(result.failed or result.checksum_errors)
                self.assertEqual(result.exported,1);self.assertEqual(result.verified_existing,0)
                self.assertEqual(written,len(expected));self.assertEqual(output.read_bytes(),expected)
                self.assertEqual((output.stat().st_dev,output.stat().st_ino),identity)
                self.assertEqual(len([e for e in events if e['type']=='start']),1)
                self.assertIn(hashlib.sha256(expected).hexdigest(),Path(result.checksums).read_text())

    def test_pause_during_hash_keeps_unconfirmed_file_and_continues_same_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            source,index,entry,target,relative,expected=test_export_interruptions.ExportInterruptionTests().fixture(Path(folder),True)
            paused=threading.Event();finished=threading.Event();cancelled=threading.Event();results=[];errors=[]
            requested=False
            def event(item):
                nonlocal requested
                if item['type']=='verify' and item['read']>0 and not requested:
                    requested=True;control.request(True)
                if item['type']=='paused':paused.set()
            control=ExportPause(cancelled,event)
            from recoverydesk.batch_export import _hash_file
            def worker():
                try:results.append(export_batch(str(source),index,[entry],str(target),cancel=control.check_cancel,event=event))
                except Exception as exc:errors.append(exc)
                finally:finished.set()
            with patch('recoverydesk.batch_export._hash_file',wraps=_hash_file) as hash_file:
                thread=threading.Thread(target=worker);thread.start()
                try:
                    self.assertTrue(paused.wait(5));self.assertFalse(finished.is_set())
                    export_root=next(target.glob('Tenshi_Export_*'))
                    self.assertEqual((export_root/'files'/relative).read_bytes(),expected)
                    self.assertFalse(list(export_root.rglob('*.sha256')))
                    control.request(False);self.assertTrue(finished.wait(5))
                    hash_file.assert_called_once()
                finally:
                    cancelled.set();control.request(False);thread.join(5)
            self.assertFalse(errors);self.assertFalse(results[0].checksum_errors)
            self.assertEqual(results[0].exported,1)

    def test_pause_resets_speed_samples_without_resetting_progress(self):
        q=QueueProgress();q.handle(dict(type='plan',total=1,total_bytes=100,items=[]))
        q.handle(dict(type='start',path='file',size=100))
        q.handle(dict(type='bytes',path='file',delta=40),now=1)
        q.handle(dict(type='bytes',path='file',delta=10),now=2)
        self.assertGreater(q.speed(2),0)
        q.handle(dict(type='paused'),now=3)
        self.assertEqual(q.written_bytes,50);self.assertEqual(q.speed(4),0);self.assertIsNone(q.eta(4))
        q.handle(dict(type='resumed'),now=100)
        self.assertEqual(q.written_bytes,50);self.assertEqual(q.speed(100),0)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class ExportPauseGuiTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ,{
            'TENSHI_SETTINGS_FILE':str(self.root/'settings.json'),'TENSHI_LOG_DIR':str(self.root/'logs')}))
        self.app=RecoveryDeskApp();self.addCleanup(self.app.destroy);self.app.change_language('de')
        self.threads=[];self.release=threading.Event()
        self.addCleanup(self.stop_worker)

    def stop_worker(self):
        self.app.export_cancel.set();self.app.export_pause.request(False);self.release.set()
        for thread in self.threads:thread.join(5)

    def pump(self,predicate):
        end=time.monotonic()+8
        while time.monotonic()<end:
            if predicate():return
            self.app.update();time.sleep(.01)
        self.fail('GUI condition timed out')

    def start_paused(self):
        source,index,entry,target,relative,expected=test_export_interruptions.ExportInterruptionTests().fixture(self.root,True)
        self.source=source;self.original=source.read_bytes();self.app.browser_source=str(source);self.app.browser_index=index
        reached=threading.Event();real_thread=threading.Thread
        def batch(*args,**kwargs):
            first=True
            def progress(count):
                nonlocal first
                if first:first=False;reached.set();self.release.wait(5)
            kwargs['byte_progress']=progress
            return export_batch(*args,**kwargs)
        def thread(*args,**kwargs):
            result=real_thread(*args,**kwargs);self.threads.append(result);return result
        for context in [patch.object(self.app,'_selected_browser_entries',return_value=[entry]),
            patch('recoverydesk.export_io.CHUNK_SIZE',2),
            patch('recoverydesk.gui.filedialog.askdirectory',return_value=str(target)),
            patch('recoverydesk.gui.messagebox.askyesno',return_value=True),
            patch('recoverydesk.gui.messagebox.showinfo'),
            patch('recoverydesk.gui.export_batch',side_effect=batch),
            patch('recoverydesk.gui.threading.Thread',side_effect=thread)]:self.stack.enter_context(context)
        self.warning=self.stack.enter_context(patch('recoverydesk.gui.messagebox.showwarning'))
        self.error=self.stack.enter_context(patch('recoverydesk.gui.messagebox.showerror'))
        self.app.export_browser_selection();self.pump(reached.is_set)
        self.app._export_progress_window.pause_button.invoke();self.release.set()
        self.pump(lambda:self.app.export_progress.paused)
        output=next(target.glob('Tenshi_Export_*'))/'files'/relative
        self.assertEqual(output.read_bytes(),expected[:2])
        return output,expected

    def test_pause_reopens_translates_and_resumes_one_worker(self):
        from recoverydesk.i18n import LANGUAGES,translate
        output,expected=self.start_paused();app=self.app
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=False):
            app.tk.call(app.protocol('WM_DELETE_WINDOW'))
        self.assertFalse(app._exit_requested);self.assertFalse(app.export_cancel.is_set())
        self.assertTrue(app.export_progress.paused);self.assertEqual(output.read_bytes(),expected[:2])
        app._export_progress_window.destroy();view=app._show_export_progress()
        for language in LANGUAGES:
            app.change_language(language)
            for theme in ('light','dark'):
                app.change_theme(theme);view.geometry('620x550+0+0')
                app.update();view.refresh_display();app.update_idletasks()
                self.assertEqual(view.pause_button.cget('text'),translate('Fortsetzen',language))
                self.assertEqual(view.labels['phase'].cget('text'),translate('Export pausiert.',language))
                self.assertLessEqual(view.pause_button.winfo_rooty()+view.pause_button.winfo_height(),view.winfo_rooty()+view.winfo_height())
        app.export_browser_selection();self.assertEqual(len(self.threads),1)
        self.assertFalse(app.export_cancel.is_set());self.assertTrue(app.export_running)
        view.pause_button.invoke();self.pump(lambda:not app.export_running)
        self.assertEqual(len(self.threads),1);self.assertEqual(output.read_bytes(),expected)
        self.assertFalse(app.export_result.cancelled or app.export_result.checksum_errors)
        self.assertEqual(self.source.read_bytes(),self.original)
        self.warning.assert_not_called();self.error.assert_not_called()

    def test_main_window_exit_releases_paused_writer_and_saves_result(self):
        output,_=self.start_paused();app=self.app
        app.tk.call(app.protocol('WM_DELETE_WINDOW'));self.pump(lambda:app._closing)
        self.assertTrue(app.export_result.cancelled);self.assertTrue(Path(app.export_result.log).is_file())
        self.assertFalse(output.exists());self.assertEqual(self.source.read_bytes(),self.original)
        self.warning.assert_not_called();self.error.assert_not_called()

    def test_cancel_button_stops_paused_export_without_closing_the_application(self):
        output,_=self.start_paused();app=self.app
        view=app._export_progress_window;view.cancel_button.invoke()
        self.pump(lambda:not app.export_running)
        self.assertTrue(app.export_result.cancelled);self.assertFalse(app._closing)
        self.assertFalse(output.exists());self.assertTrue(Path(app.export_result.log).is_file())
        view.refresh_display()
        self.assertEqual(str(view.cancel_button.cget('state')),'disabled')
        self.assertEqual(str(view.pause_button.cget('state')),'normal')
        self.assertEqual(view.pause_button.cget('text'),'Fortsetzen')
        self.assertEqual(self.source.read_bytes(),self.original)
        self.warning.assert_not_called();self.error.assert_not_called()

    def test_cancelled_export_resumes_captured_job_without_new_dialog_or_selection(self):
        from recoverydesk.i18n import LANGUAGES,translate
        output,expected=self.start_paused();app=self.app
        view=app._export_progress_window;view.cancel_button.invoke()
        self.pump(lambda:not app.export_running)
        previous_root=app.export_result.root
        self.assertFalse(output.exists());self.assertEqual(len(self.threads),1)
        app._export_progress_window.destroy();view=app._show_export_progress()
        for language in LANGUAGES:
            app.change_language(language);view.geometry('620x550+0+0')
            app.update();view.refresh_display();app.update_idletasks()
            self.assertEqual(str(view.pause_button.cget('state')),'normal')
            self.assertEqual(view.pause_button.cget('text'),translate('Fortsetzen',language))
            self.assertIn(translate('Fortsetzen prüft fertige Dateien; die abgebrochene Datei beginnt von vorn.',language),view.labels['note'].cget('text'))
        # The browser may now display a different source; resume must use the
        # captured source/index/selection/target, never current UI selections.
        app.browser_source=str(self.root/'another-source.img');app.browser_index=None
        with patch.object(app,'_selected_browser_entries',side_effect=AssertionError('New selection requested')), \
             patch('recoverydesk.gui.filedialog.askdirectory',side_effect=AssertionError('New target requested')), \
             patch('recoverydesk.gui.messagebox.askyesno',side_effect=AssertionError('Unexpected restart dialog')):
            view.pause_button.invoke()
            # A second start request before completion must not create a third worker.
            app._start_export_job(app._export_job,resume_root=previous_root)
            self.pump(lambda:not app.export_running)
        self.assertEqual(len(self.threads),2)
        self.assertEqual(app.export_result.root,previous_root);self.assertTrue(app.export_result.resumed)
        self.assertEqual(app.export_result.exported,1);self.assertEqual(app.export_result.bytes_written,len(expected))
        self.assertEqual(output.read_bytes(),expected);self.assertFalse(app.export_result.cancelled)
        self.assertFalse(app._can_resume_export());self.assertFalse(app.export_result.checksum_errors)
        self.assertEqual(self.source.read_bytes(),self.original)
        self.warning.assert_not_called();self.error.assert_not_called()

    def test_resume_waits_for_running_report_save_and_exit_prevents_restart(self):
        self.start_paused();app=self.app
        app._export_progress_window.cancel_button.invoke();self.pump(lambda:not app.export_running)
        self.assertTrue(app._can_resume_export())
        app._export_report_saving=True
        app._toggle_export_pause();self.assertEqual(len(self.threads),1)
        self.assertFalse(app._can_resume_export());app._export_report_saving=False
        app._exit_requested=True;app._toggle_export_pause()
        self.assertEqual(len(self.threads),1);self.assertFalse(app._can_resume_export())

    def test_resume_of_changed_original_source_fails_without_creating_another_export(self):
        self.start_paused();app=self.app
        app._export_progress_window.cancel_button.invoke();self.pump(lambda:not app.export_running)
        previous=Path(app.export_result.root);before=set(previous.parent.iterdir())
        stamp=self.source.stat()
        os.utime(self.source,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+1000000000))
        app._export_progress_window.pause_button.invoke();self.pump(lambda:not app.export_running)
        self.assertEqual(len(self.threads),2);self.assertTrue(app.export_progress.failed)
        self.assertEqual(set(previous.parent.iterdir()),before)
        self.assertEqual(self.source.read_bytes(),self.original)
        self.error.assert_called_once();self.warning.assert_not_called()
