# Dateisignaturen in einem Image suchen

## Bedienung

Ein reguläres RAW-, IMG- oder DD-Image auswählen und den Reiter **Dateisignaturen** öffnen. Die Kategorieknöpfe starten gezielt die Suche nach **Bildern**, **Office-Dateien**, **Archiven**, **Audio** oder **Video**. Für den Suchlauf wird das gesamte Image schreibgeschützt gelesen. Der eingetragene Partitionsoffset wird ignoriert; ein lesbares Dateisystem ist nicht erforderlich. Physische Geräte und rohe Windows-Laufwerke werden derzeit nicht direkt unterstützt.

Funde erscheinen direkt im Reiter **Dateisignaturen** mit **Name**, **Typ**, **Größe (Bytes)** und **Fundposition (Bytes)**. Spaltenüberschriften sortieren nach Text oder den numerischen Größen/Positionen. Namen setzen sich aus erkanntem Typ und absolutem Byte-Offset zusammen; es sind keine Originalnamen. Die Liste enthält höchstens die 1000 Funde des begrenzten Suchlaufs.

Mit Strg/Umschalt mehrere Funde auswählen; **Strg+A** wählt die gesamte angezeigte Fundliste. **Vorschau** zeigt die Auswahl mit manueller Vor-/Zurück-Navigation. **Datei prüfen** ist für genau einen ausgewählten Fund verfügbar. **Stapel-Export / fortsetzen** exportiert ausschließlich die ausgewählten Funde über den vorhandenen Exportablauf mit Zielprüfung und Prüfsummen. Die Auswahl in **Dateien & Ordner** wird dabei nicht verändert. Ein laufender Export wird über denselben Button erneut angezeigt; ein zweiter Auftrag wird nicht gestartet.

**In Dateiansicht anzeigen** öffnet weiterhin die bisherige Ansicht. Ein Quellenwechsel oder eine neue Analyse entfernt die alte Fundliste. Eine bereits geöffnete Vorschau oder ein laufender Export behält seinen ursprünglichen Quell- und Auswahlkontext sowie die vorhandenen Quellenprüfungen. Ein gespeicherter Exportauftrag wird beim Fortsetzen gegen das Image erneut aufgebaut.

Mit **Kategorien gemeinsam suchen…** lassen sich mehrere Kategorien auswählen. Standardmäßig sind alle fünf ausgewählt; mindestens eine muss aktiv bleiben. Tenshi durchsucht die Quelle dabei in einem gemeinsamen Durchgang und veröffentlicht die passenden Funde in einer gemeinsamen Ergebnisliste. Die Einzelbuttons stehen weiterhin zur Verfügung. Die Grenzen für Kandidaten, Funde und Strukturprüfungen gelten für den gesamten gemeinsamen Lauf; der Analysebericht nennt die ausgewählten Kategorien.

## Suchstand speichern und fortsetzen

Gemeinsame VM-Ordner unterstützen teilweise keine Synchronisierung des Verzeichnisses (`fsync` auf dem Ordner). Tenshi synchronisiert weiterhin die Datei selbst und ersetzt den Suchstand atomar. Ausschließlich die als nicht unterstützt gemeldete Ordnersynchronisierung wird protokolliert, ohne den erfolgreichen Speichervorgang als Fehler anzuzeigen. Die Beständigkeit der Ordneränderung bei Stromausfall hängt dann vom Dateisystem ab; für solche Fälle einen lokalen Linux-Ordner verwenden. Datei-Schreibfehler, fehlende Rechte und echte Datenträgerfehler bleiben Fehler und stoppen die Suche.

### Optional: nur freie NTFS-Bereiche

**Nur freie NTFS-Bereiche** beschränkt die Suche auf eine NTFS-Partition mit verlässlich lesbarer `$Bitmap`. Den **NTFS-Partitionsoffset (Bytes)** angeben: `0` bei einem reinen Volume-Image, sonst den Partitionsanfang. Die vorhandene Partitionsauswahl überträgt diesen Offset auch ins Signaturregister. Ohne die Auswahl bleibt die bisherige Suche über das ganze Image aktiv.

