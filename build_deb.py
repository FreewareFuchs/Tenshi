#!/usr/bin/env python3
"""Build the native, architecture-independent Tenshi DEB without root or pip."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DEFAULT_VERSION = '3.0.2~beta.3-1'


def build(output: Path, version: str = DEFAULT_VERSION) -> Path:
    app_version = re.search(r'__version__ = "([^"]+)"',
                            (ROOT / 'recoverydesk/__init__.py').read_text()).group(1)
    if not re.fullmatch(re.escape(app_version) + r'(?:~[a-zA-Z0-9.+]+)?-[1-9][0-9]*', version):
        raise ValueError('Package version must match the application version and include a Debian revision.')
    if not shutil.which('dpkg-deb'):
        raise RuntimeError('dpkg-deb is required (Debian/Ubuntu/Linux Mint: dpkg).')
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH') or subprocess.check_output(
        ['git', '-C', str(ROOT), 'log', '-1', '--format=%ct'], text=True).strip())
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # GitHub replaces '~' in asset names; use its safe spelling from the start.
    destination = output / f'tenshi_{version.replace("~", ".")}_all.deb'
    if destination.exists():
        raise FileExistsError(destination)
    with tempfile.TemporaryDirectory(prefix='tenshi-deb-') as temporary:
        stage = Path(temporary) / 'package'

        def copy(source: Path, target: str, mode: int = 0o644) -> None:
            path = stage / target
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
            path.chmod(mode)

        copy(ROOT / 'main.py', 'usr/share/tenshi/main.py')
        for source in sorted((ROOT / 'recoverydesk').rglob('*')):
            if source.is_file() and '__pycache__' not in source.parts and source.suffix in ('.py', '.png', '.ico'):
                copy(source, 'usr/share/tenshi/' + source.relative_to(ROOT).as_posix())
        copy(ROOT / 'packaging/linux/tenshi', 'usr/bin/tenshi', 0o755)
        copy(ROOT / 'packaging/linux/de.freewarefuchs.Tenshi.desktop',
             'usr/share/applications/de.freewarefuchs.Tenshi.desktop')
        copy(ROOT / 'recoverydesk/assets/tenshi_icon.png',
             'usr/share/icons/hicolor/256x256/apps/tenshi.png')
        for name in ('README.md', 'THIRD_PARTY_NOTICES.md', 'RELEASE_NOTES_LINUX_BETA.md'):
            copy(ROOT / name, f'usr/share/doc/tenshi/{name}')
        copy(ROOT / 'LICENSE', 'usr/share/doc/tenshi/copyright')
        changelog = stage / 'usr/share/doc/tenshi/changelog.gz'
        changelog.write_bytes(gzip.compress((ROOT / 'CHANGELOG.md').read_bytes(), mtime=0))
        installed_size = sum((p.stat().st_size + 1023) // 1024 for p in stage.rglob('*') if p.is_file())
        control = stage / 'DEBIAN'
        control.mkdir()
        (control / 'control').write_text(
            f'Package: tenshi\nVersion: {version}\nSection: utils\nPriority: optional\n'
            'Architecture: all\nMaintainer: FreewareFuchs <344442684+FreewareFuchs@users.noreply.github.com>\n'
            f'Installed-Size: {installed_size}\n'
            'Depends: python3 (>= 3.11), python3-tk, util-linux\n'
            'Homepage: https://github.com/FreewareFuchs/Tenshi\n'
            'Description: Read-only disk analysis and file recovery (experimental beta)\n'
            ' Browse supported filesystems, export recoverable files to another drive,\n'
            ' and create or resume disk images. Sources are opened read-only.\n'
            ' Physical device access requires separately configured read permissions.\n', encoding='utf-8')
        (control / 'md5sums').write_text(''.join(
            hashlib.md5(p.read_bytes()).hexdigest() + '  ' + p.relative_to(stage).as_posix() + '\n'
            for p in sorted(stage.rglob('*')) if p.is_file() and control not in p.parents), encoding='ascii')
        for path in [stage, *stage.rglob('*')]:
            path.chmod(0o755 if path.is_dir() or path == stage / 'usr/bin/tenshi' else 0o644)
            os.utime(path, (epoch, epoch))
        # Build in temporary space: a failed dpkg invocation leaves no partial deliverable.
        package = Path(temporary) / destination.name
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(package)],
                       check=True, env={**os.environ, 'SOURCE_DATE_EPOCH': str(epoch)})
        # Exclusive creation prevents silently replacing a previous release build.
        with destination.open('xb') as target, package.open('rb') as source:
            shutil.copyfileobj(source, target)
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.deb.sha256').write_text(
        f'{checksum}  {destination.name}\n', encoding='ascii')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'deb_output')
    parser.add_argument('--package-version', default=DEFAULT_VERSION)
    args = parser.parse_args()
    print(build(args.output_dir, args.package_version))
