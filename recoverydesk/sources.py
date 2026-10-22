"""Read-only source abstraction for image files and opted-in Windows physical disks.

No device write handles, locking, dismount, or filesystem repairs are performed.
"""
from __future__ import annotations
import ctypes
import errno
import os
import re
from contextlib import contextmanager
from ctypes import wintypes
from .diagnostics import log_issue
import sys
from .linux_devices import block_path, block_info, list_block_sources, ensure_separate_device

_DRIVE = re.compile(r'^\\\\\.\\PhysicalDrive(0|[1-9][0-9]{0,2})$', re.IGNORECASE)
_VOLUME = re.compile(_DRIVE.pattern.replace("PhysicalDrive(0|[1-9][0-9]{0,2})", "([A-Z]):"), re.IGNORECASE)
_IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
_IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x00070000
_IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = 0x000700A0
_IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = 0x00560000


def physical_number(path: str) -> int | None:
    m = _DRIVE.fullmatch(path)
    return int(m.group(1)) if m else None


def is_physical(path: str) -> bool:
    return physical_number(path) is not None


def volume_letter(path: str) -> str | None:
    """Return the drive letter for a Windows raw-volume source."""
    match = _VOLUME.fullmatch(path)
    return match.group(1).upper() if match else None


def is_volume(path: str) -> bool:
    return volume_letter(path) is not None


def is_device_source(path: str) -> bool:
    return is_physical(path) or is_volume(path) or (sys.platform.startswith('linux') and block_path(path))


def raw_volume_path(root: str) -> str:
    """Allow only drive-root selections, not arbitrary relative Windows paths."""
    if not re.fullmatch(r'[A-Za-z]:\\', root):
        raise ValueError('Ungültiger Windows-Laufwerksbuchstabe.')
    return '\\\\.\\' + root[:2].upper()


def validate_source(path: str) -> str:
    if not path:
        raise ValueError('Bitte eine Quelldatei oder einen Datenträger auswählen.')
    if sys.platform.startswith('linux') and block_path(path):
        return path
    if is_device_source(path):
        if os.name != 'nt':
            raise ValueError('Physische Windows-Laufwerke sind nur auf Windows verfügbar.')
        return path
    if not os.path.isfile(path):
        raise ValueError('Die Quelle muss eine vorhandene RAW-Image-Datei sein.')
    return path


def _kernel():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k.CreateFileW.restype = wintypes.HANDLE
    k.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                  wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    k.DeviceIoControl.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    return k