NTFS-Metadaten werden zuerst schreibgeschützt gelesen. Fehlende, beschädigte, nicht unterstützte oder zu große Bitmaps führen zu einer Fehlermeldung, niemals zum stillen Wechsel auf eine Vollsuche. Das vorhandene Limit von 128 MiB für die Bitmap gilt weiterhin. Nur zusammenhängende freie Bereiche werden durchsucht; Kandidaten dürfen keine belegten Grenzen überschreiten. Bereiche außerhalb des Volumes und nicht zu Clustern gehörende Restsektoren werden ausgelassen. Ein freies Cluster bestätigt keine gelöschte oder unversehrte Originaldatei. Es gibt keine Fragmentrekonstruktion.

Der Fortschritt zählt freie Suchbytes statt der gesamten Image-Größe. Metadaten-, Fingerabdruck- und Strukturprüfungen verursachen zusätzliche Lesezugriffe. Suchstände und Exportaufträge behalten Bereich und Partitionsoffset bei. Beim Fortsetzen wird die Bitmap frisch gelesen; Suchstände vergleichen zusätzlich ihren Bitmap-Hash. Gespeicherte Funde müssen weiterhin vollständig in einem freien Bereich liegen und werden erneut strukturell geprüft. Ältere Suchstände und Exportaufträge bleiben Vollsuchen. Eine neue Suche ist nötig, um den Suchbereich zu wechseln. Freie Suchstände verwenden eine eigene Formatkennung, damit ältere Programmversionen sie nicht als Vollsuche öffnen.

Im freien Suchmodus enden Suchabschnitte spätestens nach 1 MiB oder an einer belegten Grenze; Statuspositionen sind daher nicht zwingend Vielfache von 1 MiB.

Vor einer Suche **Suchstand speichern** aktivieren und nach dem Bestätigen eine neue `.tenshi-search.json`-Datei als Ziel wählen. Tenshi sichert abgeschlossene 1-MiB-Suchabschnitte regelmäßig (nach 16 MiB oder zwei Sekunden) und beim kontrollierten Anhalten. **Anhalten** stoppt eine Suche mit aktivierter Speicherung. Ein gerade bearbeiteter Abschnitt oder Fund wird beim Fortsetzen erneut gelesen. Bei einem unerwarteten Programmende kann die zuletzt automatisch gesicherte Position etwas zurückliegen.

Nach einem Programmneustart zuerst dasselbe reguläre Image auswählen und **Suchstand öffnen…** verwenden. Kategorien und Größenbegrenzung werden aus der Datei übernommen. Tenshi prüft Größe, Stichproben-Fingerabdruck und beim ursprünglichen Pfad die Änderungszeit. Gespeicherte Funde werden strukturell neu geprüft, bevor sie in die Ergebnisse gelangen. Die Stichproben sind kein vollständiger Hash des Images. Der Suchstand enthält Positionen und Metadaten, keine Dateiinhalte. Eine Prüfsumme erkennt beschädigte Statusdaten; sie ist kein Echtheitsnachweis.

Zähler und Strukturprüfbudget werden nicht zurückgesetzt. Die erneute Prüfung gespeicherter Funde hat ein eigenes begrenztes Lesebudget. Ein Suchstand, der bereits eine Suchlaufgrenze erreicht hat, erfordert eine neue Suche. Ein abgeschlossener Suchstand kann zum erneuten Anzeigen seiner verifizierten Funde geöffnet werden. Die Quelle darf niemals als Statusdatei dienen. Bei einem Schreibfehler bleibt der vorherige atomar gesicherte Suchstand erhalten; die Oberfläche meldet den Fehler.

## Unterstützte Strukturen

