"""Real session round trip and worker errors through the GUI callback queue."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from recoverydesk.filesystems import scan_tree
from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.session_store import save_session, SessionError
from test_filesystems import fat_img


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI required')
class SessionWorkerGuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        settings = mock.patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(self.root / 'settings.json')})
        settings.start()
        self.addCleanup(settings.stop)
        self.source = self.root / 'source.raw'
        self.source.write_bytes(fat_img())
        self.session = self.root / 'scan.tenshi-session'
        self.index = scan_tree(str(self.source))
        self.app = RecoveryDeskApp()
        self.addCleanup(self.app.destroy)
        self.app.withdraw()
        self.app.source_path.set(str(self.source))
        self.app._set_browser_fs('FAT32')
        self.app._show_browser_index(str(self.source), self.index)

    def wait_done(self):
        deadline = time.monotonic() + 4
        while self.app._session_running and time.monotonic() < deadline:
            self.app.update()
            time.sleep(.005)
        self.assertFalse(self.app._session_running, 'Session worker did not deliver its result')
        self.assertEqual(str(self.app.session_menu_button.cget('state')), 'normal')
        self.assertEqual(self.source.read_bytes(), fat_img())

    def test_real_save_and_load_round_trip(self):
        with mock.patch('recoverydesk.gui.messagebox.showerror') as error:
            with mock.patch('recoverydesk.gui.filedialog.asksaveasfilename', return_value=str(self.session)):
                self.app.save_analysis_session()
                self.wait_done()
            self.assertTrue(self.session.is_file())
            self.app._reset_analysis_for_source()
            self.assertIsNone(self.app.browser_index)
            with mock.patch('recoverydesk.gui.filedialog.askopenfilename', return_value=str(self.session)):
                self.app.load_analysis_session()
                self.wait_done()
            error.assert_not_called()
        self.assertEqual(self.app.browser_index.filesystem, 'FAT32')
        self.assertEqual({entry.name for entry in self.app.browser_index.entries},
                         {entry.name for entry in self.index.entries})
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))

    def test_save_worker_failure_restores_controls(self):
        with mock.patch('recoverydesk.gui.filedialog.asksaveasfilename', return_value=str(self.session)), \
             mock.patch('recoverydesk.gui.save_session', side_effect=PermissionError('test save denied')), \
             mock.patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.save_analysis_session()
            self.wait_done()
        error.assert_called_once()
        self.assertIn('test save denied', error.call_args.args[1])
        self.assertIs(self.app.browser_index, self.index)
        self.assertFalse(self.session.exists())

    def test_load_worker_failure_preserves_current_analysis(self):
        save_session(str(self.session), str(self.source), index=self.index, filesystem='FAT32')
        with mock.patch('recoverydesk.gui.filedialog.askopenfilename', return_value=str(self.session)), \
             mock.patch('recoverydesk.gui.load_session', side_effect=SessionError('test load rejected')), \
             mock.patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.load_analysis_session()
            self.wait_done()
        error.assert_called_once()
        self.assertIn('test load rejected', error.call_args.args[1])
        self.assertIs(self.app.browser_index, self.index)
