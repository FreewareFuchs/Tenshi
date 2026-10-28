"""Bounded 100-cell projection of existing serial batch events, never disk I/O.

Cells represent planned file sizes, not sectors or original file integrity.
Integer scaled intervals avoid rounding large plans into false confirmations.
"""
from dataclasses import dataclass, field

STATES = ('pending', 'copied', 'confirmed', 'error', 'unconfirmed')


@dataclass
class ExportBlocks:
    planned: bool = False
    total: int = 0
    entries: bool = False
    cursor: int = 0
    active_path: str | None = None
    active_size: int = 0
    copied: int = 0
    errors: int = 0
    skipped: int = 0
    cancelled: int = 0
    cells: list[dict] = field(default_factory=list)

    def handle(self, event):
        kind = event.get('type')
        if kind == 'plan':
            self.__dict__.update(type(self)().__dict__)
            self.planned = True
            self.entries = int(event['total_bytes']) <= 0
            self.total = max(0, int(event['total'] if self.entries else event['total_bytes']))
            self.cells = [dict.fromkeys(STATES, 0) for _ in range(100)]
            for cell in self.cells:
                cell['pending'] = self.total
        elif kind == 'start':
            self.active_path = event['path']
            self.active_size = min(max(0, self.total-self.cursor),
                                   1 if self.entries else max(0, int(event.get('size', 0))))
            self.copied = 0
        elif kind == 'bytes' and self.active_path == event['path'] and not self.entries:
            end = min(self.active_size, self.copied+max(0, int(event['delta'])))
            self._move(self.cursor+self.copied, self.cursor+end, 'pending', 'copied')
            self.copied = end
        elif kind == 'done' and self.active_path == event['path']:
            status = event['status']
            if status == 'Fehler':
                self.errors += 1
            elif status == 'Übersprungen':
                self.skipped += 1
            elif status == 'Abgebrochen':
                self.cancelled += 1
            outcome = ('confirmed' if status in ('Erfolgreich', 'Bereits verifiziert', 'Ordner erstellt')
                       else 'error' if status == 'Fehler' else 'unconfirmed')
            self._move(self.cursor, self.cursor+self.copied, 'copied', outcome)
            self._move(self.cursor+self.copied, self.cursor+self.active_size, 'pending', outcome)
            self.cursor += self.active_size
            self.active_path = None
            self.active_size = self.copied = 0

    def _move(self, start, end, before, after):
        if not self.total or end <= start:
            return
        start, end = start*100, end*100
        for number in range(start//self.total, min(100, (end+self.total-1)//self.total)):
            amount = min(end, (number+1)*self.total)-max(start, number*self.total)
            self.cells[number][before] -= amount
            self.cells[number][after] += amount

    @property
    def confirmed_fraction(self):
        if not self.total:
            return 0.
        confirmed = sum(cell['confirmed'] for cell in self.cells)
        expected = 100*self.total
        return 1. if confirmed == expected else min(.999, confirmed/expected)

    def cell_states(self):
        result = []
        for cell in self.cells:
            if cell['error']:
                state = 'error'
            elif cell['unconfirmed']:
                state = 'unconfirmed'
            elif self.total and cell['confirmed'] == self.total:
                state = 'confirmed'
            elif self.total and cell['copied'] == self.total:
                state = 'copied'
            elif cell['copied'] or cell['confirmed']:
                state = 'mixed'
            else:
                state = 'pending'
            result.append(state)
        return tuple(result or ['pending']*100)


def copy_export_report(source, report, destination):
    """Copy the existing final report, never overwrite or bypass output guards."""
    import os
    import stat
    from .sources import ensure_safe_destination
    from .secure_target import open_regular_input, open_regular_output
    if not source:
        raise ValueError('Quellzuordnung des Exports fehlt.')
    ensure_safe_destination(source, destination)
    with open_regular_input(report, source) as incoming:
        if not stat.S_ISREG(os.fstat(incoming.fileno()).st_mode):
            raise ValueError('Nur reguläre Berichte können gespeichert werden.')
        with open_regular_output(destination, 'xb', source) as outgoing:
            while chunk := incoming.read(1024*1024):
                remaining = memoryview(chunk)
                while remaining:
                    written = outgoing.write(remaining)
                    if not written:
                        raise OSError('Bericht konnte nicht vollständig geschrieben werden.')
                    remaining = remaining[written:]
            outgoing.flush()
            os.fsync(outgoing.fileno())
