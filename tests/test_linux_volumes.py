"""Linux mounted-volume metadata and GUI selection; never accesses real devices."""
import contextlib
import io
import json
import os
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk import core


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux-only volume discovery')
class LinuxMountedVolumeTests(unittest.TestCase):
    def test_lsblk_lists_only_mounted_block_volumes(self):
        with tempfile.TemporaryDirectory() as mount:
            devices = {
                'blockdevices': [
                    {'path': '/dev/mock', 'type': 'disk', 'size': 100000,
                     'fstype': None, 'mountpoints': [None], 'children': [
                         {'path': '/dev/mock1', 'type': 'part', 'size': 64000,
                          'fstype': 'ext4', 'label': 'TEST', 'mountpoints': [mount]},
                         {'path': '/dev/mock2', 'type': 'part', 'size': 32000,
                          'fstype': 'swap', 'label': None, 'mountpoints': [None]},
                    ]},
                    {'path': '/tmp/false.img', 'type': 'part', 'size': 64000,
                     'fstype': 'ext4', 'label': 'FAKE', 'mountpoints': [mount]}
                ]
            }
            output = SimpleNamespace(stdout=json.dumps(devices))
            with patch.object(core.subprocess, 'run', return_value=output) as run, \
                 patch('recoverydesk.linux_devices.block_path',
                       side_effect=lambda p: p.startswith('/dev/mock')):
                found = core._linux_volumes()
            self.assertEqual([(v.path, v.filesystem, v.label) for v in found],
                             [('/dev/mock1', 'ext4', 'TEST')])
            self.assertEqual(found[0].total_bytes, 64000)
            self.assertTrue(run.called)
            self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_lsblk_failure_is_not_silently_treated_as_empty(self):
        with patch.object(core.subprocess, 'run', side_effect=OSError('lsblk unavailable')):
            with self.assertRaisesRegex(OSError, 'lsblk unavailable'):
                core._linux_volumes()


@unittest.skipUnless(sys.platform.startswith('linux') and os.environ.get('DISPLAY'), 'Linux/X11 required')
class LinuxVolumeDialogTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()

    def test_linux_partition_selection_is_read_only_and_offset_zero(self):
        from tkinter import ttk
        from unittest.mock import patch
        mock_volume = core.VolumeInfo('/dev/mock-partition', 'Test', 'ext4', 8192, 4096)
        dialog = self.app._show_volume_dialog([mock_volume])
        self.app.update()
        widgets = []
        def walk(widget):
            for child in widget.winfo_children():
                widgets.append(child)
                walk(child)
        walk(dialog)
        select = next(w for w in widgets if isinstance(w, ttk.Button)
                      and str(w.cget('text')).startswith('Auswahl übernehmen'))
        tree = next(w for w in widgets if isinstance(w, ttk.Treeview))
        self.assertGreaterEqual(tree.column('#0')['width'], 185)
        self.assertFalse(tree.selection(), 'Linux raw device must not be preselected')
        self.assertEqual(str(select.cget('state')), 'disabled')
        tree.selection_set('/dev/mock-partition')
        self.app.update()
        self.assertEqual(str(select.cget('state')), 'normal')

        @contextlib.contextmanager
        def read_only_source(_path):
            fake = io.BytesIO(bytes(512))
            yield fake

        self.app.ntfs_byte_offset.set('4096')
        with patch('recoverydesk.gui.open_source', side_effect=read_only_source) as opened, \
             patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
             patch.object(self.app, 'scan_partitions') as scan:
            select.invoke()
        opened.assert_called_once_with('/dev/mock-partition')
        self.assertEqual(self.app.source_path.get(), '/dev/mock-partition')
        self.assertEqual(self.app.ntfs_byte_offset.get(), '0')
        scan.assert_called_once_with(False)


if __name__ == '__main__':
    unittest.main()
