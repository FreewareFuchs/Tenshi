"""Read-only check of twelve static Tenshi pages against a prepared catalog.

This checks release fields, not publication, package contents or editorial copy.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from prepare_website_catalog import _json, _LANGUAGES, _VERSION

_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
         'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.errors = []
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        for parent in self.stack:
            parent['text'] += ' '
        names = [key for key, _ in attrs]
        if len(names) != len(set(names)):
            self.errors.append(f'Duplicate HTML attribute on {tag}')
        node = dict(tag=tag, attrs=dict(attrs), text='', closed=tag in _VOID)
        self.nodes.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                self.stack[i]['closed'] = True
                del self.stack[i:]
                for parent in self.stack:
                    parent['text'] += ' '
                break

    def handle_data(self, data):
        for node in self.stack:
            node['text'] += data


def current_release(catalog):
    if not isinstance(catalog, dict) or type(catalog.get('schemaVersion')) is not int or catalog['schemaVersion'] != 1:
        raise ValueError('Unsupported catalog schema')
    programs = catalog.get('programs')
    if not isinstance(programs, list):
        raise ValueError('Missing program list')
    matches = [p for p in programs if isinstance(p, dict) and p.get('id') == 'tenshi']
    if len(matches) != 1 or not isinstance(matches[0].get('releases'), list):
        raise ValueError('Expected exactly one Tenshi program with releases')
    program = matches[0]
    releases = [r for r in program['releases'] if isinstance(r, dict) and r.get('tag') == program.get('currentTag')]
    if len(releases) != 1:
        raise ValueError('Expected exactly one current release')
    release = releases[0]
    version = release.get('version')
    if (not isinstance(version, str) or not re.fullmatch(_VERSION, version)
            or release.get('tag') != 'v' + version or release.get('prerelease') is not False
            or release.get('label') != version):
        raise ValueError('Expected a stable current release')
    base = 'https://github.com/FreewareFuchs/Tenshi/releases/'
    if release.get('releaseUrl') != base + 'tag/v' + version:
        raise ValueError('Unexpected release URL')
    downloads = release.get('downloads')
    if not isinstance(downloads, dict):
        raise ValueError('Missing downloads')
    for key, suffix in [('installer', f'Tenshi_Setup_{version}_Win64.exe'),
                        ('portable', f'Tenshi_Portable_{version}_Win64.zip')]:
        row = downloads.get(key)
        if not isinstance(row, dict) or row.get('url') != base + f'download/v{version}/' + suffix:
            raise ValueError(f'Unexpected {key} download')
    linux = downloads.get('linux')
    if not isinstance(linux, dict) or not re.fullmatch(re.escape(version) + r'-[1-9][0-9]*', str(linux.get('packageVersion', ''))):
        raise ValueError('Invalid Linux package version')
    deb = f"tenshi-recovery_{linux['packageVersion']}_all.deb"
    if linux.get('url') != 'https://freewarefuchs.de/tenshi/apt/pool/main/t/tenshi-recovery/' + deb:
        raise ValueError('Unexpected Linux download')
    for key in ['installer', 'portable', 'linux']:
        row = downloads[key]
        if (not isinstance(row.get('size'), str) or not row['size'].strip()
                or not re.fullmatch(r'[a-f0-9]{64}', str(row.get('sha256', '')))):
            raise ValueError(f'Missing size or SHA256: {key}')
    if downloads.get('checksums') != {'url': base + f'download/v{version}/SHA256SUMS.txt'}:
        raise ValueError('Unexpected checksums link')
    return release


def check_page(source, release, product):
    page = Page(source)
    errors = list(page.errors)
    downloads = release['downloads']
    fields = dict(version=release['label'], tag=release['tag'],
                  **{key + 'Size': downloads[key]['size'] for key in ['installer', 'portable', 'linux']})
    required = set(fields) if product else {'version'}
    seen = set()
    links = {key: downloads[key]['url'] for key in ['installer', 'portable', 'linux', 'checksums']}
    links['release'] = release['releaseUrl']
    found_links = set()
    structured = []
    linux_texts = []
    for node in page.nodes:
        attrs, text = node['attrs'], ' '.join(node['text'].split())
        field = attrs.get('data-ff')
        if field in fields:
            seen.add(field)
            if text != fields[field] or not node['closed']:
                errors.append(f'data-ff={field}: expected {fields[field]!r}, found {text!r}')
        key = attrs.get('data-ff-link')
        if key in links:
            found_links.add(key)
            if attrs.get('href') != links[key]:
                errors.append(f'data-ff-link={key}: expected {links[key]!r}, found {attrs.get("href")!r}')
        if node['tag'] == 'script' and attrs.get('type') == 'application/ld+json':
            try:
                data = json.loads(node['text'])
                if isinstance(data, dict) and data.get('@type') == 'SoftwareApplication' and data.get('name') == 'Tenshi':
                    structured.append(data)
                if not node['closed']:
                    errors.append('Unclosed JSON-LD script')
            except (ValueError, TypeError):
                errors.append('Invalid JSON-LD')
        if attrs.get('id') == 'linux-install' or ('ff-secondary' in (attrs.get('class') or '').split() and re.search(r'[a-fA-F0-9]{64}', text)):
            linux_texts.append(text)
            if not node['closed']:
                errors.append('Unclosed Linux installation/checksum section')
    for field in sorted(required - seen):
        errors.append(f'Missing data-ff={field}')
    if product:
        for key in sorted(set(links) - found_links):
            errors.append(f'Missing data-ff-link={key}')
        if len(structured) != 1:
            errors.append('Expected exactly one Tenshi SoftwareApplication JSON-LD block')
        for data in structured:
            for key, expected in [('softwareVersion', release['label']), ('downloadUrl', release['releaseUrl'])]:
                if data.get(key) != expected:
                    errors.append(f'JSON-LD {key}: expected {expected!r}, found {data.get(key)!r}')
    if not linux_texts:
        errors.append('Missing Linux installation/checksum section')
    for text in linux_texts:
        linux = downloads['linux']
        hashes = re.findall(r'(?<![a-fA-F0-9])[a-fA-F0-9]{64}(?![a-fA-F0-9])', text)
        if not hashes or any(value != linux['sha256'] for value in hashes):
            errors.append('Linux SHA256 missing or differs from catalog')
        packages = re.findall(r'(?<![\d.])\d+\.\d+\.\d+-\d+(?![\d.])', text)
        if not packages or any(value != linux['packageVersion'] for value in packages):
            errors.append('Linux package version missing or differs from catalog')
    # All explicit Tenshi DEB links on either page must name the current package.
    deb_links = [n['attrs']['href'] for n in page.nodes if 'tenshi-recovery_' in str(n['attrs'].get('href', '')) and str(n['attrs'].get('href', '')).endswith('.deb')]
    if not product and not deb_links:
        errors.append('Missing guide Linux DEB download')
    if any(url != downloads['linux']['url'] for url in deb_links):
        errors.append('Linux DEB link differs from catalog')
    return errors


def audit(site, catalog):
    release = current_release(catalog)
    errors = []
    for lang in sorted(_LANGUAGES):
        base = Path('tenshi') if lang == 'de' else Path(lang) / 'tenshi'
        for product, path in [(True, base / 'index.html'),
                              (False, base / ('anleitung' if lang == 'de' else 'guide') / 'index.html')]:
            target = site / path
            if target.is_symlink() or not target.is_file():
                errors.append(f'{path.as_posix()}: missing regular page')
                continue
            try:
                issues = check_page(target.read_text(encoding='utf-8'), release, product)
            except (UnicodeError, OSError) as exc:
                issues = [f'Cannot read page: {exc}']
            errors.extend(f'{path.as_posix()}: {message}' for message in issues)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = audit(args.site, _json(args.catalog))
    except (ValueError, OSError) as exc:
        print(f'Invalid input: {exc}')
        return 2
    if errors:
        print('\n'.join(errors))
        return 1
    print('All twelve static Tenshi pages match the catalog release fields.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
