# Dateisignaturen in einem Image suchen

## Bedienung

### Welche Suche zuerst?

| | Dateien & Ordner, einschließlich gelöschter Dateien | Dateisignaturen |
| --- | --- | --- |
| Woher stammen die Informationen? | Aus Dateisystemeinträgen, etwa der NTFS-Dateitabelle. | Aus erkennbaren Dateistrukturen direkt im gespeicherten Inhalt. |
| Namen und Ordner | Können erhalten bleiben, wenn die Einträge noch lesbar sind. | Originalnamen und Ordner sind unbekannt; Tenshi vergibt Namen aus Typ und Fundposition. |
| Gelöschte Dateien | Noch vorhandene Löschverweise können gefunden werden. Die Markierung beweist keinen intakten Inhalt. | Ein Fund verrät nicht, ob er gelöscht war. Auch vorhandene und eingebettete Dateien können erscheinen. |
| Beschädigtes Dateisystem | Benötigt ausreichend lesbare Metadaten. | Die Vollsuche benötigt kein lesbares Dateisystem. Nur die optionale Freiraumsuche braucht lesbare Belegungsdaten von NTFS, FAT32 oder exFAT. |
| Verteilte Dateibereiche | Kann erhaltene Zuordnungen mehrerer Bereiche nutzen, soweit das Dateisystem und die jeweilige Speicherart unterstützt werden. | Fragmente werden nicht zusammengesetzt; es werden zusammenhängende Strukturen gesucht. |
| Dateitypen | Nicht auf die unterstützten Signaturformate beschränkt. | Auf die nachfolgend beschriebenen Formate und Varianten begrenzt. |

**Empfehlung:** Zuerst unter **Dateien & Ordner** suchen. So können ursprüngliche Namen, Verzeichnisse und Dateizuordnungen erhalten bleiben. Fehlen dort Dateien oder sind die Einträge zerstört, ergänzt die **Signatursuche** diese Suche. **Nur freie Bereiche (NTFS, FAT32 oder exFAT)** reduziert Treffer aus belegten Bereichen, beweist aber weder Löschung noch vollständige Wiederherstellbarkeit. Keine der beiden Sucharten garantiert unbeschädigte Originalinhalte.

### Funde anzeigen und eingrenzen

Oberhalb der Sucheinstellungen bleibt eine **Zusammenfassung des tatsächlichen
Suchlaufs** sichtbar: Dateiname der Quelle, Suchbereich, Partitionsoffset,
Kategorien und die gewählte Prüfgrenze je Fund. Lange Dateinamen werden verkürzt.
Das „Prüflimit“ betrifft die in der Einstellung genannten Bild-/PDF-/Office-/ZIP-
Prüfungen und ist keine allgemeine Größenbegrenzung für alle Dateitypen.
Der vollständige Quellpfad steht weiterhin oben im Hauptfenster. Einstellungen
für den nächsten Lauf, Ergebnisfilter, Sortierung und Sprachwechsel ersetzen
diesen Suchkontext nicht. Bei einer neuen Suche, einem Quellenwechsel oder einer
anderen Analyse wird die Zusammenfassung ersetzt beziehungsweise entfernt.

Die Anzeige unterscheidet eine beendete Suche mit Funden, **keine passenden
Signaturen innerhalb der Prüfgrenzen**, **Prüfgrenze erreicht**, **angehalten oder
abgebrochen** und **fehlgeschlagen**. Bei einem Fehler wird kein erfolgreiches
leeres Ergebnis behauptet; die Fehlermeldung enthält die Ursache. Ein Fehler beim
Schreiben des Suchstands ist dabei kein Beleg für einen Lesefehler der Quelle.
Auch ein beendeter Lauf beweist weder das Fehlen anderer Dateien noch vollständige
oder unbeschädigte Originalinhalte. Format-, Größen- und sonstige Prüfgrenzen
gelten weiterhin. Aus Filtergründen ausgeblendete Funde werden gesondert mit
„Kein Fund passt zu den aktuellen Filtern“ bezeichnet; Gesamt- und sichtbare
Fundzahl bleiben daneben erhalten. Die Zusammenfassung ist eine Anzeige der
aktuellen Sitzung und erzeugt keine zusätzliche Datei.

