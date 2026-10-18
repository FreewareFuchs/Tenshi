"""Tenshi 3.0.2: branded exports and safe backwards-compatible resume."""
import tempfile
import json
from pathlib import Path
import unittest

from recoverydesk.batch_export import export_batch
from recoverydesk.filesystems import scan_tree
from test_filesystems import fat_img


class ExportBrand302Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'image.raw'
        self.source.write_bytes(fat_img())
        self.dest = self.base / 'target'
        self.dest.mkdir()
        self.idx = scan_tree(str(self.source))
        self.entry = next(e for e in self.idx.list_dir(5) if e.name == 'README.TXT')

    def export(self):
        return export_batch(str(self.source), self.idx, [self.entry], str(self.dest))

    def test_new_export_is_branded_and_resume_is_stable(self):
        one = self.export()
        self.assertTrue(Path(one.root).name.startswith('Tenshi_Export_'))
        self.assertEqual((Path(one.root) / 'files' / 'README.TXT').read_bytes(), b'HELLO')
        two = self.export()
        self.assertEqual(two.root, one.root)
        self.assertTrue(two.resumed)
        self.assertEqual(two.verified_existing, 1)
        self.assertEqual(two.exported, 0)

    def test_existing_legacy_export_is_resumed_not_duplicated(self):
        original = self.export()
        modern = Path(original.root)
        legacy = modern.with_name(modern.name.replace('Tenshi_Export_', 'RecoveryDesk_Export_', 1))
        modern.rename(legacy)
        continued = self.export()
        self.assertEqual(Path(continued.root), legacy)
        self.assertTrue(continued.resumed)
        self.assertEqual(continued.verified_existing, 1)
        self.assertFalse(modern.exists())

    def test_invalid_legacy_directory_is_not_bypassed(self):
        result = self.export()
        modern = Path(result.root)
        legacy = modern.with_name(modern.name.replace('Tenshi_Export_', 'RecoveryDesk_Export_', 1))
        modern.rename(legacy)
        (legacy / 'recoverydesk_status.json').unlink(missing_ok=True)
        # Even with an old invalid checkpoint, do not create a second export
        # that might camouflage the failure.
        with self.assertRaises((FileExistsError, ValueError)):
            self.export()
        self.assertFalse(modern.exists())

    def test_legacy_is_left_intact_if_new_version_exists(self):
        first = self.export()
        modern = Path(first.root)
        legacy = modern.with_name(modern.name.replace('Tenshi_Export_', 'RecoveryDesk_Export_', 1))
        legacy.mkdir()
        second = self.export()
        self.assertEqual(second.root, str(modern))
        self.assertTrue(legacy.exists())


if __name__ == '__main__':
    unittest.main()
