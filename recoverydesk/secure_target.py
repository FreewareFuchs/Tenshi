"""Linux destination handles anchored to a verified directory.

Do not trust an earlier realpath check after another process may have
exchanged a directory or symlink. Every write-open resolves the leaf beneath
an opened parent directory descriptor, rejects links and special files, and
verifies the *opened parent's* physical backing against a block-device source.

The Windows branch preserves the established path-based behavior.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import stat
import sys


def _linux() -> bool:
    return sys.platform.startswith('linux')


@contextmanager
def secure_parent(path: str, source: str):
    """Yield the verified Linux parent directory fd, or None on Windows."""
    if not _linux():
        yield None
        return
    absolute = os.path.abspath(os.fspath(path))
    parent = os.path.dirname(absolute)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(parent, flags)
    try:
        meta = os.fstat(fd)
        if not stat.S_ISDIR(meta.st_mode):
            raise ValueError('Ausgabeordner ist kein reguläres Verzeichnis.')
        from .linux_devices import block_path, _backing_disks
        if block_path(source):
            source_roots = _backing_disks(os.stat(source).st_rdev)
            target_roots = _backing_disks(meta.st_dev)
            if not source_roots or not target_roots:
                raise ValueError('Quell-/Zielzuordnung nicht eindeutig.')
            if source_roots & target_roots:
                raise ValueError('Ziel befindet sich auf demselben physischen Datenträger wie die Quelle.')
        yield fd
    finally:
        os.close(fd)


@contextmanager
def open_regular_output(path: str, mode: str, source: str, *,
                        expected_identity: tuple[int, int] | None = None):
    """Pin a regular output inode, never follow a final-component symlink.

    mode: xb (exclusive new regular file) or r+b (existing regular file).
    No O_TRUNC and no write to block/character devices, sockets or FIFOs.
    """
    if mode not in ('xb', 'r+b'):
        raise ValueError('Ungültiger Ausgabe-Modus.')
    if not _linux():
        with open(path, mode, buffering=0) as out:
            yield out
        return
    with secure_parent(path, source) as parent_fd:
        name = os.path.basename(os.path.abspath(os.fspath(path)))
        flags = (os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK |
                 (os.O_WRONLY | os.O_CREAT | os.O_EXCL if mode == 'xb' else os.O_RDWR))
        fd = os.open(name, flags, 0o600, dir_fd=parent_fd)
        try:
            identity = os.fstat(fd)
            if not stat.S_ISREG(identity.st_mode):
                raise ValueError('Nur reguläre Image-/Exportdateien sind als Ziel erlaubt.')
            actual = (identity.st_dev, identity.st_ino)
            if expected_identity is not None and actual != expected_identity:
                raise ValueError('Zieldatei wurde seit der Erstellung ausgetauscht.')
            from .sources import is_device_source
            if not is_device_source(source):
                source_meta = os.stat(source)
                if (source_meta.st_dev, source_meta.st_ino) == actual:
                    raise ValueError('Quelle und Ziel dürfen nicht dieselbe Datei sein.')
            with os.fdopen(fd, mode.replace('x', 'w'), buffering=0) as out:
                fd = -1
                yield out
        finally:
            if fd >= 0:
                os.close(fd)


def mkdir_checked(path: str, source: str) -> None:
    """Create one directory under a verified parent descriptor on Linux."""
    if not _linux():
        os.mkdir(path)
        return
    with secure_parent(path, source) as parent_fd:
        os.mkdir(os.path.basename(os.path.abspath(path)), dir_fd=parent_fd)
