import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk import support_report as report
from recoverydesk.i18n import LANGUAGES, translate
from recoverydesk.version_info import BuildInfo


class SupportReportTests(unittest.TestCase):
    def test_error_counts_discard_private_or_malformed_lines(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'log'
            path.write_text(
                '2026-10-23 21:00:00,000 ERROR operation=open_source error=PermissionError code=13 \n'
                '2026-10-23 21:00:01,000 ERROR operation=scan error=OSError code=5 offset=42\n'
                '2026-10-23 21:00:02,000 ERROR operation=scan error=OSError code=5 \n'
                '2026-10-23 21:00:03,000 ERROR operation=scan error=OSError code=5 /home/private.txt\n'
                '/home/private.txt secret contents\n', encoding='utf-8')
            summary = report.error_summary(path)
            self.assertEqual(summary, dict(state='complete', records=3, codes={'13': 1, '5': 2}))
            self.assertNotIn('private', json.dumps(summary))
            self.assertNotIn('PermissionError', json.dumps(summary))

    def test_bounded_tail_and_missing_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'log'
            self.assertEqual(report.error_summary(path)['state'], 'missing')
            line = b'2026-10-23 21:00:00,000 ERROR operation=scan error=OSError code=5 \n'
            path.write_bytes(b'x' * (report.LOG_LIMIT * 2) + b'\n' + line)
            summary = report.error_summary(path)
            self.assertEqual(summary['state'], 'tail')
            self.assertEqual(summary['records'], 1)
            self.assertEqual(report.error_summary(Path(temporary))['state'], 'unavailable')

    def test_snapshot_has_fixed_fields_and_preserves_build_identity(self):
        info = BuildInfo(commit='a' * 40)
        with patch.object(report, 'build_info', return_value=info), \
             patch.object(report, 'error_summary', return_value=dict(state='missing', records=0, codes={})):
            data = report.collect_report(language='ja', tk_version='8.6', window_system='x11')
        self.assertEqual(data['build']['commit'], 'a' * 40)
        self.assertEqual(data['language'], 'ja')
        self.assertEqual(set(data), {'schema', 'product', 'build', 'system', 'runtime', 'language', 'errors', 'scope'})
        self.assertEqual(json.loads(report.report_text(data)), data)
        self.assertNotIn(str(Path.home()), report.report_text(data))

    def test_save_is_exclusive_and_checks_each_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'report.json'
            with patch('recoverydesk.sources.ensure_safe_destination') as guard:
                report.save_report(target, '{"test": "日本語"}\n', ('source-a', 'source-b', 'source-a', ''))
                self.assertEqual(guard.call_count, 2)
            self.assertIn('日本語', target.read_text(encoding='utf-8'))
            with self.assertRaises(FileExistsError):
                report.save_report(target, 'replacement')
            self.assertIn('日本語', target.read_text(encoding='utf-8'))
            forbidden = Path(temporary) / 'forbidden.json'
            with patch('recoverydesk.sources.ensure_safe_destination', side_effect=ValueError('same disk')):
                with self.assertRaises(ValueError):
                    report.save_report(forbidden, '{}', ('source',))
            self.assertFalse(forbidden.exists())

    def test_support_ui_strings_in_every_language(self):
        for language in LANGUAGES:
            for text in ('Support-Bericht', 'Support-Bericht speichern',
                         'Vorschau: technische Metadaten und Fehlercodes. Keine Pfade, Dateinamen oder Dateiinhalte. Der Bericht wird nur lokal gespeichert.'):
                if language != 'de':
                    self.assertNotEqual(translate(text, language), text)


class SupportReportGuiTests(unittest.TestCase):
    def test_preview_and_cancel_do_not_save(self):
        import tkinter as tk
        from tkinter import ttk
        from recoverydesk.gui import RecoveryDeskApp
        try:
            app = RecoveryDeskApp()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        try:
            with patch('recoverydesk.support_report.save_report') as save, \
                 patch('recoverydesk.gui.filedialog.asksaveasfilename', return_value=''):
                win = app.show_support_report()
                app.update_idletasks()
                widgets = list(win.winfo_children()[0].winfo_children())
                output = next(w for w in widgets if isinstance(w, tk.Text))
                data = json.loads(output.get('1.0', 'end'))
                self.assertEqual(data['product'], 'Tenshi')
                self.assertEqual(output.cget('state'), 'disabled')
                next(w for w in widgets if isinstance(w, ttk.Button)).invoke()
                save.assert_not_called()
                win.destroy()
        finally:
            app.destroy()