Ein reguläres RAW-, IMG- oder DD-Image auswählen und den Reiter **Dateisignaturen** öffnen. Die Kategorieknöpfe starten gezielt die Suche nach **Bildern**, **Office-Dateien**, **Archiven**, **Audio** oder **Video**. Standardmäßig wird das gesamte Image schreibgeschützt gelesen. In dieser Vollsuche wird der eingetragene Partitionsoffset ignoriert; ein lesbares Dateisystem ist nicht erforderlich. Die optionale Freiraumsuche für NTFS, FAT32 oder exFAT wird unten erklärt. Physische Geräte und rohe Windows-Laufwerke werden derzeit nicht direkt unterstützt.

Funde erscheinen direkt im Reiter **Dateisignaturen** mit **Name**, **Typ**, **Größe (Bytes)** und **Fundposition (Bytes)**. Spaltenüberschriften sortieren nach Text oder den numerischen Größen/Positionen. Namen setzen sich aus erkanntem Typ und absolutem Byte-Offset zusammen; es sind keine Originalnamen. Die Liste enthält höchstens die 1000 Funde des begrenzten Suchlaufs.

Mit Strg/Umschalt mehrere Funde auswählen; **Strg+A** wählt die gesamte angezeigte Fundliste. **Vorschau** zeigt die Auswahl mit manueller Vor-/Zurück-Navigation. **Datei prüfen** ist für genau einen ausgewählten Fund verfügbar. **Stapel-Export / fortsetzen** exportiert ausschließlich die ausgewählten Funde über den vorhandenen Exportablauf mit Zielprüfung und Prüfsummen. Die Auswahl in **Dateien & Ordner** wird dabei nicht verändert. Ein laufender Export wird über denselben Button erneut angezeigt; ein zweiter Auftrag wird nicht gestartet.

**Strg+F** setzt den Fokus auf den Suchtext des aktiven Datei- oder Signaturreiters.
In der Fundliste hebt **Escape** nur die Auswahl auf; Filter und Ergebnisse bleiben
erhalten. **Rechtsklick** auf eine Zeile öffnet die vorhandenen Aktionen Vorschau,
Dateiprüfung, Stapel-Export und Fundliste speichern. Eine bereits markierte Zeile
behält die Mehrfachauswahl, eine andere Zeile wird allein ausgewählt.
**Umschalt+F10** öffnet dasselbe Menü für die fokussierte sichtbare Zeile, sonst
die erste sichtbare Auswahl oder den ersten sichtbaren Fund. Die Dateiprüfung
bleibt bei Mehrfachauswahl deaktiviert. Die CSV-Fundliste umfasst weiterhin alle
sichtbaren Funde, während Vorschau und Export die Auswahl verwenden.

**Fundliste speichern…** speichert alle aktuell sichtbaren Funde in der gewählten
Sortierung als CSV, unabhängig von der markierten Auswahl. Die Filter gelten
weiterhin; bei leerer oder ungültiger Filterung ist der Button deaktiviert.
Der Bericht enthält erzeugten Namen, Typ, Größe und absolute Fundposition in Bytes,
Quellpfad, Suchbereich, Partitionsoffset, Kategorien, Parserrevision, Prüfgrenze je
Fund, Vollständigkeitsstatus sowie gesamte und sichtbare Fundzahl. Er verwendet
die Einstellungen des ursprünglichen Suchlaufs, auch wenn die Optionen für den
nächsten Lauf inzwischen verändert wurden. `scan_complete=false` bedeutet, dass
der Suchlauf eine Prüfgrenze erreicht hat, nicht dass einzelne Dateien beschädigt
sind. Die CSV liest keine Imageinhalte erneut und bestätigt weder einen Export
noch die Integrität von Originaldateien.

