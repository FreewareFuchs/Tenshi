"""Tenshi 2.2.0: bounded GUI materialization, paging and responsive search."""
import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from recoverydesk.explorer import (SearchCriteria, compile_search,
                                   search_entries, construct_paths)
from recoverydesk.ntfs_browser import FileEntry, FileIndex


def file_at(i, name=None, parent=5):
    return FileEntry(i + 10, 1, name or f'Eintrag{i:06d}.dat', parent, 1,
                     False, False, i + 1, 'resident', i + 1, resident_data=b'x')


class FastSearchTests(unittest.TestCase):
    def test_compiled_search_matches_uncompiled_public_api(self):
        files = [file_at(i, f'Foto{i}.JPG' if i % 2 else f'data{i}.bin')
                 for i in range(500)]
        paths = construct_paths(files)
        terms = [SearchCriteria(name='foto', extensions='*.jpg', kind='Nur Dateien'),
                 SearchCriteria(name='*.bin'),
                 SearchCriteria(min_bytes=20, max_bytes=300),
                 SearchCriteria(name='eintrag', in_path=True),
                 SearchCriteria()]
        for criteria in terms:
            compiled = compile_search(criteria)
            expected = [x for x in files if compiled(x, paths[x.key])]
            self.assertEqual(search_entries(files, criteria, paths), expected)

    def test_invalid_search_is_rejected_before_matching(self):
        with self.assertRaises(ValueError):
            compile_search(SearchCriteria(min_bytes=-100))


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class LargeBrowserGuiTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.items = [file_at(i) for i in range(3100)]
        self.items[1700].name = 'Besonderes.jpg'
        self.items[1701].name = 'cache.TMP'
        self.index = FileIndex(info=None, entries=self.items, total_records=len(self.items),
                               scanned_records=len(self.items), children={5: self.items})
        self.app.browser_index = self.index
        self.app.browser_paths = construct_paths(self.index.entries)
        self.app._rebuild_folder_tree()
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def test_paging_renders_only_bounded_amount(self):
        app = self.app
        self.assertEqual(len(app.file_tree.get_children()), 750)
        self.assertEqual(len(app.browser_sorted_items), 3099)  # TMP hidden
        self.assertIn('1 / 5', app.browser_page_caption.get())
        app._next_browser_page()
        self.assertEqual(len(app.file_tree.get_children()), 750)
        self.assertEqual(app.browser_page, 1)
        app._previous_browser_page()
        self.assertEqual(app.browser_page, 0)

    def test_export_selection_applies_to_current_page_only(self):
        app = self.app
        app._select_all_browser_files()
        self.assertEqual(len(app._selected_browser_entries()), 750)
        app._next_browser_page()
        self.assertFalse(app.file_tree.selection())
        self.assertEqual(len(app._selected_browser_entries()), 0)

    def test_sort_and_filter_keep_paging_correct(self):
        app = self.app
        app._sort_browser('size')
        self.assertEqual(len(app.file_tree.get_children()), 750)
        app.browser_status_filter.set('Nur Ordner')
        app._on_browser_filter_change()
        self.assertEqual(len(app.file_tree.get_children()), 0)
        self.assertEqual(str(app.browser_prev_button.cget('state')), 'disabled')
        self.assertEqual(str(app.browser_next_button.cget('state')), 'disabled')

    def test_large_search_is_yielding_and_finds_late_file(self):
        app = self.app
        app.browser_search.set('Besonderes.jpg')
        app._search_browser()
        self.assertIn('Suche läuft', app.browser_path.get())
        deadline = time.monotonic() + 3
        while 'Suche läuft' in app.browser_path.get() and time.monotonic() < deadline:
            app.update()
        self.assertNotIn('Suche läuft', app.browser_path.get())
        self.assertEqual(app.file_tree.get_children(), (self.items[1700].key,))

    def test_new_search_cancels_old_search(self):
        app = self.app
        app.browser_search.set('nicht-da')
        app._search_browser()
        app.browser_search.set('Besonderes.jpg')
        app._search_browser()
        deadline = time.monotonic() + 3
        while 'Suche läuft' in app.browser_path.get() and time.monotonic() < deadline:
            app.update()
        self.assertEqual(app.file_tree.get_children(), (self.items[1700].key,))

    def test_tmp_remains_hidden_across_pages_and_search(self):
        app = self.app
        app.browser_search.set('cache.TMP')
        app._search_browser()
        deadline = time.monotonic() + 3
        while 'Suche läuft' in app.browser_path.get() and time.monotonic() < deadline:
            app.update()
        self.assertEqual(app.file_tree.get_children(), ())

    def test_six_languages_update_page_caption_without_losing_page(self):
        app = self.app
        app._next_browser_page()
        for lang, expected in [('de', 'Seite'), ('en', 'Page'), ('es', 'Página'),
                               ('zh', '页'), ('ru', 'Страница'), ('ja', 'ページ')]:
            with patch('recoverydesk.gui.save_language'):
                app.change_language(lang)
            self.assertIn(expected, app.browser_page_caption.get())
            self.assertEqual(app.browser_page, 1)
            self.assertEqual(len(app.file_tree.get_children()), 750)

    def test_source_reset_clears_pager_and_cancels_search(self):
        app = self.app
        app.browser_search.set('NichtVorhanden')
        app._search_browser()
        old_generation = app.browser_search_generation
        app._reset_analysis_for_source()
        self.assertGreater(app.browser_search_generation, old_generation)
        self.assertFalse(app.browser_sorted_items)
        self.assertEqual(app.browser_page, 0)
        app.update()
        self.assertEqual(app.file_tree.get_children(), ())

    def test_background_prepared_maps_are_consumed_without_recomputing(self):
        app = self.app
        with patch('recoverydesk.gui.construct_paths', side_effect=AssertionError('unwanted GUI recomputation')):
            app._show_browser_index('test.img', self.index,
                                    prepared=(app.browser_paths, set(), False))
        self.assertEqual(len(app.file_tree.get_children()), 750)

if __name__ == '__main__':
    unittest.main()