def _device_ioctl(path: str, code: int, length: int = 16) -> bytes:
    if os.name != 'nt':
        raise OSError('Nur auf Windows verfügbar.')
    kernel = _kernel()
    # GENERIC_READ, FILE_SHARE_READ|FILE_SHARE_WRITE, OPEN_EXISTING
    h = kernel.CreateFileW(path, 0x80000000, 0x1 | 0x2, None, 3, 0, None)
    if h == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        output = ctypes.create_string_buffer(length)
        returned = wintypes.DWORD()
        if not kernel.DeviceIoControl(h, code, None, 0, output, length, ctypes.byref(returned), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return output.raw[:returned.value]
    finally:
        kernel.CloseHandle(h)


def source_size(path: str) -> int:
    validate_source(path)
    if sys.platform.startswith('linux') and block_path(path):
        return block_info(path)[0]
    if is_device_source(path):
        data = _device_ioctl(path, _IOCTL_DISK_GET_LENGTH_INFO, 8)
        if len(data) != 8:
            raise OSError('Die physische Datenträgergröße konnte nicht ermittelt werden.')
        return int.from_bytes(data, 'little')
    return os.path.getsize(path)


def physical_sector_size(path: str) -> int:
    """Windows DISK_GEOMETRY.BytesPerSector, not guessed from partition metadata.

    When inaccessible, use conservative 4096-byte requests (aligned for both
    standard 512-byte and 4096-byte logical sectors). Read-only IOCTLs only.
    """
    if sys.platform.startswith('linux') and block_path(path):
        return block_info(path)[1]
    if not is_device_source(path) or os.name != 'nt':
        raise ValueError('Nur für Windows-Rohdatenträger und Laufwerke.')
    for code, length in ((_IOCTL_DISK_GET_DRIVE_GEOMETRY_EX, 64),
                         (_IOCTL_DISK_GET_DRIVE_GEOMETRY, 24)):
        try:
            data = _device_ioctl(path, code, length)
            if len(data) >= 24:
                sector = int.from_bytes(data[20:24], 'little')
                if sector in (512, 1024, 2048, 4096, 8192):
                    return sector
        except OSError:
            pass
    return 4096


class AlignedDeviceReader:
    """Read-only, sector-aligned adapter for Windows PhysicalDrive handles.

    The parsers call seek/read at arbitrary byte positions (including 11-byte
    signatures). Raw Windows devices can reject these unaligned reads with
    [Errno 22]. This wrapper performs *only aligned underlying requests* and
    slices the in-memory result. Unlike a normal file, no write API is exposed.
    """
    def __init__(self, raw, size: int, sector_size: int, cache_bytes: int = 4096):
        if sector_size <= 0 or sector_size & (sector_size - 1):
            raise ValueError('Ungültige logische Sektorgröße.')
        if size < 0:
            raise ValueError('Ungültige Laufwerksgröße.')
        self._raw = raw
        self._size = size
        self._sector = sector_size
        self._position = 0
        self._cache_offset = -1
        self._cache = b''
        # Restrict read-ahead on fragile USB disks: a metadata lookup for one
        # sector must not unnecessarily fetch dozens of adjacent sectors.
        # Larger reads are split into bounded 256 KiB device requests.
        self._max_request = 256 * 1024
        self._cache_bytes = min(self._max_request, max(
            sector_size, ((cache_bytes + sector_size - 1) // sector_size) * sector_size))

    @property
    def closed(self):
        return self._raw.closed

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return True

    def tell(self):
        return self._position

    def seek(self, offset: int, whence: int = 0):
        if whence == 0:
            target = offset
        elif whence == 1:
            target = self._position + offset
        elif whence == 2:
            target = self._size + offset
        else:
            raise ValueError('Ungültiger seek-Modus.')
        if target < 0:
            raise ValueError('Negativer Dateioffset.')
        self._position = target
        return target

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            raise ValueError('Auf physischen Datenträgern ist eine begrenzte Leselänge erforderlich.')
        if not size or self._position >= self._size:
            return b''
        size = min(size, self._size - self._position)
        chunks = []
        remaining = size
        while remaining:
            cached_start = self._cache_offset
            cached_end = cached_start + len(self._cache)
            if cached_start <= self._position < cached_end:
                n = min(remaining, cached_end - self._position)
                at = self._position - cached_start
                chunks.append(self._cache[at:at+n])
                self._position += n
                remaining -= n
                continue
            aligned_start = self._position - (self._position % self._sector)
            initial = self._position - aligned_start
            request = max(self._cache_bytes, initial + min(remaining, self._max_request - initial))
            request = ((request + self._sector - 1) // self._sector) * self._sector
            # Never read beyond the physical end of the disk. All hardware
            # requests must contain whole sectors.
            available = self._size - aligned_start
            request = min(request, available - (available % self._sector))
            if request <= initial:
                raise OSError('Letzter Datenträgerbereich nicht sektorausgerichtet; '
                              'logische Sektorgröße konnte nicht sicher bestimmt werden.')
            try:
                self._raw.seek(aligned_start, 0)
                block = self._raw.read(request)
            except OSError as exc:
                win_code = getattr(exc, 'winerror', None)
                if getattr(exc, 'errno', None) == errno.EINVAL or win_code == 87:
                    log_issue('raw_device_alignment', exc, offset=aligned_start, length=request)
                    raise OSError(errno.EINVAL,
                                  'Windows hat einen physikalischen Leseauftrag abgelehnt: nicht ausgerichteter oder ungueltiger '
                                  'Leseauftrag abgelehnt (Fehler 87/22). Logische '
                                  'Sektorgroesse pruefen; alternativ ein RAW-Image nutzen.') from exc
                if win_code in (21, 31, 55, 433, 1167):
                    log_issue('raw_device_disconnected', exc, offset=aligned_start, length=request)
                    raise OSError(errno.ENODEV,
                                  'Das USB-/Quelllaufwerk ist nicht mehr erreichbar oder '
                                  'nicht bereit. Kabel/Stromversorgung pruefen und '
                                  'Imaging erst mit derselben identifizierten Quelle fortsetzen.') from exc
                if isinstance(exc, PermissionError) or win_code in (5, 32, 33):
                    log_issue('raw_device_access_denied', exc, offset=aligned_start, length=request)
                    raise PermissionError(errno.EACCES,
                                          'Der schreibgeschuetzte Lesezugriff wurde von '
                                          'Windows verweigert. Administratorrechte, '
                                          'Freigaben und Sicherheitssoftware pruefen.') from exc
                # Preserve genuine CRC / hardware-I/O exceptions (WinError
                # 23/1117 or EIO): imaging may isolate their faulty sectors.
                log_issue('raw_device_read', exc, offset=aligned_start, length=request)
                raise
            if len(block) != request:
                # Never mistake an unexpected short USB/device read for EOF:
                # that could make metadata look valid but truncated. In
                # particular do not convert it to an imaging zero-filled bad
                # sector unless a real hardware media error was reported.
                error = OSError(errno.EINVAL,
                                'Quelllaufwerk hat einen unvollstaendigen '
                                'Sektor-Leseblock geliefert; Verbindung pruefen. '
                                'Vorgang aus Sicherheitsgruenden abgebrochen.')
                log_issue('raw_device_short_read', error,
                          offset=aligned_start, length=request)
                raise error
            self._cache_offset = aligned_start
            self._cache = block
        return b''.join(chunks)


@contextmanager
def open_source(path: str):
    validate_source(path)
    # Strictly rb; never r+, ab, wb or write-enabled CreateFile.
    try:
        raw = open(path, 'rb', buffering=0)
    except PermissionError as exc:
        if not is_device_source(path):
            raise
        log_issue('raw_device_open', exc)
        raise PermissionError('Der Datenträger kann nicht schreibgeschützt geöffnet werden. '
                              'Bitte Windows-Administratorrechte, Freigabe und '
                              'Gerätezugriff prüfen.') from exc
    try:
        if is_device_source(path):
            yield AlignedDeviceReader(raw, source_size(path), physical_sector_size(path))
        else:
            yield raw
    finally:
        raw.close()


def list_physical_sources(max_index: int = 32) -> list[tuple[str, int]]:
    if sys.platform.startswith('linux'):
        return list_block_sources()
    if os.name != 'nt':
        return []
    results = []
    for i in range(max_index):
        path = rf'\\.\PhysicalDrive{i}'
        try:
            size = source_size(path)
            if size >= 512:
                results.append((path, size))
        except OSError:
            continue
    return results


def volume_disk_numbers(source: str) -> set[int] | None:
    """Get every backing physical disk for a raw Windows volume. Fail closed."""
    if os.name != 'nt' or not is_volume(source):
        return None
    try:
        blob = _device_ioctl(source, _IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS, 65536)
        if len(blob) < 8:
            return None
        count = int.from_bytes(blob[:4], 'little')
        if count < 1 or count > 2500 or len(blob) < 8 + count * 24:
            return None
        return {int.from_bytes(blob[8 + 24*i:12 + 24*i], 'little') for i in range(count)}
    except OSError:
        return None


def disk_numbers_of_destination(destination: str) -> set[int] | None:
    """Read ALL Windows volume disk extents, never just a spanned volume's first disk.

    Special cases (UNC, folder-mounted volumes, inaccessible extents) are
    intentionally rejected: a false negative is safer than writing to source.
    """
    if os.name != 'nt':
        return None
    existing = destination if os.path.isdir(destination) else os.path.dirname(os.path.abspath(destination))
    drive = os.path.splitdrive(os.path.abspath(existing))[0]
    if not re.fullmatch(r'[A-Za-z]:', drive):
        return None
    # A folder-mounted volume can reside on another physical drive than C:.
    # We only allow a plain drive-root destination for verifiable mappings.
    kernel = _kernel()
    kernel.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumePathNameW.restype = wintypes.BOOL
    root_buf = ctypes.create_unicode_buffer(1024)
    if not kernel.GetVolumePathNameW(existing, root_buf, len(root_buf)):
        return None
    if os.path.normcase(root_buf.value.rstrip('\\')) != os.path.normcase(drive):
        return None
    return volume_disk_numbers('\\\\.\\' + drive)


def ensure_safe_destination(source: str, destination: str):
    """Fail closed for disk-backed sources when destination disk cannot be verified."""
    if os.path.realpath(source).casefold() == os.path.realpath(destination).casefold():
        raise ValueError('Quelle und Ziel dürfen nicht identisch sein.')
    if is_device_source(source):
        if sys.platform.startswith('linux') and block_path(source):
            ensure_separate_device(source, destination)
            return
        src_disks = ({physical_number(source)} if is_physical(source)
                     else volume_disk_numbers(source))
        dest_disks = disk_numbers_of_destination(destination)
        if not src_disks or not dest_disks:
            raise ValueError('Quell- oder Zieldatenträger kann nicht sicher zugeordnet werden. '
                             'Export nur auf ein eindeutig anderes physisches Laufwerk möglich.')
        if src_disks & dest_disks:
            raise ValueError('Export auf denselben physischen Datenträger wird verhindert. '
                             'Bitte eine andere Festplatte/SSD als Ziel wählen.')
