"""Deterministic UI callbacks simulate source edits and read loss, without hardware."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.filesystems import scan_tree
from test_filesystems import fat_img


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class SourceScanFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(self.root / 'settings.json')})
        self.env.start()
        self.source = self.root / 'source.raw'
        self.source.write_bytes(fat_img())
        self.index = scan_tree(str(self.source))
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.app.source_path.set(str(self.source))
        self.app.browser_source = str(self.source)
        self.app.browser_index = self.index
        self.app.file_tree.insert('', 'end', iid='old', values=('old',))
        self.app.scan_report_text = 'old report'
        self.callbacks = []

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def run_scan(self, scan):
        def thread(*, target, **kwargs):
            return SimpleNamespace(start=target)
        with patch('recoverydesk.gui.threading.Thread', side_effect=thread), \
             patch.object(self.app, '_post_scan_callback', side_effect=self.callbacks.append), \
             patch('recoverydesk.gui.scan_other_tree', side_effect=scan):
            self.app.start_ntfs_scan()

    def drain(self):
        for callback in self.callbacks:
            callback()

    def test_read_loss_removes_old_exportable_index_and_restores_controls(self):
        def fail(*args, **kwargs):
            raise OSError(5, 'simulated device read loss')
        self.run_scan(fail)
        self.assertIsNone(self.app.browser_index)
        self.assertIsNone(self.app.browser_source)
        self.assertEqual(self.app.file_tree.get_children(), ())
        self.assertIsNone(self.app.scan_report_text)
        with patch('recoverydesk.gui.messagebox.showerror') as error:
            self.drain()
        error.assert_called_once()
        self.assertFalse(self.app.ntfs_scanning)
        self.assertEqual(str(self.app.ntfs_scan_btn.cget('state')), 'normal')
        with patch('recoverydesk.gui.messagebox.showinfo'), \
             patch('recoverydesk.gui.filedialog.askdirectory') as destination:
            self.app.export_browser_selection()
        destination.assert_not_called()

    def test_manual_path_edit_discards_queued_success_and_filesystem_label(self):
        self.run_scan(lambda *args, **kwargs: self.index)
        self.app.source_path.set(str(self.root / 'other.raw'))
        with patch.object(self.app, '_show_browser_index') as publish, \
             patch.object(self.app, '_set_browser_fs') as label:
            self.drain()
        publish.assert_not_called()
        label.assert_not_called()
        self.assertIsNone(self.app._browser_fingerprint)
        self.assertFalse(self.app.ntfs_scanning)

    def test_source_generation_change_suppresses_old_error(self):
        def fail(*args, **kwargs):
            raise OSError(5, 'simulated loss')
        self.run_scan(fail)
        self.app._source_generation += 1
        with patch('recoverydesk.gui.messagebox.showerror') as error:
            self.drain()
        error.assert_not_called()
        self.assertFalse(self.app.ntfs_scanning)

    def test_current_scan_still_publishes(self):
        self.run_scan(lambda *args, **kwargs: self.index)
        with patch.object(self.app, '_show_browser_index') as publish:
            self.drain()
        publish.assert_called_once()
        self.assertEqual(publish.call_args.args[:2], (str(self.source), self.index))
        self.assertIsNotNone(self.app._browser_fingerprint)

    def test_same_path_device_replacement_during_scan_cannot_publish(self):
        from recoverydesk.device_identity import DeviceSourceChanged
        snapshot = {'offset': 0, 'serial_sha256': 'first-device'}
        with patch('recoverydesk.gui.capture_device_identity', return_value=snapshot), \
                patch('recoverydesk.gui.check_device_identity', side_effect=DeviceSourceChanged('replaced')):
            self.run_scan(lambda *args, **kwargs: self.index)
        with patch.object(self.app, '_show_browser_index') as publish, \
                patch('recoverydesk.gui.messagebox.showerror') as error:
            self.drain()
        publish.assert_not_called()
        error.assert_called_once()
        self.assertIsNone(self.app.browser_index)
        self.assertFalse(self.app.ntfs_scanning)

    def test_stable_device_scan_binds_snapshot_to_published_index(self):
        snapshot = {'offset': 0, 'serial_sha256': 'stable-device'}
        with patch('recoverydesk.gui.capture_device_identity', return_value=snapshot), \
                patch('recoverydesk.gui.check_device_identity') as check:
            self.run_scan(lambda *args, **kwargs: self.index)
        check.assert_called_once_with(str(self.source), snapshot)
        with patch.object(self.app, '_show_browser_index') as publish:
            self.drain()
        self.assertEqual(publish.call_args.args[1]._device_identity, snapshot)

    def test_partition_details_ignore_manual_path_edit_including_errors(self):
        part = object()
        self.app.partitions = [part]
        generation = self.app._source_generation
        self.app.source_path.set(str(self.root / 'other.raw'))
        self.app._finish_partition_details(generation, str(self.source), 0, part, object())
        self.assertEqual(self.app.partition_details, {})
        with patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app._finish_partition_details_error('old error', generation, str(self.source))
        error.assert_not_called()
