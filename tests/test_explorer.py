"""Explorer v1.7 regression tests on synthetic entries only."""
import struct
import unittest

from recoverydesk.explorer import (SearchCriteria, search_entries, matches_query,
    construct_paths, sorted_entries, display_size, display_modified, file_extension,
    display_kind)
from recoverydesk.ntfs_browser import FileEntry, _read_entry_records
from recoverydesk.ntfs import NTFSInfo
from test_browser import record, filename
from test_ntfs import resident_attr


def e(num, name, parent=5, size=0, directory=False, modified=None, deleted=False):
    entry = FileEntry(num, 1, name, parent, 1, directory, deleted, size,
                      'resident', size, resident_data=b'x'*min(size, 20))
    entry.modified_unix = modified
    return entry


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.root_folder = e(6, 'Dokumente', directory=True)
        self.folder = e(7, 'Rechnungen', parent=6, directory=True)
        self.pdf = e(8, 'Rechnung 2024.PDF', parent=7, size=3*1024**2)
        self.jpg = e(9, 'foto.jpg', parent=5, size=300)
        self.hidden = e(10, '.config', parent=5, size=10)
        self.csv = e(11, 'jahr.csv', parent=7, size=32*1024**2)
        self.items = [self.root_folder, self.folder, self.pdf, self.jpg,
                      self.hidden, self.csv]
        self.paths = construct_paths(self.items)

    def test_extensions_case_insensitive_and_multiple(self):
        self.assertEqual(file_extension(self.pdf), '.pdf')
        self.assertEqual(file_extension(self.hidden), '')
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(extensions='PDF, *.JPG'), self.paths)],
                         ['Rechnung 2024.PDF', 'foto.jpg'])
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(extensions='*.*'), self.paths)],
                         [x.name for x in self.items])

    def test_search_path_and_globs(self):
        self.assertEqual(self.paths[self.pdf.key], '\\Dokumente\\Rechnungen\\Rechnung 2024.PDF')
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(name='rechnung', in_path=False), self.paths)],
                         ['Rechnungen', 'Rechnung 2024.PDF'])
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(name='*rechnungen*', in_path=True), self.paths)],
                         ['Rechnungen', 'Rechnung 2024.PDF', 'jahr.csv'])
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(name='*.pdf'), self.paths)],
                         ['Rechnung 2024.PDF'])

    def test_size_type_and_invalid_queries(self):
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(
                         min_bytes=1*1024**2,max_bytes=4*1024**2,kind='Nur Dateien'),self.paths)],
                         ['Rechnung 2024.PDF'])
        self.assertEqual([x.name for x in search_entries(self.items, SearchCriteria(kind='Nur Ordner'),self.paths)],
                         ['Dokumente', 'Rechnungen'])
        with self.assertRaises(ValueError):
            search_entries(self.items, SearchCriteria(min_bytes=-1))
        with self.assertRaises(ValueError):
            search_entries(self.items, SearchCriteria(min_bytes=25,max_bytes=10))

    def test_path_cycles_missing_parent_never_fake_root(self):
        orphan = e(20, 'eins.doc', parent=999)
        a = e(21, 'A', parent=22, directory=True)
        b = e(22, 'B', parent=21, directory=True)
        cyclic_file = e(23, 'cyclic.bin', parent=21)
        paths = construct_paths([orphan,a,b,cyclic_file])
        self.assertIn('[Nicht zugeordnet]', paths[orphan.key])
        self.assertIn('[Zyklischer Pfad]', paths[cyclic_file.key])

    def test_sort_numeric_date_and_unknown_last(self):
        small = e(25, 'x.bin',size=100,modified=2)
        big = e(26, 'y.bin',size=9000,modified=100)
        unknown = e(27, 'z.bin',size=555,modified=None)
        self.assertEqual([x.key for x in sorted_entries([big,small,unknown],'size')],
                         [small.key,unknown.key,big.key])
        self.assertEqual([x.key for x in sorted_entries([big,small,unknown],'modified',reverse=True)],
                         [big.key,small.key,unknown.key])
        self.assertEqual(display_modified(unknown),'—')
        self.assertEqual(display_size(1024), '1.0 KiB')
        self.assertEqual(display_kind(big), 'BIN-Datei')


class NTFSTimestampTests(unittest.TestCase):
    def test_mft_standard_information_mtime_parsed(self):
        unix = 1700000000
        filetime = 116444736000000000 + unix*10000000
        standard = bytearray(48)
        struct.pack_into('<Q', standard, 8, filetime)
        raw = record([resident_attr(0x10, standard), filename('report.txt', 5),
                      resident_attr(0x80,b'TEST')])
        info = NTFSInfo(0,512,1,512,2048,4,1024)
        entries = _read_entry_records(raw, 10, info)
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0].modified_unix, unix)
        self.assertIn('2023-',display_modified(entries[0]))

    def test_missing_standard_info_does_not_invent_date(self):
        raw = record([filename('report.txt', 5),resident_attr(0x80,b'TEST')])
        info = NTFSInfo(0,512,1,512,2048,4,1024)
        entries = _read_entry_records(raw, 10, info)
        self.assertIsNone(entries[0].modified_unix)


class GUIExplorerTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        from recoverydesk.ntfs_browser import FileIndex
        self.app = RecoveryDeskApp()
        self.app.withdraw()
        self.folder = e(6, 'Dokumente', directory=True)
        self.pdf = e(8, 'Rechnung.pdf', parent=6, size=2*1024**2,modified=1700000000)
        self.jpg = e(9,'Foto.jpg',parent=6,size=30)
        self.index = FileIndex(info=None, entries=[self.folder,self.pdf,self.jpg],
            total_records=10,scanned_records=10,children={5:[self.folder],6:[self.pdf,self.jpg]})
        self.app.browser_index = self.index
        self.app.browser_paths = construct_paths(self.index.entries)
        self.app._rebuild_folder_tree()
        child = self.app.folder_tree.get_children('root')[0]
        self.app.folder_tree.selection_set(child)
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def test_advanced_search_and_reset(self):
        app=self.app
        app.browser_extension.set('.pdf')
        app.browser_min_size.set('1')
        app.browser_search.set('Rechnung')
        app._search_browser()
        app.update()
        self.assertEqual(app.file_tree.get_children(), (self.pdf.key,))
        cols=app.file_tree.item(self.pdf.key,'values')
        self.assertEqual(cols[5],'.pdf')
        self.assertIn('2023-',cols[6])
        self.assertIn('Dokumente',cols[7])
        app._clear_advanced_search()
        app.update()
        self.assertEqual(len(app.file_tree.get_children()), 2)

    def test_keyboard_select_copy_and_sort(self):
        app=self.app
        app._sort_browser('size')
        app.update()
        self.assertEqual(app.file_tree.get_children()[0],self.jpg.key)
        app._select_all_browser_files()
        self.assertEqual(set(app.file_tree.selection()), {self.pdf.key,self.jpg.key})
        app._copy_selected_browser_paths()
        self.assertIn('Dokumente',app.clipboard_get())
        self.assertIn('Foto.jpg',app.clipboard_get())

    def test_search_range_validation_no_mutation(self):
        app=self.app
        previous=app.browser_index
        app.browser_min_size.set('4')
        app.browser_max_size.set('2')
        with self.assertRaises(ValueError):
            app._read_search_criteria()
        self.assertIs(app.browser_index, previous)


if __name__ == '__main__':
    unittest.main()
