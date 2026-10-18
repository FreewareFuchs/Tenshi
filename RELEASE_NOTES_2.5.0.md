# Tenshi 2.5.0 – Windows-Veröffentlichung

Version 2.5.0 konzentriert sich auf die Auslieferung für **Windows 10/11 (64 Bit)**. Die Datenrettungsfunktionen, zwei Hauptregister, Logo, sechs Sprachen, Hell-/Dunkelmodus, gespeicherte Fensteraufteilung und die grüne **„Stapel-Export / fortsetzen“**-Schaltfläche werden nicht geändert.

## Neue Build-Ausgaben

| Skript | Ergebnis nach erfolgreichem Windows-Build |
|---|---|
| `build_windows.bat` | `dist\Tenshi.exe` – einzelne PyInstaller-EXE mit Tenshi-Icon, Assets und Windows-Version `2.5.0.0` |
| `build_portable.bat` | `portable_output\Tenshi_Portable_2.5.0_Win64.zip` – enthält ausschließlich `Tenshi.exe`, `PORTABLE_START.txt` und `SHA256SUMS.txt` |
| `build_installer.bat` | `installer_output\Tenshi_Setup_2.5.0.exe` – Inno-Setup-Installer, Inno Setup 6.3+ erforderlich |
| `run_tests.bat` | `tenshi-tests.log` – unabhängige automatisierte Tests mit separaten Benutzer- und Logeinstellungen |

Die Windows-EXE **kann hier unter Linux nicht gebaut werden**. Das vollständige Quellpaket enthält deshalb **keine** fertige EXE und keinen fertigen Installer. Auf Windows müssen diese über die genannten Skripte erstellt werden.

## Verbesserte Windows-Releaseprüfungen

- Das EXE-Icon und die drei Tenshi-Assets werden wie zuvor in das Paket aufgenommen.
- Die EXE trägt in Windows-Dateieigenschaften die Version `2.5.0.0`.
- Die Anwendung akzeptiert den nicht-destruktiven Parameter `--smoke-test`. Dieser lädt Programmkomponenten und überprüft Ressourcen, **ohne** ein Fenster zu öffnen oder Laufwerke anzufassen. Der Rückgabecode ist `0` für Erfolg, `1` bei einem Fehler.
- `--version` gibt bei Ausführung über Python die aktuelle Versionsnummer aus. Bei `--windowed` gebauter EXE ist die Konsolenausgabe unter Windows möglicherweise nicht sichtbar; zur Versionsprüfung die Dateieigenschaften nutzen.
- Ein GitHub-Actions-Workflow ist für **Windows** eingerichtet. Er führt Tests und den echten EXE-Bau aus, prüft anschließend die EXE-Startfähigkeit und ihre Version, erstellt das portable ZIP samt Prüfsumme und baut einen Installer. Die Workflow-Datei allein beweist **nicht**, dass der Ablauf schon auf GitHub ausgeführt wurde.
- Das portable ZIP verweigert ungültige EXE-Dateien, manipulierte Prüfsummen und Archive mit unerwarteten zusätzlichen Pfaden. Ein unvollständiges ZIP wird nicht als fertiges Ergebnis hinterlassen.

## Installer-Eigenschaften

- Installation standardmäßig **pro Benutzer** unter `%LOCALAPPDATA%\Programs\Tenshi` ohne allgemeine Administratorrechte.
- Optionales Desktopsymbol, Startmenüeintrag und Deinstallation.
- Prüft x64-kompatible Windows-Systeme. Kompatibilität mit Windows 11 auf ARM64 beruht auf dessen x64-Emulation und wurde nicht praktisch getestet.
- Der gleiche Anwendungscode darf bei der Nutzung weiterhin **erhöhte Rechte** für den direkten Zugriff auf physische Datenträger benötigen.
- Das Setup ist **nicht digital signiert**. Windows SmartScreen/Antivirus können deshalb Warnungen anzeigen; solche Warnungen nicht ungeprüft umgehen.

## Was „portable“ genau bedeutet

Die portable Ausgabe lässt sich ohne Setup aus einem Ordner starten. Einstellungen und Diagnoseprotokolle werden weiterhin im Windows-Benutzerprofil gespeichert; sie ist **nicht** vollständig USB-portabel. Weder portable ZIP noch Installer enthalten Dateiinhalte, Datenträgerabbilder oder Nutzerprotokolle.

## Grenzen

Die Tests verwenden synthetische Images und simulierte Fehler. Ein erfolgreicher Smoke-Test prüft den Start und die Einbindung der Programmdateien, aber **nicht** das Imaging oder die Datenrettung echter Laufwerke. Zuerst mit Testimages und auf getrennten Zielmedien ausprobieren; beschädigte Datenträger möglichst über geeignete Imaging-Verfahren sichern. Tatsächlicher Windows-Installerbau und Windows-Smoke-Test müssen auf einem Windows-System bestätigt werden.
