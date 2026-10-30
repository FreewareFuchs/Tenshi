"""Source-backed previews, content-check controls, cancellation and layout."""
import os
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from recoverydesk.content_check import ContentCancelled,describe_result,MESSAGES,STATUS,CONTENT_SCOPE
from recoverydesk.content_worker import result,MAX_INPUT
from recoverydesk.content_smoke import pdf_fixture
from recoverydesk.filesystems import scan_tree
from recoverydesk.i18n import LANGUAGES,translate
from test_content_check import picture,file_image
import test_preview_worker_gui as preview_tests


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'GUI required')
class ContentGuiTests(unittest.TestCase):
    setUp=preview_tests.PreviewWorkerGuiTests.setUp
    widgets=preview_tests.PreviewWorkerGuiTests.widgets
    wait_for=preview_tests.PreviewWorkerGuiTests.wait_for

    def fixture(self,data=None,name='PHOTO   JPG'):
        self.original=file_image(picture() if data is None else data,name)
        self.source.write_bytes(self.original)
        self.app.browser_index=scan_tree(str(self.source))
        self.item=next(entry for entry in self.app.browser_index.entries if not entry.is_directory)
        context=patch.object(self.app,'_selected_browser_entries',return_value=[self.item])
        context.start();self.addCleanup(context.stop)
        self.app.change_language('de')

    def window(self):
        return next(child for child in self.app.winfo_children() if isinstance(child,tk.Toplevel))

    def button(self,window,label):
        return next(widget for widget in self.widgets(window) if isinstance(widget,ttk.Button) and widget.cget('text')==label)

    def test_jpeg_bmp_and_pdf_previews_are_fitted_images_without_source_writes(self):
        for data,name in ((picture(),'PHOTO   JPG'),(picture('BMP'),'PHOTO   BMP'),(pdf_fixture(),'PAGE    PDF')):
            with self.subTest(name=name):
                self.fixture(data,name);self.app.preview_entry();window=self.window()
                self.wait_for(lambda:any(isinstance(widget,tk.Canvas) and hasattr(widget,'image') for widget in self.widgets(window)))
                canvas=next(widget for widget in self.widgets(window) if isinstance(widget,tk.Canvas))
                self.assertLessEqual(canvas.image.width(),720);self.assertLessEqual(canvas.image.height(),360)
                self.assertEqual(self.source.read_bytes(),self.original)
                window.destroy()

    def test_content_check_reports_scope_and_keeps_read_check_available(self):
        self.fixture();self.app.inspect_file();window=self.window()
        self.button(window,'Inhalt prüfen').invoke()
        self.wait_for(lambda:any(isinstance(widget,tk.Text) and 'Bilddaten dekodiert' in widget.get('1.0','end') for widget in self.widgets(window)))
        text=next(widget.get('1.0','end') for widget in self.widgets(window) if isinstance(widget,tk.Text))
        self.assertIn('Originalinhalte',text)
        self.assertEqual(str(self.button(window,'Vollständig lesend prüfen').cget('state')),'normal')
        self.assertEqual(str(self.button(window,'Prüfung abbrechen').cget('state')),'disabled')
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_check_buttons_are_visible_at_small_size_in_six_languages(self):
        self.fixture()
        for language in LANGUAGES:
            self.app.change_language(language);self.app.inspect_file();window=self.window()
            window.geometry('650x520+0+0');self.app.update()
            self.wait_for(lambda:any(isinstance(widget,ttk.Button) and widget.cget('text')==translate('Inhalt prüfen',language) for widget in self.widgets(window)))
            for label in ('Inhalt prüfen','Vollständig lesend prüfen','Prüfung abbrechen','Schließen'):
                button=self.button(window,translate(label,language))
                self.assertTrue(button.winfo_ismapped(),language)
                self.assertGreaterEqual(button.winfo_width(),button.winfo_reqwidth(),language)
                self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),window.winfo_rooty()+window.winfo_height(),language)
            window.destroy()

    def test_closing_during_content_check_cancels_worker_and_ignores_result(self):
        self.fixture();started=threading.Event();finished=threading.Event()
        def check(*args,**kwargs):
            started.set()
            try:
                deadline=time.monotonic()+4
                while time.monotonic()<deadline:
                    if kwargs['cancel']():raise ContentCancelled()
                    time.sleep(.01)
                self.fail('Closing did not cancel the content check')
            finally:finished.set()
        with patch('recoverydesk.gui.check_content_file',side_effect=check),patch.object(self.app,'report_callback_exception') as error:
            self.app.inspect_file();window=self.window();self.button(window,'Inhalt prüfen').invoke()
            self.assertTrue(started.wait(1));window.destroy()
            self.wait_for(finished.is_set);self.app.update();error.assert_not_called()
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_large_file_has_disabled_content_check(self):
        self.fixture();self.item.size=MAX_INPUT+1
        self.app.inspect_file();window=self.window()
        self.assertEqual(str(self.button(window,'Inhalt prüfen').cget('state')),'disabled')
        self.assertEqual(str(self.button(window,'Vollständig lesend prüfen').cget('state')),'normal')

    def test_export_result_action_checks_target_and_preserves_report_and_checksum(self):
        from pathlib import Path
        from recoverydesk.batch_export import export_batch
        self.fixture();target=Path(self.tmp.name)/'export';target.mkdir()
        report=export_batch(str(self.source),self.app.browser_index,[self.item],str(target))
        self.app.export_result=report
        file=next((Path(report.root)/'files').glob('*.JPG'))
        before={path:path.read_bytes() for path in Path(report.root).rglob('*') if path.is_file()}
        with patch('recoverydesk.gui.filedialog.askopenfilename',return_value=str(file)) as choose:
            self.app._show_export_results();window=self.window()
            self.button(window,'Exportierte Datei prüfen …').invoke()
            self.wait_for(lambda:any(isinstance(widget,tk.Text) and 'Bilddaten dekodiert' in widget.get('1.0','end') for widget in self.widgets(window)))
        self.assertEqual(choose.call_args.kwargs['initialdir'],str(Path(report.root)/'files'))
        self.assertEqual({path:path.read_bytes() for path in before},before)
        self.assertEqual(self.source.read_bytes(),self.original)


class ContentTranslationTests(unittest.TestCase):
    def test_status_and_result_messages_are_translated_without_losing_placeholders(self):
        import string
        for text in (*STATUS.values(),*MESSAGES.values(),CONTENT_SCOPE):
            fields={field for _,field,_,_ in string.Formatter().parse(text) if field}
            for language in LANGUAGES:
                translated=translate(text,language)
                if language!='de':self.assertNotEqual(translated,text,(language,text))
                self.assertEqual({field for _,field,_,_ in string.Formatter().parse(translated) if field},fields)
        for language in LANGUAGES:
            answer=result('partial','PDF','pdf_first_page',pages=7)
            text=describe_result(answer,language)
            self.assertIn('7',text);self.assertNotIn('{pages}',text)