CSV verwendet UTF-8 mit BOM und Semikolon, mit festen englischen Spaltennamen für
den Vergleich unabhängig von der Oberflächensprache. Beim Import in eine
Tabellenkalkulation die Byte-Spalten als ganze Zahlen oder Text behandeln.
Zellen mit möglichen Formelführungszeichen erhalten ein führendes Apostroph.
Ein vorhandener Bericht oder das Quellimage wird nicht überschrieben; zum
erneuten Speichern einen neuen Dateinamen wählen. Dies erzeugt keine zusätzlichen
Prüfsummendateien.

Die Liste lässt sich ohne erneutes Lesen des Images eingrenzen: **Suchtext** sucht ohne Groß-/Kleinschreibung im erzeugten Fundnamen, **Typ** wählt ein erkanntes Format und **Ab (KiB)** eine Mindestgröße. Alle Filter gelten gleichzeitig; 1 KiB sind 1024 Bytes, erlaubt sind ganze Zahlen von 0 bis 4294967296. Ungültige Größenangaben blenden die Liste bis zur Korrektur aus und zeigen einen Hinweis. Die Zähler unterscheiden sichtbare Funde, sämtliche gefundenen Einträge und die aktuelle Auswahl. Die Suchlaufgrenzen bleiben unverändert.

Beim Ausblenden werden betroffene Funde aus der Auswahl entfernt. **Strg+A** erfasst nur sichtbare Zeilen; Vorschau, Dateiprüfung und Export verwenden ausschließlich die sichtbare Auswahl. **Zurücksetzen** zeigt alle Funde wieder, markiert zuvor ausgeblendete Einträge aber nicht automatisch erneut. Ein neuer Suchlauf oder Quellenwechsel setzt die Filter zurück. Ein Sprachwechsel behält Filter und Auswahl bei. Bereits laufende Exportaufträge und geöffnete Vorschauen behalten ihre ursprüngliche Auswahl. Die separate Dateiansicht hat weiterhin ihre eigenen Ansichtsoptionen.

**In Dateiansicht anzeigen** öffnet weiterhin die bisherige Ansicht. Ein Quellenwechsel oder eine neue Analyse entfernt die alte Fundliste. Eine bereits geöffnete Vorschau oder ein laufender Export behält seinen ursprünglichen Quell- und Auswahlkontext sowie die vorhandenen Quellenprüfungen. Ein gespeicherter Exportauftrag wird beim Fortsetzen gegen das Image erneut aufgebaut.

Mit **Kategorien gemeinsam suchen…** lassen sich mehrere Kategorien auswählen. Standardmäßig sind alle fünf ausgewählt; mindestens eine muss aktiv bleiben. Tenshi durchsucht die Quelle dabei in einem gemeinsamen Durchgang und veröffentlicht die passenden Funde in einer gemeinsamen Ergebnisliste. Die Einzelbuttons stehen weiterhin zur Verfügung. Die Grenzen für Kandidaten, Funde und Strukturprüfungen gelten für den gesamten gemeinsamen Lauf; der Analysebericht nennt die ausgewählten Kategorien.

## Suchstand speichern und fortsetzen

Gemeinsame VM-Ordner unterstützen teilweise keine Synchronisierung des Verzeichnisses (`fsync` auf dem Ordner). Tenshi synchronisiert weiterhin die Datei selbst und ersetzt den Suchstand atomar. Ausschließlich die als nicht unterstützt gemeldete Ordnersynchronisierung wird protokolliert, ohne den erfolgreichen Speichervorgang als Fehler anzuzeigen. Die Beständigkeit der Ordneränderung bei Stromausfall hängt dann vom Dateisystem ab; für solche Fälle einen lokalen Linux-Ordner verwenden. Datei-Schreibfehler, fehlende Rechte und echte Datenträgerfehler bleiben Fehler und stoppen die Suche.

### Optional: nur freie NTFS-, FAT32- oder exFAT-Bereiche

