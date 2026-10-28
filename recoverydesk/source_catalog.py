"""Display-only device grouping. Never use this snapshot to authorize exports."""
from dataclasses import dataclass, replace
import os
from pathlib import Path
import sys

from .core import list_volumes
from .sources import list_physical_sources, physical_number, raw_volume_path, volume_disk_numbers


@dataclass(frozen=True)
class SourceChoice:
    key: str
    source: str
    kind: str
    size: int
    label: str = ''
    filesystem: str = ''
    parent: str = ''
    mapping: str = ''


def device_choices(drives):
    return [SourceChoice(path, path, 'disk', size,
                         str(physical_number(path)) if physical_number(path) is not None else '')
            for path, size in drives]


def volume_choices(volumes):
    return [SourceChoice(v.path, v.path if v.path.startswith('/dev/') else raw_volume_path(v.path),
                         'volume', v.total_bytes, v.label, v.filesystem)
            for v in volumes if v.total_bytes >= 512]


def _volume_parents(choice):
    if sys.platform.startswith('linux'):
        from .linux_devices import _backing_disks
        roots = _backing_disks(os.stat(choice.source).st_rdev)
        return {'/dev/' + Path(root).name for root in roots}
    numbers = volume_disk_numbers(choice.source, metadata_only=True)
    return {rf'\\.\PhysicalDrive{number}' for number in numbers} if numbers else set()


def group_choices(disks, volumes, parents=None):
    """Only attach a volume when exactly one known device is established."""
    parents = parents or _volume_parents
    known = {d.source for d in disks}
    result = list(disks)
    for volume in volumes:
        try:
            backing = parents(volume)
        except (OSError, ValueError, RuntimeError):
            backing = set()
        parent = next(iter(backing)) if len(backing) == 1 and backing <= known else ''
        mapping = '' if parent else ('multiple' if len(backing) > 1 else 'unknown')
        result.append(replace(volume, parent=parent, mapping=mapping))
    return result


def collect_choices():
    # The two independent lists may partially fail (permissions/hot unplug).
    # Keep the successful list and expose failure instead of claiming completeness.
    warnings = []
    try:
        disks = device_choices(list_physical_sources(metadata_only=True))
    except (OSError, ValueError):
        disks = []
        warnings.append('Datenträgerliste konnte nicht vollständig ermittelt werden.')
    try:
        volumes = volume_choices(list_volumes())
    except (OSError, ValueError):
        volumes = []
        warnings.append('Laufwerksliste konnte nicht vollständig ermittelt werden.')
    return group_choices(disks, volumes), warnings
