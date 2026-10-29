"""Linux destination handles anchored to a verified directory.

Do not trust an earlier realpath check after another process may have
exchanged a directory or symlink. Every write-open resolves the leaf beneath
an opened parent directory descriptor, rejects links and special files, and
verifies the *opened parent's* physical backing against a block-device source.

Windows pins each parent without write/delete sharing, opens the final file
without following reparse points and checks its identity before yielding it.
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


def _validate_output(fd: int, source: str,
                     expected_identity: tuple[int, int] | None) -> None:
    """Validate the actual opened file before callers can write or truncate it."""
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
        if sys.platform == 'win32':
            from .windows_target import open_output
            opener = open_output(path, mode, source)
        else:
            opener = open(path, mode, buffering=0)
        with opener as out:
            _validate_output(out.fileno(), source, expected_identity)
            yield out
        return
    with secure_parent(path, source) as parent_fd:
        name = os.path.basename(os.path.abspath(os.fspath(path)))
        flags = (os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK |
                 (os.O_WRONLY | os.O_CREAT | os.O_EXCL if mode == 'xb' else os.O_RDWR))
        fd = os.open(name, flags, 0o600, dir_fd=parent_fd)
        try:
            _validate_output(fd, source, expected_identity)
            with os.fdopen(fd, mode.replace('x', 'w'), buffering=0) as out:
                fd = -1
                yield out
        finally:
            if fd >= 0:
                os.close(fd)


@contextmanager
def open_regular_input(path: str, source: str):
    """Read a regular metadata file under a verified Linux parent descriptor.

    A replaced parent or final symlink cannot redirect the open to a new inode.
    This is intended for untrusted existing recovery manifests.
    """
    if not _linux():
        with open(path, 'rb') as src:
            yield src
        return
    with secure_parent(path, source) as parent_fd:
        name = os.path.basename(os.path.abspath(os.fspath(path)))
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                     os.O_CLOEXEC, dir_fd=parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Nur reguläre Statusdateien dürfen eingelesen werden.')
            with os.fdopen(fd, 'rb') as src:
                fd = -1
                yield src
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


def remove_owned_output(path, source, expected_identity, expected_payload):
    """Remove only an unchanged, identity-checked regular metadata file."""
    if sys.platform=='win32':
        from .windows_target import remove_owned_output as remove
        return remove(path,source,expected_identity,expected_payload)
    if not _linux():
        raise ValueError('Sichere Prüfsummenbereinigung ist auf diesem System nicht verfügbar.')
    with secure_parent(path,source) as parent_fd:
        name=os.path.basename(os.path.abspath(path))
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parent_fd)
        with os.fdopen(fd,'rb') as stream:
            _validate_output(stream.fileno(),source,expected_identity)
            if stream.read(len(expected_payload)+1)!=expected_payload:
                raise ValueError('Prüfsummendatei wurde verändert und bleibt erhalten.')
            named=os.stat(name,dir_fd=parent_fd,follow_symlinks=False)
            if (named.st_dev,named.st_ino)!=expected_identity or not stat.S_ISREG(named.st_mode):
                raise ValueError('Prüfsummendatei wurde ausgetauscht und bleibt erhalten.')
            os.unlink(name,dir_fd=parent_fd)
            os.fsync(parent_fd)

def atomic_bytes_checkpoint(path: str, payload: bytes, source: str) -> None:
    """Atomically persist bytes relative to a physically verified Linux dirfd.

    A swapped parent pathname cannot redirect the rename outside the opened
    directory. An existing symlink or special-file target is not replaced.
    """
    if not _linux():
        raise ValueError('Linux-spezifische Prüfpunktfunktion.')
    import secrets

    if not isinstance(payload, bytes):
        raise TypeError('Statusdaten müssen Bytes sein.')
    target = os.path.basename(os.path.abspath(path))
    with secure_parent(path, source) as parent_fd:
        temp_name = '.tenshi-checkpoint-' + secrets.token_hex(16) + '.tmp'
        temporary = False
        try:
            fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
            temporary = True
            with os.fdopen(fd, 'wb') as out:
                out.write(payload)
                out.flush()
                os.fsync(out.fileno())
            from .resilience import RETRY_DELAYS, is_transient_lock
            import time
            for delay in (*RETRY_DELAYS, None):
                try:
                    prior = os.stat(target, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    if not stat.S_ISREG(prior.st_mode):
                        raise ValueError('Status- oder Berichtsziel wurde auf einen Link oder ein Gerät umgeleitet.')
                try:
                    os.replace(temp_name, target, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                    break
                except OSError as exc:
                    if delay is None or not is_transient_lock(exc):
                        raise
                    time.sleep(delay)
            temporary = False
            os.fsync(parent_fd)
        finally:
            if temporary:
                os.unlink(temp_name, dir_fd=parent_fd)


def atomic_json_checkpoint(path: str, state: dict, source: str) -> None:
    """Atomically persist an imaging/export manifest in its pinned parent."""
    import json
    payload = (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    atomic_bytes_checkpoint(path, payload, source)
