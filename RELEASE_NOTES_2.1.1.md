# Tenshi 2.1.1 – Build-Hotfix

Die hochgeladenen `tenshi-errors.log`-Eintraege enthalten absichtlich ausgeloeste
Fehlerszenarien der automatisierten Tests. Ein echter Fehler beim Erstellen
der Windows-EXE war daraus nicht erkennbar.

- Build und Tests getrennt: `build_windows.bat` erstellt nun direkt die EXE.
- `run_tests.bat` prueft die Anwendung unabhaengig davon.
- `tenshi-build.log` nennt den fehlerhaften Schritt und enthaelt die
  tatsächliche Python-/pip-/PyInstaller-Fehlermeldung.
- Tests arbeiten mit isoliertem Temp-Einstellungs- und Logverzeichnis.
- Das Programm, die sechs Sprachen, die zwei Hauptregister, Logo und
  Datenrettungsfunktionen sind gegenüber 2.1.0 unveraendert.

**Wichtig:** Dieses Paket wurde auf Linux syntaktisch und mit
automatisierten Tests geprüft, aber nicht auf Windows kompiliert.
