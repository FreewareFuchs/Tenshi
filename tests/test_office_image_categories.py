"""Category extension regression tests for Tenshi 1.7.5."""
import unittest
from types import SimpleNamespace
from recoverydesk.explorer import (
    EXTENSION_CATEGORIES, append_category_extensions,
    SearchCriteria, matches_query, _normal_extensions,
)

class OfficeAndImageCategoriesTests(unittest.TestCase):
    def test_archive_includes_requested_disk_images(self):
        self.assertTrue({'img', 'raw', 'dd'}.issubset(EXTENSION_CATEGORIES['Archive']))

    def test_office_families_and_templates(self):
        required = {
            # MS Office old/current/macro/templates
            'doc', 'docx', 'docm', 'dot', 'dotx', 'dotm',
            'xls', 'xlsx', 'xlsm', 'xlsb', 'xlt', 'xltx', 'xltm',
            'ppt', 'pptx', 'pptm', 'pps', 'ppsx', 'ppsm', 'pot', 'potx', 'potm',
            'mdb', 'accdb', 'one', 'pub', 'vsdx', 'mpp',
            # LibreOffice/OpenOffice current and historic
            'odt', 'ott', 'ods', 'ots', 'odp', 'otp', 'odg', 'otg',
            'odb', 'odf', 'fodt', 'fods', 'fodp', 'fodg',
            'sxw', 'sxc', 'sxi', 'sxd',
        }
        self.assertTrue(required.issubset(EXTENSION_CATEGORIES['Dokumente']))

    def test_duplicate_free_combination_and_case_insensitivity(self):
        text = append_category_extensions('*.IMG, selbstdefiniert, *.DOCX', 'Archive')
        text = append_category_extensions(text, 'Dokumente')
        text = append_category_extensions(text, 'Archive')
        text = append_category_extensions(text, 'Dokumente')
        norm = _normal_extensions(text)
        for suffix in ('.img', '.raw', '.dd', '.docx', '.docm', '.odt', '.sxw'):
            self.assertEqual(norm.count(suffix), 1)
        self.assertIn('.selbstdefiniert', norm)

    def test_search_matches_new_endings_and_excludes_others(self):
        text = append_category_extensions('', 'Dokumente')
        text = append_category_extensions(text, 'Archive')
        c = SearchCriteria(extensions=text)
        def f(name):
            return SimpleNamespace(name=name, size=128, is_directory=False)
        for name in ('Sicherung.RAW', 'disk.DD', 'bild.IMG',
                     'Dokument.DOCM', 'Kalkulation.ODS', 'Zeichnung.ODG'):
            self.assertTrue(matches_query(f(name), c), name)
        self.assertFalse(matches_query(f('Tonaufnahme.mp3'), c))

if __name__ == '__main__':
    unittest.main()
