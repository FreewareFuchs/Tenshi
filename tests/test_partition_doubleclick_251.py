"""Partition double-click opens file browser and starts read-only filesystem scan."""
from __future__ import annotations
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.i18n import LANGUAGES, translate
from recoverydesk.partition_scan import AnalysisReport, Partition


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class PartitionDoubleClickTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = patch.dict(os.environ, {
            'TENSHI_SETTINGS_FILE': str(Path(self.tmp.name) / 'tenshi-settings.json')})
        self.settings.start()
        self.src = Path(self.tmp.name) / 'disk.raw'
        self.src.write_bytes(b'\0' * 4096)
        self.app = RecoveryDeskApp()
        self.app.source_path.set(str(self.src))
        self.app.partition_source = str(self.src)
        self.parts = [
            Partition(1, 'MBR', 1, 100, '0x07', filesystem='NTFS'),
            Partition(2, 'MBR', 2, 100, '0x0b', filesystem='FAT32'),
        ]
        self.app._show_partitions(AnalysisReport(4096, partitions=self.parts))
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.settings.stop()
        self.tmp.cleanup()

    def click(self, row='1'):
        self.app.part_tree.see(row)
        self.app.update()
        box = self.app.part_tree.bbox(row)
        self.assertTrue(box, 'Selected partition row must be visible')
        x, y, width, height = box
        self.app._open_partition_from_double_click(
            SimpleNamespace(x=x + 5, y=y + height // 2))

    def test_double_click_uses_clicked_row_not_stale_selection(self):
        self.app.part_tree.selection_set('0')
        with patch.object(self.app, 'start_ntfs_scan') as start:
            self.click('1')
        start.assert_called_once_with()
        self.assertEqual(self.app.ntfs_byte_offset.get(), '1024')
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))
        self.assertEqual(self.app.source_path.get(), str(self.src))
        self.assertEqual(len(self.app.tabs.tabs()), 3)
        self.assertEqual(self.app.export_button.cget('bg'), self.app._palette()['accent'])
        self.assertTrue(self.app.part_tree.bind('<Double-1>'))

    def test_4kn_partition_uses_byte_offset_not_lba(self):
        # On 4Kn media the partition start is LBA * 4096, not LBA * 512.
        self.parts[1] = Partition(2, 'GPT', 256, 128, 'test-guid',
                                  sector_size=4096, filesystem='exFAT')
        self.app._show_partitions(AnalysisReport(2 * 1024 * 1024, partitions=self.parts))
        with patch.object(self.app, 'start_ntfs_scan') as start:
            self.click('1')
        start.assert_called_once_with()
        self.assertEqual(self.app.ntfs_byte_offset.get(), str(256 * 4096))

    def test_double_click_header_and_whitespace_do_not_trigger_scan(self):
        before = self.app.ntfs_byte_offset.get()
        with patch.object(self.app, 'start_ntfs_scan') as start:
            self.app._open_partition_from_double_click(SimpleNamespace(x=30, y=3))
            self.app._open_partition_from_double_click(SimpleNamespace(x=30, y=self.app.part_tree.winfo_height() - 3))
        start.assert_not_called()
        self.assertEqual(self.app.ntfs_byte_offset.get(), before)
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))

    def test_manual_transfer_does_not_automatically_scan(self):
        self.app.part_tree.selection_set('1')
        with patch.object(self.app, 'start_ntfs_scan') as start:
            self.app.use_selected_partition()
        start.assert_not_called()
        self.assertEqual(self.app.ntfs_byte_offset.get(), '1024')
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))

    def test_busy_scanner_does_not_change_offset_or_start_another(self):
        self.app.ntfs_scanning = True
        with patch.object(self.app, 'start_ntfs_scan') as start:
            self.click('1')
        start.assert_not_called()
        self.assertEqual(self.app.ntfs_byte_offset.get(), '0')
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))

    def test_partition_scan_in_progress_blocks_double_click(self):
        self.app.partition_scanning = True
        with patch.object(self.app, 'start_ntfs_scan') as start:
            self.click('1')
        start.assert_not_called()
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))

    def test_stale_source_rejected_before_switching_or_reading(self):
        other = Path(self.tmp.name) / 'other.raw'
        other.write_bytes(b'\0' * 4096)
        self.app.source_path.set(str(other))
        with patch('recoverydesk.gui.messagebox.showerror') as err, \
             patch.object(self.app, 'start_ntfs_scan') as start:
            self.click('1')
        err.assert_called_once()
        start.assert_not_called()
        self.assertEqual(self.app.ntfs_byte_offset.get(), '0')
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))

    def test_unsupported_filesystem_warns_without_scan(self):
        self.parts[1].filesystem = 'unbekannt'
        with patch('recoverydesk.gui.messagebox.showwarning') as warn, \
             patch.object(self.app, 'start_ntfs_scan') as start:
            self.click('1')
        warn.assert_called_once()
        start.assert_not_called()
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))
        self.assertEqual(self.app.ntfs_byte_offset.get(), '1024')

    def test_hint_translated_into_six_languages(self):
        de = 'Doppelklick auf eine Partition: Dateisystem automatisch einlesen.'
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertTrue(translate(de, language))
                if language != 'de':
                    self.assertNotEqual(translate(de, language), de)

    def test_real_readonly_scan_from_double_click(self):
        # Real FAT32 parser and real background worker, no mock; changes are
        # observed in the file browser as well as in the tab selection.
        from test_filesystems import fat_img
        disk = fat_img(offset=1024 * 1024)
        self.src.write_bytes(disk)
        self.app.partition_source = str(self.src)
        self.parts[1] = Partition(2, 'MBR', 2048, 512, '0x0b', filesystem='FAT32')
        self.app._show_partitions(AnalysisReport(len(disk), partitions=self.parts))
        with patch('recoverydesk.gui.messagebox.showerror') as errors:
            self.click('1')
            # Tkinter only permits after() from worker threads while mainloop
            # is actually running; update() alone is insufficient on Windows
            # and on some Linux/Tk builds.
            def check_finished():
                if self.app.browser_index is not None or not self.app.ntfs_scanning:
                    self.app.quit()
                else:
                    self.app.after(25, check_finished)
            timeout_id = self.app.after(7000, self.app.quit)
            self.app.after(25, check_finished)
            self.app.mainloop()
            self.app.after_cancel(timeout_id)
            self.app.update()
        errors.assert_not_called()
        self.assertIsNotNone(self.app.browser_index)
        self.assertEqual(self.app.browser_index.filesystem, 'FAT32')
        self.assertEqual(self.app.ntfs_byte_offset.get(), '1048576')
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))
        self.assertEqual(self.src.read_bytes(), disk, 'Source image must remain read-only')


if __name__ == '__main__':
    unittest.main()
