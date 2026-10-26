"""Tenshi 3.0.3 release engineering regression checks (no Windows build required)."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import main as app_entry
import release_tools
from recoverydesk import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_exe(path: Path, payload=b'MZ' + b'Q' * 3000):
    path.write_bytes(payload)
    return path


class PortableArchiveTests(unittest.TestCase):
    def test_create_and_verify_portable_archive_with_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            exe = test_exe(d / 'Tenshi.exe')
            archive = release_tools.create_portable(exe, d / 'out' / 'Tenshi.zip')
            self.assertEqual(release_tools.verify_portable(archive), release_tools.file_sha256(exe))
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()), set(release_tools.PACKAGE_ITEMS))
                self.assertEqual(z.read('Tenshi.exe'), exe.read_bytes())
                self.assertIn(b'Tenshi 3.0.3', z.read('PORTABLE_START.txt'))
                self.assertIn(b'APPDATA', z.read('PORTABLE_START.txt'))
                self.assertNotIn(b'tenshi-errors.log\n2026', z.read('PORTABLE_START.txt'))

    def test_rejects_non_exe_or_short_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for payload in (b'MZ', b'PK' + b'X' * 3000):
                exe = test_exe(d / 'Tenshi.exe', payload)
                with self.assertRaises(ValueError):
                    release_tools.create_portable(exe, d / 'out.zip')
            self.assertFalse((d / 'out.zip').exists())

    def test_no_overwrite_without_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            exe = test_exe(d / 'Tenshi.exe')
            result = release_tools.create_portable(exe, d / 'out.zip')
            original = result.read_bytes()
            with self.assertRaises(FileExistsError):
                release_tools.create_portable(exe, d / 'out.zip')
            self.assertEqual(result.read_bytes(), original)
            output = release_tools.create_portable(exe, d / 'out.zip', overwrite=True)
            self.assertEqual(output.read_bytes(), original)

    def test_rejects_tampered_executable_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            exe = test_exe(d / 'Tenshi.exe')
            archive = release_tools.create_portable(exe, d / 'original.zip')
            with zipfile.ZipFile(archive) as src, zipfile.ZipFile(d / 'tampered.zip', 'w') as dst:
                for name in src.namelist():
                    data = src.read(name)
                    if name == 'Tenshi.exe':
                        data += b'corrupt'
                    dst.writestr(name, data)
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                release_tools.verify_portable(d / 'tampered.zip')

    def test_rejects_zip_with_path_traversal_or_extra_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            exe = test_exe(d / 'Tenshi.exe')
            archive = release_tools.create_portable(exe, d / 'original.zip')
            with zipfile.ZipFile(archive) as src, zipfile.ZipFile(d / 'extra.zip', 'w') as dst:
                for name in src.namelist():
                    dst.writestr(name, src.read(name))
                dst.writestr('../private.ini', 'secret')
            with self.assertRaises(ValueError):
                release_tools.verify_portable(d / 'extra.zip')

    def test_rejects_source_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            exe = test_exe(d / 'Tenshi.exe')
            link = d / 'folder' / 'Tenshi.exe'
            link.parent.mkdir()
            try:
                link.symlink_to(exe)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable on this platform')
            with self.assertRaises(ValueError):
                release_tools.create_portable(link, d / 'out.zip')

    def test_failed_creation_removes_temporary_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            exe = test_exe(d / 'Tenshi.exe')
            with patch.object(release_tools, 'verify_portable', side_effect=ValueError('bad hash')):
                with self.assertRaises(ValueError):
                    release_tools.create_portable(exe, d / 'out.zip')
            self.assertFalse((d / 'out.zip').exists())
            self.assertEqual(sorted(p.name for p in d.iterdir()), ['Tenshi.exe'])


class ReleaseIntegrationTests(unittest.TestCase):
    def test_version_sync_across_sources_installer_exe_and_portable(self):
        self.assertEqual(__version__, '3.0.3')
        installer = (ROOT / 'installer/Tenshi.iss').read_text(encoding='utf-8')
        version_info = (ROOT / 'build/version_info.txt').read_text(encoding='utf-8')
        build = (ROOT / 'build_windows.bat').read_text(encoding='ascii')
        portable = (ROOT / 'build_portable.bat').read_text(encoding='ascii')
        for target in (installer, build, portable, version_info):
            self.assertIn('3.0.3', target)
        self.assertIn('filevers=(3, 0, 3, 0)', version_info)
        self.assertIn('prodvers=(3, 0, 3, 0)', version_info)
        self.assertIn('Tenshi_Setup_3.0.3.exe', (ROOT / 'build_installer.bat').read_text(encoding='ascii'))

    def test_version_and_smoke_mode_without_creating_gui(self):
        with patch('recoverydesk.gui.RecoveryDeskApp', side_effect=AssertionError('GUI started')):
            self.assertEqual(app_entry.main(['--smoke-test']), 0)
            self.assertEqual(app_entry.main(['--version']), 0)
            self.assertEqual(app_entry.main(['--unknown-flag']), 2)

    def test_windows_build_contains_resources_and_does_not_run_tests(self):
        script = (ROOT / 'build_windows.bat').read_text(encoding='ascii')
        self.assertIn('--version-file "build/version_info.txt"', script)
        self.assertIn('--icon "recoverydesk/assets/tenshi.ico"', script)
        self.assertIn('--add-data "recoverydesk/assets;recoverydesk/assets"', script)
        self.assertNotIn('unittest discover', script)
        self.assertIn('--no-pause', script)
        self.assertIn('tenshi-build.log', script)

    def test_installer_is_per_user_and_x64(self):
        installer = (ROOT / 'installer/Tenshi.iss').read_text(encoding='utf-8')
        self.assertIn('PrivilegesRequired=lowest', installer)
        self.assertIn('ArchitecturesAllowed=x64compatible', installer)
        self.assertIn('AppId={{C2771C39-', installer)
        self.assertIn('SetupIconFile=..\\recoverydesk\\assets\\tenshi.ico', installer)
        self.assertIn('UninstallDisplayIcon={app}\\Tenshi.exe', installer)

    def test_windows_workflow_runs_tests_build_smoke_and_artifacts(self):
        workflow = (ROOT / '.github/workflows/windows-check.yml').read_text(encoding='utf-8')
        for required in ('windows-latest', 'unittest discover', 'build_windows.bat',
                         '--smoke-test', 'build_portable.bat', 'release_tools.py verify',
                         'build_installer.bat', 'Tenshi_Portable_3.0.3_Win64.zip'):
            self.assertIn(required, workflow)

    def test_portable_instructions_warn_of_nonportable_config(self):
        message = release_tools.PORTABLE_TEXT
        self.assertIn('OHNE INSTALLER', message)
        self.assertIn('NICHT komplett USB-portabel', message)
        self.assertIn('APPDATA', message)


if __name__ == '__main__':
    unittest.main()
