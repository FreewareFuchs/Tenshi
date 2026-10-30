# Tenshi 3.0.10 – Exportauftrag nach Neustart wieder öffnen

Seit 30.10.2026 stabil [auf GitHub veröffentlicht](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.10).
Funktionen und endgültige Installer-/Portable-/Mint-DEB-Versionsanzeigen sind
manuell bestätigt. Website und signierte APT-Quelle bieten 3.0.10;
alle 25 öffentlichen Abschlussvergleiche sind erfolgreich.

## Wiederaufnahme

**Exportauftrag öffnen** verwendet den erzeugten `Tenshi_Export_…`-Unterordner.
Neue Aufträge speichern Auswahl-IDs und Scan-Einstellungen in ihrer bisherigen
Statusdatei. Erst nach Bestätigung der Quelle wird das Dateisystem schreibgeschützt
erneut eingelesen. Quelle und vollständiger Plan müssen übereinstimmen. Ein
Textzähler zeigt die Vorbereitung; Ablehnen und Abbrechen während dieser Phase
verändern den Exportordner nicht.

Fertige Dateien werden erneut per SHA256 geprüft. Nach kontrolliertem Abbruch
entfernte Teil-Dateien beginnen weiterhin von vorn. Es gibt keine über Neustarts
gespeicherte Pause innerhalb einer Datei. Unbekannte vorhandene Dateien bleiben
erhalten. Die ursprüngliche Quelle muss unverändert unter demselben Pfad
erreichbar sein; ein begrenzter Fingerabdruck ersetzt keinen Vollvergleich.

Ältere Aufträge bleiben über dieselbe Quelle, Auswahl und den ursprünglichen
Zielordner manuell fortsetzbar. Ein bestätigter Lauf ergänzt die Auswahlangaben.
Dialoge und Hilfe unterscheiden diesen manuellen Weg vom neuen Öffnen des
erzeugten Unterordners. Alle sechs Sprachen sind berücksichtigt.

Es entstehen keine neue Index-/Inhaltskopie und keine Auftragsliste im Profil.
Die vorhandene Statusdatei enthält private Pfade und gehört zusammen mit `files`
zum Export. Die erneute Analyse verursacht zusätzliche Lesezugriffe.

[Benutzerhilfe](HILFE_3.0.10.md) · [Bedienung und Grenzen](docs/EXPORT_RESUME.md) ·
[Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.10.json).

## Pakete und Prüfstand

- `Tenshi_Setup_3.0.10_Win64.exe`
- `Tenshi_Portable_3.0.10_Win64.zip`
- `tenshi-recovery_3.0.10-1_all.deb`

Die abgenommenen Pakete wurden mit Kennung `stable` unverändert aus dem sauberen
Commit `6ffd94118181c67db0fa299d9edd426f843bfe47` gebaut
([gemeinsamer Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/41032646545)).
Der Tag `v3.0.10` zeigt auf diesen Build-Commit. Integrationscommit
`d68f8f7a6c7e0c3e4f48203a9934b5a1dbd55e49` enthält denselben Dateistand.

Der Funktionsstand aus PR #115 war als
`821f244dd89550e29cd64e24fdc789d49abb936c` im Windows-/Flatpak-Testpaket
mit „alle Prüfungen erfolgreich“ bestätigt und mit identischem Dateistand als
`27e5d76933adfbe0bcc27544010dbc74320c5a63` übernommen.
Die endgültigen Paketversionen bestätigt der Anwender mit „alle versionen stimmen“.
Windows und Linux bestehen jeweils 898 Tests (83 beziehungsweise sechs
plattformbedingte Ausnahmen). Manifest, Paketgrößen, SHA-Dateien,
Windows-Ressourcen und Programmstart, DEB-Buildidentität sowie enthaltene
Exportmodule und Hilfe sind geprüft. Diese Abnahme ist keine Garantie für
andere Hardware oder beschädigte Medien.

Das DEB `3.0.10-1` hat 830106 Bytes und SHA256:
`ca273c2a75c4c4dd5974bdac1e641c320a73140f23cfa9012b485d36def9bdc1`.
Die APT-Signatur wurde in Mint mit Archivschlüssel
`15D67DDA4D0D3BD1DD10A8C3B714CC0415B04529` geprüft. Alle 15 öffentlichen
APT-Dateien entsprechen dem VM-Export; öffentlicher Schlüssel und sieben ältere
DEBs sind unverändert erhalten. Die öffentliche Prüfung vergleicht Bytes und
Prüfsummen mit diesem separat signaturgeprüften Export.

Alle sieben GitHub-Assets und die Website-/Download-Verweise sind geprüft.
Der Website-Katalog enthält die [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.10.json).
Die sechs Anleitungen erklären Wiederaufnahme und eindeutige Ordnerwahl;
veraltete Anweisungen zur ausschließlich manuellen Wiederaufnahme wurden ersetzt.
Der vorherige Serverstand ist gesichert. Die vorbereiteten Manifestdateien mit
`published: false` bleiben unveränderte Buildnachweise; die tatsächliche
Veröffentlichung steht in separaten Abschlussberichten. Frühere Releases und
ihre Prüfsummen bleiben erhalten. Dokumente und Bilder erhalten keine
zusätzlichen Prüfsummen-Sidecars. Flatpak bleibt experimentell und gehört nicht
zu den drei regulären Paketen.
