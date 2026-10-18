# Tenshi 2.1.2 – Windows-Regressionstest-Hotfix

- Ursache: ein `RotatingFileHandler` hielt bei einem automatisierten Test die temporäre Datei `diagnostics/tenshi-errors.log` offen.
- Folge unter Windows: `[WinError 32]` beim Aufräumen des Testordners.
- Lösung: Ein rotierender Dateihandler schließt den Stream nach jedem Logeintrag.
- Neue Prüfung: Datei kann nach dem Schreiben umbenannt und der temporäre Ordner gelöscht werden.
- Keine Änderung der Wiederherstellung, Quellenzugriffe, UI oder des Imageformats.
- `build_windows.bat` erzeugt die EXE, `run_tests.bat` führt die Tests getrennt aus.
- Die Tests wurden auf Linux ausgeführt; der Windows-Testsatz muss auf dem Anwendergerät bestätigt werden.
