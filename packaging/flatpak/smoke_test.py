"""Run inside the installed Flatpak; only disposable regular-file fixtures."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

# Test the installed package, never a copy from the host checkout.
sys.path.insert(0, '/app/share/tenshi')
import recoverydesk
from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.imaging import create_image
from recoverydesk.version_info import build_info


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_installed_gui() -> None:
    from recoverydesk import gui
    from recoverydesk.i18n import LANGUAGES

    assert Path(gui.__file__).is_relative_to('/app/share/tenshi')

    class ProbeApp(gui.RecoveryDeskApp):
        def __init__(self):
            self.callback_errors = []
            super().__init__()

        def report_callback_exception(self, exc_type, exc, tb):
            # Fail the probe instead of blocking CI on a modal error dialog.
            self.callback_errors.append((exc_type.__name__, str(exc)))

    with tempfile.TemporaryDirectory(prefix='tenshi-flatpak-gui-') as temporary:
        root = Path(temporary)
        with patch.dict(os.environ, {
                'TENSHI_SETTINGS_FILE': str(root / 'settings.json'),
                'TENSHI_LOG_DIR': str(root / 'logs')}), \
                patch.object(gui, 'list_physical_sources',
                             side_effect=AssertionError('Unexpected device enumeration')), \
                patch.object(gui, 'list_volumes',
                             side_effect=AssertionError('Unexpected volume enumeration')):
            app = ProbeApp()
            try:
                app.geometry('1280x900+0+0')
                app.update()
                assert app.brand_logo.width() > 0
                assert app.source_path.get() == '', 'Probe must not select a source'
                from tkinter import ttk
                for theme in ('dark', 'light', 'system'):
                    app.change_theme(theme)
                    app.update()
                    style = ttk.Style(app)
                    assert style.theme_use() == 'sun-valley-' + app.theme
                    from recoverydesk.appearance import palette
                    colors = palette(app.theme)
                    for name in ('TEntry', 'TCombobox'):
                        assert style.lookup(name, 'fieldbackground', ('readonly',)) == colors['input']
                        assert style.lookup(name, 'bordercolor', ('focus',)) == colors['accent']
                    assert style.lookup('Treeview', 'background', ('selected',)) == colors['inactive']
                for language in LANGUAGES:
                    app.change_language(language)
                    app.update()
                    assert app.language == language
                    from recoverydesk.source_catalog import SourceChoice
                    with patch.object(gui, 'open_source', side_effect=AssertionError('Unconfirmed device read')):
                        picker = app._show_source_dialog([
                            SourceChoice('/dev/testdisk', '/dev/testdisk', 'disk', 16384),
                            SourceChoice('/dev/testdisk1', '/dev/testdisk1', 'volume', 8192,
                                         filesystem='FAT32', parent='/dev/testdisk')])
                        app.update()
                        assert not picker.source_tree.selection()
                        assert str(picker.confirm_button.cget('state')) == 'disabled'
                        assert picker.source_tree.parent('/dev/testdisk1') == '/dev/testdisk'
                        picker.source_tree.selection_set('/dev/testdisk1')
                        app.update()
                        assert str(picker.confirm_button.cget('state')) == 'normal'
                        picker.destroy()
                    for tab in ('partition', 'files'):
                        app._select_main_tab(tab)
                        app.update()
                        assert app.tabs.winfo_height() >= 100, (language, tab)
                    assert app.file_tree.winfo_ismapped(), language
                    assert app.file_tree.winfo_height() >= 70, language
                    assert app.export_button.winfo_ismapped(), language
                    app.geometry('1024x650+0+0')
                    app.status.set('MFT: 123,456 / 987,654 Datensätze geprüft …')
                    app.update()
                    assert app.status_label.winfo_ismapped(), language
                    assert app.status_label.winfo_height() >= app.status_label.winfo_reqheight(), language
                    assert app.status_label.winfo_rooty()+app.status_label.winfo_height() <= app.winfo_rooty()+app.winfo_height(), language
                    assert app.export_queue_collapsed, language
                    app._toggle_export_queue()
                    app.update()
                    assert app.export_queue_bar.winfo_ismapped(), language
                    assert app.file_tree.winfo_height() >= 70, language
                    assert app.status_label.winfo_ismapped(), language
                    app._toggle_export_queue()
                    app.update()
                    assert app.export_queue_collapsed, language
                    assert not app.export_queue_bar.winfo_ismapped(), language
                    app.geometry('1280x900+0+0')
                assert app.callback_errors == [], app.callback_errors
                assert app.source_path.get() == ''
            finally:
                app.destroy()
    print('Installed Flatpak GUI: six languages, main tabs and export queue passed.')


def main() -> None:
    assert Path(recoverydesk.__file__).is_relative_to('/app/share/tenshi')
    assert not build_info().released
    assert build_info().commit
    check_installed_gui()
    # Validate the lsblk interface without reading any raw device contents.
    subprocess.run(['lsblk', '--version'], check=True)
    image = Path(sys.argv[1])
    expected = json.loads(Path(sys.argv[2]).read_text())
    assert image.is_file() and not image.is_symlink()
    before = digest(image)
    index = scan_tree(str(image))
    assert index.filesystem == 'FAT32'
    entries = index.list_dir(index.root)
    with tempfile.TemporaryDirectory(prefix='tenshi-flatpak-check-') as temporary:
        output = Path(temporary) / 'export'
        output.mkdir()
        result = export_selection(str(image), index, entries, str(output))
        assert not result.errors, result.errors
        assert result.exported == len(expected)
        for name, checksum in expected.items():
            assert digest(output / name) == checksum
        copy = Path(temporary) / 'copy.img'
        create_image(str(image), str(copy))
        assert digest(copy) == before
    assert digest(image) == before, 'Source image changed'
    print('Installed Flatpak: Tenshi GUI, FAT32 export hashes and imaging hashes passed.')


if __name__ == '__main__':
    main()
