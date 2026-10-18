"""Durable, bounded, atomic checkpoint updates for user-selected export folders.

The source disk is never opened for writing. Checkpoint writers use unique
same-directory temporary files and a bounded retry for Windows sharing locks.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Mapping, Callable

RETRY_DELAYS = (0.05, 0.15, 0.35, 0.7)


def is_transient_lock(exc: OSError) -> bool:
    return isinstance(exc, PermissionError) or getattr(exc, 'winerror', None) in (5, 32, 33)


def atomic_replace_json(path: str | Path, data: Mapping, *,
                        replace: Callable | None = None,
                        sleep: Callable = time.sleep) -> None:
    """Persist JSON with fsync then replace, retry transient Windows locks.

    Does not overwrite a pre-existing .tmp, doesn't discard the previous
    checkpoint if the replace fails, and never writes to the source device.
    """
    replace = replace or os.replace
    target = Path(path)
    if target.is_symlink():
        raise ValueError('Symbolische Links sind keine gültigen Statusdateien.')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                prefix='.tenshi-checkpoint-', suffix='.tmp',
                dir=target.parent, delete=False) as fh:
            tmp = Path(fh.name)
            json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        for delay in (*RETRY_DELAYS, None):
            try:
                if target.is_symlink():
                    raise ValueError('Statusdatei wurde auf einen Link umgeleitet.')
                replace(str(tmp), str(target))
                tmp = None
                return
            except OSError as exc:
                if delay is None or not is_transient_lock(exc):
                    raise
                sleep(delay)
    finally:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
