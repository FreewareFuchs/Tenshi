"""Describe existing checks precisely; no verification level implies original integrity."""
METADATA_SCOPE = 'Nur Metadaten geprüft; Dateiinhalte ungeprüft.'
READ_SCOPE = 'Dateigröße vollständig gelesen; SHA-256 nur berechnet, nicht mit einem Original verglichen.'
EXPORT_SCOPE = 'Neue Exporte: Zieldatei gelesen und SHA-256 gespeichert. Kein erneuter Vergleich mit der Quelle.'
RESUME_SCOPE = 'Fortsetzen: Größe und SHA-256 mit dem gespeicherten Export verglichen. Kein erneuter Vergleich mit der Quelle.'
WRITTEN_LABEL = 'Exportiert – Originalinhalt ungeprüft'
RESUME_LABEL = 'Export-Prüfsumme bestätigt'
METADATA_LABEL = 'Metadaten plausibel'


def export_status_label(status):
    return {'Erfolgreich': WRITTEN_LABEL, 'Bereits verifiziert': RESUME_LABEL}.get(status, status)
