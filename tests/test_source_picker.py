"""Combined source selection: synthetic metadata/readers, never real devices."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from recoverydesk import source_catalog as catalog, sources
from recoverydesk.core import VolumeInfo


DISK = r'\\.\PhysicalDrive0'
VOLUME = VolumeInfo('D:\\', 'Data', 'NTFS', 8192, 4096)


class SourceCatalogTests(unittest.TestCase):
    def test_unique_mapping_groups_but_unknown_and_multiple_do_not_guess(self):
        disks = catalog.device_choices([(DISK, 16384)])
        volumes = catalog.volume_choices([VOLUME])
        for parents, expected_parent, mapping in (({DISK}, DISK, ''),
                ({DISK, r'\\.\PhysicalDrive1'}, '', 'multiple'),
                (set(), '', 'unknown'), ({r'\\.\PhysicalDrive8'}, '', 'unknown')):
            result = catalog.group_choices(disks, volumes, lambda _: parents)
            self.assertEqual(result[-1].parent, expected_parent)
            self.assertEqual(result[-1].mapping, mapping)
            self.assertEqual(result[-1].source, r'\\.\D:')

    def test_disconnected_mapping_does_not_hide_volume(self):
        with patch.object(catalog, '_volume_parents', side_effect=OSError('disconnected')):
            result = catalog.group_choices([], catalog.volume_choices([VOLUME]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].mapping, 'unknown')

    def test_partial_discovery_is_reported_and_does_not_drop_known_volumes(self):
        with patch.object(catalog, 'list_physical_sources', side_effect=OSError('denied')) as disks, \
             patch.object(catalog, 'list_volumes', return_value=[VOLUME]), \
             patch.object(catalog, '_volume_parents', return_value=set()):
            rows, warnings = catalog.collect_choices()
        disks.assert_called_once_with(metadata_only=True)
        self.assertEqual([r.source for r in rows], [r'\\.\D:'])
        self.assertEqual(len(warnings), 1)

    def test_windows_mapping_uses_metadata_query_only(self):
        with patch.object(catalog.sys, 'platform', 'win32'), \
             patch.object(catalog, 'volume_disk_numbers', return_value={0}) as query:
            self.assertEqual(catalog._volume_parents(catalog.volume_choices([VOLUME])[0]), {DISK})
        query.assert_called_once_with(r'\\.\D:', metadata_only=True)

    def test_linux_mapping_uses_stat_and_sysfs_without_opening_media(self):
        choice = catalog.SourceChoice('/dev/mock1', '/dev/mock1', 'volume', 8192)
        with patch.object(catalog.sys, 'platform', 'linux'), \
             patch.object(catalog.os, 'stat', return_value=SimpleNamespace(st_rdev=123)), \
             patch('recoverydesk.linux_devices._backing_disks', return_value={'/sys/devices/block/mock'}) as roots:
            self.assertEqual(catalog._volume_parents(choice), {'/dev/mock'})
        roots.assert_called_once_with(123)

    def test_windows_inventory_uses_geometry_without_read_permission(self):
        geometry = bytearray(32)
        geometry[24:32] = (8192).to_bytes(8, 'little')
        with patch.object(sources.os, 'name', 'nt'), patch.object(sources.sys, 'platform', 'win32'), \
             patch.object(sources, 'source_size', side_effect=AssertionError('READ requested')), \
             patch.object(sources, '_device_ioctl', return_value=bytes(geometry)) as query:
            self.assertEqual(sources.list_physical_sources(1, metadata_only=True), [(DISK, 8192)])
        query.assert_called_once_with(DISK, sources._IOCTL_DISK_GET_DRIVE_GEOMETRY_EX,
                                      256, metadata_only=True)

    def test_zero_access_handle_is_limited_to_two_metadata_operations(self):
        kernel = MagicMock()
        kernel.CreateFileW.return_value = 123
        kernel.DeviceIoControl.return_value = True
        with patch.object(sources.os, 'name', 'nt'), patch.object(sources, '_kernel', return_value=kernel):
            sources._device_ioctl(DISK, sources._IOCTL_DISK_GET_DRIVE_GEOMETRY_EX,
                                  256, metadata_only=True)
            self.assertEqual(kernel.CreateFileW.call_args.args[1], 0)
            kernel.CloseHandle.assert_called_once_with(123)
            kernel.reset_mock()
            sources._device_ioctl(DISK, sources._IOCTL_DISK_GET_LENGTH_INFO, 8)
            self.assertEqual(kernel.CreateFileW.call_args.args[1], 0x80000000)
            kernel.reset_mock()
            with self.assertRaises(ValueError):
                sources._device_ioctl(DISK, 0x00090020, metadata_only=True)
            kernel.CreateFileW.assert_not_called()


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'GUI display required')
class UnifiedPickerGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(Path(self.temp.name)/'settings.json'),
                                      'TENSHI_LOG_DIR': str(Path(self.temp.name)/'logs')})
        env.start()
        self.addCleanup(env.stop)
        from recoverydesk.gui import RecoveryDeskApp
        with patch('recoverydesk.gui.collect_choices', side_effect=AssertionError('Startup discovery')):
            self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.rows = catalog.group_choices(catalog.device_choices([(DISK, 16384)]),
            catalog.volume_choices([VOLUME]), lambda _: {DISK})

    def test_one_toolbar_action_and_no_implicit_device_read(self):
        actions = self.app.session_menu_button.master.winfo_children()
        self.assertEqual(len(actions), 4)
        with patch('recoverydesk.gui.open_source') as opened:
            dialog = self.app._show_source_dialog(self.rows)
            self.app.update()
            self.assertFalse(dialog.source_tree.selection())
            self.assertEqual(str(dialog.confirm_button.cget('state')), 'disabled')
            self.assertEqual(dialog.source_tree.parent('D:\\'), DISK)
            dialog.destroy()
        opened.assert_not_called()

    def test_both_source_types_use_same_read_only_preflight_and_reset_offset(self):
        @contextlib.contextmanager
        def reader(_source):
            yield io.BytesIO(bytes(512))
        for key, expected in ((DISK, DISK), ('D:\\', r'\\.\D:')):
            dialog = self.app._show_source_dialog(self.rows)
            dialog.source_tree.selection_set(key)
            self.app.update()
            self.app.ntfs_byte_offset.set('123456')
            with patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                 patch('recoverydesk.gui.open_source', side_effect=reader) as opened, \
                 patch.object(self.app, 'scan_partitions') as scan:
                dialog.confirm_button.invoke()
            opened.assert_called_once_with(expected)
            scan.assert_called_once_with(False)
            self.assertEqual(self.app.source_path.get(), expected)
            self.assertEqual(self.app.ntfs_byte_offset.get(), '0')

    def test_access_denied_keeps_source_and_unified_message(self):
        for key in (DISK, 'D:\\'):
            dialog = self.app._show_source_dialog(self.rows)
            dialog.source_tree.selection_set(key)
            self.app.update()
            self.app.source_path.set('unchanged.img')
            with patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                 patch('recoverydesk.gui.open_source', side_effect=PermissionError('denied')), \
                 patch('recoverydesk.gui.messagebox.showerror') as error, \
                 patch.object(self.app, 'scan_partitions') as scan:
                dialog.confirm_button.invoke()
            error.assert_called_once()
            scan.assert_not_called()
            self.assertTrue(dialog.winfo_exists())
            self.assertEqual(self.app.source_path.get(), 'unchanged.img')
            dialog.destroy()

    def test_unknown_group_cannot_be_used_as_a_source(self):
        rows = catalog.group_choices([], catalog.volume_choices([VOLUME]), lambda _: set())
        dialog = self.app._show_source_dialog(rows)
        tree = dialog.source_tree
        tree.selection_set(tree.parent('D:\\'))
        self.app.update()
        self.assertEqual(str(dialog.confirm_button.cget('state')), 'disabled')
        with patch('recoverydesk.gui.open_source') as opened:
            dialog.confirm_button.invoke()
        opened.assert_not_called()
        dialog.destroy()

    def test_double_click_confirms_clicked_volume_instead_of_previous_disk(self):
        dialog = self.app._show_source_dialog(self.rows)
        tree = dialog.source_tree
        tree.selection_set(DISK)
        with patch.object(tree, 'identify_region', return_value='cell'), \
             patch.object(tree, 'identify_element', return_value='text'), \
             patch.object(tree, 'identify_row', return_value='D:\\'), \
             patch.object(self.app, '_confirm_picked_source') as confirm:
            dialog._source_double_click(SimpleNamespace(x=10, y=10))
        confirm.assert_called_once_with(self.rows[1], dialog)
        self.assertEqual(tree.selection(), ('D:\\',))
        for region, element in (('heading', 'text'), ('tree', 'Treeitem.indicator')):
            with patch.object(tree, 'identify_region', return_value=region), \
                 patch.object(tree, 'identify_element', return_value=element), \
                 patch.object(self.app, '_confirm_picked_source') as confirm:
                dialog._source_double_click(SimpleNamespace(x=10, y=10))
            confirm.assert_not_called()
        dialog.destroy()

    def test_discovery_stays_off_gui_thread_and_closed_picker_is_ignored(self):
        release = threading.Event()
        started = threading.Event()
        gui_thread = threading.get_ident()
        seen = []
        def discover():
            seen.append(threading.get_ident())
            started.set()
            release.wait(5)
            return self.rows, []
        with patch('recoverydesk.gui.collect_choices', side_effect=discover) as collect:
            dialog = self.app._choose_sources()
            self.assertTrue(started.wait(2))
            self.assertIs(self.app._choose_sources(), dialog)
            self.assertEqual(collect.call_count, 1)
            dialog.destroy()
            release.set()
            for _ in range(20):
                self.app.update()
                time.sleep(.01)
        self.assertNotEqual(seen, [gui_thread])

    def test_resized_picker_remains_usable_in_all_languages_and_both_themes(self):
        from recoverydesk.i18n import LANGUAGES
        for theme in ('light', 'dark'):
            self.app.change_theme(theme)
            for language in LANGUAGES:
                with self.subTest(theme=theme, language=language):
                    self.app.change_language(language)
                    dialog = self.app._show_source_dialog(self.rows)
                    dialog.transient('')
                    dialog.deiconify()
                    for size in ('960x560+0+0', '760x450+0+0', '900x520+0+0'):
                        dialog.geometry(size)
                        self.app.update()
                        button = dialog.confirm_button
                        self.assertTrue(button.winfo_ismapped())
                        self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())
                        self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),
                                             dialog.winfo_rooty()+dialog.winfo_height())
                        self.assertGreater(dialog.source_tree.winfo_height(), 50)
                    dialog.destroy()
