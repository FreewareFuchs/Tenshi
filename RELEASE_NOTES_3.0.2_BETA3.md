# Tenshi 3.0.2 Beta.3 – Windows und Linux

Vorbereiteter Release; noch nicht veröffentlicht. Die Programmversion bleibt 3.0.2.

## Änderungen gegenüber Beta.2

- Der Hilfe-Button wird nach Entfernen des Fragezeichens wieder korrekt in allen sechs Oberflächensprachen übersetzt: Deutsch, Englisch, Spanisch, vereinfachtes Chinesisch, Russisch und Japanisch.
- Der Linux-Paketdateiname verwendet von Anfang an GitHub-kompatible Zeichen: `tenshi_3.0.2.beta.3-1_all.deb`. Die interne Debian-Version ist `3.0.2~beta.3-1`, damit APT Beta.3 als Aktualisierung von Beta.2 erkennt.

## Downloads

1. Windows-Installer: `Tenshi_Setup_3.0.2.exe`
2. Windows Portable: `Tenshi_Portable_3.0.2_Win64.zip`
3. Linux Mint 22.x: `tenshi_3.0.2.beta.3-1_all.deb`
4. Gemeinsame SHA-256-Prüfsummen: `SHA256SUMS.txt`

Linux benötigt Python >= 3.11, Tkinter und util-linux. Installation oder Aktualisierung im Downloadordner:

```bash
sudo apt install ./tenshi_3.0.2.beta.3-1_all.deb
```

Tenshi anschließend über das Anwendungsmenü oder `tenshi` ohne sudo starten. Linux Mint 21.x mit standardmäßigem Python 3.10 wird vom Paket nicht unterstützt. Es wird keine zusätzliche Paketquelle für automatische Updates eingerichtet.

## Prüfung und Grenzen

Die Hilfe-Korrektur wurde mit allen sechs Sprachen automatisiert und im installierten Linux-DEB praktisch bestätigt. Linux- und Windows-CI für die Korrektur auf main (`f6ac6dd`) sind erfolgreich. Die neuen Beta.3-Paketierungsprüfungen stehen noch aus.

Tenshi bleibt experimentelle Beta-Software. Quellen werden nur lesend geöffnet. Gerettete Daten auf einem anderen physischen Datenträger speichern und prüfen. Tatsächlich defekte Laufwerke und allgemeine Löschrettung sind nicht abgenommen. Btrfs/XFS-Navigation und Export bleiben eingeschränkt. Die Windows-Pakete sind nicht digital signiert.

Die veröffentlichten Beta.2-Dateien werden nicht ersetzt. Beta.3 wird erst nach erfolgreichem Build mit eigenen Prüfsummen bereitgestellt.
