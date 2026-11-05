# Tenshi 3.0.14 – Veröffentlichung in Vorbereitung

Die Funktionen aus PR #133–#139 sind praktisch abgenommen und im Hauptstand enthalten. Dieser Release bündelt die Ergebnisansicht, binäre Office-Dateien und die Freiraumsuche für NTFS, FAT32 und exFAT. Die endgültigen 3.0.14-Pakete werden gemeinsam gebaut; ihre manuelle Versions- und Startbestätigung sowie die Veröffentlichung stehen noch aus.

## Änderungen

- **Funde direkt im Signaturreiter:** Sortierbare Liste mit Typ, Größe und Fundposition; Mehrfachauswahl, Vorschau mit Vor/Zurück, Dateiprüfung und Stapel-Export direkt aus der Liste.
- **Ergebnisse eingrenzen:** Suchtext, Typ und Mindestgröße in KiB kombinieren, ohne das Image erneut zu lesen. Ausgeblendete Funde werden abgewählt; Vorschau, Strg+A und Export verwenden die sichtbare Auswahl.
- **Nur freie Bereiche:** Wahlweise NTFS, FAT32 oder exFAT mit Partitionsoffset durchsuchen. Belegungsdaten werden begrenzt geprüft; Funde überschreiten keine belegten Grenzen. Suchstände und Exportaufträge behalten Bereich und Offset bei und prüfen die Metadaten beim Fortsetzen erneut.
- **Binäre Office-Dateien:** Zusammenhängende DOC-/XLS-/PPT-Strukturen in CFB-Containern erkennen und exportieren. Vorschau und Inhaltsprüfung melden eine ausdrückliche **Teilprüfung** lesbarer interner Zuordnungen und ausgewählter Kopfdaten. Der Export-Dateifilter enthält die drei Endungen.
- **Gemeinsame VM-Ordner:** Eine nicht unterstützte Verzeichnissynchronisierung nach dem Speichern eines Suchstands führt nicht mehr zu einer falschen Fehlermeldung. Die Datei selbst wird weiterhin synchronisiert; echte Schreibfehler bleiben Fehler. Rücklese-Handles werden vor dem Entfernen temporärer Prüfsummendateien geschlossen.
- **Hilfe und Bedienung:** Der Unterschied zwischen Dateisystemsuche und Signatursuche sowie Umfang und Grenzen der neuen Funktionen sind in allen sechs Sprachen erklärt.

## Umfang und Grenzen

Die Signatursuche arbeitet auf regulären Images und bleibt schreibgeschützt. Die Vollsuche benötigt kein lesbares Dateisystem; die Freiraumsuche braucht passende, verlässlich lesbare Belegungsdaten. Fehler führen nicht zum stillen Wechsel auf eine Vollsuche. exFAT unterstützt genau ein FAT-/Bitmap-Paar; TexFAT ist ausgeschlossen. Es erfolgt keine vollständige Dateisystemkonsistenzprüfung.

Originalnamen, Ordner und Löschstatus sind bei Signaturfunden unbekannt. Freie Cluster oder lesbare Strukturen beweisen keine vollständigen, unbeschädigten Originalinhalte. Fragmente werden nicht zusammengesetzt. Alte Suchstände behalten ihren bisherigen Formatumfang; für zusätzliche DOC/XLS/PPT-Funde ist gegebenenfalls ein neuer Suchlauf nötig.

Die Office-Teilprüfung stellt keine Seiten, Tabellen oder Folien dar und prüft keine Dokumentsemantik, eingebetteten Dateien oder Makros. Sie bleibt auf 32 MiB pro Datei sowie die bisherigen Zeit- und Speichergrenzen beschränkt. Dokumentaktionen werden nicht ausgeführt und Inhalte nicht entschlüsselt.

[Benutzerhilfe](HILFE_3.0.14.md) · [Signatursuche und Grenzen](docs/IMAGE_SIGNATURE_SEARCH.md) · [Inhaltsprüfung](docs/CONTENT_PREVIEW.md) · [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.14.json)

## Pakete und Freigabestand

- `Tenshi_Setup_3.0.14_Win64.exe`
- `Tenshi_Portable_3.0.14_Win64.zip`
- `tenshi-recovery_3.0.14-1_all.deb`

Der gemeinsame Vorbereitungsworkflow baut die drei Pakete mit Kennung `stable` aus demselben sauberen Commit. Herkunft und Inhalt stehen in `release_manifest.json`, `SHA256SUMS.sha256` und den Paket-Prüfsummendateien. Flatpak bleibt experimentell und gehört nicht zum stabilen Dreierpaket.

Die Funktionsabnahmen sind bestätigt. Endgültige Paketstarts und Versionsanzeigen sowie Downloads, signierte APT-Quelle und Website bleiben getrennte Freigabeschritte. Bis dahin ist 3.0.13 die veröffentlichte stabile Version.

Fragen und Verbesserungsvorschläge: **kontakt@freewarefuchs.de**.
