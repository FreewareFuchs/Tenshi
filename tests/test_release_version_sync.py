"""A future version propagates to all packaging formats without manual edits."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import sync_release_version as syncer


class VersionSyncTests(unittest.TestCase):
    def fixture(self, root):
        for name in syncer.SLOTS:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((syncer.ROOT/name).read_bytes())
        p=root/'recoverydesk/__init__.py';p.parent.mkdir(exist_ok=True)
        p.write_text('__version__ = "42.7.19"\n',encoding='utf8')

    def snapshots(self, root):
        return {name:(root/name).read_bytes() for name in syncer.SLOTS}

    def test_actual_repository_is_consistent(self):
        self.assertEqual(syncer.sync(),[])

    def test_future_version_updates_windows_resources_installer_and_ci(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            original=self.snapshots(root)
            self.assertEqual(set(syncer.sync(root)),set(syncer.SLOTS))
            self.assertEqual(self.snapshots(root),original,'Check mode must not modify files')
            syncer.sync(root,write=True)
            self.assertEqual(syncer.sync(root),[])
            info=(root/'build/version_info.txt').read_text()
            self.assertIn('filevers=(42, 7, 19, 0)',info)
            self.assertIn('prodvers=(42, 7, 19, 0)',info)
            self.assertIn("'FileVersion', '42.7.19.0'",info)
            installer=(root/'installer/Tenshi.iss').read_text()
            self.assertIn('#define AppVersion "42.7.19"',installer)
            self.assertIn('OutputBaseFilename=Tenshi_Setup_42.7.19',installer)
            windows=(root/'.github/workflows/windows-check.yml').read_text()
            for text in ['Tenshi-42.7.19-Windows-release','Tenshi_Portable_42.7.19_Win64.zip',
                         'Tenshi_Setup_42.7.19.exe',"$v.FileVersion -ne '42.7.19.0'"]:
                self.assertIn(text,windows)
            self.assertIn('Tenshi-42.7.19-Linux-DEB',
                          (root/'.github/workflows/linux-check.yml').read_text())
            self.assertEqual((root/'recoverydesk/__init__.py').read_text(),'__version__ = "42.7.19"\n')

    def test_newlines_and_unrelated_dependency_versions_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            p=root/'build_windows.bat'
            raw=p.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
            p.write_bytes(raw+b'REM dependency example 24.0.0\r\n')
            syncer.sync(root,write=True)
            data=p.read_bytes()
            self.assertNotIn(b'\n',data.replace(b'\r\n',b''))
            self.assertIn(b'dependency example 24.0.0',data)

    def test_invalid_source_or_missing_slot_never_partially_writes(self):
        for text in ['__version__ = "3.0.03"','__version__ = "65536.0.0"',
                     '__version__ = "1.2.3;command"','__version__ = str(123)',
                     '__version__ = "1.2.3"\n__version__ = "4.5.6"']:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.fixture(root)
                (root/'recoverydesk/__init__.py').write_text(text)
                before=self.snapshots(root)
                with self.assertRaises(ValueError):syncer.sync(root,write=True)
                self.assertEqual(self.snapshots(root),before)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            (root/'installer/Tenshi.iss').write_text('missing version fields')
            before=self.snapshots(root)
            with self.assertRaises(ValueError):syncer.sync(root,write=True)
            self.assertEqual(self.snapshots(root),before)

    def test_cli_check_rejects_stale_files_then_write_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            script=root/'sync_release_version.py'
            shutil.copyfile(syncer.ROOT/'sync_release_version.py',script)
            def run(option):
                return subprocess.run([sys.executable,str(script),option],cwd=root,
                                      capture_output=True,text=True)
            before=self.snapshots(root)
            self.assertEqual(run('--check').returncode,1)
            self.assertEqual(self.snapshots(root),before)
            self.assertEqual(run('--write').returncode,0)
            after=self.snapshots(root)
            self.assertEqual(run('--write').returncode,0)
            self.assertEqual(self.snapshots(root),after)
            self.assertEqual(run('--check').returncode,0)


if __name__=='__main__':unittest.main()
