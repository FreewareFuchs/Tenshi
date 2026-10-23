"""Linux physical-disk discovery never opens /dev; explicit GUI opt-in.

Uses fake sysfs directories and fake GUI device names, not real disks.
"""
import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from recoverydesk import linux_devices


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux sysfs only')
class SysfsDiscoveryTests(unittest.TestCase):
    def test_discover_whole_disk_without_opening_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'sys' / 'class' / 'block'
            disk = root / 'mockdisk'
            partition = root / 'mockdisk1'
            disk.mkdir(parents=True)
            partition.mkdir()
            (disk / 'size').write_text('2048\n', encoding='ascii')
            (partition / 'size').write_text('1024\n', encoding='ascii')
            (partition / 'partition').write_text('1\n', encoding='ascii')
            real_path = Path
            with mock.patch.object(linux_devices, 'Path',
                                   side_effect=lambda name: (
                                      root if name == '/sys/class/block'
                                      else real_path(name))), \
                 mock.patch.object(linux_devices, 'block_path',
                                   side_effect=lambda name: name == '/dev/mockdisk'), \
                 mock.patch.object(linux_devices, 'block_info',
                                   side_effect=AssertionError('raw device opened')):
                result = linux_devices.list_block_sources()
        self.assertEqual(result, [('/dev/mockdisk', 2048 * 512)])


@unittest.skipUnless(sys.platform.startswith('linux') and os.environ.get('DISPLAY'),
                     'Linux graphical session required')
class DeviceOptInTests(unittest.TestCase):
    def test_unselected_linux_disk_cannot_be_confirmed(self):
        from tkinter import ttk
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        app.withdraw()
        try:
            dialog = app._show_device_dialog([('/dev/mockdisk', 2048 * 512)])
            app.update()
            widgets = []
            def walk(widget):
                for child in widget.winfo_children():
                    widgets.append(child)
                    walk(child)
            walk(dialog)
            tree = next(w for w in widgets if isinstance(w, ttk.Treeview))
            button = next(w for w in widgets if isinstance(w, ttk.Button)
                          and str(w.cget('text')).startswith('Auswahl übernehmen'))
            self.assertFalse(tree.selection())
            self.assertEqual(str(button.cget('state')), 'disabled')
            tree.selection_set('/dev/mockdisk')
            app.update()
            self.assertEqual(str(button.cget('state')), 'normal')
            dialog.destroy()
        finally:
            app.destroy()


if __name__ == '__main__':
    unittest.main()
