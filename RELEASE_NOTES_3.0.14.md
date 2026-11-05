# Tenshi 3.0.14 – stabil veröffentlicht am 05.11.2026

Die Funktionen aus PR #133–#139 sind praktisch abgenommen und im Hauptstand enthalten. Dieser Release bündelt die Ergebnisansicht, binäre Office-Dateien und die Freiraumsuche für NTFS, FAT32 und exFAT. Die endgültigen 3.0.14-Pakete sind gemeinsam gebaut, manuell bestätigt und veröffentlicht.

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

Die Funktionen und endgültigen Paketstarts und Versionsanzeigen sind manuell bestätigt. Der [stabile Release v3.0.14](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.14) ist veröffentlicht. Die unveränderten Pakete stammen aus Commit `de9a3b9733528c87a19a3fdf314462105302ac41` ([gemeinsamer Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/42047640267)).

| Paket | Bytes | SHA256 |
| --- | ---: | --- |
| `Tenshi_Setup_3.0.14_Win64.exe` | 28502383 | `bbd0b3fb8c4ad6c6adab5e86615141aa0d80dd18bf4e10087b5ac964fc73f7eb` |
| `Tenshi_Portable_3.0.14_Win64.zip` | 26749560 | `94a44f48da769a0d6f53ab2795d31bb01098b97cf6bcb9b8e7145e58899a80ce` |
| `tenshi-recovery_3.0.14-1_all.deb` | 928674 | `9a659bcb19be7889bd8db0923aea91d905ee124baf7b2b64e7249275781bd130` |

Alle sieben GitHub-Assets sind mit Größe und SHA256 geprüft. Die APT-Signatur wurde in Mint mit dem bisherigen Archivschlüssel `15D67DDA4D0D3BD1DD10A8C3B714CC0415B04529` geprüft; alle 19 öffentlichen APT-Dateien stimmen mit dem geprüften Export überein. Elf ältere Pakete und der öffentliche Schlüssel bleiben unverändert. Nach dem Website-Upload waren alle 25 abschließenden öffentlichen Vergleiche erfolgreich: Katalog, zwölf Programm-/Anleitungsseiten in sechs Sprachen, Downloads und APT-Metadaten. Der vorherige Website-Stand ist gesichert.

Die später abgenommene CSV-Fundliste aus PR #141 gehört zum folgenden Entwicklungsstand und ist nicht in diesen Release-Paketen enthalten. [Noch nicht veröffentlichte Änderungen](CHANGELOG.md).

Fragen und Verbesserungsvorschläge: **kontakt@freewarefuchs.de**.
