# Bildsignaturen in einem Image suchen

Seit Tenshi 3.0.12 stabil verfügbar. Funktion und endgültige Paketversionen sind manuell bestätigt. [Versionshinweise und öffentlicher Prüfstand](../RELEASE_NOTES_3.0.12.md).

## Bedienung

Ein reguläres RAW-/IMG-/DD-Image auswählen. Im Reiter **Bildsignaturen** den
Suchlauf mit **Bildsignaturen suchen** starten und bestätigen. Es wird das gesamte Image
gelesen; der eingetragene Partitionsoffset wird hierbei nicht verwendet.
Ein lesbares Dateisystem ist nicht erforderlich. Physische Geräte und rohe
Windows-Laufwerke werden in diesem ersten Ausbau nicht direkt unterstützt.

Der Textzähler zeigt gelesene MiB; **Scan abbrechen** stoppt den Suchlauf.
Erst ein abgeschlossener Suchlauf übergibt die Funde an die Dateiansicht.
Abgebrochene oder durch einen Quellenwechsel überholte Ergebnisse werden verworfen.
Eine erreichte Prüfgrenze wird als unvollständiges Ergebnis ausgewiesen.

Namen wie `JPEG_0000000000000201.jpg` bestehen aus Bildtyp und hexadezimalem
Byte-Offset. **Vorschau**, **Datei prüfen → Inhalt prüfen**, **Export prüfen** und
**Stapel-Export** arbeiten mit diesen Fundbereichen. Vorschau und Inhaltsprüfung
bleiben getrennte Aktionen. Den Export auf einem anderen physischen Medium ablegen.
Die üblichen Zielschutz-, SHA256-, Pause- und Abbruchregeln gelten weiter.

Ein gespeicherter Exportauftrag lässt sich nach Bestätigung wieder öffnen.
Dafür wird das Image erneut schreibgeschützt durchsucht und der vollständige
Exportplan verglichen. Fertige Dateien werden wie bisher erneut geprüft.
Eine Analysesitzung mit zwischengespeicherten Signaturfunden wird noch nicht
unterstützt; das Image erneut durchsuchen oder den gespeicherten Exportauftrag
öffnen. Es werden keine Fundinhalte auf Platte zwischengespeichert.

## Aussage und Grenzen

- Zusammenhängende JPEG-/PNG-Strukturen, maximal 32 MiB pro Fund.
- Originalname, Ordner, Zeitstempel und Löschstatus sind unbekannt.
- Belegte und freie Bereiche werden durchsucht. Auch bestehende Dateien,
  Vorschaubilder und eingebettete Bilder können erscheinen. Überlappende Funde
  werden nicht als verschiedene ursprüngliche Dateien bestätigt.
- Keine Zusammensetzung fragmentierter Dateien oder automatische Reparatur.
- Eine lesbare Struktur, Dekodierung oder Exportbestätigung beweist keine
  unversehrten Originalinhalte. Kein Fund bedeutet nicht endgültigen Datenverlust.
- Maximal 1000 Funde, 5000 untersuchte Anfangssignaturen und 512 MiB zusätzliche
  Lesezugriffe für Strukturprüfungen pro Suchlauf. PNG ist auf 4096 Chunks,
  JPEG auf 65536 Marker begrenzt. Funde über diesen Grenzen werden ausgelassen;
  die globalen Prüfgrenzen stoppen den Lauf mit einem Unvollständigkeitshinweis.
- Lesefehler führen zum Abbruch statt zum Erraten oder Zusammenziehen fehlender
  Bereiche. Bilder über der Vorschau-Pixelgrenze können als Strukturfund
  erscheinen und erst bei der Inhaltsprüfung die Pixelgrenze melden.

## Erkennung

PNG: vollständige Signatur, IHDR-Metadaten, begrenzte Chunk-Längen/-Reihenfolge,
CRC-Prüfsummen und abschließender IEND-Chunk. Eine Zeichenfolge „IEND“ innerhalb
anderer Daten gilt nicht als Dateiende. Bilddaten werden beim Suchlauf nicht
dekomprimiert. [PNG-Spezifikation](https://www.w3.org/TR/png/).

JPEG: SOI, begrenzte Markersegmente und Bildgeometrie, SOS und EOI außerhalb
von Metadaten. Byte-Stuffing und Restart-Marker in Bilddaten sowie mehrere
Scans progressiver JPEGs werden berücksichtigt. Es gibt keine Bilddekodierung
im Suchlauf und keine Unterstützung aller JPEG-Erweiterungen.
[JPEG-Dateiformat und Marker](https://www.media.mit.edu/pia/Research/deepview/exif.html).

Nur reguläre Images werden über den vorhandenen schreibgeschützten Leser
geöffnet. Dateigröße, Änderungszeit und Dateiidentität werden vor/nach dem
Suchlauf sowie beim Lesen eines Fundbereichs kontrolliert. Diese Prüfungen
sind kein vollständiger Inhaltsfingerabdruck des Images.