Unter **Suchbereich** direkt eine erkannte NTFS-, FAT32- oder exFAT-Partition
wählen. Die Liste stammt aus der aktuellen Partitionsanalyse derselben Quelle;
Dateisystem und Byte-Offset werden übernommen und die Freiraumsuche aktiviert.
Warnmarkierungen aus der Analyse bleiben sichtbar. Ein Eintrag ist ein Kandidat,
kein Nachweis gültiger Belegungsdaten. Andere Dateisysteme werden nicht angeboten.
Bei fehlenden Einträgen im Reiter **Partitionen** die Schnell- oder Tiefensuche
ausführen oder **Manuell: freie Bereiche** wählen.

Im manuellen Modus **NTFS**, **FAT32** oder **exFAT** und den
**Partitionsoffset (Bytes)** angeben: `0` bei einem reinen Volume-Image, sonst
den Partitionsanfang. Änderungen an Dateisystem oder Offset nach einer
Partitionswahl wechseln in den manuellen Modus. **Gesamtes Image** deaktiviert
diese Felder und durchsucht die ganze Quelle mit internem Offset `0`.
Die Startbestätigung nennt den tatsächlichen Bereich und Offset.

Ein Quellenwechsel entfernt die alte Partitionsliste. Veraltete Analysekontexte
können nicht als Partitionswahl übernommen werden. Vor dem Lesen einer gewählten
Partition wird der Quellenfingerabdruck der Partitionsanalyse erneut geprüft;
bei geändertem Image ist eine neue Analyse nötig. Die Optionen für den nächsten
Lauf ändern weiterhin nicht die Zusammenfassung des vorherigen Laufs.
Manuelle Eingaben und ältere Suchstände bleiben verwendbar; Parser und
gespeicherte Suchbereichskennungen ändern sich nicht. Die Dateisystemwahl wird
nicht erraten und bei Fehlern erfolgt kein stiller Wechsel auf eine Vollsuche.

**exFAT:** Unterstützt wird ein einzelnes FAT-/Bitmap-Paar, kein TexFAT und keine mehrdeutigen Bitmap-Einträge. Anders als bei FAT32 bestimmt die Belegungsbitmap freie Cluster; erhaltene FAT-Verweise gelöschter Dateien sind kein Beleg für eine aktuelle Belegung. Haupt- und Sicherungsbootbereich werden über ihre Prüfsummen und übereinstimmende Geometrie geprüft. Die laut Format veränderlichen Status-/Belegungsfelder der Sicherungskopie dürfen abweichen; maßgeblich ist der Hauptbootbereich. Unsaubere oder mit Medienfehler markierte Volumes werden abgelehnt. Root- und Bitmap-FAT-Ketten müssen innerhalb des Volumes liegen und dürfen weder zyklisch sein noch überlappen. Ihre eigenen Metadatencluster müssen in der Bitmap belegt sein.

Die exFAT-Grenzen betragen **128 MiB Bitmap**, **32 MiB Rootverzeichnis**, **192 MiB gelesene Metadaten insgesamt** und weiterhin höchstens **1 MiB je Cluster** gemäß der vorhandenen Volume-Geometrieunterstützung. Unlesbare, zu große oder widersprüchliche Metadaten stoppen die Freiraumsuche. Die Prüfung ermittelt keine vollständige Konsistenz sämtlicher Dateien und Verzeichnisse. Quelle und Belegungsdaten bleiben unverändert.

exFAT-Suchstände verwenden eine eigene Formatkennung. Beim Fortsetzen werden Bootregionen, relevante Metadatenketten, Rootverzeichnis und Bitmap erneut gelesen und über SHA256 verglichen. Funde dürfen nur innerhalb eines zusammenhängenden freien Bereichs liegen. Bereich, Dateisystemwahl und Partitionsoffset bleiben auch beim Export-Wiederaufbau erhalten. Ein Wechsel zu einem anderen Suchbereich braucht einen neuen Suchlauf. Bisherige Voll-, NTFS- und FAT32-Suchstände behalten ihren Umfang.

Grundlage: [Microsoft exFAT Specification, Abschnitte 3 und 7.1](https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification). Die Auswertung ist eine eigene begrenzte Implementierung.

