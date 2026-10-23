# Tenshi 3.0.2 Beta.4 – FAT32-Korrektur

Vorbereiteter Release; noch nicht veröffentlicht. Die angezeigte Programmversion bleibt 3.0.2.

## Wichtige Korrektur gegenüber Beta.3

Bei FAT32-Volumes mit deaktivierter FAT-Spiegelung und aktiver zweiter FAT folgte Tenshi bisher trotzdem der ersten Tabelle. War deren Clusterkette veraltet, konnte ein Export die erwartete Dateigröße haben und dennoch falsche Inhalte enthalten. Auch Vorschau und Verzeichnisfortsetzungen waren betroffen.

Tenshi berücksichtigt jetzt die aktive FAT für Datei- und Verzeichnisketten und weist ungültige FAT-Nummern ab. Die gesonderten Prüfungen für gelöschte Dateien bleiben erhalten. Quellen werden weiterhin nur lesend geöffnet.

Wer Dateien aus einem solchen FAT32-Volume mit Beta.3 oder früher exportiert hat, sollte die Ergebnisse erneut prüfen und aus einer unveränderten Quelle oder einem vorhandenen Image mit Beta.4 erneut exportieren. Der Größenvergleich allein erkennt den beschriebenen Fehler nicht.

## Downloads und Installation

- Windows 10/11, 64 Bit: `Tenshi_Setup_3.0.2.exe` oder `Tenshi_Portable_3.0.2_Win64.zip`.
- Linux Mint 22.x: `tenshi_3.0.2.beta.4-1_all.deb`, interne Paketversion `3.0.2~beta.4-1`.
- Gemeinsame Prüfsummen: `SHA256SUMS.txt` für die konkreten Beta.4-Dateien.

Die Windows-Pakete sind nicht digital signiert. Linux benötigt Python >= 3.11, Tkinter und util-linux; Linux Mint 21.x mit standardmäßigem Python 3.10 wird nicht unterstützt. Im Downloadordner installieren oder aktualisieren:

```bash
sudo apt install ./tenshi_3.0.2.beta.4-1_all.deb
```

Anschließend Tenshi über das Anwendungsmenü oder `tenshi` ohne sudo starten. Es wird keine zusätzliche Tenshi-Paketquelle eingerichtet, und Geräteberechtigungen werden nicht geändert.

## Prüfung und Grenzen

Die FAT32-Korrektur besteht Regressionstests für bytegleichen Export und Vorschau, Verzeichnisketten, Partitionsoffsets, aktivierte Spiegelung und ungültige aktive FAT-Nummern. Der Fehler wurde zuvor mit unterschiedlichen, gleich langen FAT-Ketten reproduziert. Die lokale Suite durchlief 575 Tests ohne Fehler, davon zwei übersprungen. Linux- und Windows-CI des Fix-Merge-Commits `309e98b` sind erfolgreich. Die Beta.4-Paketierungsprüfungen stehen noch aus.

Tenshi bleibt experimentelle Beta-Software. Gerettete Daten auf einem anderen physischen Datenträger speichern und prüfen. Auch Lesen kann beschädigte Medien belasten. Tatsächlich defekte Laufwerke und allgemeine Löschrettung sind nicht abgenommen. Btrfs/XFS-Navigation und Export bleiben eingeschränkt. Für beschädigte Medien ersetzt Tenshi keine spezialisierte mehrphasige Rettungsstrategie wie GNU ddrescue.

Die bereits veröffentlichten Beta.3-Downloads werden nicht ersetzt.
