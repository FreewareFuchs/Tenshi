from __future__ import annotations
import os
import ctypes
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VolumeInfo:
    path: str
    label: str
    filesystem: str
    total_bytes: int
    free_bytes: int

def list_volumes() -> list[VolumeInfo]:
    """List mounted Windows volumes via GetLogicalDrives/GetVolumeInformation."""
    if os.name != "nt":
        result = []
        for p in Path("/").iterdir():
            if p.is_dir():
                try:
                    st = os.statvfs(str(p))
                    result.append(VolumeInfo(str(p), p.name or "/", "unknown",
                                             st.f_blocks * st.f_frsize,
                                             st.f_bavail * st.f_frsize))
                except OSError:
                    pass
        return result
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
