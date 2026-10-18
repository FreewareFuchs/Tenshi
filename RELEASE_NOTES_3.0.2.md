# Tenshi 3.0.2 – Quellenwechsel und Exportnamen

## Neue Funktionen

- Neu begonnene Stapel-Exporte verwenden `Tenshi_Export_<Signatur>`; die exportierten Dateien liegen weiterhin in `files/`.
- Ältere `RecoveryDesk_Export_<Signatur>`-Aufträge bleiben bestehen und werden bei gleicher Quelle und Auswahl sicher über die vorhandene Statusdatei fortgesetzt. Keine automatische Umbenennung, kein Überschreiben bereits exportierter Dateien.
- Nach einer neuen Quellenauswahl (Image, physischer Datenträger oder logisches Windows-Laufwerk) springt Tenshi automatisch zu „Partitionen“ und startet die Schnellanalyse (erste 64 MiB und gültige Partitionstabellen), ausschließlich lesend.
- Im Eingabefeld „Ausgewählte Quelle“ kann eine manuell eingetragene Quelle mit Enter übernommen und analysiert werden.
- Bei laufendem alten Partitionsscan wartet eine neu angeforderte Schnellanalyse dessen Ende ab. Ergebnisse alter Quellen werden nicht mehr angezeigt.
- Das Laden einer zuvor geprüften Analysesitzung bleibt unverändert: Wiederherstellung ohne unnötigen neuen Scan.

## Sicherheit und Einschränkungen

- Schnellanalyse ist kein vollständiger Datenträgerscan. Für außerhalb des Suchbereichs liegende oder beschädigte Strukturen die Tiefensuche manuell verwenden.
- Physisch beschädigte Laufwerke können auch durch reine Lesezugriffe zusätzlich belastet werden; in solchen Fällen zuerst ein schonendes Image erwägen.
- Export-Ziele sollten nach wie vor auf einem anderen physischen Datenträger liegen.
- GUI- und Datenrettungsfunktionen sind mit synthetischen Medien automatisiert getestet. Ein neues Windows-Build muss auf Windows gebaut und dort geprüft werden.

## Windows

1. `run_tests.bat` für automatische Tests; `tenshi-tests.log` prüfen.
2. `build_windows.bat` für `dist\Tenshi.exe`.
3. Optional `build_portable.bat` / `build_installer.bat`.
