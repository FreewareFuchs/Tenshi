"""Tk workflow smoke test with an image file (no physical devices involved)."""
import os
from contextlib import contextmanager
import json
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
                     patch('recoverydesk.gui.messagebox.showinfo') as info, \
                     patch('recoverydesk.gui.messagebox.showwarning') as warning, \
                     patch('recoverydesk.gui.messagebox.showerror') as error:
                    start.invoke()
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline and str(start.cget('state')) == 'disabled':
                        app.update()
                        time.sleep(.025)
                    app.update()
                    self.assertEqual(str(start.cget('state')), 'normal',
                                     'GUI imaging worker did not finish before deadline')
                    info.assert_called_once()
                    warning.assert_not_called()
                    error.assert_not_called()
                self.assertTrue(destination.exists())
                self.assertEqual(destination.read_bytes(), source.read_bytes())
                manifest = Path(str(destination) + '.recovery.json')
                self.assertTrue(manifest.exists())
                import json
                state = json.loads(manifest.read_text())
                self.assertEqual(state['verification']['status'], 'verified')
                self.assertEqual(state['bad_sector_policy'], 'stop')
                self.assertEqual(len(app.tabs.tabs()), 2)
            finally:
                app.destroy()


    def test_gui_byte_corruption_shows_error_and_persists_failed_status(self):
        """No user interaction and no physical device is required."""
        from recoverydesk import imaging
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, 'source.raw')
            output = Path(tmp, 'negative.img')
            source.write_bytes(bytes(512 * 1024))
            original_opener = imaging.open_regular_input
            bad_offset = 130_002

            @contextmanager
            def corrupt_disposable_output(path, src):
                with open(path, 'r+b') as target:
                    target.seek(bad_offset)
                    target.write(b'X')
                    target.flush()
                    os.fsync(target.fileno())
                with original_opener(path, src) as reader:
                    yield reader

            app = RecoveryDeskApp()
            try:
                app.withdraw()
                app.source_path.set(str(source))
                dialog = app.open_imaging_dialog()
                app.update_idletasks()
                controls = [w for w in walk(dialog) if isinstance(w, ttk.Button)]
                begin = next(b for b in controls if
                             b.cget('text') == 'Image erstellen / fortsetzen')
                entry = next(w for w in walk(dialog) if isinstance(w, ttk.Entry))
                entry.insert(0, str(output))
                with patch('recoverydesk.imaging.open_regular_input',
                           side_effect=corrupt_disposable_output), \
                     patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                     patch('recoverydesk.gui.messagebox.showinfo') as info, \
                     patch('recoverydesk.gui.messagebox.showwarning') as warning, \
                     patch('recoverydesk.gui.messagebox.showerror') as error:
                    begin.invoke()
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline and str(begin.cget('state')) == 'disabled':
                        app.update()
                        time.sleep(.025)
                    app.update()
                    self.assertEqual(str(begin.cget('state')), 'normal')
                    info.assert_not_called()
                    warning.assert_not_called()
                    error.assert_called_once()
                    self.assertIn('INTEGRITÄTSFEHLER', str(error.call_args))
                    self.assertIn(str(bad_offset), str(error.call_args))
                state = json.loads(Path(str(output) + '.recovery.json').read_text())
                self.assertEqual(state['state'], 'integrity_failed')
                self.assertEqual(state['verification']['status'], 'failed')
                self.assertEqual(source.read_bytes(), bytes(512 * 1024))
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main()
