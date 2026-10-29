"""Privacy-conscious technical error logs; never records file contents.

Paths, filenames and exception message strings are deliberately omitted.
The logger is best effort: failure to create a log must not affect recovery.
"""
from __future__ import annotations
import functools
import logging
from logging.handlers import RotatingFileHandler
import os
import threading
from pathlib import Path

_LOG = logging.getLogger('tenshi.recovery')
_LOG.addHandler(logging.NullHandler())
_CONFIGURED = None
_LOCK = threading.RLock()


class ClosingRotatingFileHandler(RotatingFileHandler):
    """Rotate log files, but never retain an open file handle between records.

    Keeping a RotatingFileHandler open prevents Windows from deleting temporary
    test directories. Closing after each emit also allows the user to move or
    inspect the diagnostic log without restarting Tenshi.
    """

    def __init__(self, filename, **kwargs):
        super().__init__(filename, delay=True, **kwargs)

    def emit(self, record):
        # logging.Handler.handle() holds the handler's lock for the whole emit.
        try:
            super().emit(record)
        finally:
            if self.stream is not None:
                try:
                    self.stream.flush()
                finally:
                    self.stream.close()
                    self.stream = None

    def handleError(self, record):
        # The diagnostic log is best effort. A missing/unwritable log folder
        # must not print a second traceback or affect imaging/recovery.
        pass


def log_directory() -> Path:
    override = os.getenv('TENSHI_LOG_DIR')
    if override:
        return Path(override)
    if os.name == 'nt':
        return Path(os.getenv('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')) / 'Tenshi' / 'Logs'
    return Path(os.getenv('XDG_STATE_HOME') or (Path.home() / '.local' / 'state')) / 'tenshi' / 'logs'


def diagnostic_log_path() -> Path:
    return log_directory() / 'tenshi-errors.log'


def _configure():
    global _CONFIGURED
    destination = diagnostic_log_path()
    with _LOCK:
        if _CONFIGURED == destination and destination.is_file():
            return
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            handler = ClosingRotatingFileHandler(destination, maxBytes=1024 * 1024,
                                          backupCount=3, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            for old in list(_LOG.handlers):
                if not isinstance(old, logging.NullHandler):
                    _LOG.removeHandler(old)
                    old.close()
            _LOG.addHandler(handler)
            _LOG.setLevel(logging.INFO)
            _CONFIGURED = destination
        except OSError:
            # An invalid/unavailable destination must not leave a handler
            # pointing at a previous (possibly already deleted) test folder.
            for old in list(_LOG.handlers):
                if isinstance(old, RotatingFileHandler):
                    _LOG.removeHandler(old)
                    old.close()
            _CONFIGURED = None
            return


def log_issue(operation: str, exc: BaseException, **info) -> None:
    """Record only safe short operation names and codes, no user paths."""
    try:
        _configure()
        allowed = {'offset', 'length', 'processed', 'total', 'attempt', 'phase'}
        details = ' '.join(f'{k}={v}' for k, v in info.items()
                           if k in allowed and (type(v) in (int, bool) or
                                               (k == 'phase' and isinstance(v, str) and v.isidentifier())))
        code = getattr(exc, 'winerror', None) or getattr(exc, 'errno', None)
        # Exception.str may contain sensitive filenames; intentionally exclude.
        _LOG.error('operation=%s error=%s code=%s %s',
                   ''.join(c for c in operation[:40] if c.isalnum() or c in '_-'),
                   type(exc).__name__, code if isinstance(code, int) else '-', details)
    except Exception:
        pass


def traced(operation: str, *, ignore=()):
    """Preserve original traceback and behavior while logging failures."""
    def decorate(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ignore:
                raise
            except Exception as exc:
                log_issue(operation, exc)
                raise
        return inner
    return decorate