**FAT32:** Die aktive FAT wird schreibgeschützt gelesen. Bei aktivierter Spiegelung müssen die unteren 28 Bits sämtlicher relevanter Einträge in den vorhandenen FATs übereinstimmen; bei deaktivierter Spiegelung gilt ausschließlich die im Bootsektor gewählte aktive FAT. Nur Einträge mit Belegungswert null gelten als frei. Belegte, reservierte und als fehlerhaft markierte Cluster bleiben ausgeschlossen. FSInfo-Schätzwerte bestimmen die Belegung nicht. Rootcluster, Medienkennung, Geometrie, Tabellenlängen und Statusmarkierungen werden geprüft. Unsaubere/E/A-Fehler-Markierungen, widersprüchliche Spiegel, unlesbare oder zu kurze Tabellen führen zu einem Hinweis und zum Ende der Freiraumsuche. Die Prüfung bestätigt keine vollständige Konsistenz aller Verzeichnisse oder Dateiketten.

Es werden höchstens **128 MiB FAT-Tabellendaten insgesamt** gelesen; unbenötigtes Tabellen-Padding bleibt unberücksichtigt. Die Suche hält nur eine kompakte Belegungsbitmap und begrenzte Tabellenblöcke im Speicher. FAT12/FAT16 und geometrisch nicht als FAT32 einordenbare Volumes sind nicht enthalten. Fundpositionen bleiben absolute Image-Offsets, und Kandidaten dürfen belegte oder fehlerhafte Grenzen nicht überschreiten. Nur vollständige Datencluster innerhalb der Partition werden durchsucht.

FAT32-Suchstände verwenden eine eigene Formatkennung. Beim Fortsetzen werden Bootsektor und relevante FAT-Daten erneut gelesen und mit dem gespeicherten SHA256 verglichen. Ein Wechsel zwischen Vollsuche, NTFS und FAT32 erfordert einen neuen Suchlauf. Exportaufträge bewahren Bereich und Offset und bauen ihre Auswahl mit frisch gelesenen Belegungsdaten erneut auf. Alte NTFS- und Vollsuchstände bleiben lesbar und behalten ihren bisherigen Umfang.

