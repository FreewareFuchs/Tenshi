"""Prepare a local website catalog from a verified stable release bundle.

No network access, uploads, publication or HTML changes. Existing release
entries are immutable; only a newer stable release may become current.
"""
from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re

_LANGUAGES = {'de', 'en', 'es', 'zh', 'ru', 'ja'}
_GITHUB = 'https://github.com/FreewareFuchs/Tenshi/releases/'
_APT = 'https://freewarefuchs.de/tenshi/apt/pool/main/t/tenshi-recovery/'
_VERSION = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'


def _json(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Expected a regular input file: {path.name}')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def _verified_rows(bundle: Path, manifest: dict) -> dict:
    rows = manifest.get('artifacts')
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError('Expected exactly three release artifacts')
    verified = {}
    sums = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid artifact record')
        name, size, digest = row.get('file'), row.get('bytes'), row.get('sha256')
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name)
                or name in verified or type(size) is not int or size <= 0
                or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
            raise ValueError('Invalid artifact filename, size or SHA256')
        path = bundle / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing regular artifact: {name}')
        sha = hashlib.sha256()
        count = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(block)
                count += len(block)
        if count != size or sha.hexdigest() != digest:
            raise ValueError(f'Artifact differs from manifest: {name}')
        verified[name] = row
        sums.append(f'{digest}  {name}\n')
    checksum_file = bundle / 'SHA256SUMS.txt'
    if (checksum_file.is_symlink() or not checksum_file.is_file()
            or checksum_file.read_bytes() != ''.join(sums).encode('ascii')):
        raise ValueError('SHA256SUMS.txt differs from manifest')
    return verified


def update_catalog(bundle: Path, catalog: dict, notes: dict, release_date: str) -> dict:
    manifest = _json(bundle / 'release_manifest.json')
    if not isinstance(manifest, dict):
        raise ValueError('Invalid release manifest')
    version, tag = manifest.get('version'), manifest.get('tag')
    if (type(manifest.get('schema')) is not int or manifest['schema'] != 1
            or manifest.get('product') != 'Tenshi' or manifest.get('release') != 'stable'
            or not isinstance(version, str) or not re.fullmatch(_VERSION, version)
            or tag != 'v' + version
            or not isinstance(manifest.get('commit'), str)
            or not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', manifest['commit'])):
        raise ValueError('Expected a stable Tenshi release manifest with full commit')
    if date.fromisoformat(release_date).isoformat() != release_date:
        raise ValueError('Release date must use YYYY-MM-DD')
    if (not isinstance(notes, dict) or set(notes) != _LANGUAGES
            or any(not isinstance(items, list) or not items
                   or any(not isinstance(text, str) or not text.strip() for text in items)
                   for items in notes.values())):
        raise ValueError('Release notes must contain nonempty lists for all six languages')
    rows = _verified_rows(bundle, manifest)
    installer = f'Tenshi_Setup_{version}_Win64.exe'
    portable = f'Tenshi_Portable_{version}_Win64.zip'
    debs = [name for name in rows if re.fullmatch(
        rf'tenshi-recovery_{re.escape(version)}-[1-9][0-9]*_all\.deb', name)]
    if installer not in rows or portable not in rows or len(debs) != 1:
        raise ValueError('Artifact names do not match the stable release')
    deb = debs[0]
    download = _GITHUB + 'download/' + tag + '/'
    downloads = {'checksums': {'url': download + 'SHA256SUMS.txt'}}
    for key, name in [('linux', deb), ('portable', portable), ('installer', installer)]:
        row = rows[name]
        downloads[key] = dict(url=(_APT if key == 'linux' else download) + name,
                              bytes=row['bytes'], size=f"{row['bytes'] / 1_000_000:.2f} MB",
                              sha256=row['sha256'])
    downloads['linux'].update(packageVersion=deb.removeprefix('tenshi-recovery_').removesuffix('_all.deb'),
                              sourceCommit=manifest['commit'])
    entry = dict(tag=tag, version=version, label=version, date=release_date,
                 prerelease=False, releaseUrl=_GITHUB + 'tag/' + tag,
                 downloads=downloads, changes=copy.deepcopy(notes))
    if (not isinstance(catalog, dict) or type(catalog.get('schemaVersion')) is not int
            or catalog['schemaVersion'] != 1 or not isinstance(catalog.get('programs'), list)):
        raise ValueError('Unsupported website catalog')
    result = copy.deepcopy(catalog)
    programs = [p for p in result['programs'] if isinstance(p, dict) and p.get('id') == 'tenshi']
    if len(programs) != 1 or not isinstance(programs[0].get('releases'), list):
        raise ValueError('Expected exactly one Tenshi catalog entry with release history')
    program = programs[0]
    history = program['releases']
    if any(not isinstance(r, dict) or not isinstance(r.get('tag'), str) for r in history):
        raise ValueError('Invalid release history')
    tags = [r['tag'] for r in history]
    if len(tags) != len(set(tags)):
        raise ValueError('Duplicate release tags')
    if tag in tags:
        if history[tags.index(tag)] != entry or program.get('currentTag') != tag:
            raise ValueError('Existing release entries must not be replaced or promoted again')
        return result
    current = [r for r in history if r['tag'] == program.get('currentTag')]
    if len(current) != 1 or not re.fullmatch(_VERSION, str(current[0].get('version', ''))):
        raise ValueError('Invalid current release')
    numbers = lambda v: tuple(int(n) for n in v.split('.'))
    if numbers(version) <= numbers(current[0]['version']):
        raise ValueError('Only a newer stable version may become current')
    history.insert(0, entry)
    program['currentTag'] = tag
    program['status'] = 'stable'
    return result


def prepare(bundle: Path, catalog_path: Path, notes_path: Path,
            release_date: str, output: Path) -> Path:
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    catalog = update_catalog(bundle, _json(catalog_path), _json(notes_path), release_date)
    payload = json.dumps(catalog, ensure_ascii=False, indent=2) + '\n'
    # Exclusive create only after all inputs and package contents were checked.
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(payload)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--notes', type=Path, required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.bundle, args.catalog, args.notes, args.date, args.output))
