"""Offline publication checks: no requests to live services or device access."""
import hashlib
from http.client import IncompleteRead
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import URLError

import test_website_release_checks as page_fixtures
from check_public_release import (APT_METADATA, Redirects, build_plan, checked_url,
                                  fetch_digest, main, verify)


class PublicReleaseChecks(unittest.TestCase):
    def setUp(self):
        fixture = self.fixture = page_fixtures.WebsiteReleaseChecks(
            'test_twelve_pages_match_and_all_inputs_remain_byte_identical')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.site = fixture.root, fixture.site
        self.bundle, self.apt = self.root / 'bundle', self.root / 'apt'
        self.bundle.mkdir()
        self.apt.mkdir()
        self.rows = []
        for key in ('installer', 'portable', 'linux'):
            entry = fixture.release['downloads'][key]
            name = entry['url'].rsplit('/', 1)[-1]
            payload = ('package fixture ' + name).encode()
            (self.bundle / name).write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            entry.update(bytes=len(payload), sha256=digest)
            self.rows.append(dict(file=name, bytes=len(payload), sha256=digest))
        fixture.release['downloads']['linux']['sourceCommit'] = 'a' * 40
        self.manifest = dict(schema=1, product='Tenshi', release='stable',
                             version='42.7.19', tag='v42.7.19', commit='a' * 40,
                             artifacts=self.rows, published=False)
        self.save_manifest()
        (self.bundle / 'SHA256SUMS.txt').write_text(
            ''.join(f'{r["sha256"]}  {r["file"]}\n' for r in self.rows), encoding='ascii')
        for path in self.site.rglob('index.html'):
            path.write_text(fixture.page(product=path.parent.name == 'tenshi'), encoding='utf-8')
        self.catalog_path = self.site / 'programme/software.json'
        self.catalog_path.parent.mkdir()
        self.save_catalog()
        for rel in APT_METADATA:
            path = self.apt / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('public APT fixture: ' + rel).encode())
        deb = self.apt / 'pool/main/t/tenshi-recovery' / self.rows[2]['file']
        deb.parent.mkdir(parents=True)
        deb.write_bytes((self.bundle / self.rows[2]['file']).read_bytes())
        self.report = self.root / 'report.json'

    def save_manifest(self):
        (self.bundle / 'release_manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def save_catalog(self):
        self.catalog_path.write_text(json.dumps(self.fixture.catalog), encoding='utf-8')

    def plan(self):
        return build_plan(self.bundle, self.site, self.apt)

    def run_check(self, fetch=None):
        expectations = {r['url']: (r['bytes'], r['sha256']) for r in self.plan()[2]}
        return verify(self.bundle, self.site, self.apt, self.report,
                      fetch=fetch or (lambda url, size, timeout: expectations[url]))

    def test_success_checks_all_references_without_mutating_inputs(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        tag, commit, plan = self.plan()
        self.assertEqual((tag, commit), ('v42.7.19', 'a' * 40))
        self.assertEqual(len(plan), 25)
        result = self.run_check()
        self.assertTrue(result['all_passed'])
        self.assertFalse(result['apt_signature_reverified'])
        self.assertIn('separately signature-verified', result['notice'])
        self.assertEqual(json.loads(self.report.read_text()), result)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_new_checksum_format_is_checked_publicly(self):
        (self.bundle / 'SHA256SUMS.txt').rename(self.bundle / 'SHA256SUMS.sha256')
        entry = self.fixture.release['downloads']['checksums']
        entry['url'] = entry['url'].replace('SHA256SUMS.txt', 'SHA256SUMS.sha256')
        self.save_catalog()
        for path in self.site.rglob('index.html'):
            path.write_text(self.fixture.page(product=path.parent.name == 'tenshi'), encoding='utf-8')
        result = self.run_check()
        self.assertTrue(result['all_passed'])
        row = next(r for r in result['files'] if r['name'] == 'download:checksums')
        self.assertTrue(row['url'].endswith('/SHA256SUMS.sha256'))

    def test_wrong_public_content_and_missing_download_are_recorded_and_checks_continue(self):
        calls = []
        expectations = {r['url']: (r['bytes'], r['sha256']) for r in self.plan()[2]}
        def fetch(url, size, timeout):
            calls.append(url)
            if url.endswith('SHA256SUMS.txt'):
                raise URLError('https://example.invalid/?secret=do-not-log')
            if url.endswith('/ja/tenshi/'):
                return size, '0' * 64
            return expectations[url]
        result = self.run_check(fetch)
        self.assertFalse(result['all_passed'])
        self.assertEqual(len(calls), 25)
        self.assertEqual(sum(not r['verified'] for r in result['files']), 2)
        self.assertNotIn('do-not-log', self.report.read_text())

    def test_wrong_public_size_fails_even_with_expected_digest(self):
        expectations = {r['url']: r['sha256'] for r in self.plan()[2]}
        result = self.run_check(lambda url, size, timeout: (size - 1, expectations[url]))
        self.assertFalse(result['all_passed'])

    def test_incomplete_response_is_reported_as_public_failure(self):
        def fetch(url, size, timeout):
            raise IncompleteRead(b'partial', size)
        result = self.run_check(fetch)
        self.assertFalse(result['all_passed'])
        self.assertEqual(len(result['files']), 25)
        self.assertTrue(all('IncompleteRead' in r['error'] for r in result['files']))

    def test_tampered_local_package_stops_before_network_or_report(self):
        (self.bundle / self.rows[0]['file']).write_bytes(b'tampered')
        with patch('check_public_release.fetch_digest') as fetch:
            with self.assertRaisesRegex(ValueError, 'differs from manifest'):
                verify(self.bundle, self.site, self.apt, self.report)
            fetch.assert_not_called()
        self.assertFalse(self.report.exists())

    def test_catalog_hash_size_commit_and_version_must_match_bundle(self):
        for field, value in [('sha256', 'f' * 64), ('bytes', 999), ('sourceCommit', 'b' * 40)]:
            row = self.fixture.release['downloads']['linux']
            original = row[field]
            row[field] = value
            self.save_catalog()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.plan()
            row[field] = original
        self.save_catalog()
        self.manifest['version'] = '42.7.18'
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'catalog release differ'):
            self.plan()

    def test_missing_or_outdated_local_pages_stop_before_network(self):
        page = self.site / 'ru/tenshi/guide/index.html'
        original = page.read_bytes()
        page.write_text('outdated', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Local website audit failed'):
            self.plan()
        page.write_bytes(original)
        page.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing regular input'):
            self.plan()

    def test_missing_apt_metadata_and_wrong_apt_package_rejected(self):
        metadata = self.apt / 'dists/stable/InRelease'
        original = metadata.read_bytes()
        metadata.unlink()
        with self.assertRaises(ValueError):
            self.plan()
        metadata.write_bytes(original)
        deb = self.apt / 'pool/main/t/tenshi-recovery' / self.rows[2]['file']
        deb.write_bytes(b'old package')
        with self.assertRaisesRegex(ValueError, 'APT package differs'):
            self.plan()

    def test_existing_report_is_preserved_and_no_requests_are_made(self):
        self.report.write_text('previous evidence', encoding='utf-8')
        with patch('check_public_release.fetch_digest') as fetch:
            with self.assertRaises(FileExistsError):
                verify(self.bundle, self.site, self.apt, self.report)
            fetch.assert_not_called()
        self.assertEqual(self.report.read_text(), 'previous evidence')

    def test_report_cannot_be_created_in_reference_directories(self):
        for root in (self.site, self.bundle, self.apt):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'outside'):
                verify(self.bundle, self.site, self.apt, root / 'new-report.json')
            self.assertFalse((root / 'new-report.json').exists())

    def test_timeout_must_be_bounded(self):
        for timeout in (0, -1, 301):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                verify(self.bundle, self.site, self.apt, self.report, timeout=timeout)

    def test_redirects_require_https_and_known_public_hosts(self):
        for url in ('http://freewarefuchs.de/', 'https://evil.invalid/',
                    'https://github.com:444/', 'https://user:password@github.com/',
                    'https://github.com.evil.invalid/', 'file:///etc/passwd'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                checked_url(url)
            with self.assertRaises(ValueError):
                Redirects().redirect_request(None, None, 302, '', {}, url)
        self.assertEqual(checked_url('https://release-assets.githubusercontent.com/a'),
                         'https://release-assets.githubusercontent.com/a')

    def test_streaming_download_rejects_oversized_or_encoded_bodies(self):
        class Response(io.BytesIO):
            status = 200
            url = 'https://freewarefuchs.de/test'
            headers = {}
        with patch('check_public_release.build_opener') as opener:
            opener.return_value.open.return_value = Response(b'too long')
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                fetch_digest(Response.url, 2, 1)
            response = Response(b'body')
            response.headers = {'Content-Encoding': 'gzip'}
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(ValueError, 'encoded'):
                fetch_digest(Response.url, 4, 1)

    def test_cli_exit_codes_distinguish_success_public_failure_and_input_error(self):
        args = ['--bundle', str(self.bundle), '--site', str(self.site),
                '--apt', str(self.apt), '--report', str(self.report)]
        with patch('check_public_release.verify', return_value={'tag': 'v42.7.19',
                   'files': [{'name': 'test', 'verified': True}]}):
            self.assertEqual(main(args), 0)
        with patch('check_public_release.verify', return_value={'files': [
                {'name': 'test', 'verified': False}]}):
            self.assertEqual(main(args), 1)
        with patch('check_public_release.verify', side_effect=ValueError('bad input')):
            self.assertEqual(main(args), 2)


if __name__ == '__main__':
    unittest.main()
