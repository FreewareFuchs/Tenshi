# Support-Bericht

**Fehlerprotokoll → Support-Bericht** öffnet eine Vorschau. Mit
**Support-Bericht speichern** wird diese Momentaufnahme als UTF-8-JSON gespeichert.
Es erfolgt kein Versand und kein Upload. Vor dem Weitergeben die Vorschau prüfen.
Vorhandene Dateien werden nicht überschrieben. Ausgewählte Quellen und bekannte
Analysequellen werden gegen das Ausgabeziel geprüft, wie bei anderen Berichten.

Enthalten sind Version/Beta/Commit und Entwicklungsstatus, Betriebssystem-/Kernel-
und Architekturangaben, bei Linux Distributions-ID und Version, Python-/Tk-Version,
Fenstersystem, UI-Sprache sowie gezählte numerische Fehlercodes aus dem aktuellen
Fehlerprotokoll. Die technischen JSON-Schlüssel sind sprachunabhängig.

Es werden keine Quellen geöffnet oder Datenträger aufgelistet. Quellpfade,
Dateinamen, Suchausdrücke, Einstellungen, Host-/Benutzernamen, Rohprotokolle,
Exception-Texte und Datei-Inhalte werden nicht aufgenommen. Betriebssystemangaben
können eigene Kernel-Versionszusätze enthalten.

Die Fehlerstatistik liest höchstens die letzten 128 KiB der aktuellen Logdatei.
Nur vollständig erkannte strukturierte Logzeilen werden gezählt; unbekannte Zeilen
werden verworfen. Operationen und Exception-Namen werden nicht kopiert. Rotierte
Logs bleiben unberücksichtigt. `tail` bedeutet begrenzter Ausschnitt, `missing`
keine aktuelle Logdatei, `unavailable` Lesefehler. Null erkannte Fehler beweist
keine fehlerfreie Ausführung. Tests können ebenfalls Fehlercodes hinterlassen.
