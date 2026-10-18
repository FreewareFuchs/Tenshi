"""Additional MIT-distribution checks without reading user disks."""
import tempfile
from pathlib import Path
import unittest
import zipfile
from unittest.mock import patch

import open_source_preflight
import release_tools

BASE = Path(__file__).resolve().parents[1]

class MitReleaseTests(unittest.TestCase):
    def test_mit_file_uses_recognizable_canonical_template(self):
        s = (BASE / 'LICENSE').read_text(encoding='utf-8')
        self.assertTrue(s.startswith('MIT License\n'))
        self.assertIn('Permission is hereby granted, free of charge', s)
        self.assertIn('Copyright (c) 2026', s)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', s)

    def test_placeholder_prevents_official_release(self):
        # Check the validation behavior, not whether the operator has already
        # filled in the real copyright holder in the actual project.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['THIRD_PARTY_NOTICES.md', 'SECURITY.md', 'CONTRIBUTING.md',
                         'README.md', 'release_tools.py', 'installer/Tenshi.iss']:
                f = root / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text('test', encoding='utf8')
            template = (BASE / 'LICENSE').read_text(encoding='utf8')
            license = root / 'LICENSE'
            license.write_text(template.replace('Copyright (c) 2026 ',
                                                'Copyright (c) 2026 [RECHTEINHABER_EINTRAGEN] # '),
                               encoding='utf8')
            with patch.object(open_source_preflight, 'ROOT', root):
                errors = open_source_preflight.check()
                self.assertTrue(any('Platzhalter' in message for message in errors))
                license.write_text(template.replace('[RECHTEINHABER_EINTRAGEN]', 'Example Holder'),
                                   encoding='utf8')
                self.assertEqual(open_source_preflight.check(), [])

    def test_installer_includes_license_in_app_and_wizard(self):
        s = (BASE / 'installer/Tenshi.iss').read_text(encoding='utf8')
        self.assertIn('LicenseFile=..\\LICENSE', s)
        self.assertIn('Source: "..\\LICENSE"; DestDir: "{app}"', s)

    def test_portable_zip_bundles_mit_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            exe=d/'Tenshi.exe'
            exe.write_bytes(b'MZ' + b'X' * 4000)
            target=release_tools.create_portable(exe, d/'Tenshi.zip')
            with zipfile.ZipFile(target) as archive:
                self.assertIn('LICENSE', archive.namelist())
                self.assertIn(b'MIT License', archive.read('LICENSE'))
                self.assertEqual(archive.read('LICENSE'), (BASE/'LICENSE').read_bytes())
            self.assertEqual(release_tools.verify_portable(target), release_tools.file_sha256(exe))

    def test_portable_tampered_license_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            exe=d/'Tenshi.exe'
            exe.write_bytes(b'MZ' + b'X' * 4000)
            target=release_tools.create_portable(exe,d/'origin.zip')
            with zipfile.ZipFile(target) as src, zipfile.ZipFile(d/'changed.zip', 'w') as dst:
                for name in src.namelist():
                    dst.writestr(name, b'garbled' if name == 'LICENSE' else src.read(name))
            with self.assertRaisesRegex(ValueError, 'MIT'):
                release_tools.verify_portable(d/'changed.zip')

    def test_release_script_has_preflight(self):
        s=(BASE/'RELEASE_WINDOWS_ERSTELLEN.bat').read_text(encoding='utf8')
        self.assertIn('open_source_preflight.py', s)

if __name__ == '__main__':
    unittest.main()
