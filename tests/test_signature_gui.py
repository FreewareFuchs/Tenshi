"""Signature scan publication, cancellation and original-source ownership."""
import os
import threading
import time
from tkinter import ttk
import unittest
from unittest.mock import patch

import test_preview_worker_gui as preview_tests
from test_signature_search import picture
from recoverydesk.signature_search import scan_signatures,FILESYSTEM
from recoverydesk.filesystems import ScanCancelled
from recoverydesk.i18n import LANGUAGES,translate


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'GUI required')
class SignatureGuiTests(unittest.TestCase):
    setUp=preview_tests.PreviewWorkerGuiTests.setUp
    widgets=preview_tests.PreviewWorkerGuiTests.widgets
    wait_for=preview_tests.PreviewWorkerGuiTests.wait_for

    def prepare(self):
        self.source.write_bytes(b'X'*512+picture('JPEG')+b'X'*512+picture('PNG'))
        self.app.source_path.set(str(self.source))

    def test_real_scan_publishes_candidates_without_changing_source(self):
        self.prepare();before=self.source.read_bytes()
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called()
        self.assertEqual(self.app.browser_fs,FILESYSTEM);self.assertEqual(len(self.app.browser_index.entries),2)
        self.assertIn('Signatursuche beendet',self.app.status.get());self.assertEqual(self.source.read_bytes(),before)
        self.assertEqual(str(self.app.ntfs_cancel_btn.cget('state')),'disabled')

    def test_decline_keeps_previous_browser(self):
        self.prepare();index=self.app.browser_index
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=False),patch('recoverydesk.signature_search.scan_signatures') as scan:
            self.app.start_signature_scan()
        scan.assert_not_called();self.assertIs(self.app.browser_index,index)

    def test_cancelled_scan_does_not_publish_an_index(self):
        self.prepare();started=threading.Event()
        def scan(*args,cancel,**kwargs):
            started.set()
            end=time.monotonic()+2
            while not cancel() and time.monotonic()<end:time.sleep(.005)
            raise ScanCancelled()
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.signature_search.scan_signatures',side_effect=scan),patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_signature_scan();self.assertTrue(started.wait(1));self.app._cancel_scan()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        error.assert_not_called();self.assertIsNone(self.app.browser_index)

    def test_results_from_previous_source_are_discarded(self):
        self.prepare();index=scan_signatures(str(self.source));release=threading.Event();started=threading.Event()
        self.addCleanup(release.set)
        def scan(*args,**kwargs):started.set();release.wait(2);return index
        with patch('recoverydesk.gui.messagebox.askyesno',return_value=True),patch('recoverydesk.signature_search.scan_signatures',side_effect=scan):
            self.app.start_signature_scan();self.assertTrue(started.wait(1));self.app._source_generation+=1;release.set()
            self.wait_for(lambda:not self.app.ntfs_scanning)
        self.assertIsNone(self.app.browser_index)

    def test_scan_button_is_available_in_all_six_languages(self):
        self.app.deiconify();self.app.update()
        for language in LANGUAGES:
            self.app.change_language(language);self.app._scan_options_dialog();self.app.update()
            self.wait_for(lambda:any(isinstance(w,ttk.Button) and w.cget('text')==translate('Bildsignaturen suchen',language) for w in self.widgets(self.app)))
            buttons=[w for w in self.widgets(self.app) if isinstance(w,ttk.Button) and w.cget('text')==translate('Bildsignaturen suchen',language)]
            self.assertEqual(len(buttons),2)
            self.assertTrue(buttons[0].winfo_ismapped())
            buttons[0].winfo_toplevel().destroy()
