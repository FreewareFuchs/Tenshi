"""Regression checks for status filtering and warnings in folder navigation."""
import unittest

from recoverydesk.browser_filter import (
    STATUS_FILTERS, FILTER_ALL, FILTER_WARNINGS, FILTER_POSSIBLE,
    FILTER_DELETED, FILTER_LIMITED, FILTER_BLOCKED, FILTER_HINTS,
    FILTER_FOLDERS, filter_entries, folder_warning_records, visual_status,
)
from recoverydesk.ntfs_browser import FileEntry, FileIndex
from recoverydesk.filesystems import GenericEntry


def entry(no, name, parent=5, *, directory=False, deleted=False,
          reason='', hint=False):
    return FileEntry(no, 1, name, parent, 1, directory, deleted,
                     size=4, data_kind='resident', resident_data=b'test',
                     unsupported_reason=reason, metadata_only=hint)


class StatusFilterTests(unittest.TestCase):
    def setUp(self):
        self.ok = entry(10, 'ok.txt')
        self.deleted = entry(11, 'old.txt', deleted=True)
        self.blocked = entry(12, 'encrypted.bin', reason='Verschlüsselung')
        self.hint = entry(13, 'name-only.dat', hint=True)
        self.folder = entry(14, 'Unreadable', directory=True, reason='Nicht lesbar')
        self.items = [self.ok, self.deleted, self.blocked, self.hint, self.folder]

    def test_all_filter_keeps_every_file_type_and_order(self):
        self.assertEqual(filter_entries(self.items, FILTER_ALL), self.items)
        self.assertEqual(filter_entries(self.items, 'Unbekannt'), self.items)

    def test_filter_categories(self):
        expected = {
            FILTER_POSSIBLE: [self.ok],
            FILTER_DELETED: [self.deleted],
            FILTER_BLOCKED: [self.blocked],
            FILTER_HINTS: [self.hint],
            FILTER_LIMITED: [self.folder],
            FILTER_FOLDERS: [self.folder],
            FILTER_WARNINGS: [self.blocked, self.hint, self.folder],
        }
        for category, matches in expected.items():
            with self.subTest(category=category):
                self.assertEqual(filter_entries(self.items, category), matches)
        self.assertEqual(len(STATUS_FILTERS), len(set(STATUS_FILTERS)))

    def test_warning_icons_do_not_claim_content_is_broken(self):
        self.assertEqual(visual_status(self.ok)[0], '📄')
        self.assertEqual(visual_status(self.deleted)[1], 'deleted')
        self.assertEqual(visual_status(self.blocked)[1], 'warning')
        self.assertIn('Metadaten', visual_status(self.hint)[2])

    def test_generic_filesystem_damaged_directory_is_flagged(self):
        bad_folder = GenericEntry(11, 'bad', 5, True, 0, ('dir', 11),
                                  unsupported_reason='Ordnerinhalt unlesbar')
        self.assertEqual(filter_entries([bad_folder], FILTER_WARNINGS), [bad_folder])
        self.assertEqual(folder_warning_records([bad_folder]), {5, 11})

    def test_warnings_propagate_to_parent_folders(self):
        folder = entry(6, 'Docs', directory=True)
        nested = entry(7, 'Archive', parent=6, directory=True)
        broken = entry(10, 'locked.doc', parent=7, reason='nicht unterstützt')
        self.assertEqual(folder_warning_records([folder, nested, broken]), {5, 6, 7})

    def test_clean_and_deleted_entries_do_not_mislabel_folders_damaged(self):
        folder = entry(6, 'Docs', directory=True)
        deleted = entry(9, 'old', parent=6, deleted=True)
        self.assertEqual(folder_warning_records([folder, deleted]), set())

    def test_orphan_and_cycle_do_not_falsely_warn_root(self):
        orphan_folder = entry(6, 'Lost', parent=999, directory=True)
        child = entry(8, 'corrupt', parent=6, reason='nicht lesbar')
        self.assertEqual(folder_warning_records([orphan_folder, child]), {6})
        a = entry(6, 'Loop A', parent=7, directory=True)
        b = entry(7, 'Loop B', parent=6, directory=True)
        self.assertEqual(folder_warning_records([a, b, child]), {6, 7})


class BrowserGUIStatusTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.folder = entry(6, 'Docs', directory=True)
        self.safe = entry(7, 'test.bin', parent=6)
        self.bad = entry(8, 'broken.bin', parent=6, reason='Nicht unterstützte Daten')
        self.old = entry(9, 'old.bin', parent=6, deleted=True)
        entries = [self.folder, self.safe, self.bad, self.old]
        self.index = FileIndex(info=None, entries=entries, total_records=20, scanned_records=20,
                               children={5: [self.folder], 6: [self.safe, self.bad, self.old]})
        self.app.browser_index = self.index
        self.app.browser_warning_records = folder_warning_records(entries)
        self.app._rebuild_folder_tree()
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def test_folder_icon_warns_and_filter_can_be_changed_in_place(self):
        app = self.app
        child = app.folder_tree.get_children('root')[0]
        self.assertTrue(app.folder_tree.item(child, 'text').startswith('⚠'))
        app.folder_tree.selection_set(child)
        app.update()
        self.assertEqual(len(app.file_tree.get_children()), 3)
        app.browser_status_filter.set(FILTER_WARNINGS)
        app._on_browser_filter_change()
        app.update()
        self.assertEqual(len(app.file_tree.get_children()), 1)
        self.assertEqual(app.file_tree.item(app.file_tree.get_children()[0], 'values')[3],
                         'Nicht exportierbar')
        self.assertIn('1 von 3', app.browser_filter_summary.get())
        app.browser_status_filter.set(FILTER_ALL)
        app._on_browser_filter_change()
        app.update()
        self.assertEqual(len(app.file_tree.get_children()), 3)

    def test_search_respects_filter_and_restores_current_directory(self):
        app = self.app
        app.browser_status_filter.set(FILTER_BLOCKED)
        app.browser_search.set('.bin')
        app._search_browser()
        app.update()
        self.assertEqual(len(app.file_tree.get_children()), 1)
        app.browser_status_filter.set(FILTER_ALL)
        app._on_browser_filter_change()
        app.update()
        self.assertEqual(len(app.file_tree.get_children()), 3)

    def test_warning_file_is_visible_in_folder_tree_and_selectable(self):
        app = self.app
        folder_node = app.folder_tree.get_children('root')[0]
        app.folder_tree.selection_set(folder_node)
        app._load_folder_children(folder_node)
        app.update()
        leaf_nodes = [n for n in app.folder_tree.get_children(folder_node) if n.startswith('warn:')]
        self.assertEqual(len(leaf_nodes), 1)
        self.assertIn('broken.bin', app.folder_tree.item(leaf_nodes[0], 'text'))
        app.folder_tree.selection_set(leaf_nodes[0])
        app.update()
        self.assertEqual(app.file_tree.selection(), (self.bad.key,))

    def test_deleted_directory_visible_in_deleted_filter(self):
        gone = entry(20, 'Old Directory', directory=True, deleted=True)
        self.assertEqual(filter_entries([gone], FILTER_DELETED), [gone])
        self.assertEqual(visual_status(gone)[0], '✕')

    def test_source_reset_clears_warnings_and_filter(self):
        app = self.app
        app.browser_status_filter.set(FILTER_WARNINGS)
        app._reset_analysis_for_source()
        self.assertEqual(app.browser_status_filter.get(), FILTER_ALL)
        self.assertEqual(app.browser_warning_records, set())
        self.assertEqual(len(app.file_tree.get_children()), 0)


if __name__ == '__main__':
    unittest.main()
