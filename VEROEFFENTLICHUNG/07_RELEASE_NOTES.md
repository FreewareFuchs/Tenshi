# Tenshi 3.0.2 Beta – Veröffentlichungsnotizen / Release notes

**Freigabestatus:** Veröffentlichungsunterlagen vorbereitet; Veröffentlichung erst nach abschließender Lizenz-/Webseitenprüfung und Windows-Rebuild.

## Neu in 3.0.2

- Nach Auswahl einer neuen Quelle automatischer Wechsel in **Partitionen** und nur lesende Schnellanalyse.
- Sichere Behandlung schneller Quellenwechsel: veraltete Scanergebnisse werden verworfen.
- Neue Batch-Exportordner heißen `Tenshi_Export_<Signatur>` statt `RecoveryDesk_Export_*`. Ältere Exportaufträge können im bisherigen Ordner fortgesetzt werden.
- Aktuelle Analysesitzung wird beim Wiederladen nicht unnötig neu gescannt.

## Vorhandene Funktionen

- NTFS, FAT32, exFAT, ext2/3/4, begrenzte Btrfs-/XFS-Unterstützung.
- Nur lesender Quellzugriff, GPT/MBR-Partitionsanalyse, Dateibaum, Schnellsuche und Export-Vorabprüfung.
- Batch-Export mit Wiederaufnahme und Verifizierung, RAW-Imaging mit fortsetzbarem Ablauf.
- Sechs Sprachen, zwei Hauptregister, Dark Mode, Logo und F1-Hilfe.

## Bekannte Grenzen

- Keine Zusicherung vollständiger oder erfolgreicher Datenrettung. Besonders bei gelöschten Dateien sind Metadaten und belegte Cluster nicht gleichbedeutend mit tatsächlich intakten Inhalten.
- Teilweise keine Unterstützung für komprimierte, verschlüsselte oder Sparse-NTFS-Daten.
- Btrfs/XFS-Löschhinweise nicht exportierbar.
- Schwere Hardwarefehler/unstabile USB-Bridges und exotische Dateisystemvarianten nicht systematisch abgedeckt.
- Imaging-Nullfüllung dokumentiert Datenlücken; sie rekonstruiert keine fehlenden Sektoren.
- Binärdateien noch nicht digital signiert. Portable Ausgabe speichert trotzdem bestimmte Daten im Benutzerprofil.

## English short notes

**3.0.2 Beta:** Automatically switch to Partitions and run a read-only quick scan after selecting a source; stale scan results are discarded on rapid source changes. New export jobs use `Tenshi_Export_*`; older `RecoveryDesk_Export_*` jobs remain resumable. Includes read-only analysis of GPT/MBR disks, selected filesystem browsing and experimental recovery, image acquisition/resume, six UI languages and offline help. Experimental; no guarantee that recovered files are complete. Save all outputs to another physical drive.
