# Tenshi 2.1.0 – Stabilität und Windows-I/O

## Inhalt der Version

- **Stapel-Export**: Statusdateien werden in einem einzigartigen temporären Dateinamen erstellt, mit `fsync` geschrieben und atomar ersetzt. Bei vorübergehenden Windows-Dateisperren erfolgt eine begrenzte Wiederholung. Bestehende Statusdateien bleiben bei endgültigen Fehlern erhalten; die Anwendung meldet die Ursache und täuscht keine erfolgreiche Fortsetzung vor.
- **Exportberichte**: Neuer sicherer temporärer Dateiname und kurze Wiederholungsversuche bei Windows-Sperren. Unabhängige frühere `.tmp`-Dateien werden nicht gelöscht oder überschrieben.
- **Imaging**: Bei Zugriffsverweigerung, ungültigem Leseauftrag oder zu kurzen Geräteantworten wird **abgebrochen**, anstatt die Fehler als bestätigte defekte Sektoren mit Nullen zu ersetzen. Bestätigte Medien-Lesefehler (z. B. I/O-Fehler) können weiterhin als Datenlücken erfasst werden. Der vorhandene Prüfpunkt-Journal-Fallback bleibt erhalten.
- **Windows-Rohdatenträger**: Nicht ausgerichtete Leseanfragen werden weiterhin sektorausgerichtet durchgeführt. Verweigerte Geräteöffnungen liefern jetzt verständlichere Hinweise, ohne Schreibrechte anzufordern.
- **Fehlerprotokoll**: Automatische technische Fehleraufzeichnung mit begrenzter Größe; im Hauptfenster oben rechts über **Fehlerprotokoll** einsehbar. Die Protokollierung erfasst nur Fehlerart, numerische Fehlercodes und sichere technische Kenngrößen – keine Dateiinhalte oder vollständigen Dateinamen.
- **Bewährte Funktionen**: Tenshi-Logo, sechs Sprachen, zwei große Hauptregister, grüne Schaltfläche „Stapel-Export / fortsetzen“, Image-Sicherung, Partitionssuche und Dateiwiederherstellung sind erhalten geblieben.

## Sicherheits- und Kompatibilitätshinweise

- Quellgeräte werden ausschließlich mit Leserechten geöffnet. Image-Dateien und Wiederherstellungsziele werden absichtlich beschrieben; ein bereits begonnenes Image kann beim Fortsetzen verändert werden.
- Bestehende Imaging-Dateien (`.recovery.json`, `.recovery.json.journal`) bleiben kompatibel, ebenso bisherige Stapel-Export-Statusdateien (`recoverydesk_status.json`). Die alten Statusdateinamen werden **absichtlich** beibehalten, damit die Wiederaufnahme funktioniert.
- Fehlgeschlagene Wiederaufnahmen bitte zuerst diagnostizieren. Weder Quellgerät noch Image umformatieren, reparieren oder die Statusdateien löschen.
- Fehlerprotokolle werden standardmäßig in `%LOCALAPPDATA%\\Tenshi\\Logs\\tenshi-errors.log` gespeichert. Es handelt sich um eine normale Datei auf dem Systemlaufwerk. Bei Verdacht auf Hardwaredefekte möglichst ein separates, gesundes Ziel verwenden.
- Die Benutzeroberfläche und die technischen Komponenten wurden unter Linux mit einer virtuellen grafischen Anzeige und synthetischen Datenträgerabbildern getestet. **Ein echter Windows-10/11-Hardwaretest, eine Windows-EXE-Ausführung und ein Installer-Test stehen aus.**

## Validierung

`python -m unittest discover -s tests -q`

Die Tests umfassen simulierte Windows-Dateisperren, Zugriffsausfälle und die bisherigen Parser-/Exportfunktionen. Auf Linux muss für die GUI-Tests ein virtuelles Display vorhanden sein (`xvfb-run -a`).
