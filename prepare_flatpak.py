#!/usr/bin/env python3
"""Prepare a minimal, explicitly unreleased source snapshot for Flatpak tests."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
import tempfile

from recoverydesk.version_info import collect_build_info

ROOT = Path(__file__).resolve().parent
APP_ID = 'de.freewarefuchs.Tenshi.Experimental'
PACKAGING = (
    f'{APP_ID}.desktop', f'{APP_ID}.metainfo.xml', 'tenshi-flatpak', 'install.py',
)


def prepare(output: Path, root: Path = ROOT) -> Path:
    root, output = root.resolve(), output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    # This is a development probe even when built from a stable source tag.
    info = replace(collect_build_info(root), released=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tenshi-flatpak-', dir=output.parent) as temporary:
        context = Path(temporary) / 'context'
        context.mkdir()
        snapshot = context / 'tenshi-src'

        def copy(source: Path, relative: Path) -> None:
            if source.is_symlink():
                raise ValueError(f'Symlink is not a source file: {relative}')
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

        for name in ('main.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
            copy(root / name, Path(name))
        # Never copy sessions, images, arbitrary JSON, caches or the Git database.
        for source in sorted((root / 'recoverydesk').rglob('*')):
            license_asset = source.is_relative_to(root / 'recoverydesk/assets/content_licenses') and source.suffix == '.txt'
            theme_asset = (source.is_relative_to(root / 'recoverydesk/assets/sun_valley')
                           and (source.suffix == '.tcl' or source.name in ('LICENSE', 'UPSTREAM.md')))
            if ('__pycache__' not in source.parts
                    and (source.suffix in ('.py', '.png', '.ico') or theme_asset or license_asset)):
                if source.is_file() or source.is_symlink():
                    copy(source, source.relative_to(root))
        for name in PACKAGING:
            relative = Path('packaging/flatpak') / name
            copy(root / relative, relative)
        (snapshot / 'recoverydesk/_build_info.json').write_text(
            json.dumps({'schema': 1, **asdict(info)}, sort_keys=True) + '\n', encoding='utf-8')
        manifest = context / f'{APP_ID}.json'
        shutil.copyfile(root / 'packaging/flatpak' / manifest.name, manifest)
        context.rename(output)
    return output / f'{APP_ID}.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'flatpak_output/context')
    print(prepare(parser.parse_args().output_dir))
