import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.batch_export import export_batch
from recoverydesk.ntfs_browser import scan_ntfs_tree
from recoverydesk.i18n import LANGUAGES,translate
from test_browser import image_with_folders


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class ExportWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        env=patch.dict(os.environ,{'TENSHI_SETTINGS_FILE':str(self.root/'settings.json'),
                                   'TENSHI_LOG_DIR':str(self.root/'logs')})
        env.start();self.addCleanup(env.stop)
        self.app=RecoveryDeskApp();self.addCleanup(self.app.destroy)

    def pump_until(self, predicate, seconds=7):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            self.app.update()
            if predicate():return
            time.sleep(.01)
        self.fail('GUI condition timed out')

    def test_real_export_continues_after_window_close_and_reopen(self):
        source=self.root/'source.img';source.write_bytes(image_with_folders())
        index=scan_ntfs_tree(str(source))
        parent=next(e for e in index.list_dir(5) if e.name=='Dokumente')
        target=self.root/'out';target.mkdir()
        self.app.browser_source=str(source);self.app.browser_index=index
        paused=threading.Event();resume=threading.Event();threads=[]
        real_thread=threading.Thread
        def thread(*args,**kwargs):
            worker=real_thread(*args,**kwargs);threads.append(worker);return worker
        def batch(*args,**kwargs):
            send=kwargs['event']
            def event(data):
                send(data)
                if data['type']=='bytes' and not paused.is_set():
                    paused.set();resume.wait(15)
            kwargs['event']=event
            return export_batch(*args,**kwargs)
        try:
            with patch.object(self.app,'_selected_browser_entries',return_value=[parent]), \
                 patch('recoverydesk.gui.filedialog.askdirectory',return_value=str(target)), \
                 patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
                 patch('recoverydesk.gui.export_batch',side_effect=batch), \
                 patch('recoverydesk.gui.messagebox.showwarning') as warning, \
                 patch('recoverydesk.gui.threading.Thread',side_effect=thread):
                self.app.export_browser_selection()
                self.pump_until(lambda:paused.is_set() and self.app.export_progress.written_bytes>0)
                first=self.app._export_progress_window
                self.assertTrue(first.winfo_exists())
                self.assertFalse(self.app.grab_current())
                self.assertEqual(self.app.export_blocks.confirmed_fraction,0)
                first.destroy()
                self.assertTrue(self.app.export_running)
                self.assertFalse(self.app.export_cancel.is_set())
                second=self.app._show_export_progress()
                self.assertIsNot(first,second)
                self.assertEqual(self.app.export_blocks.confirmed_fraction,0)
                resume.set()
                self.pump_until(lambda:not self.app.export_running)
                second.refresh_display()
                self.assertFalse(self.app.export_result.failed)
                self.assertFalse(self.app.export_result.checksum_errors)
                warning.assert_not_called()
                self.assertEqual(self.app.export_blocks.confirmed_fraction,1)
                self.assertEqual(str(second.save_button.cget('state')),'normal')
                self.assertEqual(str(second.pause_button.cget('state')),'disabled')
                self.assertTrue(Path(self.app.export_result.log).is_file())
        finally:
            resume.set()
            for worker in threads:worker.join(timeout=3)

    def test_raster_and_actions_survive_language_theme_and_small_window(self):
        app=self.app
        app.export_running=True
        app._handle_export_event(dict(type='plan',total=1,total_bytes=100,items=[]))
        app._handle_export_event(dict(type='start',path='named file.txt',size=100))
        app._handle_export_event(dict(type='bytes',path='named file.txt',delta=50))
        win=app._show_export_progress()
        for language in LANGUAGES:
            app.change_language(language)
            for theme in ('dark','light'):
                app.change_theme(theme)
                win.geometry('620x550+0+0')
                app.update();win.refresh_display();app.update_idletasks()
                self.assertEqual(len(win.grid_view.find_all()),200)
                self.assertEqual(win.labels['phase'].cget('text'),translate('Datei kopieren',language))
                for widget in (win.close_button,win.pause_button,win.cancel_button,win.save_button,win.folder_button,win.report_button):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertGreaterEqual(widget.winfo_width(),widget.winfo_reqwidth(),str(widget.cget('text')))
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),win.winfo_rooty()+win.winfo_height())
                self.assertGreater(win.grid_view.winfo_height(),60)
                x1,y1,x2,y2=win.grid_view.coords(win.grid_view.rectangles[0])
                self.assertAlmostEqual(x2-x1,y2-y1)
                for label in list(win.labels.values())+list(win.legend_labels.values()):
                    self.assertLessEqual(label.winfo_rooty()+label.winfo_height(),win.winfo_rooty()+win.winfo_height())
        before=win.grid_view.find_all()
        win.refresh_display()
        self.assertEqual(before,win.grid_view.find_all())
        win.pause_button.invoke()
        self.assertFalse(app.export_cancel.is_set())
        self.assertTrue(app.export_pause.requested)
        self.assertTrue(app.export_running)
        win.refresh_display()
        self.assertEqual(str(win.pause_button.cget('state')),'normal')
        self.assertEqual(win.pause_button.cget('text'),translate('Fortsetzen',app.language))
        win.pause_button.invoke()
        self.assertFalse(app.export_pause.requested)
        win.destroy()

    def test_report_save_keeps_the_original_export_source_mapping(self):
        from types import SimpleNamespace
        report=self.root/'report.txt';report.write_text('complete report')
        app=self.app
        export_folder=self.root/'export';export_folder.mkdir()
        app.export_result=SimpleNamespace(log=str(report),root=str(export_folder))
        app._export_source='original.img'
        app.browser_source='another.img'
        target=str(self.root/'copy.txt')
        with patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=target) as dialog, \
             patch('recoverydesk.gui.copy_export_report') as save, \
             patch('recoverydesk.gui.messagebox.showinfo'), \
             patch('recoverydesk.gui.threading.Thread',side_effect=lambda *,target,**_:SimpleNamespace(start=target)):
            app._save_export_report()
            app._drain_scan_callbacks()
        save.assert_called_once_with('original.img',str(report),target)
        self.assertEqual(dialog.call_args.kwargs['initialdir'],str(export_folder))
        self.assertTrue(dialog.call_args.kwargs['initialfile'].startswith('Tenshi_Exportbericht_'))

    def test_resume_verification_is_distinct_from_new_copy_in_all_languages(self):
        app=self.app;app.export_running=True
        app._handle_export_event(dict(type='plan',total=1,total_bytes=100,items=[],resumed=True))
        app._handle_export_event(dict(type='start',path='saved.bin',size=100))
        app._handle_export_event(dict(type='verify',path='saved.bin',size=100,read=100,existing=True))
        win=app._show_export_progress()
        for language in LANGUAGES:
            app.change_language(language)
            for theme in ('light','dark'):
                app.change_theme(theme);win.geometry('620x550+0+0')
                app.update();win.refresh_display();app.update_idletasks()
                self.assertEqual(win.labels['phase'].cget('text'),translate('Vorhandene Datei prüfen',language))
                self.assertEqual(win.labels['verification'].cget('text'),translate('Vorhandene Datei wird geprüft, nicht erneut kopiert.',language))
                self.assertIn(translate('Bestehender Export erkannt.',language),win.labels['scope'].cget('text'))
                self.assertIn(translate('Pause erhält den aktuellen Stand, solange Tenshi geöffnet bleibt.',language),win.labels['note'].cget('text'))
                for label in win.labels.values():
                    self.assertLessEqual(label.winfo_rooty()+label.winfo_height(),win.winfo_rooty()+win.winfo_height())
                self.assertGreater(win.grid_view.winfo_height(),60)
                self.assertEqual(app.export_progress.written_bytes,0)
                self.assertEqual(app.export_blocks.confirmed_fraction,0)
        app._handle_export_event(dict(type='done',path='saved.bin',size=100,status='Bereits verifiziert'))
        self.assertFalse(app.export_progress.verifying_existing)
        self.assertEqual(app.export_blocks.confirmed_fraction,1)
        app._handle_export_event(dict(type='start',path='new.bin',size=100))
        app._handle_export_event(dict(type='verify',path='new.bin',size=100,read=20))
        win.refresh_display()
        self.assertEqual(win.labels['phase'].cget('text'),translate('SHA256 prüfen',app.language))
        self.assertFalse(app.export_progress.verifying_existing)

    def test_export_confirmation_explains_resume_without_changing_the_target(self):
        app=self.app;app.browser_index=object();app.browser_source='source.img'
        target='X:/Datei kopieren/{count}/日本語'
        with patch.object(app,'_selected_browser_entries',return_value=[object()]), \
             patch('recoverydesk.gui.ensure_safe_destination'), \
             patch('recoverydesk.gui.filedialog.askdirectory',return_value=target), \
             patch('recoverydesk.gui._messagebox.askyesno',return_value=False) as ask:
            for language in LANGUAGES:
                app.change_language(language);app.export_browser_selection()
                text=ask.call_args.args[1]
                self.assertIn(target,text)
                if language=='de':self.assertIn('Unvollständige Dateien beginnen von vorn.',text)
                else:self.assertNotIn('Unvollständige Dateien',text)
        self.assertFalse(app.export_running)

    def test_checksum_save_phases_and_failures_are_visible_in_all_languages(self):
        from recoverydesk.batch_export import BatchResult
        app=self.app;app.export_running=True
        app._handle_export_event(dict(type='plan',total=1,total_bytes=100,items=[]))
        win=app._show_export_progress()
        for language in LANGUAGES:
            app.change_language(language)
            for phase,text in [('individual','Prüfsummendatei speichern …'),('summary','Prüfsummen zusammenfassen …')]:
                app._handle_export_event(dict(type='checksums',phase=phase));win.refresh_display()
                self.assertEqual(win.labels['phase'].cget('text'),translate(text,language))
                self.assertEqual(win.labels['verification'].cget('text'),'')
            result=BatchResult(exported=1,checksum_errors=['disk full (checksum file)'])
            with patch('recoverydesk.gui._messagebox.showwarning') as warning:
                app._handle_export_event(dict(type='run_finish',result=result))
            warning.assert_called_once()
            self.assertIn('disk full (checksum file)',warning.call_args.args[1])
            self.assertTrue(app.export_progress.failed)
            win.refresh_display()
            self.assertEqual(win.labels['phase'].cget('text'),translate('Beendet mit Fehlern',language))
            app.export_running=True;app.export_progress.ended=False

    def test_report_dialog_suggests_a_new_filename_on_each_save(self):
        from types import SimpleNamespace
        report=self.root/'report.txt';report.write_text('original report')
        self.app.export_result=SimpleNamespace(log=str(report),root=str(self.root))
        with patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value='') as dialog:
            self.app._save_export_report();self.app._save_export_report()
        names=[call.kwargs['initialfile'] for call in dialog.call_args_list]
        self.assertEqual(len(set(names)),2)
        self.assertEqual(report.read_text(),'original report')

    def test_idle_and_between_file_phases_do_not_claim_to_build_a_new_plan(self):
        app=self.app;app.change_language('de')
        win=app._show_export_progress()
        self.assertEqual(win.labels['phase'].cget('text'),'Noch kein Stapel-Export gestartet.')
        app.export_running=True
        app._handle_export_event(dict(type='plan',total=2,total_bytes=100,items=[]))
        app._handle_export_event(dict(type='start',path='first',size=50))
        app._handle_export_event(dict(type='done',path='first',size=50,status='Erfolgreich'))
        win.refresh_display()
        self.assertEqual(win.labels['phase'].cget('text'),'Export läuft …')
        app._handle_export_event(dict(type='start',path='second',size=50))
        app._handle_export_event(dict(type='done',path='second',size=50,status='Erfolgreich'))
        win.refresh_display()
        self.assertEqual(win.labels['phase'].cget('text'),'Export wird abgeschlossen …')

