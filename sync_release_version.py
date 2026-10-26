"""Generate/check release-version fields from recoverydesk/__init__.py.

No application imports, builds, Git changes, tags or publication. The checked-in
outputs preserve the existing Windows and Actions entry points.
"""
from __future__ import annotations
import argparse
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
VERSION = r'(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))'
# Only explicitly owned version slots are changed, never dependencies/history.
SLOTS = {
    'build/version_info.txt': [rf'Tenshi {VERSION}', rf"StringStruct\('(?:FileVersion|ProductVersion)', '{VERSION}\.0'\)",
                               r'(?:filevers|prodvers)=\((?P<version>[0-9]+, [0-9]+, [0-9]+, 0)\)'],
    'installer/Tenshi.iss': [rf'#define AppVersion "{VERSION}"',
                            rf'VersionInfo(?:Product)?Version={VERSION}\.0',
                            rf'OutputBaseFilename=Tenshi_Setup_{VERSION}'],
    'build_windows.bat': [rf'Tenshi {VERSION}'],
    'build_portable.bat': [rf'Tenshi {VERSION}', rf'Tenshi_Portable_{VERSION}_Win64\.zip'],
    'build_installer.bat': [rf'Tenshi {VERSION}', rf'Tenshi_Setup_{VERSION}\.exe'],
    'RELEASE_WINDOWS_ERSTELLEN.bat': [rf'Tenshi {VERSION}'],
    '.github/workflows/windows-check.yml': [rf'Tenshi(?:_Setup_|_Portable_|-){VERSION}',
                                           rf"\$v\.FileVersion -ne '{VERSION}\.0'"],
    '.github/workflows/linux-check.yml': [rf'Tenshi-{VERSION}-Linux-DEB'],
}


def read_version(root: Path = ROOT) -> str:
    tree = ast.parse((root/'recoverydesk/__init__.py').read_text(encoding='utf-8'))
    values = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets)
              and isinstance(node.value, ast.Constant)]
    if len(values) != 1 or not isinstance(values[0], str) or not re.fullmatch(VERSION, values[0]):
        raise ValueError('__version__ must be one literal major.minor.patch version')
    if any(int(part) > 65535 for part in values[0].split('.')):
        raise ValueError('Windows version fields must fit in 16 bits')
    return values[0]


def planned_files(root: Path = ROOT) -> dict[str, bytes]:
    """Validate every input before writing anything; preserve newline styles."""
    version = read_version(root)
    result = {}
    for name, patterns in SLOTS.items():
        text = (root/name).read_bytes().decode('utf-8')
        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if not matches:
                raise ValueError(f'Missing version slot in {name}: {pattern}')
            for match in reversed(matches):
                replacement = ', '.join(version.split('.') + ['0']) if ', ' in match['version'] else version
                text = text[:match.start('version')] + replacement + text[match.end('version'):]
        result[name] = text.encode('utf-8')
    return result


def sync(root: Path = ROOT, *, write: bool = False) -> list[str]:
    rendered = planned_files(root)
    changed = [name for name, data in rendered.items() if (root/name).read_bytes() != data]
    if write:
        for name in changed:
            (root/name).write_bytes(rendered[name])
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    try:
        changed = sync(write=args.write)
    except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
        parser.exit(2, f'Version metadata error: {exc}\n')
    if changed:
        print(('Updated: ' if args.write else 'Outdated: ') + ', '.join(changed))
        if not args.write:
            print('Run: python sync_release_version.py --write, then commit the generated files.')
            return 1
    else:
        print(f'Version metadata consistent: {read_version()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
