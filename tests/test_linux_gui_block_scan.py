"""Linux GUI device scanning tests (no physical device is opened)."""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from recoverydesk.gui import RecoveryDeskApp

FAKE_DEVICE = '/dev/tenshi-mocked-block-device'


class _RunSynchronously:
    """Run GUI worker in test thread to deterministically check its branch."""
    def __init__(self, *args, **kwargs):
        self._target = kwargs['target']

    def start(self):
        self._target()


@unittest.skipUnless(sys.platform.startswith('linux') and os.environ.get('DISPLAY'),
                     'Linux/X11 required')
class LinuxGuiDeviceScanTests(unittest.TestCase):
    def setUp(self):
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.app.source_path.set(FAKE_DEVICE)

    def tearDown(self):
        self.app.destroy()

    def test_partition_scan_does_not_fingerprint_linux_raw_device(self):
        with mock.patch.object(self.app, 'get_source', return_value=FAKE_DEVICE), \
             mock.patch('recoverydesk.gui.is_device_source', return_value=True), \
             mock.patch('recoverydesk.gui.fingerprint_image',
                        side_effect=AssertionError('block device fingerprint attempted')) as fp, \
             mock.patch('recoverydesk.gui.analyze_image',
                        side_effect=PermissionError('Linux test permission denied')) as scan, \
             mock.patch('recoverydesk.gui.messagebox.showerror') as error, \
             mock.patch('recoverydesk.gui.threading.Thread', _RunSynchronously):
            self.app.scan_partitions(False)
            self.app.update()
            scan.assert_called_once()
            fp.assert_not_called()
            self.assertTrue(error.called)
            self.assertIn('Linux test permission denied', error.call_args.args[-1])

    def test_filesystem_scan_does_not_fingerprint_linux_raw_device(self):
        self.app.ntfs_byte_offset.set('0')
        self.app.mft_record_limit.set('0')
        self.app.tolerant_scan.set(False)
        with mock.patch.object(self.app, 'get_source', return_value=FAKE_DEVICE), \
             mock.patch('recoverydesk.gui.is_device_source', return_value=True), \
             mock.patch('recoverydesk.gui.fingerprint_image',
                        side_effect=AssertionError('block device fingerprint attempted')) as fp, \
             mock.patch('recoverydesk.gui.open_source',
                        side_effect=PermissionError('Linux test permission denied')) as opened, \
             mock.patch('recoverydesk.gui.messagebox.showerror') as error, \
             mock.patch('recoverydesk.gui.threading.Thread', _RunSynchronously):
            self.app.start_ntfs_scan()
            self.app.update()
            opened.assert_called_once_with(FAKE_DEVICE)
            fp.assert_not_called()
            self.assertTrue(error.called)
            self.assertIn('Linux test permission denied', error.call_args.args[-1])

    def test_tolerant_scan_denied_for_linux_physical_device(self):
        self.app.tolerant_scan.set(True)
        with mock.patch.object(self.app, 'get_source', return_value=FAKE_DEVICE), \
             mock.patch('recoverydesk.gui.is_device_source', return_value=True), \
             mock.patch('recoverydesk.gui.open_source') as opened, \
             mock.patch('recoverydesk.gui.messagebox.showerror') as error:
            self.app.start_ntfs_scan()
            opened.assert_not_called()
            error.assert_called_once()
            self.assertIn('nur für Image-Dateien', error.call_args.args[-1])


if __name__ == '__main__':
    unittest.main()
