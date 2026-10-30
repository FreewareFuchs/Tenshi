# Gespeicherten Exportauftrag wieder öffnen

Entwicklungsstand nach 3.0.9, noch nicht veröffentlicht.

Neue Aufträge speichern die ausgewählten Wurzeleinträge und verwendeten
Scan-Einstellungen in der vorhandenen Statusdatei im Exportordner. Es entstehen
keine neue Index- oder Inhaltskopie und keine Auftragsliste im Benutzerprofil.
Die vorhandene Statusdatei enthält bereits private Quell- und Dateipfade und
gehört zusammen mit dem Unterordner `files` zum Export.

## Nach einem Programmneustart

1. **Exportauftrag öffnen** neben **Export prüfen** anklicken.
2. Den bisherigen erzeugten Export-Unterordner auswählen, zum Beispiel
   `Tenshi_Export_…`. Der übergeordnete Zielordner allein reicht hier nicht.
3. Quelle und Exportordner in der Bestätigung kontrollieren. Bis zur Bestätigung
   wird ausschließlich die ausgewählte Statusdatei gelesen, kein Quellmedium.
4. Nach Ja liest Tenshi das Dateisystem schreibgeschützt erneut ein. Der
   gespeicherte Partitionsoffset, das ursprüngliche NTFS-Scan-Limit und der
   ursprüngliche Toleranzmodus werden übernommen. Die Vorbereitung zeigt einen
   Textzähler und bleibt über Abbrechen kontrolliert beendbar.
5. Quelle, Auswahl und vollständiger Exportplan müssen zu der Statusdatei passen.
   Danach prüft und setzt derselbe Exportmechanismus den vorhandenen Ordner fort.

Fertige Dateien werden erneut anhand ihrer gespeicherten SHA256 geprüft. Nach
kontrolliertem Abbruch entfernte unvollständige Dateien werden von vorn kopiert.
Nicht zuordenbare vorhandene Dateien, auch mögliche Reste eines Systemabsturzes,
werden weiterhin nicht überschrieben. Dies ist keine Wiederaufnahme innerhalb
einer teilweise geschriebenen Datei und keine über Neustarts gespeicherte Pause.

Die Zielprüfung bleibt wirksam. Bei neuer Platzwarnung ist eine Entscheidung
erforderlich; ohne neue Warnung genügt die Auftragsbestätigung. Quelle und
Exportauftrag werden nicht automatisch beim Programmstart geöffnet.

## Grenzen und Datenschutz

- Die ursprüngliche Quelle muss unter demselben Pfad erreichbar sein. Geänderte
  Images, ausgetauschte Geräte, fehlende Einträge und abweichende Exportpläne
  stoppen die Wiederaufnahme. Ein anderes Quellmedium wird nicht stillschweigend
  eingesetzt. Gerätezugriffe benötigen dieselben Leserechte wie zuvor.
- Die Quelle wird neu eingelesen. Bei großen Dateisystemen kann das dauern und
  bei beschädigter Hardware zusätzliche Leselast verursachen. Die vorhandenen
  Quell-/Zielschutzregeln gelten unverändert.
- Der gespeicherte Fingerabdruck und Gerätekennungen sind begrenzte
  Konsistenzprüfungen und kein Nachweis identischer vollständiger Quellinhalte.
  Die nachfolgende Plan- und Zieldateiprüfung bleibt erforderlich.
- Aufträge aus älteren Versionen ohne gespeicherte Auswahl lassen sich weiter
  manuell mit derselben Quelle, Auswahl und dem ursprünglichen Zielordner
  fortsetzen. Ein bestätigter manueller Wiederaufnahmelauf ergänzt die neuen
  Auswahlangaben. Die bisherigen Verzeichnisnamen und Signaturen bleiben erhalten.
- Die Statusdatei wird als nicht vertrauenswürdige JSON-Metadatei behandelt.
  Sie wird nicht ausgeführt. Reguläre Dateien, Größenbegrenzung (64 MiB),
  Schema, Pfade, Auswahlkennungen und Scan-Parameter werden geprüft. Zu große
  Dateien benötigen weiter den bisherigen manuellen Weg.

## Prüfung

Automatische Tests öffnen abgebrochene Aufträge in einem frischen Prozess und
einer frischen Programmoberfläche. Sie prüfen NTFS, FAT32, exFAT und ext,
Partitionsoffset und NTFS-Limit, neue Quellprüfung, manipulierte Statusdateien,
Abbruch und kontrolliertes Beenden, sechs Sprachen und alte Aufträge. Bis zur
Bestätigung erfolgt kein Zugriff auf die gespeicherte Quelle; Ablehnen und
Abbruch während der Vorbereitung verändern den Exportordner nicht.
