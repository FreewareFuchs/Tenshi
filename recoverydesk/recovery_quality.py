"""Conservative metadata-based assessment; NEVER claims content integrity.

A valid file size/runlist does not show whether old clusters were overwritten.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Assessment:
    label: str
    detail: str
    grade: str

SIGNATURE_DETAIL = ('Dateistruktur erkannt; der Dateiinhalt wurde noch nicht gesondert geprüft. '
    'Originalname, Ordner und Löschstatus sind unbekannt. '
    'Ob die ursprüngliche Datei vollständig und unbeschädigt ist, bleibt offen.')

SIGNATURE_CHECK_GUIDE = ('Fund: Tenshi hat eine passende Dateistruktur erkannt. Das allein bestätigt keine vollständige Datei.\n\n'
    'Vollständig lesend prüfen: Prüft, ob alle Daten des Funds gelesen werden können. '
    'Die dabei berechnete SHA256 ist kein Vergleich mit dem Original.\n\n'
    'Inhalt prüfen: Untersucht unterstützte Bild-, PDF- und Office-Inhalte innerhalb der Prüfgrenzen. '
    'Das Ergebnis nennt, was geprüft wurde und was offenbleibt. Nicht geprüft oder Prüfgrenze erreicht bedeutet nicht automatisch beschädigt.')

def assess(entry) -> Assessment:
    if getattr(entry,'locator',()) and entry.locator[0]=='signature-v1':
        return Assessment('Signaturfund · ungeprüft',
            SIGNATURE_DETAIL, 'uncertain')
    if getattr(entry, 'metadata_only', False):
        return Assessment('Nur Namenshinweis',
            'Aus einem NTFS-Verzeichnisindex rekonstruiert; kein verifizierter Dateidatensatz.', 'unknown')
    reason = getattr(entry, 'unsupported_reason', '')
    if getattr(entry, 'is_directory', False):
        return Assessment('Ordner' if not reason else 'Ordner eingeschränkt',
                          reason or 'Ordner kann untersucht werden; einzelne Dateien sind separat zu prüfen.',
                          'directory' if not reason else 'limited')
    if not getattr(entry, 'recoverable', False):
        return Assessment('Nicht exportierbar', reason or 'Kein unterstützter Datenstrom vorhanden.', 'blocked')
    if getattr(entry, 'is_deleted', False):
        return Assessment('Gelöscht · unsicher',
            'Ein Datenstrom ist lesbar, aber frühere Cluster können inzwischen überschrieben sein. '
            'Ein Export beweist nicht die Unversehrtheit der Datei.', 'uncertain')
    return Assessment('Export möglich · ungeprüft',
        'Dateisystem-Metadaten sind auswertbar. Der tatsächliche Dateiinhalt wurde nicht '
        'mit einer bekannten Prüfsumme verifiziert.', 'possible')
