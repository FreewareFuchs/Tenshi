"""Linux block-device discovery and fail-closed source/destination separation.

Only metadata from sysfs and read-only ioctl calls is used here. No mount,
filesystem repair, or write-enabled handle is created.
"""
from __future__ import annotations
import errno
import os
from pathlib import Path
import stat
import struct

BLKGETSIZE64 = 0x80081272
BLKSSZGET = 0x1268


ACCESS_HEADER = 'Linux-Datenträger: Leseberechtigung fehlt.'
ACCESS_HINT = 'Geräteberechtigungen durch die Systemverwaltung gezielt für dieses Gerät prüfen lassen; nur Lesezugriff wird benötigt.'
ACCESS_ALTERNATIVE = 'Alternativ ein vorhandenes Image öffnen. Danach die Quelle erneut auswählen. Tenshi ohne sudo starten.'
ACCESS_UNCHANGED = 'Tenshi ändert keine Geräteberechtigungen.'


def device_access_details(path: str, *, sysfs_root: Path = Path('/sys/dev/block')) -> dict:
    """Read only device-node metadata and bounded sysfs text, never disk contents."""
    details = {'path': path}
    try:
        node_stat = os.stat(path)
        if not stat.S_ISBLK(node_stat.st_mode):
            return details
        key = f'{os.major(node_stat.st_rdev)}:{os.minor(node_stat.st_rdev)}'
        details['address'] = key
        node = (sysfs_root / key).resolve(strict=True)
        def text(file):
            try:
                with file.open('r', encoding='utf-8', errors='replace') as stream:
                    return ' '.join(stream.read(256).split())
            except OSError:
                return ''
        sectors = text(node / 'size')
        if sectors.isdecimal() and 0 < int(sectors) * 512 < 2 ** 63:
            details['size_bytes'] = int(sectors) * 512
        model_node = node.parent if (node / 'partition').exists() else node
        model = text(model_node / 'device/model')
        if model:
            details['model'] = model
    except (OSError, ValueError, RuntimeError):
        pass  # Missing/hot-unplugged metadata must not hide the access error.
    return details


class LinuxReadAccessError(PermissionError):
    def __init__(self, path: str):
        details = device_access_details(path)
        lines = [ACCESS_HEADER, '', 'Gerät:', path]
        if 'address' in details:
            lines += ['Gerätekennung (Major:Minor):', details['address']]
        if 'model' in details:
            lines += ['Modell:', details['model']]
        if 'size_bytes' in details:
            lines += ['Gerätegröße (Bytes):', str(details['size_bytes'])]
        lines += ['', ACCESS_HINT, ACCESS_ALTERNATIVE, ACCESS_UNCHANGED]
        super().__init__(errno.EACCES, '\n'.join(lines), path)

    def __str__(self):
        # Whole-line UI translation must not be obscured by an [Errno 13] prefix.
        return self.strerror


def block_path(path: str) -> bool:
    if not isinstance(path, str) or not path.startswith('/dev/'):
        return False
    try:
        return stat.S_ISBLK(os.stat(path).st_mode)
    except OSError:
        return False


def block_info(path: str) -> tuple[int, int]:
    import fcntl
    if not block_path(path):
        raise ValueError('Kein Linux-Blockgerät.')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
    except PermissionError as exc:
        raise LinuxReadAccessError(path) from exc
    try:
        size = struct.unpack('Q', fcntl.ioctl(fd, BLKGETSIZE64, bytes(8)))[0]
        sector = struct.unpack('I', fcntl.ioctl(fd, BLKSSZGET, bytes(4)))[0]
        if size < 512 or sector not in (512, 1024, 2048, 4096, 8192, 16384):
            raise OSError('Nicht unterstützte Datenträgergeometrie.')
        return size, sector
    finally:
        os.close(fd)


def list_block_sources() -> list[tuple[str, int]]:
    """List whole disks from sysfs without opening any physical source.

    The kernel's sysfs size is expressed in units of 512 bytes, regardless
    of the physical/logical sector size. Opening a chosen device and querying
    its actual geometry remains a separate read-only operation, which may
    fail for an unprivileged user.
    """
    result = []
    try:
        entries = sorted(Path('/sys/class/block').iterdir())
    except OSError:
        return result
    for entry in entries:
        if (entry / 'partition').exists():
            continue
        path = '/dev/' + entry.name
        try:
            if not block_path(path):
                continue
            raw_size = (entry / 'size').read_text(encoding='ascii').strip()
            if not raw_size.isdecimal():
                continue
            size = int(raw_size) * 512
            if not (512 <= size < 2 ** 63):
                continue
            result.append((path, size))
        except (OSError, ValueError):
            continue
    return result


def _backing_disks(dev: int, seen=None) -> set[str]:
    """Resolve stacked devices and partitions to physical disk sysfs names."""
    seen = set() if seen is None else seen
    key = f'{os.major(dev)}:{os.minor(dev)}'
    if key in seen:
        raise ValueError('Zyklische Blockgerätezuordnung.')
    seen.add(key)
    node = Path('/sys/dev/block') / key
    if not node.exists():
        raise ValueError('Blockgerät ist in sysfs nicht auflösbar.')
    node = node.resolve(strict=True)
    slaves = node / 'slaves'
    if slaves.is_dir() and any(slaves.iterdir()):
        roots = set()
        for slave in slaves.iterdir():
            roots |= _backing_disks(os.stat('/dev/' + slave.name).st_rdev, seen.copy())
        return roots
    if (node / 'partition').exists():
        node = node.parent
    # Unknown virtual/loop devices cannot certify separate physical media.
    if not (node / 'device').exists():
        raise ValueError('Virtueller Datenträger ohne nachweisbares physisches Ziel.')
    return {str(node.resolve())}


def ensure_separate_device(source: str, destination: str):
    if not block_path(source):
        raise ValueError('Ungültiger Linux-Quelldatenträger.')
    # Never treat a raw /dev node, including a symlink to one, as a regular
    # output destination. This check does not open or write the device.
    resolved_destination = os.path.realpath(destination)
    if resolved_destination.startswith('/dev/') and block_path(resolved_destination):
        raise ValueError('Linux-Blockgerät darf niemals als Ausgabeziel verwendet werden.')
    parent = resolved_destination
    while not os.path.exists(parent):
        ancestor = os.path.dirname(parent)
        if ancestor == parent:
            raise ValueError('Zielpfad nicht auflösbar.')
        parent = ancestor
    if not os.path.isdir(parent):
        parent = os.path.dirname(parent)
    source_roots = _backing_disks(os.stat(source).st_rdev)
    target_roots = _backing_disks(os.stat(parent).st_dev)
    if source_roots & target_roots:
        raise ValueError('Ziel befindet sich auf demselben physischen Datenträger wie die Quelle.')
