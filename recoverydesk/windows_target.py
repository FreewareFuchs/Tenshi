"""Windows output handles with pinned parents and no reparse-point traversal.

Parents are opened from the root down and kept open without write/delete
sharing until the output closes. This prevents ordinary directory replacement
and reparse-point modification during a write. This is not a sandbox against
an administrator changing drive mappings, mounts or filesystem drivers.
"""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
import ctypes
from ctypes import wintypes
import os
from pathlib import Path

_DIRECTORY = 0x10
_REPARSE = 0x400
_OPEN_REPARSE = 0x00200000
_BACKUP = 0x02000000


class _FileInfo(ctypes.Structure):
    _fields_ = [('attributes', wintypes.DWORD),
                ('created', wintypes.FILETIME), ('accessed', wintypes.FILETIME),
                ('written', wintypes.FILETIME), ('volume', wintypes.DWORD),
                ('size_high', wintypes.DWORD), ('size_low', wintypes.DWORD),
                ('links', wintypes.DWORD), ('index_high', wintypes.DWORD),
                ('index_low', wintypes.DWORD)]


class _API:
    def __init__(self):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.create = self.kernel.CreateFileW
        self.create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE)
        self.create.restype = wintypes.HANDLE
        self.close = self.kernel.CloseHandle
        self.close.argtypes = (wintypes.HANDLE,)
        self.close.restype = wintypes.BOOL
        self.info = self.kernel.GetFileInformationByHandle
        self.info.argtypes = (wintypes.HANDLE, ctypes.POINTER(_FileInfo))
        self.info.restype = wintypes.BOOL

    def open(self, path, *, directory=False, mode='r+b'):
        # Parents need attributes only. Denying WRITE also prevents an already
        # pinned ordinary directory being changed into a reparse point in place.
        access = 0x80 if directory else (0x80010000 if mode == 'delete' else 0xC0000000)
        sharing = 1  # FILE_SHARE_READ; no write or delete sharing
        disposition = 3 if directory or mode in ('r+b','delete') else 1
        handle = self.create(str(path), access, sharing, None, disposition,
                             _OPEN_REPARSE | _BACKUP, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = _FileInfo()
            if not self.info(handle, ctypes.byref(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if info.attributes & _REPARSE:
                raise ValueError('Links und Junctions sind im Ausgabeziel nicht erlaubt.')
            if bool(info.attributes & _DIRECTORY) != directory:
                raise ValueError('Ausgabeziel hat einen unerwarteten Dateityp.')
            return handle
        except BaseException:
            self.close(handle)
            raise


@contextmanager
def open_output(path: str, mode: str, source: str):
    """Yield a CRT-backed file while every parent and the leaf remain pinned."""
    import msvcrt
    if mode not in ('xb', 'r+b'):
        raise ValueError('Ungültiger Ausgabe-Modus.')
    absolute = Path(os.path.abspath(os.fspath(path)))
    # Alternate streams and device namespace paths are not recovery outputs.
    if (not absolute.name or any(':' in p for p in absolute.parts[1:]) or
            str(absolute).startswith(('\\\\.\\', '\\\\?\\'))):
        raise ValueError('Ungültiger Windows-Ausgabepfad.')
    api = _API()
    with ExitStack() as parents:
        for parent in reversed(absolute.parents):
            handle = api.open(parent, directory=True)
            parents.callback(api.close, handle)
        # Recheck physical source/destination separation while parents are held.
        from .sources import ensure_safe_destination
        ensure_safe_destination(source, str(absolute.parent))
        handle = api.open(absolute, mode=mode)
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_BINARY | os.O_RDWR)
        except BaseException:
            api.close(handle)
            raise
        # open_osfhandle transfers ownership; fdopen must not truncate the file.
        try:
            out = os.fdopen(fd, 'r+b', buffering=0)
        except BaseException:
            os.close(fd)
            raise
        with out:
            yield out


def remove_owned_output(path, source, expected_identity, expected_payload):
    """Delete the validated opened checksum, without a close/unlink race."""
    import msvcrt
    from .secure_target import _validate_output
    absolute=Path(os.path.abspath(os.fspath(path)))
    if (not absolute.name or any(':' in p for p in absolute.parts[1:]) or
            str(absolute).startswith(('\\\\.\\','\\\\?\\'))):
        raise ValueError('Ungültiger Windows-Ausgabepfad.')
    api=_API()
    with ExitStack() as parents:
        for parent in reversed(absolute.parents):
            handle=api.open(parent,directory=True);parents.callback(api.close,handle)
        from .sources import ensure_safe_destination
        ensure_safe_destination(source,str(absolute.parent))
        handle=api.open(absolute,mode='delete')
        try:
            fd=msvcrt.open_osfhandle(handle,os.O_BINARY|os.O_RDONLY)
        except BaseException:
            api.close(handle);raise
        with os.fdopen(fd,'rb') as stream:
            _validate_output(stream.fileno(),source,expected_identity)
            if stream.read(len(expected_payload)+1)!=expected_payload:
                raise ValueError('Prüfsummendatei wurde verändert und bleibt erhalten.')
            disposition=ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO.DeleteFile
            mark=api.kernel.SetFileInformationByHandle
            mark.argtypes=(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD)
            mark.restype=wintypes.BOOL
            if not mark(msvcrt.get_osfhandle(stream.fileno()),4,ctypes.byref(disposition),ctypes.sizeof(disposition)):
                raise ctypes.WinError(ctypes.get_last_error())
