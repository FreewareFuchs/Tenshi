# Tenshi 3.0.8 – Export steuern und Prüfsummen sichern

Stabile Pakete in Vorbereitung. Die Funktionen sind im Entwicklungspaket aus
PR #101 manuell abgenommen. Installer, Portable und DEB werden gemeinsam neu
gebaut; ihre endgültigen Starts und Versionsanzeigen stehen zur Abnahme aus.
Die veröffentlichten Downloads, Website und APT-Quelle bieten weiterhin 3.0.7.

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

Die Pakete werden mit Kennung `stable` aus demselben sauberen Commit gebaut.
Release-Manifest und `.sha256`-Dateien nennen Paketgrößen, Prüfsummen und Quellstand.
Dokumente und Bilder erhalten keine zusätzlichen Prüfsummen-Sidecars.
Die [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.8.json) stehen als
Eingabe für die anschließende Website-Vorbereitung bereit.

Der abgenommene Funktionsstand liegt in Hauptcommit
`427b5c726ff5fb8b54e24ef3b233d105b4b94562`. Windows- und Linux-Gesamtprüfungen
umfassen jeweils 856 Tests mit den jeweiligen Plattform-Skips; das installierte
experimentelle Flatpak ist ebenfalls geprüft. Die Release-Vorbereitung ändert
Versionsfelder und Dokumentation. Die endgültige Paketabnahme wird gesondert
protokolliert; diese Datei bestätigt noch keine Veröffentlichung oder neue
Hardwareprüfung. Frühere Releases und ihre Prüfsummen bleiben erhalten.
