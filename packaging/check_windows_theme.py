"""Verify that the frozen EXE contains the exact theme assets and license."""
from pathlib import Path
import sys
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[1]
archive = CArchiveReader(sys.argv[1])
entries = {name.replace('\\', '/'): name for name in archive.toc}
for source in (root / 'recoverydesk/assets/sun_valley').rglob('*'):
    if source.is_file():
        relative = source.relative_to(root).as_posix()
        assert relative in entries, f'Missing bundled theme file: {relative}'
        assert archive.extract(entries[relative]) == source.read_bytes(), relative
print('Bundled Sun Valley theme and MIT license verified.')