| Kategorie | Erkennung | Grenzen |
| --- | --- | --- |
| Bilder | JPEG, PNG, BMP, GIF, klassisches TIFF, WebP | TIFF: klassische 32-Bit-Variante und ausgewiesene Strip-/Tile-Daten; WebP: RIFF-Länge und erster Bild-Chunk. |
| Office/PDF | PDF 1.0–1.7/2.0, DOCX/DOCM/DOTX/DOTM, XLSX/XLSM/XLTX/XLTM, PPTX/PPTM/POTX/POTM sowie ODT/ODS/ODP/ODG in ZIP-Containern | PDF: Header, startxref/EOF, Querverweisstruktur und Root-Verweis; vollständige inkrementelle Nachträge werden über Prev-Verknüpfungen verfolgt. ZIP: Zentraldaten und begrenzte Content-Types-/MIME-Information. Klassische DOC/XLS/PPT-Dateien im OLE/CFB-Format sind noch nicht enthalten. |
| Archive | ZIP, RAR 4/5, 7z, TAR im ustar-Format | RAR: Header-CRC, Blockgrößen und Endmarker; keine mehrteiligen Archive oder verschlüsselten Header. ZIP64 wird nicht erkannt. TAR endet am ersten gültigen doppelten Nullblock; zusätzliche Nullauffüllung ist nicht Teil des Fundbereichs. |
| Audio | WAV, Ogg mit Vorbis oder Opus, MP3 mit ID3v2-Kopf | Ogg muss als einzelne logische Bitstream-Sequenz vorliegen und eine gültige CRC sowie EOS-Seite haben. MP3 braucht mindestens drei aufeinanderfolgende passende Frames. |
| Video | AVI, MP4/ISO-BMFF | MP4 benötigt gültige Boxgrößen sowie `ftyp`, `moov` und `mdat`; die erste ungültige Folgebox begrenzt den Kandidaten. |

Nicht alle möglichen Varianten eines Formats werden erkannt. ZIP64, BigTIFF, fragmentierte Dateien und Formate ohne zuverlässig ableitbares zusammenhängendes Ende werden ausgelassen. RAR-Dateiinhalte werden nicht entpackt, entschlüsselt oder per Daten-CRC geprüft; Header-Prüfsummen bestätigen keine intakten Nutzdaten. Bei SFX-Dateien ist nur der eingebettete RAR-Bereich ein Fund, nicht das vorangestellte Programm.

PDF-Prüfung ist eine begrenzte Strukturprüfung, kein vollständiger PDF-Decoder. Querverweistabellen sind auf 1 MiB Metadaten und 50.000 Einträge begrenzt, Wörterbücher auf 64 KiB und Endmarker-Prüfungen auf 128. Querverweisströme werden anhand ihrer Metadaten und Begrenzungen geprüft, nicht vollständig dekodiert. Unvollständige inkrementelle Nachträge werden abgelehnt, statt eine frühere Fassung zu exportieren. Ungewöhnliche Erweiterungen, indirekte Streamlängen und beschädigte Strukturen können unerkannt bleiben. Dokumentaktionen und eingebettete Programme werden nicht ausgeführt.

Gespeicherte Suchstände und Exportaufträge vor der PDF/RAR-Erweiterung verwenden weiterhin ihre ursprüngliche Suchversion. Für PDF/RAR im gesamten Image eine neue Suche starten; bereits übersprungene Abschnitte alter Suchstände werden nicht nachträglich als geprüft behauptet.

## Aussage und Grenzen

