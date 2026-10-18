"""Report button and source-change safety tests (virtual Tk display)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from recoverydesk.gui import RecoveryDeskApp

class ReportGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)

    def test_report_save_and_no_overwrite(self):
        source = Path(self.temp.name) / 'quelle.raw'
        source.write_bytes(b'Dummy image')
        target = Path(self.temp.name) / 'report.txt'
        self.app.browser_source = str(source)
        self.app.scan_report_text = 'RecoveryDesk – Testbericht\n'
        with patch('recoverydesk.gui.filedialog.asksaveasfilename', return_value=str(target)), \
             patch('recoverydesk.gui.messagebox.showinfo') as info, \
             patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.save_scan_report()
            self.assertEqual(target.read_text(encoding='utf-8'), 'RecoveryDesk – Testbericht\n')
            info.assert_called_once()
            self.app.save_scan_report()
            error.assert_called_once()
            self.assertEqual(target.read_text(encoding='utf-8'), 'RecoveryDesk – Testbericht\n')
        self.assertEqual(source.read_bytes(), b'Dummy image')

    def test_source_change_clears_previous_report(self):
        self.app.scan_report_text = 'früherer Bericht'
        self.app._reset_analysis_for_source()
        self.assertIsNone(self.app.scan_report_text)

if __name__ == '__main__':
    unittest.main()
