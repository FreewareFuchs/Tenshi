"""Partition metadata worker delivers both outcomes on the GUI thread."""
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

from recoverydesk.gui import RecoveryDeskApp
from recoverydesk.partition_scan import Partition


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI required')
class PartitionDetailsWorkerTests(unittest.TestCase):
    def test_success_and_failure_are_delivered_on_main_thread(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {
                'TENSHI_SETTINGS_FILE': str(Path(folder) / 'settings.json')}):
            source = Path(folder) / 'source.raw'
            source.write_bytes(b'protected source')
            app = RecoveryDeskApp()
            app.withdraw()
            try:
                part = Partition(1, 'MBR', 0, 512, '0x0b', filesystem='FAT32')
                app.partitions = [part]
                app.source_path.set(str(source))
                app.part_tree.insert('', 'end', iid='0')
                app.part_tree.selection_set('0')
                for failure in (False, True):
                    with self.subTest(failure=failure):
                        delivered = []
                        def finish(*args):
                            delivered.append((threading.get_ident(), args))
                            app.partition_diagnosing = False
                        with mock.patch('recoverydesk.gui.inspect_partition',
                                        side_effect=ValueError('test error') if failure else None,
                                        return_value='metadata'), \
                             mock.patch.object(app, '_finish_partition_details', side_effect=finish), \
                             mock.patch.object(app, '_finish_partition_details_error', side_effect=finish):
                            app.check_selected_partition()
                            deadline = time.monotonic() + 3
                            while not delivered and time.monotonic() < deadline:
                                app.update()
                                time.sleep(.005)
                        self.assertEqual(len(delivered), 1)
                        self.assertEqual(delivered[0][0], threading.get_ident())
                        self.assertEqual(delivered[0][1][-1], 'test error' if failure else 'metadata')
                self.assertEqual(source.read_bytes(), b'protected source')
            finally:
                app.destroy()
