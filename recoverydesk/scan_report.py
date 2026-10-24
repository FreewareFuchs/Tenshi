"""Human-readable diagnostic report, never alters the source volume."""
from __future__ import annotations
from datetime import datetime, timezone


def format_scan_report(source, index) -> str:
    lines = ["Tenshi – Analysebericht", "UTC: " + datetime.now(timezone.utc).isoformat(),
             "Quelle: " + source, "Quelle nur gelesen, kein Dateisystem repariert.", ""]
    fs = getattr(index, 'filesystem', 'NTFS')
    lines.append('Dateisystem: ' + fs)
    lines.append(f'Gefundene Datei-/Ordnereinträge: {len(index.entries)}')
    lines.append(f'Als gelöscht gekennzeichnete Einträge/Hinweise: {sum(bool(getattr(e, "is_deleted", False)) for e in index.entries)}')
    if hasattr(index, 'damaged_records'):
        lines.extend([
            f'MFT-Datensätze geprüft: {index.scanned_records} / {index.total_records}',
            f'Nicht auswertbare MFT-Datensätze: {index.damaged_records}',
            f'Nicht lesbare MFT-Datensätze: {index.unreadable_records}',
            f'Nicht zugeordnete Datei-/Ordnernamen: {index.orphan_count}',
            f'Nicht zugeordnete Stammordner/-einträge: {getattr(index, "orphan_roots", 0)}',
            f'Erkannte zyklische Verweisketten: {getattr(index, "orphan_cycles", 0)}',
            f'Index-Hinweise aus nicht residentem $INDEX_ALLOCATION: {getattr(index, "allocation_index_hints", 0)}',
            f'Nur aus NTFS-Verzeichnisindizes rekonstruierte Namen (unbestätigt): {getattr(index, "reconstructed_index_hints", 0)}',
            f'Erfolgreich zusammengeführte NTFS-Datenattributlisten: {getattr(index, "resolved_attribute_lists", 0)}',
            f'Nicht auflösbare NTFS-Datenattributlisten: {getattr(index, "unresolved_attribute_lists", 0)}',
            f'Fehlertoleranter Image-Scan: {"Ja" if index.tolerant else "Nein"}',
        ])
        lines.extend([
            'Auswertungsfehler sind kein alleiniger Nachweis eines Datenträgerschadens.',
            f'Wegen Attributlisten-Limit nicht untersuchte Basisrecords: {getattr(index, "attribute_list_limit_skipped", 0)}',
            f'Verzeichnisindex-Auswertungsmeldungen: {getattr(index, "index_parse_failures", 0)}',
            'MFT-Auswertungsfehler nach Grund (maximal 20 Gründe, weitere zusammengefasst):',
        ])
        reasons = getattr(index, 'record_error_reasons', {})
        if reasons:
            lines.extend(f'  {count}: {reason}' for reason, count in reasons.items())
        else:
            lines.append('  Keine Details vorhanden (bei älteren Sitzungen nicht erfasst).')
        samples = getattr(index, 'record_error_samples', [])
        if samples:
            lines.append('Beispiele (maximal 20 MFT-Recordnummern):')
            lines.extend(f'  MFT {sample["record"]}: {sample["reason"]}' for sample in samples)
        ranges = index.read_error_ranges
        lines.append('Nicht lesbare MFT-Bereiche (Recordnummern):')
        if ranges:
            lines.extend(f'  {start}–{end}' for start,end in ranges[:1000])
            if len(ranges) > 1000:
                lines.append(f'  ... {len(ranges)-1000} weitere Bereiche')
        else:
            lines.append('  Keine')
        if index.scan_warnings:
            lines.append('Hinweise:')
            lines.extend('  ' + w for w in index.scan_warnings)
    else:
        lines.extend([
            f'Nicht lesbare Unterordner: {index.unreadable_directories}',
            f'Fehlertoleranter Image-Scan: {"Ja" if index.tolerant else "Nein"}',
        ])
        if index.scan_warnings:
            lines.append('Betroffene Ordner:')
            lines.extend('  ' + w for w in index.scan_warnings)
    lines.extend(['', 'Grenzen:',
                  '- Nicht lesbare oder beschädigte Metadaten werden nicht geraten.',
                  '- Nicht gefundene Dateien sind nicht zwingend endgültig verloren.',
                  '- Gelöschte/überschriebene Dateiinhalte können trotz erhaltenem Eintrag fehlen.',
                  '- FAT32/exFAT-Löschkandidaten benutzen nur unter engen Voraussetzungen eine hypothetische zusammenhängende Clusterfolge.',
                  '- Ext-Löschhinweise aus Verzeichnis-Slack haben keinen gesicherten Dateiinhaltsnachweis; experimenteller Export nur bei vollständig als frei erkannten Datenblöcken.',
                  '- Nur anhand von INDEX_ROOT/INDEX_ALLOCATION rekonstruierte Namen sind unbestätigte Metadaten und nicht exportierbar.',
                  '- Zusammengeführte Attributlisten nur bei vollständig geprüfter VCN-Zuordnung.',
                  '- Keine automatische Dateireparatur oder Journal-Rekonstruktion.',
                  '- Exportierte Dateien auf Vollständigkeit und Integrität prüfen.', ''])
    return '\n'.join(lines)
