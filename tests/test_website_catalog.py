"""Offline catalog preparation with disposable artifacts; no publication."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from prepare_website_catalog import prepare, update_catalog


class WebsiteCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        self.rows = []
        for name in ['Tenshi_Setup_42.7.19_Win64.exe', 'Tenshi_Portable_42.7.19_Win64.zip',
                     'tenshi-recovery_42.7.19-2_all.deb']:
            payload = ('fixture: ' + name).encode()
            (self.bundle / name).write_bytes(payload)
            self.rows.append(dict(file=name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
        self.manifest = dict(schema=1, product='Tenshi', version='42.7.19', release='stable',
                             tag='v42.7.19', commit='a' * 40, published=False, artifacts=self.rows)
        self.save_manifest()
        (self.bundle / 'SHA256SUMS.txt').write_text(
            ''.join(f'{r["sha256"]}  {r["file"]}\n' for r in self.rows), encoding='ascii')
        self.old = dict(tag='v42.7.18', version='42.7.18', changes={'de': ['historisch']}, extra=True)
        self.catalog = dict(schemaVersion=1, custom='preserve', programs=[
            dict(id='other', currentTag='unrelated'),
            dict(id='tenshi', name='Tenshi', currentTag='v42.7.18', status='stable',
                 releases=[self.old], summary={'de': 'unverändert'})])
        self.notes = {lang: ['Test release'] for lang in ['de', 'en', 'es', 'zh', 'ru', 'ja']}
        self.catalog_path = self.root / 'software.json'
        self.notes_path = self.root / 'notes.json'
        self.catalog_path.write_text(json.dumps(self.catalog), encoding='utf-8')
        self.notes_path.write_text(json.dumps(self.notes), encoding='utf-8')
        self.output = self.root / 'software-new.json'

    def save_manifest(self):
        (self.bundle / 'release_manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def generate(self):
        return update_catalog(self.bundle, self.catalog, self.notes, '2026-10-26')

    def test_verified_download_fields_and_history_preserved_without_input_mutation(self):
        before = copy.deepcopy(self.catalog)
        result = self.generate()
        self.assertEqual(self.catalog, before)
        self.assertEqual(result['programs'][0], before['programs'][0])
        program = result['programs'][1]
        self.assertEqual(program['currentTag'], 'v42.7.19')
        self.assertEqual(program['releases'][1:], [self.old])
        entry = program['releases'][0]
        self.assertEqual(entry['changes'], self.notes)
        linux = entry['downloads']['linux']
        self.assertEqual(linux['packageVersion'], '42.7.19-2')
        self.assertEqual(linux['sourceCommit'], 'a' * 40)
        self.assertEqual(linux['url'], 'https://freewarefuchs.de/tenshi/apt/pool/main/t/tenshi-recovery/tenshi-recovery_42.7.19-2_all.deb')
        for key, row in zip(['installer', 'portable', 'linux'], self.rows):
            self.assertEqual(entry['downloads'][key]['sha256'], row['sha256'])
            self.assertEqual(entry['downloads'][key]['bytes'], row['bytes'])
        self.assertIn('/v42.7.19/SHA256SUMS.txt', entry['downloads']['checksums']['url'])
        self.catalog = result
        self.assertEqual(self.generate(), result)  # deterministic repeat, no duplicate
        self.notes['de'] = ['changed']
        with self.assertRaisesRegex(ValueError, 'must not be replaced'):
            self.generate()

    def test_tampered_package_and_checksum_file_stop_before_output_creation(self):
        for name in [self.rows[0]['file'], 'SHA256SUMS.txt']:
            path = self.bundle / name
            original = path.read_bytes()
            path.write_bytes(b'changed')
            with self.subTest(name=name), self.assertRaises(ValueError):
                prepare(self.bundle, self.catalog_path, self.notes_path, '2026-10-26', self.output)
            self.assertFalse(self.output.exists())
            path.write_bytes(original)

    def test_manifest_rejects_beta_wrong_tag_duplicate_or_unsafe_artifacts(self):
        cases = [('release', 'beta.1'), ('tag', 'v42.7.20'), ('schema', True),
                 ('commit', 'short'), ('artifacts', [self.rows[0]] * 3),
                 ('artifacts', [{**self.rows[0], 'file': '../escape'}, *self.rows[1:]]),
                 ('artifacts', [{**self.rows[0], 'bytes': True}, *self.rows[1:]])]
        for field, value in cases:
            with self.subTest(field=field):
                original = self.manifest[field]
                self.manifest[field] = value
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.generate()
                self.manifest[field] = original
        self.save_manifest()

    def test_invalid_notes_dates_catalogs_and_downgrades_rejected(self):
        for notes in [{}, {**self.notes, 'fr': ['extra']}, {**self.notes, 'ja': [' ']}]:
            with self.assertRaises(ValueError):
                update_catalog(self.bundle, self.catalog, notes, '2026-10-26')
        for value in ['2026-02-30', '20261026']:
            with self.assertRaises(ValueError):
                update_catalog(self.bundle, self.catalog, self.notes, value)
        self.catalog['programs'][1]['releases'][0]['version'] = '43.0.0'
        with self.assertRaisesRegex(ValueError, 'newer'):
            self.generate()
        self.catalog['programs'].append(copy.deepcopy(self.catalog['programs'][1]))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.generate()

    def test_duplicate_json_keys_are_not_silently_accepted(self):
        self.notes_path.write_text('{"de": [], "de": []}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            prepare(self.bundle, self.catalog_path, self.notes_path, '2026-10-26', self.output)
        self.assertFalse(self.output.exists())

    def test_cli_creates_only_new_output_and_never_overwrites_inputs(self):
        script = Path(__file__).resolve().parents[1] / 'prepare_website_catalog.py'
        args = [sys.executable, str(script), '--bundle', str(self.bundle),
                '--catalog', str(self.catalog_path), '--notes', str(self.notes_path),
                '--date', '2026-10-26', '--output', str(self.output)]
        before = self.catalog_path.read_bytes()
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = self.output.read_bytes()
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), expected)
        self.assertEqual(self.catalog_path.read_bytes(), before)
