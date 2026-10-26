"""Validate actual DEB contents and reproducibility without root or raw devices."""
from recoverydesk import __version__
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from build_deb import build, DEFAULT_VERSION, ROOT


@unittest.skipUnless(shutil.which('dpkg-deb'), 'Debian package tools required')
class DebPackageTests(unittest.TestCase):
    def test_release_package_is_reproducible_and_has_complete_readonly_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = build(Path(tmp) / 'first')
            second = build(Path(tmp) / 'second')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            digest = hashlib.sha256(first.read_bytes()).hexdigest()
            self.assertEqual(first.with_suffix('.deb.sha256').read_text(),
                             f'{digest}  {first.name}\n')
            metadata = subprocess.check_output(['dpkg-deb', '-f', str(first)], text=True)
            self.assertIn(f'Version: {DEFAULT_VERSION}', metadata)
            self.assertNotIn('~', first.name)
            subprocess.run(['dpkg', '--compare-versions', DEFAULT_VERSION, 'gt',
                            f'{__version__}~beta.6-1'], check=True)
            subprocess.run(['dpkg', '--compare-versions', DEFAULT_VERSION, 'gt',
                            '3.0.2-2'], check=True)
            self.assertIn('Package: tenshi-recovery\n', metadata)
            for field in ('Conflicts:', 'Replaces:', 'Provides:', 'Breaks:'):
                self.assertNotIn(field, metadata)
            self.assertTrue(first.name.startswith('tenshi-recovery_'))
            self.assertIn('Architecture: all', metadata)
            self.assertIn('Depends: python3 (>= 3.11), python3-tk, util-linux', metadata)
            archive = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(first)])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                metadata = json.load(tar.extractfile('./usr/share/tenshi-recovery/recoverydesk/_build_info.json'))
                self.assertEqual(metadata['schema'], 1)
                self.assertEqual(metadata['version'], f'{__version__}')
                self.assertEqual(len(metadata['commit']), 40)
                for member in tar.getmembers():
                    self.assertEqual((member.uid, member.gid), (0, 0))
                    self.assertFalse(member.issym() or member.islnk())
                    self.assertFalse(member.mode & 0o6022, member.name)
                    self.assertNotIn('__pycache__', member.name)
                self.assertEqual(tar.extractfile('./usr/share/tenshi-recovery/main.py').read(),
                                 (ROOT / 'main.py').read_bytes())
                for source in (ROOT / 'recoverydesk').rglob('*.py'):
                    target = './usr/share/tenshi-recovery/' + source.relative_to(ROOT).as_posix()
                    self.assertEqual(tar.extractfile(target).read(), source.read_bytes())
                self.assertTrue(tar.extractfile('./usr/share/icons/hicolor/256x256/apps/tenshi-recovery.png').read().startswith(b'\x89PNG'))
                self.assertNotIn('./usr/bin/tenshi', tar.getnames())
                launcher = tar.extractfile('./usr/bin/tenshi-recovery').read().decode()
                self.assertIn('/usr/bin/python3 -EsB /usr/share/tenshi-recovery/main.py "$@"', launcher)
            controls = subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(first)])
            with tarfile.open(fileobj=io.BytesIO(controls)) as tar:
                # No installer hooks may change device permissions or user groups.
                self.assertEqual({m.name for m in tar.getmembers() if m.isfile()},
                                 {'./control', './md5sums'})

    def test_explicit_stable_rejects_beta_package_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Release identity'):
                build(Path(tmp), f'{__version__}~beta.6-1', 'stable')
            with self.assertRaisesRegex(ValueError, 'Release identity'):
                build(Path(tmp), f'{__version__}-1', 'beta.6')


if __name__ == '__main__':
    unittest.main()
