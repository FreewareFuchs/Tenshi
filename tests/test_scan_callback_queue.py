"""Scan workers enqueue callbacks without entering Tcl/Tk."""
import queue
import threading
import unittest
from unittest import mock

from recoverydesk.gui import RecoveryDeskApp


class ScanCallbackQueueTests(unittest.TestCase):
    def setUp(self):
        self.app = RecoveryDeskApp.__new__(RecoveryDeskApp)
        self.app._scan_callbacks = queue.Queue()
        self.app._closing = False
        self.app.after = mock.Mock()

    def test_worker_callbacks_execute_in_order_on_draining_thread(self):
        calls = []
        main = threading.get_ident()
        def worker():
            for number in range(3):
                self.app._post_scan_callback(lambda n=number: calls.append((n, threading.get_ident())))
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(calls, [])
        self.app.after.assert_not_called()
        self.app._drain_scan_callbacks()
        self.assertEqual(calls, [(n, main) for n in range(3)])
        self.app.after.assert_called_once_with(20, self.app._drain_scan_callbacks)

    def test_closing_window_does_not_execute_or_reschedule_callbacks(self):
        callback = mock.Mock()
        self.app._post_scan_callback(callback)
        self.app._closing = True
        self.app._drain_scan_callbacks()
        callback.assert_not_called()
        self.app.after.assert_not_called()

    def test_progress_burst_leaves_time_for_other_gui_events(self):
        callback = mock.Mock()
        for _ in range(101):
            self.app._post_scan_callback(callback)
        self.app._drain_scan_callbacks()
        self.assertEqual(callback.call_count, 100)
        self.assertEqual(self.app._scan_callbacks.qsize(), 1)
