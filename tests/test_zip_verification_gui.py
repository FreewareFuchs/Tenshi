"""Exercise the optional exported-ZIP action through the actual Tk dialog."""
import os
from pathlib import Path
import tempfile
import time
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from recoverydesk.gui import RecoveryDeskApp


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class ZipVerificationGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(self.root / 'settings.json')})
        env.start()
        self.addCleanup(env.stop)
        self.app = RecoveryDeskApp()
        self.addCleanup(self.app.destroy)
        self.app.withdraw()

    def walk(self, root):
        yield root
        for child in root.winfo_children():
            yield from self.walk(child)

    def test_export_report_action_checks_real_zip_and_keeps_report(self):
        report = self.root / 'report.txt'
        report.write_text('Original export report', encoding='utf-8')
        archive = self.root / 'export.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as out:
            out.writestr('test.txt', b'known reference')
        before = archive.read_bytes()
        self.app.export_result = SimpleNamespace(log=str(report))
        self.app._show_export_results()
        button = next(w for w in self.walk(self.app) if isinstance(w, ttk.Button)
                      and w.cget('text') == 'Exportierte ZIP-Datei prüfen …')
        with patch('recoverydesk.gui.filedialog.askopenfilename', return_value=str(archive)):
            button.invoke()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.app.update()
            labels = [w.cget('text') for w in self.walk(self.app) if isinstance(w, ttk.Label)]
            if any('ZIP-Struktur und CRC-Prüfsummen ohne Fehler geprüft.' in text for text in labels):
                break
            time.sleep(.01)
        else:
            self.fail('ZIP worker did not report a successful check')
        self.assertEqual(archive.read_bytes(), before)
        self.assertEqual(report.read_text(), 'Original export report')
        self.assertTrue(any('Kein Vergleich mit dem Original' in text for text in labels))

    def test_cancelling_file_picker_does_not_start_check(self):
        before = self.app.winfo_children()
        with patch('recoverydesk.gui.filedialog.askopenfilename', return_value=''), \
                patch('recoverydesk.gui.verify_zip') as check:
            self.app._check_exported_zip(self.app, str(self.root))
        check.assert_not_called()
        self.assertEqual(self.app.winfo_children(), before)
