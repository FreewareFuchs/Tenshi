"""Presentation-only .tmp filters: files remain available for deliberate recovery."""
import os
import unittest
from recoverydesk.explorer import (is_temporary_file, visible_entries,
                                   SearchCriteria, search_entries)
from recoverydesk.ntfs_browser import FileEntry
from recoverydesk.gui import RecoveryDeskApp


def entry(number, name, parent=5, directory=False, deleted=False,
          warning=False):
    return FileEntry(number, 1, name, parent, 1, directory, deleted,
                     0, 'none', unsupported_reason='Nicht geprüft' if warning else '')


class FakeIndex:
    def __init__(self, entries):
        self.entries = list(entries)
        self.orphan_count = sum(e.parent_record == -1 for e in self.entries)

    def list_dir(self, parent, show_deleted=True):
        return [e for e in self.entries if e.parent_record == parent
                and (show_deleted or not e.is_deleted)]


class TmpVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.files = [entry(10, 'bild.jpg'), entry(11, 'CACHE.TMP'),
                      entry(12, 'draft.tmp', deleted=True),
                      entry(13, '.tmp'), entry(14, 'Dokumente.tmp', directory=True),
                      entry(15, 'arbeitsdatei.tmpx'), entry(16, 'temp.tmp', parent=-1),
                      entry(17, 'defekt.TmP', warning=True)]

    def test_only_real_tmp_files_hidden_case_insensitively(self):
        shown = visible_entries(self.files)
        names = {e.name for e in shown}
        self.assertEqual(names, {'bild.jpg', 'arbeitsdatei.tmpx'})
        self.assertTrue(is_temporary_file(self.files[4]))
        self.assertTrue(is_temporary_file(self.files[3]))

    def test_optional_visibility_preserves_original_instances(self):
        self.assertEqual(visible_entries(self.files, True), self.files)
        self.assertEqual(len(self.files), 8)

    def test_global_search_can_exclude_tmp_before_matching(self):
        query = SearchCriteria(name='*')
        self.assertEqual(len(search_entries(visible_entries(self.files), query)), 2)
        self.assertEqual(len(search_entries(visible_entries(self.files, True), query)), 8)

    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
    def test_browser_views_and_toggle(self):
        app = RecoveryDeskApp()
        try:
            app.update()
            app.browser_fs = 'NTFS'
            app.browser_index = FakeIndex(self.files)
            app.browser_paths = {e.key: '\\' + e.name for e in self.files}
            app.browser_warning_records = set()
            app.show_tmp.set(False)
            app._refresh_browser()
            app.update()
            visible = [app.file_tree.item(i, 'text') for i in app.file_tree.get_children('')]
            self.assertTrue(all(not is_temporary_file(app.browser_entries_visible[i]) for i in app.browser_entries_visible), visible)
            self.assertNotIn('orphans', app.folder_tree.get_children(''))
            self.assertTrue(all('Dokumente.tmp' not in app.folder_tree.item(i, 'text') for i in app.folder_tree.get_children('root')))
            self.assertFalse(any('defekt.TmP' in app.folder_tree.item(i, 'text')
                                 for i in app.folder_tree.get_children('root')))
            self.assertFalse(app.show_tmp.get())
            # Show tmp and recover access to the exact same index data.
            app.show_tmp.set(True)
            app._refresh_browser()
            app.update()
            visible = [app.file_tree.item(i, 'text') for i in app.file_tree.get_children('')]
            self.assertTrue(any('CACHE.TMP' in x for x in visible), visible)
            self.assertIn('orphans', app.folder_tree.get_children(''))
            self.assertTrue(any('defekt.TmP' in app.folder_tree.item(i, 'text')
                                for i in app.folder_tree.get_children('root')))
            # Restore and global search hides tmp again.
            app.show_tmp.set(False)
            app._refresh_browser()
            app.browser_search.set('*')
            app._search_browser()
            app.update()
            self.assertTrue(all(not is_temporary_file(e) for e in app.browser_entries_visible.values()))
        finally:
            app.destroy()

if __name__ == '__main__':
    unittest.main()
