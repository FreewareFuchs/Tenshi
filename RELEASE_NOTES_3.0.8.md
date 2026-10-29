# Tenshi 3.0.8 – Export steuern und Prüfsummen sichern

Seit 29.10.2026 stabil [auf GitHub veröffentlicht](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.8).
Funktionen, endgültige Installer-/Portable-/Mint-DEB-Paketstarts, Versionsanzeigen
und die aktualisierte Hilfe sind manuell bestätigt. Die Website und die signierte
APT-Quelle bieten 3.0.8; alle 25 öffentlichen Abschlussvergleiche sind erfolgreich.

## Pause, Abbrechen und Fortsetzen

- Pause hält denselben Exportauftrag an einer vorhandenen Lese-/Schreibgrenze an.
  Die angefangene Datei, Fortschrittszähler und laufende SHA256-Berechnung bleiben
  erhalten. Fortsetzen arbeitet im selben Auftrag weiter, solange Tenshi offen ist.
- Abbrechen beendet kontrolliert und entfernt eine unvollständige Datei. Nach
  Abschluss des Abbruchs ist Fortsetzen wieder verfügbar. Es verwendet die
  gespeicherte Quelle, Auswahl und den ursprünglichen Zielordner, unabhängig
  von der inzwischen angezeigten Dateiansicht. Fertige Dateien werden geprüft;
  die unvollständige Datei wird von vorn kopiert.
- Bei geänderter Quelle oder fehlendem bisherigen Exportordner wird kein neuer
  Auftrag stillschweigend angelegt. Quelle und Ziel werden wie bisher geprüft.
- Schließen blendet die Fortschrittsansicht aus. Beim bestätigten Beenden des
  Hauptfensters wartet Tenshi auf die kontrollierte Unterbrechung laufender
  Schreibvorgänge. Eine Pause verhindert das Beenden nicht. Abschlussfehler
  bleiben vor dem Schließen sichtbar.

## Prüfsummendateien

- Nach jeder vollständig kopierten und bestätigten Datei wird eine `.sha256`
  unter `Pruefsummen_Einzeln` im Exportordner gespeichert.
- Nach vollständig erfolgreichem Export entsteht `SHA256SUMS.sha256`. Erst nach
  sicherem Speichern und Rücklesen der Sammeldatei werden die unveränderten eigenen
  Einzeldateien und der anschließend leere Zwischenordner entfernt.
- Bei Abbruch oder Fehlern bleiben vorhandene Einzeldateien erhalten. Ein Ordner
  mit weiteren fremden Dateien wird nicht gelöscht. Geänderte oder ersetzte
  Prüfsummendateien werden nicht überschrieben oder als eigene Dateien entfernt.
- Ergebnisse und Fehler stehen im Bericht. Ungeprüfte Dateien erhalten keine
  bestätigte Prüfsumme; fertige Kopien mit noch offener Prüfung werden wie bisher
  anhand des gespeicherten Kopier-Prüfwerts erneut geprüft.

## Fortschrittsfenster

Die Aktionen stehen als Ergebnisbericht / Bericht speichern, Pause bzw.
Fortsetzen / Zielordner öffnen und Abbrechen / Schließen. Der Bericht erläutert
den Prüfumfang. Alle sechs Oberflächensprachen und Hell/Dunkel sind berücksichtigt.
Die Offline-Hilfe erläutert den aktuellen Export- und Imaging-Ablauf. Unter
„Über Tenshi“ steht ein Kontakt für Fragen und Verbesserungsvorschläge.
[Aktuelle Benutzerhilfe](HILFE_3.0.8.md).

Ein Rasterfeld entspricht einem Prozent des gesamten Exportumfangs und kann
mehrere Dateien überlappen. Bestätigte Daten der vorherigen Datei und noch
ungeprüfte Daten der laufenden Datei erscheinen bis zu deren Bestätigung gemischt.
Die Felder sind keine physischen Sektoren; eine Exportbestätigung bestätigt
nicht die ursprüngliche Integrität wiederhergestellter Inhalte.

## Pakete und Prüfstand

- `Tenshi_Setup_3.0.8_Win64.exe`
- `Tenshi_Portable_3.0.8_Win64.zip`
- `tenshi-recovery_3.0.8-1_all.deb`

Die abgenommenen Pakete wurden mit Kennung `stable` unverändert aus dem sauberen
Commit `461fce51792c37903c2ce6b45c6810ba02f693c7` gebaut
([gemeinsamer Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40878364119)).
Der Tag `v3.0.8` zeigt auf diesen Build-Commit. Der Integrationscommit
`10fc1e33d0ff5c287b5a37d97149fe74388d87ba` enthält denselben Dateistand.

Windows und Linux bestehen jeweils 856 Tests (82 beziehungsweise 6 plattformbedingte
Skips). Manifest, Paketgrößen, Prüfsummen, Windows-Ressourcen, Programmstarttest
und die im DEB enthaltene Hilfe sind geprüft. Der Anwender hat die endgültigen
Pakete mit „ok, funktioniert alles“ bestätigt. Diese Abnahme ersetzt keine
allgemeine Garantie für andere Geräte oder beschädigte Medien.

Das DEB `3.0.8-1` hat 817954 Bytes und SHA256:
`3678ead73af9d0797cc21541db8f43e7f5cd3b67af8ba8911f7400b8ee7d1926`.
Die APT-Signatur wurde in Mint mit Archivschlüssel
`15D67DDA4D0D3BD1DD10A8C3B714CC0415B04529` geprüft. Alle 13 öffentlichen
APT-Dateien entsprechen dem VM-Export; der öffentliche Schlüssel und fünf ältere
DEBs sind unverändert erhalten. Die öffentliche Prüfung vergleicht Bytes und
Prüfsummen mit diesem separat signaturgeprüften Export.

Alle sieben GitHub-Assets und die Download-/Website-Verweise sind geprüft.
Der Website-Katalog enthält die [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.8.json);
die sechs Online-Anleitungen erläutern den aktuellen Exportablauf. Der vorherige
Serverstand ist gesichert. Die unveränderten vorbereiteten Manifestdateien mit
`published: false` bleiben Buildnachweise; die tatsächliche Veröffentlichung wird
in separaten Abschlussberichten dokumentiert. Dokumente und Bilder erhalten
keine zusätzlichen Prüfsummen-Sidecars. Frühere Releases und ihre Prüfsummen
bleiben erhalten. Flatpak bleibt experimentell und gehört nicht zu den drei
regulären Release-Paketen.
