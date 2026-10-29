import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from tkinter import ttk
from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.i18n import LANGUAGES,translate


def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class ControlledExitTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        env=patch.dict(os.environ,{'TENSHI_SETTINGS_FILE':str(self.root/'settings.json'),
                                   'TENSHI_LOG_DIR':str(self.root/'logs')})
        env.start();self.addCleanup(env.stop)
        self.app=RecoveryDeskApp();self.addCleanup(self.app.destroy)
        self.app.change_language('de')

    def pump(self,predicate,seconds=10):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            if predicate():return
            self.app.update();time.sleep(.01)
        self.fail('GUI condition timed out')

    def close_main(self):
        self.app.tk.call(self.app.protocol('WM_DELETE_WINDOW'))

    def test_idle_close_needs_no_confirmation(self):
        with patch('recoverydesk.gui._messagebox.askyesno') as ask:
            self.close_main()
        ask.assert_not_called();self.assertTrue(self.app._closing)

    def test_declining_leaves_export_running_and_default_is_no_in_all_languages(self):
        app=self.app;app.export_running=True
        for language in LANGUAGES:
            app.change_language(language)
            with patch('recoverydesk.gui._messagebox.askyesno',return_value=False) as ask:
                self.close_main()
            self.assertEqual(ask.call_args.kwargs['default'],'no')
            self.assertEqual(ask.call_args.args[0],translate('Tenshi beenden',language))
            if language!='de':self.assertNotIn('Es laufen noch',ask.call_args.args[1])
            self.assertTrue(app.export_running);self.assertFalse(app.export_cancel.is_set())
            self.assertFalse(app._exit_requested);self.assertFalse(app._closing)
        app.export_running=False

    def test_pending_saves_are_waited_for_and_new_work_is_not_started(self):
        app=self.app;app._export_report_saving=True
        app._imaging_session={'running':False,'saving':True}
        app._session_running=True
        with patch('recoverydesk.gui._messagebox.askyesno',return_value=True) as ask, \
             patch.object(app,'destroy') as destroy, \
             patch.object(app,'get_source',side_effect=AssertionError('New work started')), \
             patch('recoverydesk.gui.filedialog.asksaveasfilename',side_effect=AssertionError('Save started')):
            self.close_main();self.close_main()
            ask.assert_called_once();destroy.assert_not_called()
            self.assertTrue(app._exit_requested)
            app.open_imaging_dialog();app.export_browser_selection()
            app._save_export_report();app.save_analysis_session();app.load_analysis_session()
            app._export_report_saving=False;app._imaging_session['saving']=False
            app._wait_for_exit_work();destroy.assert_not_called()
            app._session_running=False;app._wait_for_exit_work();destroy.assert_called_once()

    def test_actual_imaging_checkpoint_is_saved_before_the_main_window_closes(self):
        from recoverydesk.imaging import create_image
        source=self.root/'source.img';data=bytes(range(256))*8192;source.write_bytes(data)
        destination=self.root/'copy.img';self.app.source_path.set(str(source))
        setup=self.app.open_imaging_dialog()
        next(w for w in walk(setup) if isinstance(w,ttk.Entry)).insert(0,str(destination))
        begin=next(w for w in walk(setup) if isinstance(w,ttk.Button) and w.cget('text')=='Image erstellen / fortsetzen')
        reached=threading.Event();release=threading.Event();threads=[];real_thread=threading.Thread
        def thread(*args,**kwargs):
            worker=real_thread(*args,**kwargs);threads.append(worker);return worker
        def imaging(*args,**kwargs):
            send=kwargs['progress']
            def progress(item):
                send(item)
                if item.processed>=1024*1024 and not reached.is_set():
                    reached.set();release.wait(15)
            kwargs['progress']=progress
            return create_image(*args,**kwargs)
        try:
            with patch('recoverydesk.gui.create_image',side_effect=imaging), \
                 patch('recoverydesk.gui.threading.Thread',side_effect=thread), \
                 patch('recoverydesk.gui._messagebox.askyesno',return_value=True), \
                 patch('recoverydesk.gui._messagebox.showinfo') as info, \
                 patch('recoverydesk.gui._messagebox.showwarning') as warning, \
                 patch('recoverydesk.gui._messagebox.showerror') as error:
                begin.invoke();self.pump(lambda:reached.is_set())
                session=self.app._imaging_session;session['window'].destroy()
                self.close_main()
                self.assertTrue(session['stop'].is_set());self.assertFalse(self.app._closing)
                release.set();self.pump(lambda:self.app._closing)
                info.assert_not_called();warning.assert_not_called();error.assert_not_called()
            state=json.loads(Path(str(destination)+'.recovery.json').read_text())
            self.assertEqual(state['state'],'paused');self.assertEqual(state['processed'],1024*1024)
            self.assertEqual(source.read_bytes(),data)
            resumed=create_image(str(source),str(destination),resume=True,verify=True)
            self.assertEqual(resumed['verification']['status'],'verified')
            self.assertEqual(destination.read_bytes(),data)
        finally:
            release.set()
            for worker in threads:worker.join(10)

    def test_exit_failures_are_shown_once_after_all_writers_finish(self):
        app=self.app;app._export_report_saving=True
        with patch('recoverydesk.gui._messagebox.askyesno',return_value=True), \
             patch('recoverydesk.gui._messagebox.showerror') as error, \
             patch.object(app,'destroy') as destroy:
            self.close_main()
            self.assertTrue(app._defer_exit_error('Disk full: report was not saved'))
            self.assertTrue(app._defer_exit_error(None))
            app._wait_for_exit_work();error.assert_not_called();destroy.assert_not_called()
            app._export_report_saving=False;app._wait_for_exit_work()
            error.assert_called_once();destroy.assert_called_once()
            self.assertIn('Disk full: report was not saved',error.call_args.args[1])
            self.assertEqual(app._exit_errors,[])

    def test_actual_export_writes_its_result_before_the_main_window_closes(self):
        from recoverydesk.batch_export import export_batch
        from recoverydesk.ntfs_browser import scan_ntfs_tree
        from test_browser import image_with_folders
        source=self.root/'source.img';data=image_with_folders();source.write_bytes(data)
        index=scan_ntfs_tree(str(source));parent=next(e for e in index.list_dir(5) if e.name=='Dokumente')
        destination=self.root/'export';destination.mkdir()
        app=self.app;app.browser_source=str(source);app.browser_index=index
        reached=threading.Event();release=threading.Event();threads=[];real_thread=threading.Thread
        def thread(*args,**kwargs):
            worker=real_thread(*args,**kwargs);threads.append(worker);return worker
        def batch(*args,**kwargs):
            send=kwargs['event']
            def event(item):
                send(item)
                if item['type']=='bytes' and not reached.is_set():
                    reached.set();release.wait(15)
            kwargs['event']=event
            return export_batch(*args,**kwargs)
        try:
            with patch.object(app,'_selected_browser_entries',return_value=[parent]), \
                 patch('recoverydesk.gui.filedialog.askdirectory',return_value=str(destination)), \
                 patch('recoverydesk.gui.export_batch',side_effect=batch), \
                 patch('recoverydesk.gui.threading.Thread',side_effect=thread), \
                 patch('recoverydesk.gui._messagebox.askyesno',return_value=True), \
                 patch('recoverydesk.gui._messagebox.showerror') as error:
                app.export_browser_selection();self.pump(lambda:reached.is_set())
                app._export_progress_window.destroy();self.close_main()
                self.assertTrue(app.export_cancel.is_set());self.assertFalse(app._closing)
                release.set();self.pump(lambda:app._closing)
                error.assert_not_called()
            self.assertTrue(Path(app.export_result.log).is_file())
            self.assertTrue(app.export_result.cancelled)
            self.assertEqual(source.read_bytes(),data)
            resumed=export_batch(str(source),index,[parent],str(destination))
            self.assertEqual(resumed.failed,0)
        finally:
            release.set()
            for worker in threads:worker.join(10)
