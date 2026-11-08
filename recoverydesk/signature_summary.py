"""Immutable display context for a signature run; no source access."""
from dataclasses import dataclass, replace

from .i18n import translate


@dataclass(frozen=True)
class SignatureSummary:
    source: str
    area: str
    offset: int
    categories: tuple
    file_limit: int
    state: str = 'running'
    count: int = 0

    @classmethod
    def from_index(cls, source, index):
        return cls(source, index.signature_search_area, index.signature_partition_offset,
                   tuple(index.signature_categories), index.signature_file_limit,
                   'finished' if index.signature_complete else 'limited', len(index.entries))

    def outcome(self, state):
        return replace(self, state=state)


def _short(text, maximum):
    text = ' '.join(text.splitlines())
    return text if len(text) <= maximum else text[:maximum//2] + '…' + text[-maximum//2:]


def summary_text(run, language):
    tr = lambda text: translate(text, language)
    name = run.source.replace('\\', '/').rsplit('/', 1)[-1]
    title = tr('Suchlauf: {source}').format(source=_short(name, 60))
    area = {'all': 'Gesamtes Image', 'ntfs-free': 'Freie NTFS-Bereiche',
            'fat32-free': 'Freie FAT32-Bereiche', 'exfat-free': 'Freie exFAT-Bereiche'}[run.area]
    categories = dict(images='Bilder', office='Office/PDF', archives='Archive', audio='Audio', video='Video')
    settings = tr('{area} · Offset {offset} B · Prüflimit {limit} MiB · {categories}').format(
        area=tr(area), offset=run.offset, limit=run.file_limit//1024**2,
        categories=', '.join(tr(categories[key]) for key in run.categories))
    if run.state == 'finished':
        status = tr('Suchlauf beendet: {count} Funde.').format(count=run.count) if run.count else tr(
            'Keine passenden Signaturen innerhalb der Prüfgrenzen gefunden.')
    else:
        status = tr({'running': 'Suche läuft; noch kein abgeschlossenes Ergebnis.',
                     'limited': 'Prüfgrenze erreicht; Suchergebnis unvollständig.',
                     'cancelled': 'Suche angehalten oder abgebrochen; kein abgeschlossenes Ergebnis.',
                     'failed': 'Suche fehlgeschlagen; kein abgeschlossenes Ergebnis.'}[run.state])
    return '\n'.join((title, settings, status))
