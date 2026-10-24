"""Large-tree path storage preserves semantics and bounds retained full paths."""
import unittest
from unittest.mock import Mock
from recoverydesk.explorer import construct_paths, search_entries, SearchCriteria, sorted_entries
from test_explorer import e


class LazyPathTests(unittest.TestCase):
    def test_matches_eager_paths_with_orphans_cycles_and_multiple_links(self):
        entries = [e(6, 'dir', directory=True), e(7, 'sub', parent=6, directory=True),
                   e(8, 'doc.txt', parent=7), e(9, 'orphan', parent=999),
                   e(21, 'A', parent=22, directory=True),
                   e(22, 'B', parent=21, directory=True), e(23, 'cyclic', parent=21)]
        other_link = e(8, 'other.txt', parent=6)
        other_link.link_index = 2
        entries.append(other_link)
        eager = construct_paths(entries)
        lazy = construct_paths(iter(entries), lazy=True)
        self.assertEqual(dict(lazy), eager)
        self.assertEqual(len(lazy), len(eager))
        self.assertEqual(lazy.get('absent', 'fallback'), 'fallback')
        self.assertEqual([x.key for x in sorted_entries(entries, 'path', paths=lazy)],
                         [x.key for x in sorted_entries(entries, 'path', paths=eager)])
        for criteria in (SearchCriteria(name='dir', in_path=True), SearchCriteria(extensions='txt')):
            self.assertEqual(search_entries(entries, criteria, lazy), search_entries(entries, criteria, eager))

    def test_full_path_cache_remains_bounded_after_scanning_all_entries(self):
        entries = [e(6, 'long-folder-' * 40, directory=True)]
        entries += [e(n, f'file-{n}.txt', parent=6) for n in range(10, 10010)]
        paths = construct_paths(entries, lazy=True)
        self.assertEqual(len(paths._cache), 0)
        first_key = entries[1].key
        expected = paths[first_key]
        for item in entries:
            self.assertTrue(paths[item.key].endswith(item.name))
        self.assertLessEqual(len(paths._cache), 256)
        self.assertEqual(len(paths._parents), 2)
        self.assertEqual(paths[first_key], expected)

    def test_name_extension_and_empty_path_queries_do_not_resolve_paths(self):
        entries = [e(10, 'photo.jpg'), e(11, 'note.txt')]
        paths = Mock()
        paths.get.side_effect = AssertionError('Path lookup during non-path search')
        for criteria in (SearchCriteria(name='photo'), SearchCriteria(extensions='txt'),
                         SearchCriteria(in_path=True)):
            self.assertTrue(search_entries(entries, criteria, paths))
        paths.get.assert_not_called()

    def test_depth_limit_and_unordered_directory_records_match_eager(self):
        entries = [e(20, 'leaf', parent=19)] + [e(n, str(n), parent=n-1, directory=True) for n in range(6, 20)]
        for depth in (1, 3, 256):
            self.assertEqual(dict(construct_paths(entries, max_depth=depth, lazy=True)),
                             construct_paths(entries, max_depth=depth))