- Nur strukturell plausible, zusammenhängende Bereiche werden veröffentlicht. Prüfsummen/CRC werden dort kontrolliert, wo die jeweilige Struktur sie bereitstellt; das ersetzt keine vollständige Dekodierung oder Inhaltsprüfung.
- Ein Fund zeigt weder, ob eine Datei gelöscht war, noch ob der gesamte ursprüngliche Inhalt unversehrt ist. Originalnamen, Pfade, Zeitstempel und Fragmentzuordnung sind nicht bekannt.
- Es werden belegte und freie Imagebereiche durchsucht. Daher können aktive Dateien, Vorschaubilder, eingebettete Objekte und überlappende Kandidaten erscheinen.
- Es gibt keine Zusammensetzung fragmentierter Dateien und keine automatische Reparatur. Vorschau, Inhaltsprüfung und Export bleiben getrennte Aktionen.
- Pro Suchlauf gelten maximal 1000 Funde, 5000 Anfangssignaturen und 512 MiB zusätzliche Strukturprüfungen. Für JPEG/PNG/GIF/TIFF/PDF sowie Office-/ZIP-Dateien lässt sich vor dem Start eine Grenze von 32, 64, 128 oder 256 MiB je Fund wählen (Standard: 32 MiB). Dateien darüber können bei der Suche fehlen. Größere Grenzen erhöhen gegebenenfalls die Lesezeit; das Gesamtbudget gilt weiterhin für den gesamten Suchlauf. RAR verwendet geprüfte Blocklängen bis zur allgemeinen Formatgrenze von 4 TiB.
- JPEG/PNG und ZIP werden blockweise gelesen. ZIP-Inhalte werden nicht vollständig entpackt; nur der begrenzte Office-Inhaltstyp-Eintrag wird zur Typbestimmung entpackt und per CRC geprüft. TIFF-Metadaten und die übrigen Formatprüfungen haben zusätzliche feste Grenzen. Für BMP/WebP, Archive wie TAR/7z, Audio und Video können Formatlängen größere Fundbereiche bestimmen, maximal 4 TiB und nie über das Image-Ende hinaus.
- Analysebericht und neue gespeicherte Exportaufträge enthalten die gewählte Grenze. Beim Fortsetzen werden Grenze und Kategorien des Auftrags erneut verwendet; alte Aufträge bleiben lesbar. Vorschau und Inhaltsprüfung behalten ihre eigenen 32-MiB-Grenzen.
- Lesefehler brechen den Scan ab. Das Quell-Image wird vor und nach der Suche auf Identität und Metadatenänderungen kontrolliert und bleibt schreibgeschützt.

## Formatgrundlagen

PNG prüft IHDR, Chunk-Reihenfolge, CRC-Prüfsummen und IEND; JPEG prüft Markersegmente, Bildgeometrie und EOI. BMP, GIF, WebP und TIFF werden anhand begrenzter Header- und Datenbereichsangaben geprüft. Office-Erkennung beruht auf den Paketpfaden in der ZIP-Zentralstruktur. ZIP nutzt EOCD und Zentralverzeichnis; 7z prüft Start- und Endheader-CRC; TAR kontrolliert ustar-Headerchecksummen und Eintragslängen. WAV/AVI basieren auf RIFF-Längen und benötigten Unterstrukturen; Ogg auf Seitenfolge, CRC und EOS; MP3 auf ID3v2-Länge und mindestens drei plausiblen MPEG-Audioframes; MP4 auf Boxgrenzen und erforderlichen Top-Level-Boxen.

Formatreferenzen: [PDF 32000-1, Abschnitt 7.5](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf), [RAR-5-Format](https://www.rarlab.com/technote.htm), [RARLAB UnRAR-Quellreferenz für RAR 4](https://www.rarlab.com/rar_add.htm), [PNG](https://www.w3.org/TR/png/), [GNU tar – Basisformat und Headerchecksummen](https://www.gnu.org/software/tar/manual/tar.html), [7z-Struktur](https://www.7-zip.org/recover.html), [QuickTime/MP4-Atome](https://developer.apple.com/documentation/quicktime-file-format/atoms). Die Parser sind eigene begrenzte Implementierungen; UnRAR und zusätzliche PDF-Bibliotheken sind keine Laufzeitabhängigkeiten.
