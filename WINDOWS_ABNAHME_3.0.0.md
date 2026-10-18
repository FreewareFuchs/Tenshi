# Tenshi 3.0.0 – Windows-Abnahmeplan (nicht destruktiv)

**Status: offen.** Dieser Leitfaden ist keine Bestätigung einer bereits erfolgten Windows- oder Hardwareprüfung. Nur mit **eigenen, entbehrlichen Testmedien** prüfen. Keine produktiven Datenträger verändern und keine absichtlichen USB-Trennungen bei wichtigen Daten.

## A. Windows 10 und Windows 11 (jeweils 64 Bit)

- [ ] `check_windows.bat` ausführen; `tenshi-windows-check.log` auf Fehler prüfen. Das Skript öffnet keine physischen Medien.
- [ ] `run_tests.bat` ausführen; `tenshi-tests.log` kontrollieren. Simulierte Fehler in der Logdatei bedeuten nicht automatisch fehlgeschlagene Tests.
- [ ] `build_windows.bat` ausführen; `dist\Tenshi.exe` muss erstellt werden.
- [ ] `Tenshi.exe --smoke-test` ausführen; Exitcode **0** prüfen. Dieser Test öffnet keine Laufwerke.
- [ ] `build_portable.bat` und `python release_tools.py verify portable_output\Tenshi_Portable_3.0.0_Win64.zip` prüfen.
- [ ] Optional `build_installer.bat` mit Inno Setup 6.3+ ausführen. Installations-, Startmenü- und Deinstallationsablauf mit einer **Testinstallation** prüfen.

## B. Oberfläche

- [ ] Logo, Symbol und beide Hauptregister sind sichtbar, der Stapel-Export ist grün.
- [ ] Hilfe oben rechts und F1 öffnen die richtigen Hilfekapitel; Suche, Themenwechsel, Esc und Register-Navigation funktionieren.
- [ ] Alle sechs Sprachen auswählen, Hilfe offen lassen und Sprache wechseln; Inhalte aktualisieren sich.
- [ ] Hell/Dunkel wechseln, Fenster neu starten; Ordnerbaum und Tabellenspalten bleiben lesbar, auch bei 1024×650 Pixeln und Windows-Anzeigeskalierung.

## C. Dateisysteme (nur synthetische Images oder Kopien)

- [ ] Testimages mit GPT/MBR und bekannten NTFS/FAT32/exFAT/ext4-Dateien öffnen.
- [ ] Partition doppelklicken; korrektes Dateisystem in **Dateien & Ordner** und korrekter Byte-Offset.
- [ ] Testdatei exportieren und Hash gegen die bewusst bekannte Quelldatei vergleichen.
- [ ] Manipuliertes Testimage bzw. geänderte Sitzungsdatei wird abgewiesen.
- [ ] Stapel-Export pausieren und wiederaufnehmen; vorhandene unbekannte Zieldateien werden nicht überschrieben.

## D. Physische Laufwerke – nur entbehrliches Testmedium

- [ ] Auf **separatem und entbehrlichem** USB-Testlaufwerk ausschließlich den schreibgeschützten Scan verifizieren.
- [ ] Bei fehlenden Rechten wird eine verständliche Meldung angezeigt; kein Schreibzugriff auf die Quelle.
- [ ] Fehlerprotokoll prüfen und sicherstellen, dass sensible Angaben vor einer Weitergabe entfernt werden.
- [ ] Keine beschädigte wertvolle Festplatte für Stresstests verwenden. Keine absichtliche Trennung unter laufendem Betrieb, wenn Daten verloren gehen könnten.

## Abschlusskriterien

Eine öffentliche Veröffentlichung erst nach dokumentierter erfolgreicher Abnahme mit verwendeter Windows-Build-Nummer, Python-/PyInstaller-Version, Testmedien, Prüfergebnissen und bekannten Einschränkungen. Eine vollständig grüne automatisierte Testsuite ersetzt diese Dokumentation nicht.
