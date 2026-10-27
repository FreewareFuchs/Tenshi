"""Tenshi 3.0: offline help, six translations and non-invasive GUI navigation."""
import os
import tempfile
import unittest
from unittest import mock

from recoverydesk import __version__
from recoverydesk.help_center import (DATA, TOPICS, LANG_INDEX, WINDOW_LABELS,
                                      available_topics, topic_text)
from recoverydesk.i18n import LANGUAGES, translate
from recoverydesk.gui import RecoveryDeskApp


class HelpContentTests(unittest.TestCase):
    def test_all_nine_topics_have_six_complete_languages(self):
        self.assertEqual(len(TOPICS), 9)
        self.assertEqual(set(TOPICS), set(DATA))
        for topic in TOPICS:
            self.assertEqual(len(DATA[topic][0]), len(LANGUAGES))
            self.assertEqual(len(DATA[topic][1]), len(LANGUAGES))
            for lang in LANGUAGES:
                title, text = topic_text(topic, lang)
                self.assertTrue(title.strip())
                self.assertGreater(len(text), 75, (topic, lang))
                self.assertNotIn('{version}', text)

    def test_help_window_labels_are_translated(self):
        self.assertEqual(set(WINDOW_LABELS), set(LANGUAGES))
        for lang, strings in WINDOW_LABELS.items():
            self.assertEqual(len(strings), 5)
            self.assertTrue(all(strings))
        for lang in LANGUAGES:
            self.assertNotEqual(translate('Hilfe', lang), 'Hilfe' if lang != 'de' else '')

    def test_version_and_safety_limits_in_help(self):
        for language in LANGUAGES:
            about = topic_text('about', language)[1]
            self.assertIn(__version__, about)
            self.assertIn('Btrfs/XFS', topic_text('browser', language)[1])
            self.assertIn('SHA-256', topic_text('sessions', language)[1])
            self.assertIn('0', topic_text('imaging', language)[1])
        self.assertIn('nicht', topic_text('safety', 'de')[1])
        self.assertIn('nicht', topic_text('sessions', 'de')[1])
        self.assertIn('750', topic_text('browser', 'de')[1])

    def test_search_finds_body_and_title_in_selected_language(self):
        self.assertIn('export', available_topics('en', 'BATCH EXPORT'))
        self.assertIn('partitions', available_topics('de', 'Partitionen'))
        self.assertIn('sessions', available_topics('ja', '.tenshi-session'))
        self.assertEqual(available_topics('en', 'no-such-keyword-528917'), [])
        self.assertEqual(available_topics('en', ''), list(TOPICS))

    def test_chinese_and_japanese_search_does_not_use_german_fallback(self):
        self.assertIn('safety', available_topics('zh', '安全'))
        self.assertIn('about', available_topics('ja', 'について'))
        self.assertEqual(topic_text('partitions','zh')[0], '分区')

    def test_invalid_topic_rejected_and_language_fallback(self):
        with self.assertRaises(ValueError):
            topic_text('not-a-topic', 'de')
        self.assertEqual(topic_text('start', 'not-a-language'), topic_text('start', 'de'))

    def test_packaged_smoke_checks_translated_help_without_gui(self):
        import main
        self.assertEqual(main.main(['--smoke-test']), 0)
        with mock.patch('recoverydesk.help_center.topic_text', return_value=('','')):
            self.assertEqual(main.main(['--smoke-test']), 1)

    def test_help_content_contains_no_file_source_actions(self):
        from recoverydesk import help_center
        from pathlib import Path
        source = Path(help_center.__file__).read_text(encoding='utf-8')
        for forbidden in ('.open_source(', '.create_image(', '.export_batch(', 'pickle.loads', 'exec('):
            self.assertNotIn(forbidden, source)


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Display required')
class HelpWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {
            'TENSHI_SETTINGS_FILE': os.path.join(self.temp.name,'settings.json'),
            'TENSHI_LOG_DIR': os.path.join(self.temp.name,'logs'),
        })
        self.env.start()
        self.app = RecoveryDeskApp()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_header_help_button_translates_in_all_six_languages_and_back(self):
        from recoverydesk.version_info import display_version
        self.app.source_path.set('test-image.raw')
        labels = {'de': 'Hilfe', 'en': 'Help', 'es': 'Ayuda',
                  'zh': '帮助', 'ru': 'Справка', 'ja': 'ヘルプ'}
        for language in (*LANGUAGES, 'de'):
            with self.subTest(language=language):
                self.app.change_language(language)
                self.app.update()
                self.assertEqual(self.app.help_button.cget('text'), labels[language])
                self.assertEqual(self.app.source_path.get(), 'test-image.raw')
                self.assertIn(display_version(), self.app.title())

    def test_button_opens_help_without_changing_two_tabs_or_source(self):
        self.app.source_path.set('test-image.raw')
        with mock.patch('recoverydesk.gui.open_source', side_effect=AssertionError('disk read')):
            window = self.app.show_help()
            self.app.update()
        self.assertEqual(len(self.app.tabs.tabs()), 2)
        self.assertEqual(self.app.source_path.get(), 'test-image.raw')
        self.assertEqual(window.topic, 'start')
        self.assertEqual(window.topics_list.size(), 9)
        self.assertEqual(self.app.export_button.cget('bg'), self.app._palette()['accent'])

    def test_f1_defaults_to_current_tab(self):
        self.app._select_main_tab('partition')
        self.app._help_shortcut()
        self.assertEqual(self.app._help_window.topic, 'partitions')
        self.app._select_main_tab('files')
        self.app._help_shortcut()
        self.assertEqual(self.app._help_window.topic, 'browser')

    def test_search_and_topic_selection_does_not_modify_source(self):
        w = self.app.show_help()
        w.search_var.set('Stapel-Export')
        self.app.update()
        self.assertIn('export', w._visible_topics)
        w.search_var.set('gar-nicht-vorhanden-990')
        self.assertEqual(w._visible_topics, [])
        self.assertEqual(str(w.go_button.cget('state')), 'disabled')
        w.search_var.set('')
        w.topics_list.selection_clear(0,'end')
        pos = w._visible_topics.index('sessions')
        w.topics_list.selection_set(pos)
        w._topic_selected()
        self.assertEqual(w.topic,'sessions')
        self.assertIn('SHA-256', w.body_text.get('1.0','end-1c'))

    def test_immediate_language_and_theme_changes(self):
        w = self.app.show_help('imaging')
        self.app.change_language('en')
        self.assertEqual(w.language,'en')
        self.assertEqual(w.title_label.cget('text'),topic_text('imaging','en')[0])
        self.app.change_language('ja')
        self.assertEqual(w.title_label.cget('text'),topic_text('imaging','ja')[0])
        self.app.change_theme('dark')
        self.assertEqual(w.body_text.cget('background'),self.app._palette()['input'])

    def test_help_control_visible_at_minimum_window_size(self):
        self.app.geometry('1024x650+0+0')
        self.app.update()
        self.assertGreater(self.app.help_button.winfo_width(), 45)
        self.assertLessEqual(self.app.help_button.winfo_rootx() + self.app.help_button.winfo_width(),
                             self.app.winfo_rootx() + self.app.winfo_width())
        self.assertEqual(len(self.app.tabs.tabs()), 2)

    def test_tab_navigation_and_reuse(self):
        window = self.app.show_help('browser')
        self.assertEqual(str(window.go_button.cget('state')), 'normal')
        window._go_to_tab()
        self.assertEqual(self.app.tabs.select(), str(self.app.ntfs_tab))
        again = self.app.show_help('partitions')
        self.assertIs(again,window)
        again._go_to_tab()
        self.assertEqual(self.app.tabs.select(), str(self.app.partition_tab))
        window.destroy()
        new = self.app.show_help('start')
        self.assertIsNot(new,window)

if __name__ == '__main__':
    unittest.main()
