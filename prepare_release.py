"""Assemble already tested CI artifacts on Linux; never tag, upload or publish a release."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from recoverydesk import __version__
from release_finalize import check_pe
from release_tools import file_sha256, verify_portable


def validate_identity(data, release, commit):
    expected = dict(schema=1, version=__version__, release=release, commit=commit,
                    dirty=False, released=True)
    if (data != expected or type(data.get('dirty')) is not bool or
            type(data.get('released')) is not bool):
        raise ValueError('Build identity does not match the requested clean release commit')


def prepare(artifacts: Path, output: Path, release: str, commit: str) -> Path:
    if not re.fullmatch(r'beta\.[1-9][0-9]*', release):
        raise ValueError('Release must have the form beta.N')
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
        raise ValueError('A full Git commit hash is required')
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)

    def one(name):
        matches = list(artifacts.rglob(name))
        if len(matches) != 1 or matches[0].is_symlink() or not matches[0].is_file():
            raise ValueError(f'Expected exactly one regular artifact: {name}')
        return matches[0]

    exe = one('Tenshi.exe')
    installer = one(f'Tenshi_Setup_{__version__}.exe')
    portable = one(f'Tenshi_Portable_{__version__}_Win64.zip')
    package_version = f'{__version__}~{release}-1'
    deb = one(f'tenshi_{package_version.replace("~", ".")}_all.deb')
    identity = one('windows-build-info.json')
    validate_identity(json.loads(identity.read_text(encoding='utf-8')), release, commit)
    check_pe(exe)
    check_pe(installer)
    if verify_portable(portable) != file_sha256(exe):
        raise ValueError('Portable executable differs from the Windows build')
    for field, expected in [('Package', 'tenshi'), ('Version', package_version), ('Architecture', 'all')]:
        value = subprocess.check_output(['dpkg-deb', '-f', str(deb), field], text=True).strip()
        if value != expected:
            raise ValueError(f'Unexpected DEB {field}: {value}')
    # Stream the package archive without extracting paths or executing its scripts.
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['dpkg-deb', '--fsys-tarfile', str(deb)], stdout=stream, check=True)
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode='r:') as archive:
            names = [m for m in archive.getmembers()
                     if m.name.removeprefix('./') == 'usr/share/tenshi/recoverydesk/_build_info.json']
            if len(names) != 1 or not names[0].isfile() or names[0].size > 4096:
                raise ValueError('Missing or invalid DEB build identity')
            with archive.extractfile(names[0]) as metadata:
                validate_identity(json.load(metadata), release, commit)

    tag = f'v{__version__}-{release}'
    download = f'https://github.com/FreewareFuchs/Tenshi/releases/download/{tag}/'
    files = [(installer, f'Tenshi_Setup_{__version__}-{release}_Win64.exe'),
             (portable, f'Tenshi_Portable_{__version__}-{release}_Win64.zip'),
             (deb, deb.name)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.release-') as temporary:
        stage = Path(temporary) / 'bundle'
        stage.mkdir()
        rows = []
        for source, name in files:
            before = file_sha256(source)
            target = stage / name
            shutil.copyfile(source, target)
            if file_sha256(target) != before or file_sha256(source) != before:
                raise ValueError('Artifact changed during preparation')
            rows.append(dict(file=name, bytes=target.stat().st_size, sha256=before))
        manifest = dict(schema=1, product='Tenshi', version=__version__, release=release,
                        tag=tag, commit=commit, published=False, artifacts=rows)
        (stage / 'release_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        (stage / 'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["file"]}\n' for r in rows), encoding='ascii')
        (stage / 'RELEASE_NOTES.md').write_text(
            f'# Tenshi {__version__} {release.replace("beta.", "Beta.")}\n\n'
            f'Quellstand: `{commit}`\n\n'
            f'- [Windows Installer]({download}{rows[0]["file"]})\n'
            f'- [Windows Portable]({download}{rows[1]["file"]})\n'
            f'- [Linux DEB – Linux Mint 22.x / Python ≥ 3.11]({download}{rows[2]["file"]})\n\n'
            'Experimentelle Beta. Quellen werden nur lesend geöffnet. Gerettete Dateien können beschädigt sein.\n\n'
            'Änderungen und manuelle Tests vor Veröffentlichung ergänzen. '
            'Dieses Paket wurde nur vorbereitet; es wurde kein GitHub-Release angelegt.\n', encoding='utf-8')
        stage.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    print(prepare(args.artifacts, args.output, args.release, args.commit))
