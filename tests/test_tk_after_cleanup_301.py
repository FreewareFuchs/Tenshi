"""Regression: Tcl `after` scripts must never outlive their Python widgets."""
from __future__ import annotations
import os
import tkinter as tk
import unittest
from unittest.mock import patch

from recoverydesk.ntfs_browser import FileEntry, FileIndex
from recoverydesk.explorer import construct_paths


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'GUI display required')
class TkAfterCleanup301Tests(unittest.TestCase):
    def setUp(self):
        from recoverydesk.gui import RecoveryDeskApp
        self.app = RecoveryDeskApp()
        self.app.withdraw()

    def tearDown(self):
        if not self.app._closing:
            self.app.destroy()

    def test_root_pending_timers_are_canceled_on_destroy(self):
        called = []
        job = self.app.after(10000, lambda: called.append('late'))
        idle = self.app.after_idle(lambda: called.append('idle'))
        self.assertIn(job, self.app._pending_after)
        self.assertIn(idle, self.app._pending_after)
        self.app.destroy()
        self.assertFalse(self.app._pending_after)
        self.assertNotIn(job, self.app.tk.call('after', 'info'))
        self.assertNotIn(idle, self.app.tk.call('after', 'info'))
        # Drive the surviving Tcl event loop: no orphan callbacks may remain.
        self.app.tk.eval('update')
        self.assertFalse(called)

    def test_executed_and_explicitly_canceled_timers_are_untracked(self):
        fired = []
        first = self.app.after(0, lambda: fired.append('done'))
        second = self.app.after(10000, lambda: fired.append('canceled'))
        self.app.after_cancel(second)
        self.app.update()
        self.assertEqual(fired, ['done'])
        self.assertNotIn(first, self.app._pending_after)
        self.assertNotIn(second, self.app._pending_after)

    def test_dialog_timer_is_canceled_when_window_is_destroyed(self):
        win = tk.Toplevel(self.app)
        fired = []
        job = self.app._after_window(win, 10000, lambda: fired.append(True))
        self.assertIn(job, win._tenshi_pending_after)
        # Destroying a child should not cancel a dialog-wide poll.
        label = tk.Label(win, text='child')
        label.destroy()
        self.assertIn(job, win._tenshi_pending_after)
        win.destroy()
        self.assertFalse(win._tenshi_pending_after)
        self.assertNotIn(job, self.app.tk.call('after', 'info'))
        self.app.tk.eval('update')
        self.assertEqual(fired, [])

    def test_search_pending_chunk_is_removed_on_close(self):
        app = self.app
        entries = [FileEntry(i + 10, 1, f'file{i}.txt', 5, 1, False, False,
                             1, 'resident', 1, resident_data=b'X')
                   for i in range(2500)]
        app.browser_index = FileIndex(info=None, entries=entries,
                                      total_records=len(entries),
                                      scanned_records=len(entries), children={5: entries})
        app.browser_paths = construct_paths(entries)
        app.browser_search.set('file')
        app._search_browser()  # First 2000 synchronous; schedules one 1ms chunk.
        self.assertIn('Suche läuft', app.browser_path.get())
        self.assertTrue(app._pending_after)
        app.destroy()
        self.assertFalse(app._pending_after)
        self.app.tk.eval('update')

    def test_dialog_poll_stops_when_app_closes(self):
        win = tk.Toplevel(self.app)
        fired = []
        job = self.app._after_window(win, 10000, lambda: fired.append(True))
        self.app.destroy()
        self.assertNotIn(job, self.app.tk.call('after', 'info'))
        self.app.tk.eval('update')
        self.assertFalse(fired)

    def test_background_late_schedule_after_close_is_ignored(self):
        self.app.destroy()
        self.assertIsNone(self.app.after(0, lambda: self.fail('late callback')))
