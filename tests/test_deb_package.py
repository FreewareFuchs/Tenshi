"""Validate actual DEB contents and reproducibility without root or raw devices."""
import hashlib
import io
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
            self.assertIn('Architecture: all', metadata)
            self.assertIn('Depends: python3 (>= 3.11), python3-tk, util-linux', metadata)
            archive = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(first)])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                for member in tar.getmembers():
                    self.assertEqual((member.uid, member.gid), (0, 0))
                    self.assertFalse(member.issym() or member.islnk())
                    self.assertFalse(member.mode & 0o6022, member.name)
                    self.assertNotIn('__pycache__', member.name)
                self.assertEqual(tar.extractfile('./usr/share/tenshi/main.py').read(),
                                 (ROOT / 'main.py').read_bytes())
                for source in (ROOT / 'recoverydesk').rglob('*.py'):
                    target = './usr/share/tenshi/' + source.relative_to(ROOT).as_posix()
                    self.assertEqual(tar.extractfile(target).read(), source.read_bytes())
                self.assertTrue(tar.extractfile('./usr/share/icons/hicolor/256x256/apps/tenshi.png').read().startswith(b'\x89PNG'))
                launcher = tar.extractfile('./usr/bin/tenshi').read().decode()
                self.assertIn('/usr/bin/python3 -EsB /usr/share/tenshi/main.py "$@"', launcher)
            controls = subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(first)])
            with tarfile.open(fileobj=io.BytesIO(controls)) as tar:
                # No installer hooks may change device permissions or user groups.
                self.assertEqual({m.name for m in tar.getmembers() if m.isfile()},
                                 {'./control', './md5sums'})


if __name__ == '__main__':
    unittest.main()
