"""Captured multi-selection, manual navigation and stale decoder results."""
from dataclasses import replace
import os
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

import test_preview_worker_gui as preview_tests
from recoverydesk.gui import read_preview_file
from recoverydesk.i18n import LANGUAGES,translate


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'GUI required')
class PreviewNavigationTests(unittest.TestCase):
    setUp=preview_tests.PreviewWorkerGuiTests.setUp
    widgets=preview_tests.PreviewWorkerGuiTests.widgets
    wait_for=preview_tests.PreviewWorkerGuiTests.wait_for

    def selected(self,entries=None):
        index=self.app.browser_index
        self.first=next(entry for entry in index.entries if entry.name=='README.TXT')
        self.second=next(entry for entry in index.entries if entry.name=='DATA.BIN')
        context=patch.object(self.app,'_selected_browser_entries',return_value=entries if entries is not None else [self.first,self.second])
        context.start();self.addCleanup(context.stop)
        return context

    def window(self):return next(widget for widget in self.app.winfo_children() if isinstance(widget,tk.Toplevel))

    def button(self,win,label):
        return next(widget for widget in self.widgets(win) if isinstance(widget,ttk.Button) and widget.cget('text')==translate(label,self.app.language))

    def shown(self,win,text):
        return any(isinstance(widget,tk.Text) and text in widget.get('1.0','end') for widget in self.widgets(win))

    def counter(self,win,current,total):
        expected=translate('Datei {current} von {total}',self.app.language).format(current=current,total=total)
        return any(isinstance(widget,ttk.Label) and widget.cget('text')==expected for widget in self.widgets(win))

    def test_previous_next_boundaries_and_one_window(self):
        self.selected();before=self.source.read_bytes()
        self.app.preview_entry();win=self.window();self.wait_for(lambda:self.shown(win,'HELLO'))
        self.assertTrue(self.counter(win,1,2));self.assertEqual(str(self.button(win,'Zurück').cget('state')),'disabled')
        self.button(win,'Weiter').invoke();self.wait_for(lambda:self.shown(win,'ABCDEF'))
        self.assertTrue(self.counter(win,2,2));self.assertIn('DATA.BIN',win.title())
        self.assertEqual(str(self.button(win,'Weiter').cget('state')),'disabled')
        self.button(win,'Zurück').invoke();self.wait_for(lambda:self.shown(win,'HELLO'))
        self.assertTrue(self.counter(win,1,2));self.assertEqual(self.window(),win)
        self.assertEqual(self.source.read_bytes(),before)
        thread=win._preview_thread;win.destroy();self.wait_for(lambda:not thread.is_alive())

    def test_original_source_and_selection_remain_captured(self):
        self.selected();source,index=self.app.browser_source,self.app.browser_index
        self.app.preview_entry();win=self.window();self.wait_for(lambda:self.shown(win,'HELLO'))
        self.app.browser_source='must-not-open.img';self.app.browser_index=None
        with patch.object(self.app,'_selected_browser_entries',side_effect=AssertionError('Selection changed')),patch('recoverydesk.gui.read_preview_file',wraps=read_preview_file) as read:
            self.button(win,'Weiter').invoke();self.wait_for(lambda:self.shown(win,'ABCDEF'))
        self.assertEqual(read.call_args.args[:2],(source,index))

    def test_rapid_navigation_skips_cancelled_jobs_and_ignores_old_error(self):
        self.selected();started=threading.Event();release=threading.Event();self.addCleanup(release.set)
        calls=[];active=0;maximum=0
        def delayed(source,index,entry,*args,**kwargs):
            nonlocal active,maximum
            active+=1;maximum=max(maximum,active);calls.append(entry.name)
            try:
                if len(calls)==1:
                    started.set();release.wait(3);raise OSError('stale preview error')
                return read_preview_file(source,index,entry,*args,**kwargs)
            finally:active-=1
        with patch('recoverydesk.gui.read_preview_file',side_effect=delayed),patch.object(self.app,'report_callback_exception') as error:
            self.app.preview_entry();win=self.window();self.assertTrue(started.wait(1))
            self.button(win,'Weiter').invoke();self.button(win,'Zurück').invoke();self.button(win,'Weiter').invoke()
            self.assertTrue(self.counter(win,2,2));release.set()
            self.wait_for(lambda:self.shown(win,'ABCDEF'));self.app.update()
            self.assertNotIn('stale preview error',str([widget.cget('text') for widget in self.widgets(win) if isinstance(widget,ttk.Label)]))
            self.assertEqual(calls,['README.TXT','DATA.BIN']);self.assertEqual(maximum,1);error.assert_not_called()

    def test_folders_are_ignored_and_unreadable_files_remain_navigable(self):
        self.selected();folder=next(entry for entry in self.app.browser_index.entries if entry.is_directory)
        blocked=replace(self.second,unsupported_reason='Kein unterstützter Datenstrom')
        with patch.object(self.app,'_selected_browser_entries',return_value=[folder,self.first,blocked]),patch('recoverydesk.gui.read_preview_file',wraps=read_preview_file) as read:
            self.app.preview_entry();win=self.window();self.wait_for(lambda:self.shown(win,'HELLO'))
            self.assertTrue(self.counter(win,1,2));self.button(win,'Weiter').invoke();self.app.update()
            self.assertTrue(self.counter(win,2,2));self.assertEqual(read.call_count,1)
            self.assertTrue(any(isinstance(widget,ttk.Label) and 'Kein unterstützter' in widget.cget('text') for widget in self.widgets(win)))
            self.button(win,'Zurück').invoke();self.wait_for(lambda:self.shown(win,'HELLO'))

    def test_controls_visible_and_translated_in_six_languages(self):
        self.selected()
        for language in LANGUAGES:
            self.app.change_language(language);self.app.preview_entry();win=self.window()
            win.geometry('650x500+0+0');self.app.update()
            self.wait_for(lambda:any(isinstance(widget,ttk.Button) and widget.cget('text')==translate('Weiter',language) for widget in self.widgets(win)))
            self.assertTrue(self.counter(win,1,2))
            for label in ('Zurück','Weiter','Schließen'):
                button=self.button(win,label)
                self.assertTrue(button.winfo_ismapped());self.assertGreaterEqual(button.winfo_width(),button.winfo_reqwidth())
                self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),win.winfo_rooty()+win.winfo_height())
            win.destroy()

    def test_no_automatic_advance(self):
        self.selected();self.app.preview_entry();win=self.window();self.wait_for(lambda:self.shown(win,'HELLO'))
        # Process ordinary UI polling while the worker remains idle. Navigation
        # must have no scheduled file transition and must keep the first item.
        end=time.monotonic()+.3
        while time.monotonic()<end:self.app.update();time.sleep(.01)
        self.assertTrue(self.counter(win,1,2));self.assertTrue(self.shown(win,'HELLO'))

    def test_close_cancels_active_read_and_stops_worker(self):
        self.selected();started=threading.Event();stopped=threading.Event()
        def read(*args,**kwargs):
            started.set()
            try:
                end=time.monotonic()+3
                while time.monotonic()<end:
                    if kwargs['cancel']():return b'late data'
                    time.sleep(.01)
                self.fail('Preview read was not cancelled')
            finally:stopped.set()
        with patch('recoverydesk.gui.read_preview_file',side_effect=read):
            self.app.preview_entry();win=self.window();thread=win._preview_thread
            self.assertTrue(started.wait(1));win.destroy()
            self.wait_for(lambda:stopped.is_set() and not thread.is_alive())
