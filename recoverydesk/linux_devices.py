"""Linux block-device discovery and fail-closed source/destination separation.

Only metadata from sysfs and read-only ioctl calls is used here. No mount,
filesystem repair, or write-enabled handle is created.
"""
from __future__ import annotations
import os
from pathlib import Path
import stat
import struct

BLKGETSIZE64 = 0x80081272
BLKSSZGET = 0x1268


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
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        size = struct.unpack('Q', fcntl.ioctl(fd, BLKGETSIZE64, bytes(8)))[0]
        sector = struct.unpack('I', fcntl.ioctl(fd, BLKSSZGET, bytes(4)))[0]
        if size < 512 or sector not in (512, 1024, 2048, 4096, 8192, 16384):
            raise OSError('Nicht unterstützte Datenträgergeometrie.')
        return size, sector
    finally:
        os.close(fd)


def list_block_sources() -> list[tuple[str, int]]:
    result = []
    for entry in sorted(Path('/sys/class/block').iterdir()):
        # Only whole disks. Individual partitions may be supplied explicitly.
        if (entry / 'partition').exists():
            continue
        path = '/dev/' + entry.name
        try:
            size, _ = block_info(path)
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
    parent = os.path.realpath(destination)
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
