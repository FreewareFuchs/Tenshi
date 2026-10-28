import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from tkinter import ttk
from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.imaging import create_image,ImagingProgress
from recoverydesk.imaging_window import ImagingProgressWindow,LEGEND
from recoverydesk.imaging_blocks import ImagingBlocks
from recoverydesk.i18n import LANGUAGES,translate


def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Display required')
class ImagingWindowTests(unittest.TestCase):
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
            self.app.update()
            if predicate():return
            time.sleep(.01)
        self.fail('GUI condition timed out')

    def test_close_reopen_pause_resume_and_save_report_for_actual_image(self):
        source=self.root/'source.img';source.write_bytes(bytes(range(256))*8192)
        dest=self.root/'target.img';self.app.source_path.set(str(source))
        setup=self.app.open_imaging_dialog()
        entry=next(w for w in walk(setup) if isinstance(w,ttk.Entry));entry.insert(0,str(dest))
        begin=next(w for w in walk(setup) if isinstance(w,ttk.Button) and w.cget('text')=='Image erstellen / fortsetzen')
        paused=threading.Event();release=threading.Event();threads=[]
        real_thread=threading.Thread
        def thread(*args,**kwargs):
            worker=real_thread(*args,**kwargs);threads.append(worker);return worker
        def copy(*args,**kwargs):
            send=kwargs['progress']
            def progress(item):
                send(item)
                if item.processed>=1024*1024 and not paused.is_set():
                    paused.set();release.wait(15)
            kwargs['progress']=progress
            return create_image(*args,**kwargs)
        try:
            with patch('recoverydesk.gui.create_image',side_effect=copy), \
                 patch('recoverydesk.gui.threading.Thread',side_effect=thread), \
                 patch('recoverydesk.gui.messagebox.askyesno',return_value=True), \
                 patch('recoverydesk.gui.messagebox.showinfo'), \
                 patch('recoverydesk.gui.messagebox.showwarning'), \
                 patch('recoverydesk.gui.messagebox.showerror') as error:
                begin.invoke();s=self.app._imaging_session
                self.pump(lambda:paused.is_set() and s['blocks'].processed>=1024*1024)
                first=s['window'];first.destroy()
                self.app.tk.call(setup.protocol('WM_DELETE_WINDOW'))
                self.assertTrue(s['running']);self.assertFalse(s['stop'].is_set())
                with patch.object(self.app,'get_source',side_effect=AssertionError('job source must stay captured')):
                    self.assertIs(self.app.open_imaging_dialog(),setup)
                second=s['window'];self.assertIsNot(first,second)
                self.assertEqual(s['blocks'].cell_states().count('confirmed'),50)
                second.buttons['pause'].invoke();release.set()
                self.pump(lambda:not s['running'])
                self.assertEqual(s['state'],'paused')
                self.assertNotIn('VERIFIZIERT:',second.labels['verification'].cget('text'))
                second.buttons['settings'].invoke();begin.invoke()
                self.pump(lambda:not s['running'])
                self.assertEqual(s['report']['verification']['status'],'verified')
                self.assertEqual(set(s['blocks'].cell_states()),{'confirmed'})
                self.assertEqual(dest.read_bytes(),source.read_bytes())
                saved=self.root/'saved-report.txt'
                with patch('recoverydesk.gui.filedialog.asksaveasfilename',return_value=str(saved)) as dialog:
                    second.buttons['save'].invoke()
                    self.pump(lambda:not s['saving'])
                    self.assertEqual(dialog.call_args.kwargs['initialdir'],str(self.root))
                    before=saved.read_bytes()
                    second.buttons['save'].invoke();self.pump(lambda:not s['saving'])
                    self.assertEqual(saved.read_bytes(),before)
                error.assert_called_once()  # existing report cannot be replaced
        finally:
            release.set()
            session=self.app.__dict__.get('_imaging_session')
            if session:session['stop'].set()
            for worker in threads:worker.join(10)

    def test_small_window_all_languages_themes_and_verification_phase(self):
        b=ImagingBlocks();b.handle(ImagingProgress(100,100,1,1,'complete',((33,1),)))
        s=dict(blocks=b,running=True,state='verifying',stop=threading.Event(),started=time.monotonic(),
               baseline=0,report=None,destination=str(self.root/'copy.img'),saving=False,error='',ended=None)
        win=ImagingProgressWindow(self.app,s,pause=s['stop'].set,report=lambda:None,
            save=lambda:None,folder=lambda:None,settings=lambda:None)
        self.addCleanup(win.destroy)
        for language in LANGUAGES:
            self.app.change_language(language)
            for theme in ('dark','light'):
                self.app.change_theme(theme);win.geometry('660x590+0+0')
                self.app.update();win.refresh_display();self.app.update_idletasks()
                self.assertEqual(win.labels['phase'].cget('text'),translate('Vollvergleich läuft …',language))
                self.assertIn('error',b.cell_states())
                for widget in [*win.labels.values(),*win.legend.values(),*win.buttons.values()]:
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),win.winfo_rooty()+win.winfo_height())
                for button in win.buttons.values():
                    self.assertGreaterEqual(button.winfo_width(),button.winfo_reqwidth(),button.cget('text'))
                x1,y1,x2,y2=win.grid_view.coords(win.grid_view.rectangles[0])
                self.assertAlmostEqual(x2-x1,y2-y1)
                self.assertGreater(x2-x1,4)
                self.assertEqual(len(win.grid_view.find_all()),200)
        for phrase in [*LEGEND.values(),'100 Felder = 100 % der Quellbytes.']:
            for language in LANGUAGES:
                if language!='de':self.assertNotEqual(translate(phrase,language),phrase)