Grundlage: [Microsoft FAT Specification, Abschnitte 3.3, 3.5 und 4.2–4.4](https://academy.cba.mit.edu/classes/networking_communications/SD/FAT.pdf). Die Auswertung ist eine eigene begrenzte Implementierung; das Spezifikationsdokument wird nicht mitgeliefert.

**NTFS:** Die Metadaten werden zuerst schreibgeschützt gelesen. Fehlende, beschädigte, nicht unterstützte oder zu große Bitmaps führen zu einer Fehlermeldung, niemals zum stillen Wechsel auf eine Vollsuche. Das vorhandene Limit von 128 MiB für die Bitmap gilt weiterhin. Nur zusammenhängende freie Bereiche werden durchsucht; Kandidaten dürfen keine belegten Grenzen überschreiten. Bereiche außerhalb des Volumes und nicht zu Clustern gehörende Restsektoren werden ausgelassen. Ein freies Cluster bestätigt keine gelöschte oder unversehrte Originaldatei. Es gibt keine Fragmentrekonstruktion.

Der Fortschritt zählt freie Suchbytes statt der gesamten Image-Größe. Metadaten-, Fingerabdruck- und Strukturprüfungen verursachen zusätzliche Lesezugriffe. Suchstände und Exportaufträge behalten Bereich und Partitionsoffset bei. Beim Fortsetzen wird die Bitmap frisch gelesen; Suchstände vergleichen zusätzlich ihren Bitmap-Hash. Gespeicherte Funde müssen weiterhin vollständig in einem freien Bereich liegen und werden erneut strukturell geprüft. Ältere Suchstände und Exportaufträge bleiben Vollsuchen. Eine neue Suche ist nötig, um den Suchbereich zu wechseln. Freie Suchstände verwenden eine eigene Formatkennung, damit ältere Programmversionen sie nicht als Vollsuche öffnen.

Im freien Suchmodus enden Suchabschnitte spätestens nach 1 MiB oder an einer belegten Grenze; Statuspositionen sind daher nicht zwingend Vielfache von 1 MiB.

Vor einer Suche **Suchstand speichern** aktivieren und nach dem Bestätigen eine neue `.tenshi-search.json`-Datei als Ziel wählen. Tenshi sichert abgeschlossene 1-MiB-Suchabschnitte regelmäßig (nach 16 MiB oder zwei Sekunden) und beim kontrollierten Anhalten. **Anhalten** stoppt eine Suche mit aktivierter Speicherung. Ein gerade bearbeiteter Abschnitt oder Fund wird beim Fortsetzen erneut gelesen. Bei einem unerwarteten Programmende kann die zuletzt automatisch gesicherte Position etwas zurückliegen.

Nach einem Programmneustart zuerst dasselbe reguläre Image auswählen und **Suchstand öffnen…** verwenden. Kategorien und Größenbegrenzung werden aus der Datei übernommen. Tenshi prüft Größe, Stichproben-Fingerabdruck und beim ursprünglichen Pfad die Änderungszeit. Gespeicherte Funde werden strukturell neu geprüft, bevor sie in die Ergebnisse gelangen. Die Stichproben sind kein vollständiger Hash des Images. Der Suchstand enthält Positionen und Metadaten, keine Dateiinhalte. Eine Prüfsumme erkennt beschädigte Statusdaten; sie ist kein Echtheitsnachweis.

Zähler und Strukturprüfbudget werden nicht zurückgesetzt. Die erneute Prüfung gespeicherter Funde hat ein eigenes begrenztes Lesebudget. Ein Suchstand, der bereits eine Suchlaufgrenze erreicht hat, erfordert eine neue Suche. Ein abgeschlossener Suchstand kann zum erneuten Anzeigen seiner verifizierten Funde geöffnet werden. Die Quelle darf niemals als Statusdatei dienen. Bei einem Schreibfehler bleibt der vorherige atomar gesicherte Suchstand erhalten; die Oberfläche meldet den Fehler.

## Unterstützte Strukturen

| Kategorie | Erkennung | Grenzen |
| --- | --- | --- |
| Bilder | JPEG, PNG, BMP, GIF, klassisches TIFF, WebP | TIFF: klassische 32-Bit-Variante und ausgewiesene Strip-/Tile-Daten; WebP: RIFF-Länge und erster Bild-Chunk. |
| Office/PDF | PDF 1.0–1.7/2.0, DOCX/DOCM/DOTX/DOTM, XLSX/XLSM/XLTX/XLTM, PPTX/PPTM/POTX/POTM sowie ODT/ODS/ODP/ODG in ZIP-Containern; binäre DOC/XLS/PPT in CFB-Containern | PDF: Header, startxref/EOF, Querverweisstruktur und Root-Verweis; vollständige inkrementelle Nachträge werden über Prev-Verknüpfungen verfolgt. ZIP: Zentraldaten und begrenzte Content-Types-/MIME-Information. CFB: Verkettungstabellen, Verzeichnis und formatspezifische Stream-Köpfe. |
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

Binäre Office-Kandidaten umfassen Word ab Generation 97 mit WordDocument/FIB und passendem Tabellenstream, Excel mit BIFF8-Workbook sowie PowerPoint mit Current-User-/User-Edit-Strukturen. CFB-Versionen 3 und 4 werden mit begrenzten FAT-, DIFAT-, MiniFAT- und Verzeichnisprüfungen gelesen. Schleifen, überlappende Zuordnungen, nicht zugeordnete belegte Sektoren und widersprüchliche Strukturen führen zur Ablehnung. Höchstens 8192 Verzeichniseinträge werden geprüft. Der Fundbereich endet am höchsten zugeordneten Sektor; unbekanntes freies Padding am Dateiende wird nicht übernommen. Ungewöhnliche oder beschädigte Varianten können deshalb fehlen. Beliebige OLE-Container und verschlüsselte moderne Office-Pakete werden nicht als DOC/XLS/PPT etikettiert. Interne Sektorketten werden geprüft; eine auf dem Datenträger fragmentierte Datei wird nicht rekonstruiert.

Für CFB gilt die gewählte Office-Prüfgrenze. Gespeicherte Suchstände mit Parserrevision 1 oder 2 behalten ihren bisherigen Formatumfang; für zusätzliche DOC/XLS/PPT-Funde ist eine neue Suche nötig. Vorschau und Inhaltsprüfung zeigen bei erkannten binären DOC/XLS/PPT-Strukturen eine **Teilprüfung**: Interne Sektorketten, Verzeichnis und ausgewählte formatspezifische Kopfdaten sind lesbar. Dokumentinhalte, Seiten, Zellen, Folien, eingebettete Dateien und Makros werden nicht geprüft; eine Darstellung ist nicht enthalten. Unbekannte OLE-/CFB-Varianten bleiben „Nicht geprüft“. Fehlerhafte oder nicht unterstützte Containerstrukturen werden mit einem entsprechenden Hinweis gemeldet; das beweist keine Beschädigung. Die Inhaltsprüfung läuft getrennt vom Hauptprogramm, liest höchstens 32 MiB je Datei und behält ihre Zeit- und Speichergrenzen. Die gewählte Suchgrenze von bis zu 256 MiB erweitert diese Inhaltsgrenze nicht. Makros werden nicht ausgeführt, Inhalte nicht entschlüsselt und vollständige Originalinhalte nicht bestätigt.

Grundlagen der eigenen CFB-Implementierung: [CFB-Header](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-cfb/05060311-bfce-4b12-874d-71fd4ce63aea), [CFB-Sektorketten](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-cfb/b089deda-be20-4b4a-aad5-fbe68bb19672), [Word-FIB](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/26fb6c06-4e5c-4778-ab4e-edbf26a545bb), [Excel-BOF](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xls/4d6a3d1e-d7c5-405f-bbae-d01e9cb79366), [PowerPoint CurrentUserAtom](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-ppt/940d5700-e4d7-4fc0-ab48-fed5dbc48bc1). Unabhängige Apache-POI-Testdateien und ihre Lizenzhinweise liegen unter `tests/fixtures/office_cfb`; sie sind keine Laufzeitabhängigkeit.

PNG prüft IHDR, Chunk-Reihenfolge, CRC-Prüfsummen und IEND; JPEG prüft Markersegmente, Bildgeometrie und EOI. BMP, GIF, WebP und TIFF werden anhand begrenzter Header- und Datenbereichsangaben geprüft. Moderne Office-Erkennung beruht auf den Paketpfaden in der ZIP-Zentralstruktur. ZIP nutzt EOCD und Zentralverzeichnis; 7z prüft Start- und Endheader-CRC; TAR kontrolliert ustar-Headerchecksummen und Eintragslängen. WAV/AVI basieren auf RIFF-Längen und benötigten Unterstrukturen; Ogg auf Seitenfolge, CRC und EOS; MP3 auf ID3v2-Länge und mindestens drei plausiblen MPEG-Audioframes; MP4 auf Boxgrenzen und erforderlichen Top-Level-Boxen.

Formatreferenzen: [PDF 32000-1, Abschnitt 7.5](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf), [RAR-5-Format](https://www.rarlab.com/technote.htm), [RARLAB UnRAR-Quellreferenz für RAR 4](https://www.rarlab.com/rar_add.htm), [PNG](https://www.w3.org/TR/png/), [GNU tar – Basisformat und Headerchecksummen](https://www.gnu.org/software/tar/manual/tar.html), [7z-Struktur](https://www.7-zip.org/recover.html), [QuickTime/MP4-Atome](https://developer.apple.com/documentation/quicktime-file-format/atoms). Die Parser sind eigene begrenzte Implementierungen; UnRAR und zusätzliche PDF-Bibliotheken sind keine Laufzeitabhängigkeiten.
