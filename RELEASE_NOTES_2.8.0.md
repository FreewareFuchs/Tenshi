# Tenshi 2.8.0 – Wiederherstellungsprüfung

## Neuer Schutz vor falsch zugeordneten gelöschten NTFS-Daten

Beim Export gelöschter NTFS-Dateien reicht eine lesbare alte MFT-Runlist allein nicht aus. Bereits wiederverwendete Cluster können andere heutige Dateiinhalte enthalten. Tenshi gleicht daher die Datenbereiche gelöschter NTFS-Einträge mit bekannten Datenbereichen noch vorhandener Dateien ab. Ein nachgewiesener Konflikt sperrt den betreffenden Export.

Zusätzlich werden überlappende physische Clusterbereiche innerhalb desselben NTFS-Datenstroms erkannt. Das ist ein Plausibilitätsproblem der Metadaten und wird aus Sicherheitsgründen nicht exportiert.

Der neue Abgleich arbeitet nur mit dem bereits aufgebauten Dateisystemindex, liest keine Datei vollständig und verändert die Quelle nicht. Der Warntext erscheint in der Export-Vorabprüfung; derselbe Sperrgrund gilt direkt beim Stapel-Export.

**Keine Garantie:** Fehlende Überlappungen bedeuten keine nachgewiesene Unversehrtheit. Unvollständige MFT-Scans, nicht erkannte Dateieinträge, bereits überschriebenes oder neu freigegebenes Material und externe Änderungen am Image können sich der Prüfung entziehen. Inhalt und Authentizität werden nicht geprüft. Btrfs/XFS-Löschhinweise bleiben nicht exportierbar; FAT32, exFAT, ext2/3/4 behalten ihre bisherigen Einschränkungen.

## Bestehende Funktionen

Zwei Hauptregister, Tenshi-Logo, sechs Sprachen, Hell-/Dunkelmodus, gespeicherte Fensteraufteilung, grüner Stapel-Export, Partitions-Doppelklick, Analysesitzungen und sicheres Imaging mit Wiederaufnahme bleiben erhalten. Die neuen Warnungen sind in alle sechs UI-Sprachen übersetzt.

## Build und Test

Unter Windows: `build_windows.bat` erzeugt `dist\Tenshi.exe`. Separat `run_tests.bat`. Optional `build_portable.bat` für eine portable ZIP und `build_installer.bat` mit Inno Setup 6.3+.

Die 397 automatisierten Tests wurden in einer Linux-Testumgebung mit virtueller GUI durchgeführt. Eine auf Windows kompilierte EXE, Installer und echte beschädigte Datenträger wurden hier nicht getestet. Die Projektquelle wird nur gelesen. Für beschädigte Hardware zuerst ein geeignetes schonendes Abbild erstellen.
