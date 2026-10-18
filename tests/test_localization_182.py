"""Six-language localization, persistence, native dialogs, and UI safety."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import unittest

from recoverydesk.i18n import (LANGUAGES, canonical_choice, translate,
                                load_language, save_language)
from recoverydesk.browser_filter import FILTER_ALL, FILTER_WARNINGS, STATUS_FILTERS
from recoverydesk.gui import RecoveryDeskApp

class LocalizationLogicTests(TestCase):
    def test_languages_and_translations(self):
        self.assertEqual(set(LANGUAGES), {'de', 'en', 'es', 'zh', 'ru', 'ja'})
        for locale in LANGUAGES:
            self.assertTrue(translate('Partitionen', locale))
            self.assertTrue(translate('Dateien & Ordner', locale))
            self.assertEqual(canonical_choice(translate(FILTER_WARNINGS, locale),
                                              STATUS_FILTERS, locale), FILTER_WARNINGS)
            self.assertEqual(canonical_choice(translate('Nur Dateien', locale),
                                              ('Alle', 'Nur Dateien', 'Nur Ordner'), locale), 'Nur Dateien')

    def test_settings_save_load_and_invalid_language(self):
        with TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'prefs' / 'settings.json')
            with mock.patch.dict(os.environ, {'TENSHI_SETTINGS_FILE': path}):
                self.assertEqual(load_language(), 'de')
                save_language('zh')
                self.assertEqual(load_language(), 'zh')
                self.assertEqual(json.loads(Path(path).read_text(encoding='utf-8'))['language'], 'zh')
                with self.assertRaises(ValueError):
                    save_language('xx')
                self.assertEqual(load_language(), 'zh')
                Path(path).write_text('{bad json', encoding='utf-8')
                self.assertEqual(load_language(), 'de')

@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'Display required')
class LanguageGuiTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {'TENSHI_SETTINGS_FILE':str(Path(self.temp.name)/'prefs.json')})
        self.patch.start()
        self.app = RecoveryDeskApp()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.patch.stop()
        self.temp.cleanup()

    def test_switch_all_six_without_losing_source_or_tab_and_queue(self):
        app = self.app
        app.source_path.set('/safe/readonly/important.raw')
        app._select_main_tab('files')
        app.browser_extension.set('jpg,.docx')
        for locale in LANGUAGES:
            app.change_language(locale)
            app.update()
            self.assertEqual(app.language, locale)
            self.assertEqual(app.source_path.get(), '/safe/readonly/important.raw')
            self.assertEqual(app.browser_extension.get(), 'jpg,.docx')
            self.assertEqual(app.tabs.select(), str(app.ntfs_tab))
            self.assertEqual(app.export_button.cget('bg'), '#16803c')
            self.assertEqual(app.export_button.cget('text'), translate('Stapel-Export / fortsetzen', locale))
            self.assertEqual(app._nav_buttons['partition'].cget('text'), translate('▦  Partitionen',locale))
            self.assertEqual(app.file_tree.heading('#0')['text'], translate('Name', locale))
            self.assertEqual(app.browser_status_display.get(), translate(FILTER_ALL,locale))
            self.assertEqual(load_language(), locale)
        app.change_language('de')
        self.assertEqual(app.export_button.cget('text'), 'Stapel-Export / fortsetzen')

    def test_menu_click_switches_language_and_reloads(self):
        self.app._language_menu.invoke(4)  # Russian language option
        self.app.update()
        self.assertEqual(self.app.language, 'ru')
        self.assertEqual(self.app._language_button.cget('text'), '🌐  Русский')
        self.assertEqual(self.app.title(), translate('Tenshi — Datenrettung', 'ru'))
        self.app.destroy()
        self.app = RecoveryDeskApp()
        self.app.update()
        self.assertEqual(self.app.language, 'ru')
        self.assertEqual(self.app.export_button.cget('text'), translate('Stapel-Export / fortsetzen','ru'))

    def test_change_filter_under_translation(self):
        app=self.app
        app.change_language('ja')
        app.browser_status_display.set(translate(FILTER_WARNINGS,'ja'))
        app._on_localized_status_selected()
        self.assertEqual(app.browser_status_filter.get(),FILTER_WARNINGS)
        app.change_language('en')
        self.assertEqual(app.browser_status_display.get(),translate(FILTER_WARNINGS,'en'))
        app.browser_status_filter.set(FILTER_ALL)
        self.assertEqual(app.browser_status_display.get(),translate(FILTER_ALL,'en'))

    def test_advanced_search_dialog_switches_and_keeps_canonical_kind(self):
        app=self.app
        app.change_language('ru')
        app._advanced_search_dialog()
        app.update()
        app._i18n.refresh()
        self.assertEqual(app.browser_kind_combo['values'][1], translate('Nur Dateien','ru'))
        app.browser_kind_display.set(translate('Nur Dateien','ru'))
        criteria = app._read_search_criteria()
        self.assertEqual(criteria.kind,'Nur Dateien')
        # Ensure source search strings are not rewritten.
        app.browser_extension.set('*.raw;*.img')
        app.change_language('zh')
        self.assertEqual(app.browser_extension.get(), '*.raw;*.img')

    def test_popup_copy_uses_current_language(self):
        from recoverydesk.gui import messagebox
        self.app.change_language('es')
        with mock.patch('recoverydesk.gui._messagebox.showinfo') as native:
            messagebox.showinfo('Auswahl fehlt', 'Bitte zuerst ein Laufwerk markieren.')
            args, kwargs = native.call_args
            self.assertEqual(args[0], translate('Auswahl fehlt','es'))
            self.assertEqual(args[1], translate('Bitte zuerst ein Laufwerk markieren.','es'))
