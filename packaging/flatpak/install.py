"""Install the prepared source snapshot inside flatpak-builder, without pip."""
from pathlib import Path
import shutil
import sys

APP_ID = 'de.freewarefuchs.Tenshi.Experimental'


def install(root: Path, prefix: Path) -> None:
    def copy(source: Path, relative: str, mode: int = 0o644) -> None:
        target = prefix / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(mode)

    copy(root / 'main.py', 'share/tenshi/main.py')
    for source in sorted((root / 'recoverydesk').rglob('*')):
        license_asset = source.is_relative_to(root / 'recoverydesk/assets/content_licenses') and source.suffix == '.txt'
        theme_asset = (source.is_relative_to(root / 'recoverydesk/assets/sun_valley')
                       and (source.suffix == '.tcl' or source.name in ('LICENSE', 'UPSTREAM.md')))
        if source.is_file() and (source.suffix in ('.py', '.png', '.ico', '.json') or theme_asset or license_asset):
            copy(source, 'share/tenshi/' + source.relative_to(root).as_posix())
    files = root / 'packaging/flatpak'
    copy(files / 'tenshi-flatpak', 'bin/tenshi-flatpak', 0o755)
    copy(files / f'{APP_ID}.desktop', f'share/applications/{APP_ID}.desktop')
    copy(files / f'{APP_ID}.metainfo.xml', f'share/metainfo/{APP_ID}.metainfo.xml')
    copy(root / 'recoverydesk/assets/tenshi_icon.png',
         f'share/icons/hicolor/256x256/apps/{APP_ID}.png')
    copy(root / 'LICENSE', 'share/licenses/tenshi/LICENSE')
    copy(root / 'THIRD_PARTY_NOTICES.md', 'share/doc/tenshi/THIRD_PARTY_NOTICES.md')


if __name__ == '__main__':
    install(Path.cwd(), Path(sys.argv[1]))
