# Tenshi 2.1.1 – Build-Fehlersuche

Die Logs `tenshi-errors.log` und `tenshi-errors (1).log` enthalten Operationen
`raw_device_alignment`, `batch_export`, `imaging` und `test_io`.
Viele dieser Fehler werden von der automatisierten Testsuite bewusst erzeugt.
Sie sind nicht der genaue Windows-Buildfehler.

## Neuer Ablauf

1. Alte Tenshi-Version schließen und das **neue Paket** in einen neuen Ordner entpacken.
2. `build_windows.bat` ausführen. Das Skript erzeugt `tenshi-build.log`.
3. Falls ein Fehler angezeigt wird, dessen Schritt und die letzten Zeilen
   aus `tenshi-build.log` prüfen.
4. `run_tests.bat` kann unabhängig davon ausgeführt werden; sein Ergebnis
   liegt in `tenshi-tests.log`.

## Typische Fehlerstellen

- Schritt 1: Python nicht gefunden oder falsche Architektur.
- Schritt 2: Virtuelle Umgebung fehlgeschlagen (Zugriff, Antivirus, defekte `.venv`).
- Schritt 3: PyInstaller nicht installierbar (Netzwerk, Proxy, pip, Berechtigung).
- Schritt 4: PyInstaller-Buildfehler – vollständige Ursache in `tenshi-build.log`.

Im Fehlerfall `tenshi-build.log` vor dem Teilen auf private lokale Pfade prüfen.
Das Ausführen der automatisierten Tests ist nicht mit einem Test des fertigen
Windows-Programms auf echten Festplatten gleichzusetzen.


## Neue Release-Skripte (2.5.1)

- `build_windows.bat`: erzeugt `dist\Tenshi.exe`, jetzt mit Windows-Version `2.5.1.0` und Tenshi-Icon.
- `build_portable.bat`: setzt eine vorhandene `dist\Tenshi.exe` voraus; verpackt sie mit SHA-256 in ein ZIP. Eine fehlerhafte Eingabedatei wird abgelehnt.
- `build_installer.bat`: setzt außerdem Inno Setup 6.3 oder neuer voraus; Details bei Fehlern in `tenshi-installer-build.log`. Der gemeldete Ausgabename ist jetzt `Tenshi_Setup_2.5.1.exe`.
- `--no-pause` unterdrückt Pausen im nicht-interaktiven Windows-Build/Installerlauf für die CI.
- `Tenshi.exe --smoke-test` kann zur schnellen Startprüfung ohne Laufwerkszugriff dienen. `0` = erfolgreich, `1` = Ressourcen-/Importfehler. Keine Aussage über die Rettungsqualität.
- Windows SmartScreen-Warnungen wegen fehlender Code-Signierung sind möglich. Keine Sicherheitsprogramme ungeprüft deaktivieren.

## Tenshi 2.9.0 – Windows- und USB-Diagnose

1. `check_windows.bat` ausfuehren; `tenshi-windows-check.log` pruefen. Dies oeffnet keine Datentraeger.
2. `run_tests.bat` separat starten. Simulierte Zugriffsfehler im Test sind kein Beweis fuer ein Hardwareproblem.
3. `build_windows.bat` baut die EXE. Bei Abbruch `tenshi-build.log` pruefen.
4. WinError 21/31/55/433/1167: Quelle nicht mehr erreichbar/USB getrennt – Abbruch und Verbindung pruefen, keine automatisch wieder aufgenommene Quelle annehmen.
5. WinError 5/32/33: Berechtigungen oder Dateisperren; Quelllaufwerk nur schreibgeschuetzt, bei Bedarf als Administrator starten.
6. WinError 23/1117: Bestaetigter Lese-/CRC-Fehler; Imaging kann ihn dokumentieren. Nullen sind keine geretteten Daten.
7. Kurze Rohgeraete-Leseantwort: fataler Fehler statt vermeintlichem End-of-File oder nicht verifizierter Nullfuellung.

Vor dem Teilen der Build- oder Testlogs persoenliche Windows-Verzeichnispfade pruefen.
