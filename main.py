"""Tenshi entrypoint; diagnostics can run without opening a GUI or a disk."""
from __future__ import annotations
import sys


def smoke_test() -> int:
    """Minimal non-destructive smoke check for a packaged Windows executable."""
    from recoverydesk.branding import asset_path
    from recoverydesk import __version__
    import recoverydesk.gui as gui
    for name in ('tenshi_logo.png', 'tenshi_icon.png', 'tenshi.ico'):
        path = asset_path(name)
        if not path.is_file() or path.stat().st_size < 128:
            raise RuntimeError('Required application asset is missing.')
    if gui.APP_NAME != 'Tenshi' or not __version__:
        raise RuntimeError('Invalid application identity.')
    if not (asset_path('tenshi_icon.png').parent/'content_licenses/SOURCES.txt').is_file():
        raise RuntimeError('Content dependency notices are missing.')
    from PIL import Image
    from defusedxml import ElementTree
    from recoverydesk.content_worker import pdf_backend
    if not pdf_backend():
        raise RuntimeError('PDF preview backend is missing.')
    if getattr(sys, 'frozen', False):
        from pathlib import Path
        from recoverydesk import version_info
        if not Path(version_info.__file__).with_name('_build_info.json').is_file():
            raise RuntimeError('Packaged build identity is missing.')
    # Verify bundled offline help and all localized topics without launching Tk
    # or opening a data source. Useful with Windows PyInstaller --onefile.
    from recoverydesk.help_center import TOPICS, topic_text
    from recoverydesk.i18n import LANGUAGES
    if len(TOPICS) != 9:
        raise RuntimeError('Offline help topics are missing.')
    for language in LANGUAGES:
        for topic in TOPICS:
            title, body = topic_text(topic, language)
            if not title.strip() or len(body) < 50:
                raise RuntimeError('Offline help translation is missing.')
    from recoverydesk.content_smoke import run as check_content_package
    check_content_package()
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 3 and args[0] == '--content-worker':
        from recoverydesk.content_worker import main as content_main
        return content_main(args[1], '' if args[2] == '-' else args[2])
    if args == ['--smoke-test']:
        try:
            return smoke_test()
        except Exception:
            return 1
    if args == ['--version']:
        from recoverydesk.version_info import display_version
        print(f'Tenshi {display_version()}')
        return 0
    if args:
        # Unknown CLI args are not silently ignored (for example typos in CI).
        return 2
    from recoverydesk.gui import main as gui_main
    gui_main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
