# Tenshi 3.0.10 – Exportauftrag nach Neustart wieder öffnen

Stabile Pakete in Vorbereitung. Die Funktionen aus PR #115 sind im Windows-/
Flatpak-Testpaket manuell bestätigt. Die endgültige Paketabnahme und die
Veröffentlichung folgen getrennt.

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

Installer, Portable und DEB werden gemeinsam mit expliziter Kennung `stable`
aus einem sauberen Commit gebaut. Manifest und `.sha256`-Dateien dokumentieren
Größen, Prüfsummen und Quellstand. Dokumente erhalten keine eigenen Sidecars.

Abgenommener Funktionsstand: `821f244dd89550e29cd64e24fdc789d49abb936c`,
übernommen als `27e5d76933adfbe0bcc27544010dbc74320c5a63` mit identischem Dateistand.
Windows und Linux bestehen jeweils 898 Tests (83 beziehungsweise sechs Skips).
Das installierte experimentelle Flatpak ist ebenfalls geprüft. Der Anwender
bestätigt das Testpaket mit „alle Prüfungen erfolgreich“. Die endgültigen
stabilen Pakete erhalten eine gesonderte Start- und Versionsabnahme.

GitHub-Veröffentlichung, signierte APT-Quelle und Website folgen nach der
Paketabnahme. Frühere veröffentlichte Pakete und Prüfsummen bleiben erhalten.
