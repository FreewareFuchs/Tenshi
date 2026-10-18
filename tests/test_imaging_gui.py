"""Tk workflow smoke test with an image file (no physical devices involved)."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from recoverydesk.gui import RecoveryDeskApp
try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None


def walk(widget):
    for c in widget.winfo_children():
        yield c
        yield from walk(c)


@unittest.skipUnless(tk and (os.name == 'nt' or os.environ.get('DISPLAY')),
                     'A graphical display is required')
class ImagingGuiTests(unittest.TestCase):
    def test_new_image_from_dialog(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, 'original.raw')
            destination = Path(tmp, 'recovered.img')
            source.write_bytes(b'test recoverydesk ' * (1024 * 36))
            app = RecoveryDeskApp()
            try:
                app.withdraw()
                app.source_path.set(str(source))
                dialog = app.open_imaging_dialog()
                app.update_idletasks()
                buttons = [w for w in walk(dialog) if isinstance(w, ttk.Button)]
                self.assertTrue(any('Image erstellen' in b.cget('text') for b in buttons))
                entries = [w for w in walk(dialog) if isinstance(w, ttk.Entry)]
                self.assertTrue(entries)
                entries[0].insert(0, str(destination))
                start = next(b for b in buttons if b.cget('text') == 'Image erstellen / fortsetzen')
                with patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                     patch('recoverydesk.gui.messagebox.showinfo'):
                    start.invoke()
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline and (not destination.exists() or
                            destination.stat().st_size < source.stat().st_size):
                        app.update()
                        time.sleep(.025)
                    # Handle last event and finish dialog update.
                    for _ in range(5):
                        app.update()
                        time.sleep(.03)
                self.assertTrue(destination.exists())
                self.assertEqual(destination.read_bytes(), source.read_bytes())
                self.assertTrue(Path(str(destination) + '.recovery.json').exists())
                self.assertEqual(len(app.tabs.tabs()), 2)
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main()
