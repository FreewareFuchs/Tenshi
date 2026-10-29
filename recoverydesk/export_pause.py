"""Cooperative in-session pause; keep the existing exporter and hash context."""
import threading


class ExportPause:
    def __init__(self,cancel,event):
        self.cancel=cancel;self.event=event
        self._condition=threading.Condition()
        self._requested=False

    @property
    def requested(self):
        with self._condition:return self._requested

    def request(self,pause):
        with self._condition:
            self._requested=bool(pause)
            self._condition.notify_all()

    def check_cancel(self):
        """Called by the worker at existing copy/hash/checkpoint boundaries."""
        with self._condition:
            if self.cancel.is_set():return True
            if self._requested:
                self.event({'type':'paused'})
                while self._requested and not self.cancel.is_set():
                    # Main-window shutdown sets the existing cancellation Event.
                    # It must release a paused worker even without a resume click.
                    self._condition.wait(.1)
                if not self.cancel.is_set():self.event({'type':'resumed'})
            return self.cancel.is_set()
