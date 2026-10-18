# Tenshi 2.7.0 – Imaging-Verbesserungen

**Neue Funktionen:** 0–3 zusätzliche Leseversuche bei bestätigten Medienfehlern auf kleinster Leseeinheit, konfigurierbare Fehlerstrategie (Nullfüllung oder sicherer Stopp), Fehlerstellen-Bericht sowie Reaktion auf Unterbrechungen während eines fehlerhaften Lesevorgangs. Die Wiederaufnahme verwendet den letzten sicher bestätigten Block. Die neuen Optionen können beim Fortsetzen für noch nicht gesicherte Bereiche geändert werden.

**Sicherheit:** Quelle bleibt lesegeschützt; nach bestätigtem Lesefehler eingefügte Nullen sind **keine** Originaldaten. Berechtigungs- und Verbindungsfehler dürfen nicht als defekte Sektoren maskiert werden. Zusätzliche Leseversuche verschlechtern unter Umständen den Zustand beschädigter Hardware. Bestehende Datenrettungsfunktionen und das Sitzungsformat aus 2.6.0 bleiben erhalten.

**Tests:** Synthetische Fehlerbilder und GUI-Regressionstests unter Linux. Echte physische Datenträger und Windows-EXE müssen weiterhin auf realer Hardware geprüft werden.

**Windows:** `build_windows.bat` -> `dist\Tenshi.exe`; `run_tests.bat` startet die separate Testsuite. `build_portable.bat` und `build_installer.bat` erstellen die optionalen Verteilungsformate nach erfolgreichem EXE-Bau.
