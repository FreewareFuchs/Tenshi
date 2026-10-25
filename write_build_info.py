"""Generate deterministic package build metadata; never modifies application sources."""
import argparse
import os
from pathlib import Path
from recoverydesk.version_info import write_build_info

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/identity/recoverydesk/_build_info.json'))
    parser.add_argument('--release', default=os.environ.get('TENSHI_RELEASE'),
                        help='Explicit release identity: stable or beta.N; requires a clean Git tree')
    args = parser.parse_args()
    print(write_build_info(args.output, Path(__file__).resolve().parent, args.release).display())
