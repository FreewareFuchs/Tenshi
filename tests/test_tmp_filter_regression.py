"""Regression tests: hidden .tmp warnings must disappear in both GUI panes."""
import os
import unittest
from recoverydesk.explorer import visible_entries, is_temporary_file
from recoverydesk.ntfs_browser import FileEntry, FileIndex
from recoverydesk.browser_filter import folder_warning_records


def make(no, name, parent=5, *, directory=False, deleted=False, reason='', hint=False):
    return FileEntry(no, 1, name, parent, 1, directory, deleted,
                     size=5, data_kind='resident', resident_data=b'hello',
                     unsupported_reason=reason, metadata_only=hint)


class TmpFilterTests(unittest.TestCase):
    def test_hidden_for_all_recovery_states(self):
        entries = [
            make(10, 'damaged.tmp', reason='nicht lesbar'),
            make(11, 'name.TMP', hint=True),
            make(12, 'deleted.TmP', deleted=True),
            make(13, 'orphan.tmp', parent=-1, reason='fehlende Zuordnung'),
            make(14, 'lost.tmp', directory=True, reason='nicht lesbar'),
            make(15, 'red.tmp   ', reason='nicht lesbar'),
            make(16, 'old.tmp.', hint=True),
            make(17, 'zero.tmp\u200b', reason='nicht lesbar'),
            make(18, '.tmp'),
            make(19, 'keep.tmpx'), make(20, 'keep.tmp.old'),
            make(21, 'Ordner', directory=True),
        ]
        assert len(visible_entries(entries)) == 3
        self.assertEqual([e.name for e in visible_entries(entries)],
                         ['keep.tmpx', 'keep.tmp.old', 'Ordner'])
        self.assertEqual(visible_entries(entries, True), entries)
        self.assertTrue(is_temporary_file(entries[4]))
        self.assertFalse(is_temporary_file(entries[10]))

    def test_warning_propagation_excludes_filtered_tmp(self):
        entries = [make(6, 'Docs', directory=True),
                   make(10, 'damage.tmp', 6, reason='nicht lesbar')]
        self.assertEqual(folder_warning_records(entries), {5, 6})
        self.assertEqual(folder_warning_records(visible_entries(entries)), set())


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class TmpGUIRegressionTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        entries = [make(6, 'Ordner', directory=True),
                   make(10, 'red.tmp', 6, reason='nicht lesbar'),
                   make(11, 'reconstructed.tmp', 6, hint=True),
                   make(12, 'damaged.tmp ', 6, reason='nicht lesbar'),
                   make(13, 'a.tmp', 5, directory=True, reason='nicht lesbar'),
                   make(14, 'good.docx', 6),
                   make(15, 'orphan.tmp', -1, reason='nicht lesbar')]
        index=FileIndex(info=None, entries=entries, total_records=22,
                        scanned_records=22,
                        children={5:[entries[0],entries[4]],
                                  6:[entries[1],entries[2],entries[3],entries[5]],
                                  -1:[entries[6]]})
        self.app.browser_fs='NTFS'
        self.app.browser_index=index
        self.app.browser_warning_records=folder_warning_records(visible_entries(entries))
        self.app.show_tmp.set(False)
        self.app._rebuild_folder_tree()
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def tree_text(self, parent):
        return [self.app.folder_tree.item(i,'text') for i in self.app.folder_tree.get_children(parent)]

    def test_hidden_in_tree_and_list_even_when_warned(self):
        self.assertFalse(any('.tmp' in name for name in self.tree_text('root')))
        self.assertNotIn('orphans', self.app.folder_tree.get_children(''))
        dirs=[i for i in self.app.folder_tree.get_children('root') if 'Ordner' in self.app.folder_tree.item(i,'text')]
        self.assertEqual(len(dirs),1)
        self.app._load_folder_children(dirs[0])
        self.assertFalse(any('.tmp' in name for name in self.tree_text(dirs[0])))
        self.app.current_folder=6
        self.app._show_current_directory()
        self.app.update()
        self.assertEqual([e.name for e in self.app.browser_entries_visible.values()], ['good.docx'])

    def test_toggle_restores_entries_and_search_hides_again(self):
        self.app.show_tmp.set(True)
        self.app._refresh_browser()
        self.app.update()
        self.assertTrue(any('a.tmp' in x for x in self.tree_text('root')))
        self.assertIn('orphans', self.app.folder_tree.get_children(''))
        self.app.show_tmp.set(False)
        self.app._refresh_browser()
        self.app.browser_search.set('*.tmp')
        self.app._search_browser()
        self.app.update()
        self.assertTrue(all(not is_temporary_file(e) for e in self.app.browser_entries_visible.values()))

if __name__=='__main__':
    unittest.main()
