# Tenshi 2.9.0 – Windows-/USB-Zuverlaessigkeit

## Aenderungen

1. Windows-Rohgeraete: Unerwartet kurze Leseantworten werden als Verbindungs-/Lesefehler angezeigt. Dies ist **kein** bestaetigter Medienfehler und darf niemals stillschweigend nullgefuellt werden.
2. USB-Geraet verloren/nicht bereit (WinError 21, 31, 55, 433, 1167): klarer Abbruch statt fehlerhafte Fortsetzung. Nach erneutem Anschluss dieselbe Quelle unbedingt eindeutig pruefen. Ausrichtung (22/87) und fehlende Berechtigung (5/32/33) erhalten gesonderte Meldungen.
3. Lesen von Dateisystem-Metadaten erfolgt mit kleinerem Read-ahead, grosse Rohgeraete-Leseauftraege werden sektorkonform auf maximal 256 KiB begrenzt. Auf physikalisch stark beschaedigten Datentraegern trotzdem Vorsicht und moeglichst zuerst ein schonendes Roh-Image anlegen.
4. Bestaetigte CRC-/I/O-Medienfehler (WinError 23, 1117) werden weiterhin nach der Imaging-Konfiguration isoliert: 'Nullen + protokollieren' oder 'Sicher anhalten'. Nullfuellung bedeutet fehlende Originaldaten.
5. Neues `check_windows.bat`: nicht invasiver Vorabtest fuer Windows/Python/TEMP, mit Ergebnis unter `tenshi-windows-check.log`. Er prueft bewusst keine USB-Geraete und bestaetigt keinen erfolgreichen Windows-Hardwarezugriff.
6. Logo, sechs Sprachen, zwei Hauptregister, gruenes Stapel-Export, gespeicherte Analysesitzungen und Partitions-Doppelklick bleiben erhalten.

## Erstellen unter Windows

- `check_windows.bat` fuer die ungefaehrliche Vorabpruefung (ohne Laufwerkszugriffe).
- `build_windows.bat` fuer `dist\Tenshi.exe`.
- `run_tests.bat` fuer die komplette automatisierte Testsuite; Logs sind unter `tenshi-tests.log`.
- `build_portable.bat` fuer `Tenshi_Portable_2.9.0_Win64.zip`.
- `build_installer.bat` fuer `Tenshi_Setup_2.9.0.exe` (Inno Setup 6.3+).

**Testgrenze:** Automatisierte Tests wurden nur unter Linux/Xvfb mit simulierten Windows-Fehlern durchgefuehrt. Eine reale Windows-Hardwareabnahme mit USB-Laufwerken, hot-unplug, inkompatiblen Treibern, Berechtigungen sowie EXE und Installer steht aus. Dabei keine produktiven oder defekten Laufwerke gefaehrden.
