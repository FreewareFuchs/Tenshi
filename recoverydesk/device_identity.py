"""Bounded read-only device consistency checks; not proof of media/content identity."""
import hashlib
import os
from pathlib import Path
import struct
import sys

from .sources import is_device_source, source_size, physical_sector_size, open_source, _device_ioctl


class DeviceSourceChanged(OSError):
    pass


def windows_serial(path):
    # STORAGE_PROPERTY_QUERY: StorageDeviceProperty / PropertyStandardQuery,
    # including AdditionalParameters[1] and structure padding.
    try:
        raw = _device_ioctl(path, 0x002D1400, 4096, bytes(12))
    except OSError:
        return None
    if len(raw) < 36:
        return None
    size = struct.unpack_from('<I', raw, 4)[0]
    offset = struct.unpack_from('<I', raw, 24)[0]
    if not 36 <= offset < min(size, len(raw)):
        return None
    end = raw.find(b'\0', offset, min(size, len(raw)))
    if end < 0:
        return None
    serial = raw[offset:end].strip()
    return hashlib.sha256(serial).hexdigest() if serial else None


def linux_identity(path):
    st = os.stat(path)
    node = Path(f'/sys/dev/block/{os.major(st.st_rdev)}:{os.minor(st.st_rdev)}').resolve()
    if (node / 'partition').exists():
        node = node.parent
    values = {'device_number': st.st_rdev}
    for key in ('diskseq', 'device/serial', 'wwid'):
        try:
            with (node / key).open('rb') as stream:
                value = stream.read(1024).strip()
            if value:
                values[key] = hashlib.sha256(value).hexdigest()
        except OSError:
            pass
    return values


def _volume_id(boot):
    # Compare only stable on-disk IDs, not live counters or allocation metadata.
    if len(boot) != 512 or boot[510:512] != b'\x55\xaa':
        return None
    if boot[3:11] == b'NTFS    ':
        return 'NTFS:' + boot[72:80].hex()
    if boot[3:11] == b'EXFAT   ':
        return 'exFAT:' + boot[100:104].hex()
    if boot[82:90] == b'FAT32   ':
        return 'FAT32:' + boot[67:71].hex()
    return None


def capture_device_identity(source, offset=0):
    if not is_device_source(source):
        return None
    identity = {'size': source_size(source), 'sector_size': physical_sector_size(source),
                'offset': offset}
    if sys.platform.startswith('linux') and source.startswith('/dev/'):
        identity['hardware'] = linux_identity(source)
    elif os.name == 'nt':
        identity['serial_sha256'] = windows_serial(source)
    with open_source(source) as stream:
        volumes = []
        for position in sorted({0, offset}):
            stream.seek(position)
            boot = stream.read(512)
            if len(boot) != 512:
                raise OSError('Datenträgerkennung konnte nicht vollständig gelesen werden.')
            volumes.append([position, _volume_id(boot)])
        identity['volume_ids'] = volumes
    return identity


def check_device_identity(source, expected):
    if expected is None:
        return
    try:
        actual = capture_device_identity(source, expected['offset'])
    except (OSError, ValueError) as exc:
        raise DeviceSourceChanged('Quelle nicht mehr erreichbar. Datenträger erneut einlesen.') from exc
    if actual != expected:
        raise DeviceSourceChanged('Datenträger wurde ausgetauscht oder geändert. Quelle erneut einlesen.')
