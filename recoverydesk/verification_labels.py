"""Describe existing checks precisely; no verification level implies original integrity."""
METADATA_SCOPE = 'Nur Metadaten geprüft; Dateiinhalte ungeprüft.'
READ_SCOPE = 'Dateigröße vollständig gelesen; SHA-256 nur berechnet, nicht mit einem Original verglichen.'
EXPORT_SCOPE = 'Neue Exporte: Zieldatei mit der Prüfsumme des kopierten Datenstroms verglichen. Kein Nachweis ursprünglicher Integrität.'
RESUME_SCOPE = 'Fortsetzen: Größe und SHA-256 mit dem gespeicherten Prüfwert verglichen. Kein erneutes Lesen der Quelle für den Inhaltsvergleich.'
WRITTEN_LABEL = 'Exportiert – Originalinhalt ungeprüft'
RESUME_LABEL = 'Export-Prüfsumme bestätigt'
METADATA_LABEL = 'Metadaten plausibel'


def export_status_label(status):
    return {'Erfolgreich': WRITTEN_LABEL, 'Bereits verifiziert': RESUME_LABEL}.get(status, status)
