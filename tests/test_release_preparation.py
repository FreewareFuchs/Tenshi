"""Release assembly uses disposable packages, never user disks or publishing APIs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recoverydesk import __version__
from release_tools import create_portable
from prepare_release import prepare


@unittest.skipUnless(shutil.which('dpkg-deb'), 'Linux package tools required')
class ReleasePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        self.output = self.root / 'release'
        self.commit = 'a' * 40
        self.identity = dict(schema=1, version=__version__, release='beta.99',
                             commit=self.commit, dirty=False, released=True)
        (self.inputs / 'windows-build-info.json').write_text(json.dumps(self.identity), encoding='utf-8')
        self.exe = self.inputs / 'Tenshi.exe'
        self.exe.write_bytes(b'MZ' + b'x' * 4096)
        (self.inputs / f'Tenshi_Setup_{__version__}.exe').write_bytes(b'MZ' + b'y' * 4096)
        create_portable(self.exe, self.inputs / f'Tenshi_Portable_{__version__}_Win64.zip')
        self.make_deb()

    def make_deb(self, identity=None, release='beta.99'):
        suffix = '' if release == 'stable' else '~' + release
        version = f'{__version__}{suffix}-1'
        stage = self.root / 'stage'
        (stage / 'DEBIAN').mkdir(parents=True, exist_ok=True)
        (stage / 'DEBIAN/control').write_text(
            f'Package: tenshi\nVersion: {version}\nArchitecture: all\n'
            'Maintainer: Test <test@example.com>\nDescription: test\n', encoding='utf-8')
        path = stage / 'usr/share/tenshi/recoverydesk/_build_info.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(identity or self.identity), encoding='utf-8')
        subprocess.run(['dpkg-deb', '--build', str(stage),
                        str(self.inputs / f'tenshi_{version.replace("~", ".")}_all.deb')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def run_prepare(self):
        return prepare(self.inputs, self.output, 'beta.99', self.commit)

    def test_three_packages_and_checksums_no_raw_executable(self):
        self.run_prepare()
        manifest = json.loads((self.output / 'release_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['commit'], self.commit)
        self.assertFalse(manifest['published'])
        self.assertEqual(len(manifest['artifacts']), 3)
        for row in manifest['artifacts']:
            self.assertEqual(hashlib.sha256((self.output / row['file']).read_bytes()).hexdigest(), row['sha256'])
        self.assertFalse((self.output / 'Tenshi.exe').exists())
        self.assertIn('[Windows Installer]', (self.output / 'RELEASE_NOTES.md').read_text(encoding='utf-8'))
        with self.assertRaises(FileExistsError):
            self.run_prepare()

    def test_mixed_commit_or_dev_metadata_rejected_without_output(self):
        for field, value in [('commit', 'b' * 40), ('dirty', True), ('released', False), ('release', 'beta.98')]:
            with self.subTest(field=field):
                data = {**self.identity, field: value}
                (self.inputs / 'windows-build-info.json').write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'identity'):
                    self.run_prepare()
                self.assertFalse(self.output.exists())

    def test_embedded_deb_identity_must_match(self):
        self.make_deb({**self.identity, 'commit': 'b' * 40})
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_duplicate_missing_and_changed_artifacts_rejected(self):
        extra = self.inputs / 'other'
        extra.mkdir()
        shutil.copyfile(self.exe, extra / 'Tenshi.exe')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.run_prepare()
        (extra / 'Tenshi.exe').unlink()
        self.exe.write_bytes(b'MZ' + b'z' * 4096)
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.run_prepare()
        self.exe.unlink()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_stable_bundle_names_identity_and_deb_version(self):
        self.identity['release'] = 'stable'
        (self.inputs / 'windows-build-info.json').write_text(json.dumps(self.identity))
        self.make_deb(release='stable')
        prepare(self.inputs, self.output, 'stable', self.commit)
        manifest = json.loads((self.output / 'release_manifest.json').read_text())
        self.assertEqual(manifest['tag'], 'v3.0.2')
        self.assertEqual({a['file'] for a in manifest['artifacts']}, {
            'Tenshi_Setup_3.0.2_Win64.exe', 'Tenshi_Portable_3.0.2_Win64.zip',
            'tenshi_3.0.2-1_all.deb'})
        self.assertIn('Stabile Version.', (self.output / 'RELEASE_NOTES.md').read_text())
        for row in manifest['artifacts']:
            self.assertEqual(hashlib.sha256((self.output / row['file']).read_bytes()).hexdigest(), row['sha256'])

    def test_stable_rejects_beta_build_identity(self):
        with self.assertRaisesRegex(ValueError, 'exactly one|identity'):
            prepare(self.inputs, self.output, 'stable', self.commit)
        self.assertFalse(self.output.exists())

    def test_invalid_release_input(self):
        with self.assertRaisesRegex(ValueError, 'beta.N'):
            prepare(self.inputs, self.output, 'beta.0; command', self.commit)
