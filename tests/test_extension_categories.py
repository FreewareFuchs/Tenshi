"""Tests for category shortcuts in the Tenshi advanced file search."""
import unittest
from types import SimpleNamespace
from recoverydesk.explorer import (EXTENSION_CATEGORIES, SearchCriteria,
    append_category_extensions, matches_query, _normal_extensions)


def file(name):
    return SimpleNamespace(name=name, size=17, is_directory=False)


class ExtensionCategoryTests(unittest.TestCase):
    def test_all_five_categories_available(self):
        self.assertEqual(tuple(EXTENSION_CATEGORIES),
                         ('Bilder', 'Videos', 'Audio', 'Dokumente', 'Archive'))

    def test_expected_common_extensions_present(self):
        for name, example in [('Bilder', 'jpeg'), ('Videos', 'mp4'),
                              ('Audio', 'flac'), ('Dokumente', 'docx'),
                              ('Archive', '7z')]:
            self.assertIn(example, EXTENSION_CATEGORIES[name])

    def test_shortcuts_append_without_erasing_manual_entries(self):
        result = append_category_extensions('custom, *.PDF', 'Bilder')
        self.assertTrue(result.startswith('custom, *.PDF,'))
        self.assertIn('.jpg', _normal_extensions(result))
        self.assertIn('.custom', _normal_extensions(result))

    def test_combined_categories_are_or_filter(self):
        both = append_category_extensions(append_category_extensions('', 'Bilder'), 'Archive')
        self.assertTrue(matches_query(file('urlaub.JPG'), SearchCriteria(extensions=both)))
        self.assertTrue(matches_query(file('backup.ZIP'), SearchCriteria(extensions=both)))
        self.assertFalse(matches_query(file('musik.mp3'), SearchCriteria(extensions=both)))
        self.assertFalse(matches_query(SimpleNamespace(name='Ordner',is_directory=True,size=0),
                                       SearchCriteria(extensions=both)))

    def test_clicking_same_category_twice_does_not_duplicate_extensions(self):
        once = append_category_extensions('*.PNG', 'Bilder')
        twice = append_category_extensions(once, 'Bilder')
        self.assertEqual(twice, once)
        self.assertEqual(_normal_extensions(twice).count('.png'), 1)

    def test_unknown_category_is_reported(self):
        with self.assertRaises(ValueError):
            append_category_extensions('pdf', 'Musikvideos')


class GUIExtensionCategoryTests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()

    def test_dialog_buttons_update_extension_field_without_auto_search(self):
        app = self.app
        app.browser_extension.set('eigene')
        app._advanced_search_dialog()
        app.update()
        dialogs = [child for child in app.winfo_children()
                   if child.winfo_class() == 'Toplevel']
        self.assertEqual(len(dialogs), 1)
        dialog = dialogs[0]

        def iter_widgets(widget):
            for child in widget.winfo_children():
                yield child
                yield from iter_widgets(child)

        buttons = {item.cget('text'): item for item in iter_widgets(dialog)
                   if item.winfo_class() == 'TButton'}
        self.assertTrue(set(EXTENSION_CATEGORIES).issubset(buttons))
        buttons['Bilder'].invoke()
        buttons['Videos'].invoke()
        buttons['Bilder'].invoke()
        app.update()
        exts = _normal_extensions(app.browser_extension.get())
        self.assertEqual(exts.count('.png'), 1)
        self.assertIn('.mp4', exts)
        self.assertIn('.eigene', exts)
        dialog.destroy()


if __name__ == '__main__':
    unittest.main()
