"""Read-only preview delivery and closing while a read is in flight."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest import mock

from recoverydesk.filesystems import scan_tree
from recoverydesk.gui import RecoveryDeskApp
from test_filesystems import fat_img


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI required')
class PreviewWorkerGuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        settings = mock.patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(Path(self.tmp.name) / 'settings.json')})
        settings.start()
        self.addCleanup(settings.stop)
        self.source = Path(self.tmp.name) / 'source.raw'
        self.source.write_bytes(fat_img())
        self.app = RecoveryDeskApp()
        self.addCleanup(self.app.destroy)
        self.app.withdraw()
        index = scan_tree(str(self.source))
        self.item = next(item for item in index.entries if item.name == 'README.TXT')
        self.app.browser_index = index
        self.app.browser_source = str(self.source)
        self.app.browser_fs = 'FAT32'
        selection = mock.patch.object(self.app, '_selected_browser_entries', return_value=[self.item])
        selection.start()
        self.addCleanup(selection.stop)

    def widgets(self, root):
        for child in root.winfo_children():
            yield child
            yield from self.widgets(child)

    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.update()
            time.sleep(.005)
        self.assertTrue(predicate(), 'Preview result was not delivered')

    def test_real_preview_displays_file_contents_without_source_changes(self):
        self.app.preview_entry()
        window = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        self.wait_for(lambda: any(isinstance(w, tk.Text) for w in self.widgets(window)))
        texts = [w.get('1.0', 'end') for w in self.widgets(window) if isinstance(w, tk.Text)]
        self.assertTrue(any('HELLO' in text for text in texts))
        self.assertEqual(self.source.read_bytes(), fat_img())

    def test_read_error_is_displayed(self):
        with mock.patch('recoverydesk.gui.open_source', side_effect=OSError('test preview unavailable')):
            self.app.preview_entry()
            self.wait_for(lambda: any('test preview unavailable' in str(w.cget('text'))
                          for w in self.widgets(self.app) if 'text' in w.keys()))
        self.assertEqual(self.source.read_bytes(), fat_img())

    def test_closed_preview_ignores_late_worker_result(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        @contextmanager
        def delayed_read(*args):
            started.set()
            release.wait(2)
            raise OSError('late read error')
            yield  # contextmanager interface
        with mock.patch('recoverydesk.gui.open_source', side_effect=delayed_read), \
             mock.patch.object(self.app, '_post_scan_callback', wraps=self.app._post_scan_callback) as posted, \
             mock.patch.object(self.app, 'report_callback_exception') as callback_error:
            self.app.preview_entry()
            self.assertTrue(started.wait(1))
            window = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
            window.destroy()
            release.set()
            self.wait_for(lambda: posted.called)
            self.wait_for(lambda: self.app._scan_callbacks.empty())
            callback_error.assert_not_called()
        self.assertEqual(self.source.read_bytes(), fat_img())
