"""Run inside the installed Flatpak; only disposable regular-file fixtures."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import tkinter as tk

# Test the installed package, never a copy from the host checkout.
sys.path.insert(0, '/app/share/tenshi')
import recoverydesk
from recoverydesk.branding import asset_path
from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk.imaging import create_image
from recoverydesk.version_info import build_info


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    assert Path(recoverydesk.__file__).is_relative_to('/app/share/tenshi')
    assert not build_info().released
    assert build_info().commit
    window = tk.Tk()
    logo = tk.PhotoImage(file=str(asset_path('tenshi_logo.png')))
    assert logo.width() > 0
    window.update()
    window.destroy()
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
    print('Installed Flatpak: Tk/logo, FAT32 export hashes and imaging hashes passed.')


if __name__ == '__main__':
    main()
