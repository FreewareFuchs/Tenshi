"""Compare a public release with verified local bundle, website and APT files.

Read-only HTTPS requests; writes only a new JSON report. APT signatures must
have been verified separately before supplying the local public APT export.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from check_website_release import audit, current_release
from prepare_website_catalog import _json, _LANGUAGES, _verified_rows

SITE = 'https://freewarefuchs.de/'
APT = SITE + 'tenshi/apt/'
HOSTS = {'freewarefuchs.de', 'www.freewarefuchs.de', 'github.com',
         'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
APT_METADATA = ('dists/stable/InRelease', 'dists/stable/Release',
                'dists/stable/Release.gpg',
                'dists/stable/main/binary-amd64/Release',
                'dists/stable/main/binary-amd64/Packages',
                'dists/stable/main/binary-amd64/Packages.gz',
                'tenshi-archive-keyring.gpg')


def checked_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in HOSTS
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError('Unexpected HTTPS destination')
    return url


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def regular(path):
    if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
           for p in (path, *path.parents)):
        raise ValueError(f'Input uses a redirected path: {path}')
    if not path.is_file():
        raise ValueError(f'Missing regular input: {path}')
    return path


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with regular(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def build_plan(bundle, site, apt):
    """Validate all local references before making any network requests."""
    manifest = _json(regular(bundle / 'release_manifest.json'))
    catalog_path = regular(site / 'programme/software.json')
    catalog = _json(catalog_path)
    release = current_release(catalog)
    if (not isinstance(manifest, dict) or type(manifest.get('schema')) is not int
            or manifest['schema'] != 1 or manifest.get('product') != 'Tenshi'
            or manifest.get('release') != 'stable'
            or manifest.get('version') != release['version']
            or manifest.get('tag') != release['tag']
            or not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', str(manifest.get('commit', '')))):
        raise ValueError('Bundle and current stable catalog release differ')
    for row in manifest.get('artifacts', []):
        # _verified_rows performs the filename and payload validation below.
        if isinstance(row, dict) and isinstance(row.get('file'), str):
            regular(bundle / row['file'])
    regular(bundle / 'SHA256SUMS.txt')
    rows = _verified_rows(bundle, manifest)
    downloads = release['downloads']
    if set(downloads) != {'installer', 'portable', 'linux', 'checksums'}:
        raise ValueError('Expected exactly four download references')
    for key in ('installer', 'portable', 'linux'):
        entry = downloads[key]
        name = entry['url'].rsplit('/', 1)[-1]
        row = rows.get(name)
        if not row or (entry.get('bytes'), entry['sha256']) != (row['bytes'], row['sha256']):
            raise ValueError(f'Catalog {key} differs from verified bundle')
    if downloads['linux'].get('sourceCommit') != manifest['commit']:
        raise ValueError('Catalog Linux commit differs from bundle')
    if len(rows) != 3:
        raise ValueError('Expected three package references')
    pages = []
    for lang in sorted(_LANGUAGES):
        base = Path('tenshi') if lang == 'de' else Path(lang) / 'tenshi'
        pages.extend((base / 'index.html',
                      base / ('anleitung' if lang == 'de' else 'guide') / 'index.html'))
    for path in pages:
        regular(site / path)
    errors = audit(site, catalog)
    if errors:
        raise ValueError('Local website audit failed: ' + '; '.join(errors))
    plan = []

    def add(name, url, path):
        size, digest = fingerprint(path)
        plan.append(dict(name=name, url=checked_url(url), bytes=size, sha256=digest))

    add('website:catalog', SITE + 'programme/software.json', catalog_path)
    for path in pages:
        # Check the public directory URLs used by visitors, including redirects.
        add('website:' + path.as_posix(), SITE + path.parent.as_posix() + '/', site / path)
    for key, entry in downloads.items():
        name = entry['url'].rsplit('/', 1)[-1]
        add('download:' + key, entry['url'], bundle / name)
    linux_path = Path('pool/main/t/tenshi-recovery') / downloads['linux']['url'].rsplit('/', 1)[-1]
    size, digest = fingerprint(apt / linux_path)
    if (size, digest) != (downloads['linux']['bytes'], downloads['linux']['sha256']):
        raise ValueError('Local APT package differs from verified bundle')
    for name in APT_METADATA:
        add('apt:' + name, APT + name, apt / name)
    add('apt:' + linux_path.as_posix(), APT + linux_path.as_posix(), apt / linux_path)
    return release['tag'], manifest['commit'], plan


def fetch_digest(url, expected_size, timeout):
    """Stream bounded responses; never retain packages or signed redirect URLs."""
    request = Request(checked_url(url), headers={
        'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity',
        'User-Agent': 'Tenshi-Public-Release-Check/1'})
    digest = hashlib.sha256()
    size = 0
    with build_opener(Redirects()).open(request, timeout=timeout) as response:
        checked_url(response.url)
        if response.status != 200:
            raise ValueError('Expected HTTP 200')
        if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('Unexpected encoded response')
        for block in iter(lambda: response.read(1024 * 1024), b''):
            size += len(block)
            if size > expected_size:
                raise ValueError('Response exceeds expected byte count')
            digest.update(block)
    return size, digest.hexdigest()


def verify(bundle, site, apt, report, *, timeout=30, fetch=None):
    if timeout <= 0 or timeout > 300:
        raise ValueError('Timeout must be between 1 and 300 seconds')
    if report.exists() or report.is_symlink():
        raise FileExistsError(report)
    # A report is not allowed to create or overwrite a reference file.
    for reference in (bundle, site, apt):
        if report.resolve().is_relative_to(reference.resolve()):
            raise ValueError('Report must be outside the reference directories')
    tag, commit, plan = build_plan(bundle, site, apt)
    fetch = fetch or fetch_digest
    # Reserve the report before network access. Failed checks remain visible.
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        result = dict(schema=1, tag=tag, commit=commit,
                      checked_at=datetime.now(timezone.utc).isoformat(),
                      all_passed=False, apt_signature_reverified=False,
                      notice='APT comparison requires a separately signature-verified local export.',
                      files=[])
        for row in plan:
            checked = dict(row, verified=False)
            try:
                size, digest = fetch(row['url'], row['bytes'], timeout)
                checked.update(actual_bytes=size, actual_sha256=digest)
                if (size, digest) != (row['bytes'], row['sha256']):
                    raise ValueError('Public bytes or SHA256 differ from local reference')
                checked['verified'] = True
            except (OSError, ValueError, HTTPException) as exc:
                # Do not include exceptions that may expose expiring redirect queries.
                checked['error'] = type(exc).__name__ + ': public request or content check failed'
            result['files'].append(checked)
        result['all_passed'] = all(row['verified'] for row in result['files'])
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'site', 'apt', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=30)
    args = parser.parse_args(argv)
    try:
        result = verify(args.bundle, args.site, args.apt, args.report, timeout=args.timeout)
    except (OSError, ValueError, TypeError) as exc:
        print(f'Invalid local input: {exc}')
        return 2
    failed = [row['name'] for row in result['files'] if not row['verified']]
    if failed:
        print('Public checks failed: ' + ', '.join(failed))
        return 1
    print(f"{result['tag']}: all {len(result['files'])} public file checks passed.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
