# Dateisignaturen in einem Image suchen

## Bedienung

Ein reguläres RAW-, IMG- oder DD-Image auswählen und den Reiter **Dateisignaturen** öffnen. Die Kategorieknöpfe starten gezielt die Suche nach **Bildern**, **Office-Dateien**, **Archiven**, **Audio** oder **Video**. Für den Suchlauf wird das gesamte Image schreibgeschützt gelesen. Der eingetragene Partitionsoffset wird ignoriert; ein lesbares Dateisystem ist nicht erforderlich. Physische Geräte und rohe Windows-Laufwerke werden derzeit nicht direkt unterstützt.

Funde erscheinen danach in der bestehenden Dateiansicht und können dort wie andere Einträge geprüft, in der Vorschau geöffnet und exportiert werden. Namen setzen sich aus erkanntem Typ und Byte-Offset zusammen. Ein gespeicherter Exportauftrag wird beim Fortsetzen gegen das Image erneut aufgebaut.

## Unterstützte Strukturen

| Kategorie | Erkennung | Grenzen |
| --- | --- | --- |
| Bilder | JPEG, PNG, BMP, GIF, klassisches TIFF, WebP | TIFF: klassische 32-Bit-Variante und ausgewiesene Strip-/Tile-Daten; WebP: RIFF-Länge und erster Bild-Chunk. |
| Office | DOCX/DOCM/DOTX/DOTM, XLSX/XLSM/XLTX/XLTM, PPTX/PPTM/POTX/POTM sowie ODT/ODS/ODP/ODG in ZIP-Containern | Die ZIP-Zentraldaten werden geprüft; höchstens der kleine Content-Types- bzw. MIME-Eintrag wird gelesen. Dokumentinhalte werden nicht entpackt. Klassische DOC/XLS/PPT-Dateien im OLE/CFB-Format sind noch nicht enthalten. |
| Archive | ZIP, 7z, TAR im ustar-Format | ZIP64 und RAR werden nicht erkannt. TAR endet am ersten gültigen doppelten Nullblock; zusätzliche Nullauffüllung ist nicht Teil des Fundbereichs. |
| Audio | WAV, Ogg mit Vorbis oder Opus, MP3 mit ID3v2-Kopf | Ogg muss als einzelne logische Bitstream-Sequenz vorliegen und eine gültige CRC sowie EOS-Seite haben. MP3 braucht mindestens drei aufeinanderfolgende passende Frames. |
| Video | AVI, MP4/ISO-BMFF | MP4 benötigt gültige Boxgrößen sowie `ftyp`, `moov` und `mdat`; die erste ungültige Folgebox begrenzt den Kandidaten. |

Nicht alle möglichen Varianten eines Formats werden erkannt. RAR, ZIP64, BigTIFF, fragmentierte Dateien und Formate ohne zuverlässig ableitbares zusammenhängendes Ende werden bewusst ausgelassen.

## Aussage und Grenzen

- Nur strukturell plausible, zusammenhängende Bereiche werden veröffentlicht. Prüfsummen/CRC werden dort kontrolliert, wo die jeweilige Struktur sie bereitstellt; das ersetzt keine vollständige Dekodierung oder Inhaltsprüfung.
- Ein Fund zeigt weder, ob eine Datei gelöscht war, noch ob der gesamte ursprüngliche Inhalt unversehrt ist. Originalnamen, Pfade, Zeitstempel und Fragmentzuordnung sind nicht bekannt.
- Es werden belegte und freie Imagebereiche durchsucht. Daher können aktive Dateien, Vorschaubilder, eingebettete Objekte und überlappende Kandidaten erscheinen.
- Es gibt keine Zusammensetzung fragmentierter Dateien und keine automatische Reparatur. Vorschau, Inhaltsprüfung und Export bleiben getrennte Aktionen.
- Pro Suchlauf gelten maximal 1000 Funde, 5000 Anfangssignaturen und 512 MiB zusätzliche Strukturprüfungen. JPEG/PNG/GIF/WebP/TIFF sowie ZIP-Indizes sind auf 32 MiB begrenzt; Formatlängen können bei anderen Formaten größere Fundbereiche bestimmen, maximal 4 TiB und nie über das Image-Ende hinaus.
- Lesefehler brechen den Scan ab. Das Quell-Image wird vor und nach der Suche auf Identität und Metadatenänderungen kontrolliert und bleibt schreibgeschützt.

## Formatgrundlagen

PNG prüft IHDR, Chunk-Reihenfolge, CRC-Prüfsummen und IEND; JPEG prüft Markersegmente, Bildgeometrie und EOI. BMP, GIF, WebP und TIFF werden anhand begrenzter Header- und Datenbereichsangaben geprüft. Office-Erkennung beruht auf den Paketpfaden in der ZIP-Zentralstruktur. ZIP nutzt EOCD und Zentralverzeichnis; 7z prüft Start- und Endheader-CRC; TAR kontrolliert ustar-Headerchecksummen und Eintragslängen. WAV/AVI basieren auf RIFF-Längen und benötigten Unterstrukturen; Ogg auf Seitenfolge, CRC und EOS; MP3 auf ID3v2-Länge und mindestens drei plausiblen MPEG-Audioframes; MP4 auf Boxgrenzen und erforderlichen Top-Level-Boxen.

Formatreferenzen: [PNG](https://www.w3.org/TR/png/), [GNU tar – Basisformat und Headerchecksummen](https://www.gnu.org/software/tar/manual/tar.html), [7z-Struktur](https://www.7-zip.org/recover.html), [QuickTime/MP4-Atome](https://developer.apple.com/documentation/quicktime-file-format/atoms).
