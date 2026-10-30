"""Tenshi 2.4.0: durable theme, column widths and pane geometry."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recoverydesk.i18n import load_language, save_language, settings_path, LANGUAGES
from recoverydesk.ui_preferences import clean_ui_preferences, load_ui_preferences, save_ui_preferences, valid_geometry


class AppearancePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(Path(self.temp.name) / 'settings.json')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_invalid_values_cannot_corrupt_layout(self):
        result = clean_ui_preferences({'theme':'nonsense', 'geometry':'1x1-10000-10000',
            'folder_ratio':100, 'files_columns':{'#0':-1, 'type':180, 'secret':'100'},
            'partitions_columns':{'name':5000}})
        self.assertEqual(result['theme'], 'system')
        self.assertIsNone(result['geometry'])
        self.assertIsNone(result['folder_ratio'])
        self.assertEqual(result['files_columns'], {'type':180})
        self.assertEqual(result['partitions_columns'], {})
        self.assertIsNone(valid_geometry('800x600+0+0'))
        self.assertIsNotNone(valid_geometry('1340x900+10+10'))

    def test_preferences_and_language_survive_each_other(self):
        save_language('ja')
        save_ui_preferences({'theme': 'dark', 'folder_ratio':0.42,
                             'files_columns':{'#0':340, 'status':220}})
        self.assertEqual(load_language(), 'ja')
        save_language('ru')
        settings = load_ui_preferences()
        self.assertEqual(settings['theme'], 'dark')
        self.assertAlmostEqual(settings['folder_ratio'], 0.42)
        self.assertEqual(settings['files_columns']['status'], 220)
        self.assertEqual(load_language(), 'ru')
        self.assertNotIn('C:', settings_path().read_text(encoding='utf-8'))

    def test_preserve_full_language_catalog(self):
        save_ui_preferences({'theme':'dark'})
        for language in LANGUAGES:
            save_language(language)
            self.assertEqual(load_ui_preferences()['theme'], 'dark')


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'GUI display required')
class AppearanceGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': str(Path(self.temp.name) / 'settings.json')})
        patcher.start()
        self.addCleanup(patcher.stop)
        from recoverydesk.gui import RecoveryDeskApp
        detector = patch('recoverydesk.gui.detect_system_theme', return_value='light')
        detector.start()
        self.addCleanup(detector.stop)
        self.app = RecoveryDeskApp()
        self.app.update()

    def tearDown(self):
        if self.app.winfo_exists():
            self.app.destroy()

    def test_light_dark_toggle_keeps_accent_export_and_tabs(self):
        self.assertEqual(self.app.theme, 'light')
        self.app.change_theme('dark')
        self.app.update()
        self.assertEqual(self.app.theme, 'dark')
        self.assertEqual(self.app.cget('bg'), '#1c1c1c')
        self.assertEqual(self.app.export_button.cget('bg'), '#57c8ff')
        self.assertEqual(len(self.app.tabs.tabs()), 3)
        self.assertEqual(load_ui_preferences()['theme'], 'dark')
        self.app.change_theme('light')
        self.assertEqual(self.app.cget('bg'), '#fafafa')
        self.assertEqual(self.app.export_button.cget('bg'), '#005fb8')

    def test_sash_widths_geometry_and_language_persist(self):
        self.app._select_main_tab('files')
        self.app.update()
        pane = self.app.browser_paned
        pane.sashpos(0, 455)
        self.app.file_tree.column('status', width=258)
        self.app.part_tree.column('name', width=183)
        # Windows CI runners may use a virtual screen too small for 1260x820.
        # Compare the actual usable geometry, not a size the WM may clamp.
        target_w = max(1024, min(1260, self.app.winfo_screenwidth() - 80))
        target_h = max(650, min(820, self.app.winfo_screenheight() - 100))
        self.app.geometry(f'{target_w}x{target_h}+20+20')
        self.app.update()
        actual_geometry = self.app.geometry()
        first_ratio = pane.sashpos(0) / pane.winfo_width()
        self.app.change_language('en')
        self.app.change_theme('dark')
        self.app.destroy()
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.update()
        self.assertEqual(self.app.language,'en')
        self.assertEqual(self.app.theme,'dark')
        self.assertEqual(self.app.file_tree.column('status','width'),258)
        self.assertEqual(self.app.part_tree.column('name','width'),183)
        restored = self.app.geometry()
        # A different WM may adjust the offset but should preserve size.
        self.assertEqual(restored.split('+')[0].split('-')[0],
                         actual_geometry.split('+')[0].split('-')[0])
        self.app._select_main_tab('files')
        self.app.update()
        self.assertAlmostEqual(self.app.browser_paned.sashpos(0) / self.app.browser_paned.winfo_width(),first_ratio,delta=.035)

    def test_partition_quality_summary_is_not_a_recovery_guarantee(self):
        from types import SimpleNamespace
        part = lambda confidence, warning: SimpleNamespace(index=1, scheme='GPT',
            confidence=confidence, warning=warning, name='', offset_bytes=0,
            size_bytes=100000, filesystem='NTFS', sector_size=512, type_code='ntfs',
            evidence=[])
        report = SimpleNamespace(partitions=[part('Hoch',''),part('Mittel','warning'),part('Niedrig','')],
            image_size=10000000, table_type='GPT', candidates=1, scanned_bytes=10000, warnings=[])
        self.app._show_partitions(report)
        text = self.app.partition_quality_summary.get()
        self.assertIn('Hohe Plausibilität: 1',text)
        self.assertIn('Auffällige Partitionen: 1',text)
        self.app.change_language('es')
        self.assertIn('Alta confianza',self.app.partition_quality_summary.get())
        self.app._reset_analysis_for_source()
        self.assertEqual(self.app.partition_quality_summary.get(),'')
