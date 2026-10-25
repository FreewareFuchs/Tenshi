"""UI-independent export progress accounting (does not touch a source disk).

The transfer rate reflects *bytes actually written* rather than time spent
validating earlier exports. ETA is only approximate and deliberately omitted
until there is enough information to estimate it.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import time


def readable_bytes(value: float) -> str:
    value = max(0.0, float(value))
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
        if value < 1024 or unit == 'PiB':
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024
    return '0 B'


def readable_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds > 60 * 60 * 24 * 365:
        return '–'
    whole = round(seconds)
    hours, rem = divmod(whole, 3600)
    mins, secs = divmod(rem, 60)
    return f'{hours} h {mins:02} min' if hours else f'{mins} min {secs:02} s'


@dataclass
class QueueProgress:
    total: int = 0
    total_bytes: int = 0
    done_count: int = 0
    done_bytes: int = 0
    written_bytes: int = 0
    root: str = ''
    log: str = ''
    resumed: bool = False
    ended: bool = False
    cancelled: bool = False
    active_path: str = ''
    active_written: int = 0
    visible_items: dict[str, dict] = field(default_factory=dict)
    _active_size: int = 0
    _samples: deque = field(default_factory=deque)
    _current_seen: set[str] = field(default_factory=set)

    def handle(self, event: dict, now: float | None = None) -> None:
        if now is None:
            now = time.monotonic()
        kind = event['type']
        if kind == 'plan':
            self.total = int(event['total'])
            self.total_bytes = max(0, int(event['total_bytes']))
            self.done_count = self.done_bytes = self.written_bytes = 0
            self.root, self.log = event.get('root', ''), event.get('log', '')
            self.resumed = bool(event.get('resumed'))
            self.cancelled = self.ended = False
            self.active_path = ''
            self.active_written = self._active_size = 0
            self._current_seen.clear()
            self._samples.clear()
            self.visible_items = {i['path']: {'size': max(0, int(i['size'])),
                                            'status': 'Wartend', 'detail': '',
                                            'directory': bool(i.get('directory'))}
                                  for i in event.get('items', [])}
        elif kind == 'start':
            self.active_path = event['path']
            self.active_written = 0
            item = self.visible_items.get(self.active_path)
            self._active_size = item['size'] if item else 0
            if item:
                item['status'] = 'Läuft'
        elif kind == 'bytes':
            delta = max(0, int(event['delta']))
            self.written_bytes += delta
            if self.active_path == event['path']:
                self.active_written += delta
            self._samples.append((now, self.written_bytes))
            self._trim(now)
        elif kind == 'done':
            name = event['path']
            if name not in self._current_seen:
                self._current_seen.add(name)
                self.done_count += 1
                self.done_bytes += max(0, int(event.get('size', 0)))
            item = self.visible_items.get(name)
            if item:
                item['status'] = event['status']
                item['detail'] = event.get('detail', '')
            self.active_path = ''
            self.active_written = self._active_size = 0
        elif kind == 'complete':
            self.ended = True
            self.cancelled = bool(event.get('cancelled'))

    def _trim(self, now: float) -> None:
        while len(self._samples) > 2 and self._samples[1][0] < now - 8:
            self._samples.popleft()

    def speed(self, now: float | None = None) -> float:
        if now is None:
            now = time.monotonic()
        self._trim(now)
        if len(self._samples) < 2:
            return 0.0
        a, b = self._samples[0], self._samples[-1]
        elapsed = b[0] - a[0]
        if elapsed < 0.2 or now - b[0] > 4:
            return 0.0
        return max(0., (b[1] - a[1]) / elapsed)

    @property
    def remaining_bytes(self) -> int:
        return max(0, self.total_bytes - self.done_bytes - self.active_written)

    def eta(self, now: float | None = None) -> float | None:
        rate = self.speed(now)
        if rate <= 0 or self.ended:
            return None
        return self.remaining_bytes / rate

    @property
    def item_fraction(self) -> float:
        return self.done_count / self.total if self.total else 0.0

    @property
    def overall_fraction(self) -> float:
        """Show live byte progress *during* large files, not only after each file.

        For directories/zero-size jobs use the item count. This indicates
        completion of processing, NOT how many files are recoverable.
        """
        if self.cancelled or self.total <= 0:
            return 0.0
        if self.total_bytes <= 0:
            return min(1.0, max(0.0, self.item_fraction))
        completed = self.done_bytes + min(self.active_written, self._active_size)
        fraction = max(0.0, min(1.0, completed / self.total_bytes))
        # Hold a tiny remainder while e.g. checksums, directories or manifest
        # updates are still pending, rather than claiming the batch is done.
        return fraction if self.done_count == self.total else min(0.999, fraction)

    def summary(self, now: float | None = None) -> str:
        rate = self.speed(now)
        return (f'{self.done_count:,}/{self.total:,} Einträge · '
                f'{readable_bytes(self.written_bytes)} übertragen · '
                f'{readable_bytes(self.remaining_bytes)} offen · '
                f'{readable_bytes(rate)}/s · '
                f'Restzeit ca. {readable_duration(self.eta(now))}')
