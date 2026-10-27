"""Static release checks use disposable pages, never a live website."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from check_website_release import audit, check_page, current_release


class WebsiteReleaseChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        version = '42.7.19'
        base = 'https://github.com/FreewareFuchs/Tenshi/releases/'
        self.release = dict(version=version, label=version, tag='v' + version,
                            prerelease=False, releaseUrl=base + 'tag/v' + version)
        downloads = self.release['downloads'] = {}
        for key, name in [('installer', f'Tenshi_Setup_{version}_Win64.exe'),
                          ('portable', f'Tenshi_Portable_{version}_Win64.zip')]:
            downloads[key] = dict(url=base + f'download/v{version}/' + name,
                                  size='1.23 MB', sha256='a' * 64)
        downloads['linux'] = dict(url='https://freewarefuchs.de/tenshi/apt/pool/main/t/tenshi-recovery/'
                                 f'tenshi-recovery_{version}-2_all.deb',
                                 size='0.74 MB', sha256='b' * 64, packageVersion=version + '-2')
        downloads['checksums'] = dict(url=base + f'download/v{version}/SHA256SUMS.txt')
        self.catalog = dict(schemaVersion=1, programs=[dict(id='tenshi', currentTag='v' + version,
                                                         releases=[self.release])])
        self.catalog_path = self.root / 'software.json'
        self.catalog_path.write_text(json.dumps(self.catalog), encoding='utf-8')
        self.site = self.root / 'site'
        for lang in ['de', 'en', 'es', 'ru', 'zh', 'ja']:
            prefix = Path('tenshi') if lang == 'de' else Path(lang) / 'tenshi'
            for product, rel in [(True, prefix / 'index.html'),
                                 (False, prefix / ('anleitung' if lang == 'de' else 'guide') / 'index.html')]:
                path = self.site / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(self.page(product), encoding='utf-8')

    def page(self, product=True):
        r, d = self.release, self.release['downloads']
        fields = dict(version=r['label'])
        if product:
            fields.update(tag=r['tag'], **{key + 'Size': d[key]['size'] for key in ['installer', 'portable', 'linux']})
        text = ''.join(f'<span data-ff="{key}"><b>{value}</b></span>' for key, value in fields.items())
        if product:
            text += ''.join(f'<a data-ff-link="{key}" href="{d[key]["url"]}">download</a>'
                            for key in ['installer', 'portable', 'linux', 'checksums'])
            text += f'<a data-ff-link="release" href="{r["releaseUrl"]}">release</a>'
            structured = dict(**{'@type': 'SoftwareApplication'}, name='Tenshi',
                              softwareVersion=r['label'], downloadUrl=r['releaseUrl'])
            text += '<script type="application/ld+json">' + json.dumps(structured) + '</script>'
            text += f'<p class="ff-secondary">Linux {d["linux"]["packageVersion"]} SHA256: {d["linux"]["sha256"]}</p>'
        else:
            text += f'<section id="linux-install"><p>{d["linux"]["packageVersion"]}</p>'
            text += f'<a href="{d["linux"]["url"]}">DEB</a><code>{d["linux"]["sha256"]}</code></section>'
        return '<html><head></head><body>' + text + '<p>Historical release 3.0.0</p></body></html>'

    def test_twelve_pages_match_and_all_inputs_remain_byte_identical(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        catalog_before = copy.deepcopy(self.catalog)
        self.assertEqual(audit(self.site, self.catalog), [])
        self.assertEqual(self.catalog, catalog_before)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_every_version_size_and_download_field_is_checked(self):
        source = self.page()
        for field in ['version', 'tag', 'installerSize', 'portableSize', 'linuxSize']:
            with self.subTest(field=field):
                altered = source.replace(f'data-ff="{field}"><b>', f'data-ff="{field}"><b>wrong ')
                self.assertTrue(any(f'data-ff={field}' in e for e in check_page(altered, self.release, True)))
        for key in ['installer', 'portable', 'linux', 'checksums']:
            with self.subTest(download=key):
                altered = source.replace(self.release['downloads'][key]['url'], 'https://example.invalid/wrong')
                self.assertTrue(check_page(altered, self.release, True))
        self.assertTrue(check_page(source.replace(self.release['releaseUrl'], 'https://example.invalid/release'), self.release, True))

    def test_missing_fields_links_and_structured_data_are_rejected(self):
        source = self.page()
        for marker in ['data-ff="version"', 'data-ff="tag"', 'data-ff="linuxSize"',
                       'data-ff-link="portable"', 'data-ff-link="checksums"']:
            with self.subTest(marker=marker):
                self.assertTrue(check_page(source.replace(marker, 'data-ignored="x"'), self.release, True))
        self.assertTrue(check_page(source.replace('SoftwareApplication', 'Organization'), self.release, True))
        self.assertTrue(check_page(source.replace('"softwareVersion": "42.7.19"', '"softwareVersion": "1.0.0"'), self.release, True))
        self.assertTrue(check_page(source.replace('"name": "Tenshi"', 'invalid json'), self.release, True))
        self.assertTrue(check_page(source + source, self.release, True))

    def test_missing_or_different_linux_package_hash_and_guide_links_rejected(self):
        for product in [True, False]:
            source = self.page(product)
            for old, new in [('b' * 64, 'c' * 64), ('b' * 64, ''), ('42.7.19-2', '42.7.19-1')]:
                with self.subTest(product=product, change=old):
                    self.assertTrue(check_page(source.replace(old, new), self.release, product))
        guide = self.page(False)
        self.assertTrue(check_page(guide.replace(self.release['downloads']['linux']['url'], '/missing.deb'), self.release, False))
        self.assertTrue(check_page(guide.replace('id="linux-install"', 'id="removed"'), self.release, False))

    def test_duplicate_attributes_and_unclosed_fields_do_not_pass(self):
        source = self.page()
        altered = source.replace('data-ff="version"', 'data-ff="version" data-ff="version"', 1)
        self.assertTrue(any('Duplicate HTML attribute' in e for e in check_page(altered, self.release, True)))
        self.assertTrue(check_page(source.replace('</span>', '', 1), self.release, True))

    def test_all_repeated_values_checked_even_when_one_is_correct(self):
        source = self.page() + '<span data-ff="version">1.0.0</span>'
        self.assertTrue(check_page(source, self.release, True))

    def test_missing_files_and_invalid_encoding_identify_the_page(self):
        path = self.site / 'ja/tenshi/guide/index.html'
        path.unlink()
        self.assertEqual(len(audit(self.site, self.catalog)), 1)
        self.assertIn('ja/tenshi/guide/index.html', audit(self.site, self.catalog)[0])
        path.write_bytes(b'\xff\xfe')
        self.assertIn('Cannot read page', audit(self.site, self.catalog)[0])

    def test_invalid_catalogs_fail_closed(self):
        cases = [None, {}, dict(schemaVersion=True, programs=[])]
        duplicate = copy.deepcopy(self.catalog)
        duplicate['programs'].append(copy.deepcopy(duplicate['programs'][0]))
        cases.append(duplicate)
        for key, value in [('prerelease', True), ('tag', 'v1.0.0'), ('downloads', {}), ('version', None)]:
            altered = copy.deepcopy(self.catalog)
            altered['programs'][0]['releases'][0][key] = value
            cases.append(altered)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                current_release(value)

    def test_cli_exit_codes_success_mismatch_invalid_catalog(self):
        script = Path(__file__).resolve().parents[1] / 'check_website_release.py'
        args = [sys.executable, str(script), '--site', str(self.site), '--catalog', str(self.catalog_path)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.site / 'en/tenshi/index.html').unlink()
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('en/tenshi/index.html', result.stdout)
        self.catalog_path.write_text('{"schemaVersion": 1, "schemaVersion": 1}', encoding='utf-8')
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Duplicate JSON key', result.stdout)
