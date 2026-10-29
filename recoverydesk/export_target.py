"""Read-only destination capacity hints; no probe writes or raw device access."""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import os
import posixpath
from pathlib import Path
import re
import shutil
import sys

from .export_queue import readable_bytes
from .i18n import translate

FAT_MAX_FILE = 2**32 - 1


class TargetReviewDeclined(Exception):
    """The user cancelled before any export target changes."""


def _windows_filesystem(path):
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetVolumePathNameW.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
    kernel.GetVolumePathNameW.restype = wintypes.BOOL
    root = ctypes.create_unicode_buffer(32768)
    if not kernel.GetVolumePathNameW(path, root, len(root)):
        raise ctypes.WinError(ctypes.get_last_error())
    kernel.GetVolumeInformationW.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD)
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    name = ctypes.create_unicode_buffer(261)
    if not kernel.GetVolumeInformationW(root.value, None, 0, None, None, None, name, len(name)):
        raise ctypes.WinError(ctypes.get_last_error())
    return name.value or None


def _mount_filesystem(path, device, text):
    """Use this process's mount namespace, component boundaries and st_dev."""
    candidates = []
    for line in text.splitlines():
        fields = line.split()
        try:
            separator = fields.index('-')
            if separator < 6 or len(fields) < separator+4:
                continue
            major, minor = map(int, fields[2].split(':'))
            if (major, minor) != device:
                continue
            mount = re.sub(r'\\(040|011|012|134)',
                           lambda m: chr(int(m[1], 8)), fields[4])
            if not mount.startswith('/') or posixpath.commonpath((path, mount)) != mount:
                continue
            candidates.append((len(mount), fields[separator+1]))
        except (ValueError, IndexError):
            continue
    if not candidates:
        return None
    longest = max(n for n, _ in candidates)
    types = {name for n, name in candidates if n == longest}
    return types.pop() if len(types) == 1 else None


def destination_filesystem(path):
    path = os.path.realpath(os.path.abspath(path))
    if sys.platform == 'win32':
        return _windows_filesystem(path)
    if sys.platform.startswith('linux'):
        device = os.stat(path).st_dev
        with open('/proc/self/mountinfo', encoding='utf-8') as stream:
            text = stream.read(8*1024*1024+1)
        if len(text) > 8*1024*1024:
            return None
        return _mount_filesystem(path, (os.major(device), os.minor(device)), text)
    return None


@dataclass(frozen=True)
class TargetAssessment:
    target: str
    total_bytes: int
    required_bytes: int
    existing_files: int
    free_bytes: int | None
    filesystem: str | None
    oversized_count: int
    oversized_paths: tuple[str, ...]

    @property
    def insufficient(self):
        return self.free_bytes is not None and self.required_bytes > self.free_bytes

    def text(self, language='de'):
        t = lambda value: translate(value, language)
        lines = [t('Exportziel: {target}').format(target=self.target),
                 t('Dateisystem des Ziels: {filesystem}').format(
                     filesystem=self.filesystem or t('Nicht ermittelbar')),
                 t('Geplante Dateiinhalte: {size}').format(size=readable_bytes(self.total_bytes)),
                 t('Zusätzlich benötigte Dateibytes (Obergrenze): {size}').format(size=readable_bytes(self.required_bytes)),
                 t('Vollständig vorhandene Dateien zur erneuten Prüfung: {count}').format(count=self.existing_files),
                 t('Aktuell verfügbar: {size}').format(size=readable_bytes(self.free_bytes) if self.free_bytes is not None else t('Nicht ermittelbar'))]
        if self.insufficient:
            lines += ['', t('Der verfügbare Platz reicht voraussichtlich nicht aus. Wähle möglichst ein anderes Ziel oder gib dort Speicherplatz frei.')]
        if self.oversized_count:
            lines += ['', t('{count} Dateien überschreiten die FAT/FAT32-Grenze von 4 GiB minus 1 Byte. Bitte ein anderes Exportziel wählen.').format(count=self.oversized_count)]
            lines.extend(self.oversized_paths)
        if self.filesystem is None or self.filesystem.casefold() in ('vboxsf', 'cifs', 'nfs', 'nfs4', 'smbfs', 'fuse', 'fuseblk') or self.filesystem.casefold().startswith('fuse.'):
            lines += ['', t('Die Dateigrößengrenze des Ziels ist unbekannt, etwa bei manchen VM- oder Netzwerkfreigaben.')]
        lines += ['', t('Schätzung anhand der Metadaten, ohne zusätzliche Lesezugriffe auf Dateiinhalte. Dateisystem-, Berichts- und Prüfsummendateien benötigen zusätzlichen Platz. Verfügbarer Speicher kann sich ändern.')]
        return '\n'.join(lines)


def assess_target(target, plan, existing=frozenset()):
    """Estimate new content bytes, never treating an unverified file as verified."""
    try:
        free = shutil.disk_usage(target).free
        if type(free) is not int or free < 0:
            free = None
    except OSError:
        free = None
    try:
        filesystem = destination_filesystem(target)
    except (OSError, ValueError):
        filesystem = None
    fat = bool(filesystem and filesystem.casefold() in ('fat', 'fat32', 'vfat', 'msdos'))
    total = required = present = oversized = 0
    examples = []
    for task in plan:
        if (task.is_directory or not getattr(task.entry, 'recoverable', False)
                or getattr(task.entry, 'metadata_only', False)
                or getattr(task.entry, 'unsupported_reason', '')):
            continue
        size = max(0, int(task.entry.size))
        total += size
        if task.path in existing:
            present += 1
            continue
        required += size
        if fat and size > FAT_MAX_FILE:
            oversized += 1
            if len(examples) < 3:
                examples.append(task.path)
    return TargetAssessment(str(Path(target)), total, required, present, free,
                            filesystem, oversized, tuple(examples))
