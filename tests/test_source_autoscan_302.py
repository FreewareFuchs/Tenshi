"""Tenshi 3.0.2: source changes trigger read-only quick partition analysis."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.partition_scan import AnalysisReport


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class SourceAutoScan302Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(Path(self.temp.name) / 'settings.json')})
        self.settings.start()
        self.a = Path(self.temp.name) / 'first.raw'
        self.b = Path(self.temp.name) / 'second.raw'
        self.a.write_bytes(b'\0' * 4096)
        self.b.write_bytes(b'\0' * 8192)
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.settings.stop()
        self.temp.cleanup()

    def test_image_picker_starts_quick_scan_and_selects_partitions(self):
        self.app._select_main_tab('files')
        with patch('recoverydesk.gui.filedialog.askopenfilename', return_value=str(self.a)), \
             patch.object(self.app, 'scan_partitions') as scan:
            self.app.choose_source()
        self.assertEqual(self.app.source_path.get(), str(self.a))
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))
        scan.assert_called_once_with(False)
        self.assertEqual(self.app.ntfs_byte_offset.get(), '0')

    def test_cancel_source_picker_changes_nothing(self):
        self.app.source_path.set(str(self.a))
        self.app._select_main_tab('files')
        with patch('recoverydesk.gui.filedialog.askopenfilename', return_value=''), \
             patch.object(self.app, 'scan_partitions') as scan:
            self.app.choose_source()
        scan.assert_not_called()
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))
        self.assertEqual(self.app.source_path.get(), str(self.a))

    def test_manually_entered_source_return_starts_quick_scan(self):
        self.app.source_path.set(str(self.b))
        self.app._select_main_tab('files')
        with patch.object(self.app, 'scan_partitions') as scan:
            self.assertEqual(self.app._accept_source_entry(), 'break')
        scan.assert_called_once_with(False)
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))

    def test_invalid_manual_path_does_not_start(self):
        self.app.source_path.set(str(Path(self.temp.name) / 'absent.raw'))
        with patch('recoverydesk.gui.messagebox.showerror') as error, \
             patch.object(self.app, 'scan_partitions') as scan:
            self.app._accept_source_entry()
        error.assert_called_once()
        scan.assert_not_called()

    def test_switch_during_scan_queues_latest_source_and_rejects_stale_results(self):
        self.app.source_path.set(str(self.a))
        self.app.partition_scanning = True
        old_generation = self.app._source_generation
        with patch.object(self.app, 'scan_partitions') as scan:
            self.app._activate_source_and_quick_scan(str(self.b))
            scan.assert_not_called()
            self.assertEqual(self.app._pending_source_quick_scan, str(self.b))
            self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))
            self.app._show_partitions(AnalysisReport(4096), old_generation, str(self.a))
            self.assertIsNone(self.app.last_partition_report)
            self.app._finish_partition_scan()
            scan.assert_called_once_with(False)
            self.assertIsNone(self.app._pending_source_quick_scan)

    def test_multiple_changes_while_busy_use_only_latest_source(self):
        self.app.partition_scanning = True
        third = str(Path(self.temp.name) / 'third.raw')
        with patch.object(self.app, 'scan_partitions') as scan:
            self.app._activate_source_and_quick_scan(str(self.a))
            self.app._activate_source_and_quick_scan(str(self.b))
            self.app._activate_source_and_quick_scan(third)
            self.app._finish_partition_scan()
            scan.assert_called_once_with(False)
        self.assertEqual(self.app.source_path.get(), third)

    def test_session_restore_is_not_replaced_by_auto_scan(self):
        # A previously verified cached session deliberately bypasses source
        # selection automation. A fresh automatic scan would discard its index.
        from types import SimpleNamespace
        result = SimpleNamespace(source=str(self.a), report=None, index=None,
                                 fingerprint=None, filesystem=None, offset=0)
        with patch.object(self.app, 'scan_partitions') as scan:
            self.app._finish_session_load(result, self.app._source_generation,
                                          self.app.source_path.get())
        scan.assert_not_called()
        self.assertEqual(self.app.source_path.get(), str(self.a))
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))

    def test_real_small_image_autoscans_in_background(self):
        from test_filesystems import fat_img
        self.a.write_bytes(fat_img())
        before = self.a.read_bytes()
        with patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app._activate_source_and_quick_scan(str(self.a))
            self.assertTrue(self.app.partition_scanning)
            def wait_done():
                if not self.app.partition_scanning:
                    self.app.quit()
                else:
                    self.app.after(20, wait_done)
            self.app.after(20, wait_done)
            self.app.after(7000, self.app.quit)
            self.app.mainloop()
        error.assert_not_called()
        self.assertIsNotNone(self.app.last_partition_report)
        self.assertTrue(any(p.filesystem == 'FAT32' for p in self.app.partitions))
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))
        self.assertEqual(self.a.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
