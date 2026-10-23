"""Build identity: embedded in packages, read-only Git discovery in source runs."""
from dataclasses import asdict, dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import subprocess

from . import __release__, __version__


@dataclass(frozen=True)
class BuildInfo:
    version: str = __version__
    release: str = __release__
    commit: str | None = None
    dirty: bool = False
    released: bool = False

    def display(self):
        label = self.release.replace('beta.', 'Beta.', 1)
        if not self.released:
            label += '+dev'
        commit = self.commit[:10] if self.commit else '?'
        if self.dirty:
            commit += '+dirty'
        return f'{self.version} {label} ({commit})'


def collect_build_info(root: Path, release: str | None = None) -> BuildInfo:
    root = root.resolve()
    def git(*args):
        return subprocess.check_output(
            ['git', '-C', str(root), *args], text=True, stderr=subprocess.DEVNULL,
            timeout=3, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).strip()
    try:
        if Path(git('rev-parse', '--show-toplevel')).resolve() != root:
            raise ValueError('Not the application repository')
        commit = git('rev-parse', 'HEAD')
        if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
            raise ValueError('Invalid commit')
        dirty = bool(git('status', '--porcelain', '--untracked-files=normal'))
        tags = git('tag', '--points-at', 'HEAD').splitlines()
    except (OSError, subprocess.SubprocessError, ValueError):
        if release is not None:
            raise ValueError('A release build requires a known clean Git commit')
        return BuildInfo()
    if release is not None and not re.fullmatch(r'beta\.[1-9][0-9]*', release):
        raise ValueError('Release must have the form beta.N')
    if release is not None and dirty:
        raise ValueError('A release build requires a clean working tree')
    if release is None and not dirty:
        matching = [tag.removeprefix(f'v{__version__}-') for tag in tags
                    if re.fullmatch(r'v' + re.escape(__version__) + r'-beta\.[1-9][0-9]*', tag)]
        if len(matching) == 1:
            release = matching[0]
    return BuildInfo(commit=commit, dirty=dirty, release=release or __release__,
                     released=release is not None)


def write_build_info(path: Path, root: Path, release: str | None = None) -> BuildInfo:
    info = collect_build_info(root, release)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'schema': 1, **asdict(info)}, sort_keys=True) + '\n', encoding='utf-8')
    return info


@lru_cache(maxsize=1)
def build_info() -> BuildInfo:
    path = Path(__file__).with_name('_build_info.json')
    try:
        if path.stat().st_size > 4096:
            raise ValueError('Oversized build metadata')
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['schema'] != 1 or data['version'] != __version__ or
            not re.fullmatch(r'beta\.[1-9][0-9]*', data['release']) or
            type(data['dirty']) is not bool or type(data['released']) is not bool or
            (data['commit'] is not None and not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', data['commit'])) or
            (data['released'] and (data['dirty'] or not data['commit']))):
            raise ValueError('Invalid build metadata')
        return BuildInfo(**{k: data[k] for k in ('version', 'release', 'commit', 'dirty', 'released')})
    except (OSError, ValueError, TypeError, KeyError):
        # Installed copies must not accidentally identify an unrelated parent repository.
        root = Path(__file__).resolve().parents[1]
        if (root / '.git').exists():
            return collect_build_info(root)
        return BuildInfo()


def display_version() -> str:
    return build_info().display()
