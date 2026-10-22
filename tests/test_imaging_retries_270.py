"""Imaging 2.7.0: bounded retries, safe pause, and source never written."""
import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.imaging import (_recover_read, create_image, sidecar_path,
                                  describe_bad_ranges, ImagingError)
from recoverydesk.i18n import LANGUAGES, TRANSLATIONS


class SimulatedReader:
    def __init__(self, data, fail_on=None, error=None):
        self.data = data
        self.position = 0
        self.fail_on = fail_on or {}
        self.error = error or OSError(errno.EIO, 'simulated disk CRC')
        self.calls = []
        self.writes = 0

    def seek(self, pos):
        self.position = pos

    def read(self, amount):
        key = (self.position, amount)
        self.calls.append(key)
        remaining = self.fail_on.get(key, 0)
        if remaining:
            if remaining != -1:
                self.fail_on[key] = remaining - 1
            raise self.error
        return self.data[self.position:self.position + amount]

    def write(self, data):
        self.writes += 1
        raise AssertionError('source must never be written')


class ReadRetryUnitTests(unittest.TestCase):
    def setUp(self):
        self.data = b'A' * 4096 + b'B' * 4096

    def test_transient_media_error_is_retried_at_minimum_unit(self):
        f = SimulatedReader(self.data, {(0, 8192): -1, (4096, 4096): 1})
        bad, counter = [], [0]
        result = _recover_read(f, 0, 8192, 4096, bad, read_retries=2,
                               retry_delay_ms=0, retry_counter=counter)
        self.assertEqual(result, self.data)
        self.assertEqual(bad, [])
        self.assertEqual(counter, [1])
        self.assertEqual(f.calls, [(0, 8192), (0, 4096), (4096, 4096),
                                   (4096, 4096)])

    def test_persistent_sector_has_bounded_attempts_and_zero_report(self):
        f = SimulatedReader(self.data, {(0, 8192): -1, (0, 4096): -1})
        bad, count = [], [0]
        result = _recover_read(f, 0, 8192, 4096, bad, read_retries=2,
                               retry_delay_ms=0, retry_counter=count)
        self.assertEqual(result, bytes(4096) + self.data[4096:])
        self.assertEqual(bad, [[0, 4096]])
        self.assertEqual(f.calls.count((0, 8192)), 1)
        self.assertEqual(f.calls.count((0, 4096)), 3)
        self.assertEqual(count, [2])

    def test_stop_policy_never_inserts_zeros(self):
        f = SimulatedReader(self.data, {(0, 4096): -1})
        with self.assertRaisesRegex(ImagingError, 'Byteoffset 0'):
            _recover_read(f, 0, 4096, 4096, [], read_retries=1,
                          retry_delay_ms=0, bad_sector_policy='stop')
        self.assertEqual(f.calls.count((0, 4096)), 2)

    def test_access_denied_does_not_retry_or_zero_fill(self):
        denied = PermissionError(errno.EACCES, 'Access denied')
        f = SimulatedReader(self.data, {(0, 4096): -1}, denied)
        bad = []
        with self.assertRaisesRegex(ImagingError, 'NICHT'):
            _recover_read(f, 0, 4096, 4096, bad, read_retries=3,
                          retry_delay_ms=0)
        self.assertEqual(bad, [])
        self.assertEqual(f.calls, [(0, 4096)])

    def test_cancel_while_retrying_aborts_inflight_block(self):
        f = SimulatedReader(self.data, {(0, 4096): -1})
        from recoverydesk.imaging import ImagingPaused
        with self.assertRaises(ImagingPaused):
            _recover_read(f, 0, 4096, 4096, [], read_retries=3,
                          retry_delay_ms=0, cancel=lambda: len(f.calls) >= 1)
        self.assertEqual(len(f.calls), 1)

    def test_bad_error_is_not_misidentified_as_media_error(self):
        exc = OSError(errno.EINVAL, 'bad seek')
        f = SimulatedReader(self.data, {(0, 4096): -1}, exc)
        with self.assertRaises(ImagingError):
            _recover_read(f, 0, 4096, 4096, [], read_retries=3,
                          retry_delay_ms=0)
        self.assertEqual(len(f.calls), 1)


class ImagingRetryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'input.img'
        self.target = Path(self.temp.name) / 'output.img'
        self.content = b'A' * 4096 + b'B' * 4096 + b'C' * (1024 * 1024 - 8192)
        self.source.write_bytes(self.content)

    def _fake_source(self, read_failure):
        from contextlib import contextmanager
        reader = SimulatedReader(self.content, read_failure)
        @contextmanager
        def source_ctx(_source):
            yield reader
        return reader, source_ctx

    def test_recovered_sector_has_no_bad_map_and_counts_retries(self):
        class FaultRegion(SimulatedReader):
            def read(self, amount):
                start = self.position
                self.calls.append((start, amount))
                if start <= 4096 < start + amount:
                    if amount != 4096:
                        raise OSError(errno.EIO, 'CRC')
                    if not getattr(self, '_recovered_once', False):
                        self._recovered_once = True
                        raise OSError(errno.EIO, 'CRC')
                return self.data[start:start + amount]
        reader = FaultRegion(self.content)
        from contextlib import contextmanager
        @contextmanager
        def open_fake(_source):
            yield reader
        with patch('recoverydesk.imaging.open_source', open_fake):
            result = create_image(str(self.source), str(self.target),
                                  read_retries=2, retry_delay_ms=0, verify=False)
        self.assertEqual(result['unreadable_bytes'], 0)
        self.assertEqual(result['read_retries_performed'], 1)
        self.assertEqual(self.target.read_bytes(), self.content)
        self.assertEqual(reader.writes, 0)
        self.assertEqual(self.source.read_bytes(), self.content)
        self.assertIn('Wiederholte Sektor-Leseversuche: 1', describe_bad_ranges(result))

    def test_stop_policy_preserves_previous_checkpoint_and_resumes(self):
        extended = self.content + b'Z' * (1024 * 1024)
        self.source.write_bytes(extended)
        class PersistentFault(SimulatedReader):
            def read(self, amount):
                start = self.position
                self.calls.append((start, amount))
                if start <= 1024 * 1024 < start + amount:
                    raise OSError(errno.EIO, 'CRC')
                return self.data[start:start + amount]
        reader = PersistentFault(extended)
        from contextlib import contextmanager
        @contextmanager
        def source_ctx(_source):
            yield reader
        with patch('recoverydesk.imaging.open_source', source_ctx):
            with self.assertRaises(ImagingError):
                create_image(str(self.source), str(self.target),
                             read_retries=1, retry_delay_ms=0,
                             bad_sector_policy='stop')
        self.assertEqual(self.target.read_bytes(), extended[:1024 * 1024])
        checkpoint = json.loads(Path(sidecar_path(str(self.target))).read_text('utf-8'))
        self.assertEqual(checkpoint['processed'], 1024 * 1024)
        self.assertEqual(checkpoint['bad_ranges'], [])
        result = create_image(str(self.source), str(self.target), resume=True)
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(self.target.read_bytes(), extended)

    def test_invalid_controls_rejected_before_creating_image(self):
        for kwargs in ({'read_retries': -1}, {'read_retries': 4},
                       {'read_retries': True}, {'retry_delay_ms': 2001},
                       {'bad_sector_policy': 'ignore'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ImagingError):
                create_image(str(self.source), str(self.target), **kwargs)
            self.assertFalse(self.target.exists())

    def test_old_checkpoint_remains_readable_after_pause(self):
        flag = [False]
        def on_progress(event):
            flag[0] = event.processed >= 1024 * 1024
        extended = self.content + b'Z' * 4096
        self.source.write_bytes(extended)
        result = create_image(str(self.source), str(self.target),
                              progress=on_progress, cancel=lambda: flag[0])
        self.assertEqual(result['state'], 'paused')
        with open(sidecar_path(str(self.target)), 'r+', encoding='utf-8') as f:
            state = json.load(f)
            for name in ('read_retries', 'retry_delay_ms', 'read_retries_performed',
                         'bad_sector_policy'):
                state.pop(name, None)
            f.seek(0)
            json.dump(state, f)
            f.truncate()
        done = create_image(str(self.source), str(self.target), resume=True)
        self.assertEqual(done['state'], 'complete')
        self.assertEqual(self.target.read_bytes(), extended)

    def test_translations_cover_new_imaging_controls(self):
        for phrase in ('Leseversuche:', 'Bei Medienfehler:', 'Nullen + protokollieren',
                       'Sicher anhalten', 'Fehlerstellen-Bericht', 'Bericht speichern'):
            self.assertIn(phrase, TRANSLATIONS)
            self.assertEqual(set(TRANSLATIONS[phrase]), set(LANGUAGES) - {'de'})

if __name__ == '__main__':
    unittest.main()


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'GUI display required')
class ImagingRetryGuiTests(unittest.TestCase):
    def test_dialog_transfers_retries_and_safe_stop_to_worker(self):
        import time
        import tkinter as tk
        from tkinter import ttk
        from recoverydesk.gui import RecoveryDeskApp

        def walk(w):
            for sub in w.winfo_children():
                yield sub
                yield from walk(sub)

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'src.img'
            dest = Path(td) / 'copy.img'
            source.write_bytes(bytes(8192))
            app = RecoveryDeskApp()
            try:
                app.withdraw()
                app.source_path.set(str(source))
                dialog = app.open_imaging_dialog()
                app.update_idletasks()
                choices = [w for w in walk(dialog) if isinstance(w, ttk.Combobox)]
                retries = next(w for w in choices if '3' in list(w['values']))
                modes = next(w for w in choices if len(w['values']) == 2 and
                             any('Sicher anhalten' in str(x) for x in w['values']))
                retries.set('2')
                modes.set('Sicher anhalten')
                target_entry = next(w for w in walk(dialog) if isinstance(w, ttk.Entry))
                target_entry.insert(0, str(dest))
                begin = next(w for w in walk(dialog) if isinstance(w, ttk.Button) and
                             w.cget('text') == 'Image erstellen / fortsetzen')
                captured = []
                def fake_create(*args, **kwargs):
                    captured.append(kwargs)
                    return {'state':'complete','processed':8192,'source':{'size':8192},
                            'unreadable_bytes':0,'bad_ranges':[],
                            'read_retries_performed':0,'bad_sector_policy':kwargs['bad_sector_policy']}
                with patch('recoverydesk.gui.create_image', side_effect=fake_create), \
                     patch('recoverydesk.gui.messagebox.askyesno', return_value=True), \
                     patch('recoverydesk.gui.messagebox.showinfo'):
                    begin.invoke()
                    until = time.monotonic() + 4
                    while time.monotonic() < until:
                        app.update()
                        if captured and str(begin.cget('state')) != 'disabled':
                            break
                        time.sleep(0.02)
                self.assertTrue(captured)
                self.assertEqual(captured[0]['read_retries'], 2)
                self.assertEqual(captured[0]['bad_sector_policy'], 'stop')
                report_button = next(w for w in walk(dialog) if isinstance(w, ttk.Button) and
                                     w.cget('text') == 'Fehlerstellen-Bericht')
                self.assertNotEqual(str(report_button.cget('state')), 'disabled')
            finally:
                app.destroy()
