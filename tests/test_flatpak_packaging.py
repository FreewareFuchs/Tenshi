"""Packaging boundary: no user data and no stable identity in the test Flatpak."""
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import prepare_flatpak
from recoverydesk.version_info import BuildInfo

ROOT = Path(__file__).resolve().parents[1]


class FlatpakPackagingTests(unittest.TestCase):
    def test_snapshot_excludes_local_data_and_cannot_claim_stable_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'source'
            root.mkdir()
            # Minimal source tree plus hostile/unrelated local files.
            for name in ('main.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
                (root / name).write_text('fixture')
            (root / 'recoverydesk').mkdir()
            (root / 'recoverydesk/module.py').write_text('# module')
            for name in ('session.json', '_build_info.json', 'secret.img'):
                (root / 'recoverydesk' / name).write_text('do not copy')
            (root / 'recoverydesk/__pycache__').mkdir()
            (root / 'recoverydesk/__pycache__/cached.py').write_text('do not copy')
            packaging = root / 'packaging/flatpak'
            packaging.mkdir(parents=True)
            for name in (*prepare_flatpak.PACKAGING, f'{prepare_flatpak.APP_ID}.json'):
                (packaging / name).write_text('fixture')
            stable = BuildInfo(commit='a' * 40, released=True)
            with patch.object(prepare_flatpak, 'collect_build_info', return_value=stable):
                manifest = prepare_flatpak.prepare(Path(temp) / 'context', root)
            snapshot = manifest.parent / 'tenshi-src'
            self.assertEqual(json.loads((snapshot / 'recoverydesk/_build_info.json').read_text()),
                             {'schema': 1, **vars(replace(stable, released=False))})
            self.assertEqual(set(p.name for p in (snapshot / 'recoverydesk').iterdir()),
                             {'module.py', '_build_info.json'})
            self.assertFalse((snapshot / '.git').exists())
            with self.assertRaises(FileExistsError):
                prepare_flatpak.prepare(manifest.parent, root)

    def test_source_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'source'
            root.mkdir()
            (root / 'main.py').symlink_to(ROOT / 'main.py')
            with self.assertRaises(ValueError):
                prepare_flatpak.prepare(Path(temp) / 'context', root)
            self.assertFalse((Path(temp) / 'context').exists())

    def test_install_and_launcher_use_prepared_package(self):
        spec = importlib.util.spec_from_file_location('flatpak_install', ROOT / 'packaging/flatpak/install.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            manifest = prepare_flatpak.prepare(Path(temp) / 'context')
            prefix = Path(temp) / 'app'
            module.install(manifest.parent / 'tenshi-src', prefix)
            for source in (ROOT / 'recoverydesk/assets/sun_valley').rglob('*'):
                if source.is_file():
                    relative = source.relative_to(ROOT)
                    self.assertEqual((manifest.parent / 'tenshi-src' / relative).read_bytes(), source.read_bytes())
                    self.assertEqual((prefix / 'share/tenshi' / relative).read_bytes(), source.read_bytes())
            if os.name == 'posix':
                self.assertEqual((prefix / 'bin/tenshi-flatpak').stat().st_mode & 0o777, 0o755)
            result = subprocess.run([sys.executable, '-EsB', str(prefix / 'share/tenshi/main.py'),
                                     '--version'], check=True, capture_output=True, text=True)
            self.assertIn('+dev', result.stdout)
            self.assertTrue((prefix / 'share/licenses/tenshi/LICENSE').is_file())
            self.assertTrue((prefix / 'share/metainfo' / f'{prepare_flatpak.APP_ID}.metainfo.xml').is_file())
