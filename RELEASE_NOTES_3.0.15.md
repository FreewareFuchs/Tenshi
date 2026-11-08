# Tenshi 3.0.15 – Veröffentlichung in Vorbereitung

Dieses Bedienungsupdate bündelt die abgenommenen Funktionen aus PR #141,
#143, #144 und #146 sowie die anhand unabhängiger Formatprüfungen bestätigte
XFS-Korrektur aus PR #145. Die endgültigen stabilen Pakete werden gemeinsam
gebaut; ihre Versions- und Startbestätigung sowie die Veröffentlichung folgen
getrennt. Bis dahin bleibt 3.0.14 die veröffentlichte stabile Version.

## Änderungen

- **CSV-Fundliste:** Alle sichtbaren Signaturfunde in aktueller Sortierung sichern,
  unabhängig von der markierten Auswahl. Der Bericht enthält Typ, Byte-Größe,
  absoluten Offset, Quelle und ursprüngliche Sucheinstellungen. UTF-8 mit BOM
  und Semikolon; bestehende Dateien werden nicht überschrieben. Für diesen
  Bericht entstehen keine zusätzlichen Prüfsummendateien.
- **Kontextmenü und Tastatur:** Rechtsklick oder Umschalt+F10 öffnen die bestehenden
  Aktionen. Mehrfachauswahl bleibt bei Rechtsklick auf einen markierten Fund
  erhalten; Dateiprüfung bleibt auf eine Datei begrenzt. Strg+F fokussiert den
  Suchfilter des aktiven Reiters, Escape hebt nur die Fundauswahl auf.
- **Dauerhafte Suchlauf-Zusammenfassung:** Quelle, Bereich, Offset, Kategorien und
  Prüflimit bleiben dem tatsächlichen Lauf zugeordnet. Filter und Optionen für
  den nächsten Lauf ändern diese Angaben nicht. Keine passenden Signaturen,
  ausgefilterte Funde, Prüfgrenze, Anhalten und Fehler werden unterschieden.
- **Direkte Partitionsauswahl:** Zwischen gesamtem Image, manuell eingegebenen
  freien Bereichen und erkannten NTFS-/FAT32-/exFAT-Partitionen wählen.
  Partitionswahl übernimmt Dateisystem und Byte-Offset. Veraltete Kontexte und
  veränderte Images werden abgefangen; Warnmarkierungen und Startbestätigung
  bleiben erhalten. Manuelle Eingaben bleiben möglich.
- **XFS-NREXT64:** Bei entsprechend gekennzeichneten v3-Inodes den Datenzähler
  aus dem 64-Bit-Feld lesen, statt einen Attributzähler von null als Sparse-Datei
  zu behandeln. Gegenproben prüfen Standardformat und nrext64=0/1 mit unabhängig
  erstellten Dateisystemen. Grenzen der Inline-Liste und Ablehnung widersprüchlicher
  Metadaten bleiben bestehen; keine zusätzliche Btree-Dateidaten-Unterstützung.

## Umfang und Grenzen

Die Signatursuche arbeitet weiterhin auf regulären Images und bleibt
schreibgeschützt. Die Vollsuche benötigt kein lesbares Dateisystem; die
Freiraumsuche benötigt verlässlich lesbare Belegungsdaten einer unterstützten
NTFS-, FAT32- oder exFAT-Partition. Bei Fehlern gibt es keinen stillen Wechsel
auf eine Vollsuche. Erkannte Partitionen können heuristische Kandidaten sein;
sie garantieren keine intakten Metadaten.

Ein beendeter Lauf bestätigt weder, dass alle Dateien gefunden wurden, noch
vollständige oder unbeschädigte Originalinhalte. Dateisignaturen liefern keine
ursprünglichen Namen, Ordner oder Löschzustände; Fragmente werden nicht
zusammengesetzt. Die bestehenden Format-, Größen-, Lese- und Fundgrenzen bleiben
unverändert. Das angezeigte Prüflimit betrifft nur die in der Einstellung
genannten Bild-/PDF-/Office-/ZIP-Prüfungen, nicht sämtliche Dateiformate.

Die CSV-Fundliste verwendet den bestehenden Ergebnisindex ohne erneute
Inhaltslesevorgänge und ist kein Nachweis eines Exports oder der Originalintegrität.
Die Suchlauf-Zusammenfassung gilt für die aktuelle Sitzung und erzeugt keine
zusätzliche Datei. Alte Suchstände und Exportaufträge behalten ihre bisherigen
Formatkennungen und Prüfgrenzen. Die XFS-Korrektur ist keine allgemeine
Dateisystemkonsistenzprüfung oder Reparatur. Die Quellen werden nicht verändert.

[Benutzerhilfe](HILFE_3.0.15.md) · [Signatursuche](docs/IMAGE_SIGNATURE_SEARCH.md) ·
[XFS-Prüfung](docs/XFS_EXTENT_COUNTERS.md) ·
[Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.15.json)

## Pakete und Freigabestand

- `Tenshi_Setup_3.0.15_Win64.exe`
- `Tenshi_Portable_3.0.15_Win64.zip`
- `tenshi-recovery_3.0.15-1_all.deb`

Der gemeinsame Vorbereitungsworkflow baut diese drei Pakete mit Kennung `stable`
aus demselben sauberen Commit und prüft Build-Herkunft, Paketgrößen und SHA256.
Manifest und Prüfsummendateien des vorbereiteten Bundles bleiben unverändert.
Flatpak bleibt experimentell und gehört nicht zum stabilen Dreierpaket.

Funktionsabnahmen sind bestätigt. Endgültige Paketstarts und Versionsanzeigen,
GitHub-Veröffentlichung, signierte APT-Quelle und Website bleiben getrennte
Freigabeschritte. Bestehende Releases und frühere Paketprüfsummen bleiben erhalten.

Fragen und Verbesserungsvorschläge: **kontakt@freewarefuchs.de**.
