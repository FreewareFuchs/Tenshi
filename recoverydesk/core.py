from __future__ import annotations
import os
import ctypes
import json
import subprocess
from dataclasses import dataclass


@dataclass
class VolumeInfo:
    path: str
    label: str
    filesystem: str
    total_bytes: int
    free_bytes: int

def _linux_volumes() -> list[VolumeInfo]:
    """Discover mounted Linux block volumes through read-only lsblk metadata.

    Listing a mount point does not open the device. Selecting it later opens
    its underlying block path via sources.open_source() in read-only mode.
    """
    from .linux_devices import block_path
    command = ['lsblk', '--json', '--bytes', '--output',
               'PATH,TYPE,LABEL,FSTYPE,SIZE,MOUNTPOINTS']
    completed = subprocess.run(command, capture_output=True, text=True,
                               check=True, timeout=8)
    if len(completed.stdout) > 4 * 1024 * 1024:
        raise OSError('Zu viele Linux-Laufwerksmetadaten.')
    records = json.loads(completed.stdout).get('blockdevices', [])
    if not isinstance(records, list):
        raise ValueError('Ungültige Linux-Geräteliste.')
    result = []
    seen = set()

    def visit(items, depth=0):
        if depth > 12:
            raise ValueError('Zu tief verschachtelte Linux-Geräteliste.')
        for item in items:
            if not isinstance(item, dict):
                continue
            path = item.get('path')
            device_type = item.get('type')
            fs_type = item.get('fstype')
            mounts = item.get('mountpoints')
            size = item.get('size')
            if (device_type in ('part', 'crypt', 'lvm') and
                    isinstance(path, str) and path not in seen and
                    isinstance(fs_type, str) and fs_type and
                    type(size) is int and size >= 512 and
                    isinstance(mounts, list) and block_path(path)):
                mount = next((m for m in mounts if isinstance(m, str) and
                              m.startswith('/') and os.path.isdir(m)), None)
                if mount is not None:
                    seen.add(path)
                    try:
                        stat = os.statvfs(mount)
                        free = stat.f_bavail * stat.f_frsize
                    except OSError:
                        free = 0
                    label = item.get('label')
                    if not isinstance(label, str) or not label:
                        label = mount
                    result.append(VolumeInfo(path, label, fs_type, size, free))
            children = item.get('children', [])
            if isinstance(children, list):
                visit(children, depth + 1)
    visit(records)
    return result


def list_volumes() -> list[VolumeInfo]:
    """List Windows drive letters or mounted Linux block volumes, metadata only."""
    if os.name != "nt":
        return _linux_volumes()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    mask = kernel32.GetLogicalDrives()
    volumes = []
    for i in range(26):
        if mask & (1 << i):
            root = f"{chr(65+i)}:\\"
            label_buf = ctypes.create_unicode_buffer(261)
            fs_buf = ctypes.create_unicode_buffer(261)
            serial = ctypes.c_ulong()
            max_comp = ctypes.c_ulong()
            flags = ctypes.c_ulong()
            ok = kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root), label_buf, len(label_buf),
                ctypes.byref(serial), ctypes.byref(max_comp), ctypes.byref(flags),
                fs_buf, len(fs_buf))
            total = ctypes.c_ulonglong()
            free = ctypes.c_ulonglong()
            kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(root), None,
                                         ctypes.byref(total), ctypes.byref(free))
            volumes.append(VolumeInfo(root, label_buf.value if ok else "",
                                      fs_buf.value if ok else "unknown",
                                      total.value, free.value))
    return volumes
