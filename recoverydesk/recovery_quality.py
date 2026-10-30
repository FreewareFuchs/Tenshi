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

def assess(entry) -> Assessment:
    if getattr(entry,'locator',()) and entry.locator[0]=='signature-v1':
        return Assessment('Signaturfund · ungeprüft',
            'Zusammenhängende Bildstruktur erkannt. Originalname, Ordner und Löschstatus sind unbekannt. Vorschau und Inhaltsprüfung bestätigen keine unversehrten Originalinhalte.', 'uncertain')
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
