# Tenshi 3.0.13 – Benutzerhilfe

Die Offline-Hilfe im Programm ist über **Hilfe** oder **F1** erreichbar, durchsuchbar
und in allen sechs Oberflächensprachen verfügbar. F1 zeigt das Thema des aktiven
Hauptregisters. Das Hilfefenster kann neben dem Programm geöffnet bleiben.

## Erster Durchgang

1. Nach Möglichkeit ein zuvor erstelltes Image über **Image auswählen** öffnen.
2. Die Schnellanalyse im Register **Partitionen** startet nach der Quellenauswahl.
   Die Tiefensuche nur bei Bedarf verwenden.
3. Eine gefundene Partition doppelklicken: Tenshi übernimmt den Byte-Offset,
   wechselt zu **Dateien & Ordner** und liest das Dateisystem ein.
4. Dateien oder Ordner auswählen und **Export prüfen** verwenden. Diese Vorprüfung
   bewertet Metadaten. **Bereit** garantiert keine unbeschädigten Inhalte.
5. **Stapel-Export / fortsetzen** starten und ein separates Ziel auf einem anderen
   physischen Datenträger wählen. Fremde bestehende Dateien werden nicht überschrieben.

Unter Dateien & Ordner zeigen große Listen bis zu 750 Einträge pro Seite. Strg+A wählt nur die angezeigte
Seite. Verborgene TMP-Dateien werden nicht gelöscht und können bei rekursiven
Ordnerexporten enthalten sein.

## Dateisignaturen ohne lesbares Dateisystem suchen

### Unterschied zur Suche unter Dateien & Ordner

**Dateien & Ordner** liest Dateisystemeinträge, etwa die NTFS-Dateitabelle.
Dadurch können ursprüngliche Namen, Ordner und die Zuordnung mehrerer Dateibereiche
erhalten bleiben, soweit die jeweilige Speicherart unterstützt wird. Auch gelöschte
Einträge können noch vorhanden sein. Die Markierung „gelöscht“ bestätigt jedoch
nicht, dass der frühere Dateiinhalt noch vollständig vorhanden ist.

**Dateisignaturen** sucht erkennbare Strukturen direkt in den gespeicherten Daten.
Die Vollsuche funktioniert auch ohne lesbares Dateisystem, kennt aber weder
Originalnamen und Ordner noch den Löschstatus. Sie erkennt nur unterstützte
Dateiformate und setzt Fragmente nicht zusammen. Auch vorhandene und eingebettete
Dateien können als Funde erscheinen.

Zuerst **Dateien & Ordner** verwenden. Fehlen dort Dateien oder sind die Einträge
zerstört, die **Signatursuche** ergänzend einsetzen. „Nur freie NTFS-Bereiche“
benötigt eine lesbare Belegungsbitmap und reduziert Treffer aus belegten Bereichen.
Freier Speicher und erkennbare Strukturen garantieren keine unbeschädigten Originalinhalte.

Ein reguläres Image auswählen und **Dateisignaturen** öffnen. Die Buttons suchen
nach **Bildern**, **Office/PDF**, **Archiven**, **Audio** oder **Video**.
**Kategorien gemeinsam suchen…** bietet eine Mehrfachauswahl und durchsucht das
Image in einem Durchgang. In der Vollsuche wird der Partitionsoffset ignoriert. Physische Geräte
und rohe Laufwerke werden für die Signatursuche nicht direkt unterstützt.

Unterstützt werden JPEG, PNG, BMP, GIF, TIFF, WebP; moderne Office-/ODF-Dateien,
binäre DOC/XLS/PPT und PDF; ZIP, RAR 4/5, 7z und TAR; WAV, MP3 mit ID3v2,
Ogg/Opus; AVI und MP4.
Nicht alle Formatvarianten sind enthalten. RAR-Mehrteiler und verschlüsselte
RAR-Header, ZIP64 und BigTIFF werden ausgelassen.

Bei binären Office-Dateien werden Word ab Generation 97, Excel mit BIFF8 und
PowerPoint mit Current-User-/User-Edit-Strukturen anhand ihrer internen
Container geprüft. Beschädigte oder ungewöhnliche Varianten können fehlen.
Die Suche rekonstruiert keine auf dem Datenträger fragmentierten Dateien.
Für erkannte binäre DOC/XLS/PPT-Dateien melden Vorschau und Inhaltsprüfung
**Teilprüfung**: Sektorketten, Verzeichnis und ausgewählte Kopfdaten sind lesbar.
Dokumentinhalte, Seiten, Zellen, Folien, eingebettete Dateien und Makros bleiben
ungeprüft. Eine Office-Darstellung ist nicht enthalten. Unbekannte Varianten
bleiben „Nicht geprüft“; die Inhaltsprüfung bleibt auf 32 MiB begrenzt. Makros werden nicht
ausgeführt und Inhalte nicht entschlüsselt. Ältere Suchstände behalten ihren
bisherigen Umfang; für zusätzliche DOC/XLS/PPT-Funde eine neue Suche starten.

Die Prüfgrenze für JPEG/PNG/GIF/TIFF/PDF sowie Office/ZIP lässt sich auf
**32, 64, 128 oder 256 MiB** je Fund setzen. Andere Formate können größer sein.
Je Suchlauf gelten 1000 Funde, 5000 Anfangssignaturen und 512 MiB zusätzliche
Strukturlesevorgänge. Grenzen können Ergebnisse unvollständig machen. Größere
Einstellungen können mehr Lesezeit benötigen. Vorschau und Inhaltsprüfung haben
weiterhin eigene Grenzen.

Funde enthalten Typ und Byte-Offset statt Originalnamen. Vorschau mit Vor/Zurück,
Dateiprüfung und Stapel-Export sind direkt an der Fundliste verfügbar.

Die Funde stehen auch direkt im Reiter **Dateisignaturen**. **Suchtext**, **Typ**
und **Ab (KiB)** grenzen die Liste ein, ohne das Image erneut zu lesen.
Die Mindestgröße ist eine ganze Zahl; 1 KiB = 1024 Bytes. Alle Filter gelten
gleichzeitig. Zähler zeigen sichtbare Funde, Gesamtzahl und Auswahl.
Ausgeblendete Funde werden abgewählt. Strg+A und Export erfassen ausschließlich
sichtbare markierte Funde. **Zurücksetzen** zeigt alle Funde wieder, ohne
ausgeblendete Dateien erneut zu markieren. Bei neuer Quelle oder Analyse werden
die Filter zurückgesetzt. **In Dateiansicht anzeigen** öffnet die bisherige Ansicht.

Für **Nur freie NTFS-Bereiche** den **NTFS-Partitionsoffset (Bytes)** angeben:
0 bei einem reinen Volume-Image, sonst den Anfang der NTFS-Partition.
Die Partitionsauswahl übernimmt diesen Offset. Fehlt eine verlässlich lesbare
Belegungsbitmap, wird die Suche mit einem Hinweis gestoppt. Funde überschreiten
keine belegten Grenzen. Suchstand und Exportauftrag behalten Bereich und Offset bei.

### Suchstand nach einem Neustart fortsetzen

Vor dem Start **Suchstand speichern** aktivieren und eine neue
`.tenshi-search.json`-Datei wählen. **Anhalten** speichert den letzten vollständig
bearbeiteten Abschnitt. Nach einem Neustart dasselbe Image auswählen und
**Suchstand öffnen…** verwenden. Kategorien und Prüfgrenze werden übernommen;
Quelle und bisherige Fundbereiche werden erneut geprüft. Der unvollständige
Abschnitt wird wiederholt. Bei unerwartetem Programmende wird am letzten
automatisch gespeicherten Stand weitergemacht.

Der Quellenvergleich verwendet Stichproben, keinen vollständigen Image-Hash.
Erreichte Suchlaufgrenzen werden durch Fortsetzen nicht zurückgesetzt. Ältere
Suchstände behalten ihren bisherigen Formatumfang: Für neue PDF-/RAR-Funde im
bereits durchsuchten Bereich eine neue Suche starten. Gespeicherte Exportaufträge
werden weiterhin durch erneute Suche und Abgleich der Auswahl rekonstruiert.

### Aussage der Ergebnisse

In der Vollsuche werden belegte und freie Bereiche durchsucht. Auch aktive und eingebettete
Dateien können erscheinen. Originalnamen, Ordner und Löschstatus sind unbekannt.
Zusammenhängende Strukturen bestätigen weder vollständige Originalinhalte noch
Rettbarkeit gelöschter Daten. Fragmente werden nicht zusammengesetzt. Archive
werden bei der Signatursuche nicht entpackt und Dokumentaktionen nicht ausgeführt.

Unter **Dateien & Ordner → Scanoptionen…** befinden sich die fehlertolerante
Dateisystemsuche und das Speichern eines Analyseberichts. Die Signatursuche hat
ihren eigenen Reiter.

[Formatumfang und Grenzen](docs/IMAGE_SIGNATURE_SEARCH.md).

## Vorschau und Inhaltsprüfung

Eine oder mehrere Dateien markieren und **Vorschau** öffnen. **Zurück / Weiter**
blättert manuell durch diese Auswahl; **Datei … von …** nennt die Position.
Es gibt keinen automatischen Wechsel. Ordner werden ausgelassen. Hinweise zu
nicht darstellbaren Dateien verhindern das Weiterblättern nicht. Eine spätere
Auswahländerung im Hauptfenster verändert das geöffnete Vorschaufenster nicht.

JPEG, PNG, BMP und GIF werden verkleinert angezeigt; Animationen zeigen das
erste Bild. PDF zeigt nur die erste Seite. DOCX kann einen begrenzten Textauszug
zeigen. XLSX/PPTX werden strukturell geprüft, ohne Tabellen-/Folienansicht.
Microsoft Office ist für diese Prüfungen nicht erforderlich.

**Datei prüfen → Inhalt prüfen** prüft Bilder sowie PDF-/Office-Strukturen.
Ergebnisse unterscheiden lesbare Struktur, Teilprüfung, Schutz, nicht lesbar
und erreichte Prüfgrenzen. Dateien mit Kennwort werden nicht entschlüsselt.
Links, Makros und Dokumentaktionen werden nicht ausgeführt.

Vorschau und Inhaltsprüfung sind auf 32 MiB pro Datei, 20 Millionen Bildpixel
und begrenzte ZIP-/XML-Daten beschränkt. Textvorschau bleibt auf 128 KiB begrenzt.
Lesbare Struktur ist kein Nachweis vollständiger Originalinhalte oder der
Rettbarkeit gelöschter Daten. Die vollständige Leseprüfung mit SHA256 bleibt
separat verfügbar. Schließen oder Dateiwechsel beendet die bisherige Vorschau.

Im Ergebnisbericht öffnet **Exportierte Datei prüfen …** die Auswahl im
Exportordner `files`. Diese Prüfung liest die gewählte reguläre Datei vom Ziel;
Bericht, Exportdatei und gespeicherte Prüfsummen werden nicht verändert.

[Ausführlicher Umfang und Grenzen](docs/CONTENT_PREVIEW.md).

## Exportziel vorab prüfen

Vor dem ersten Schreibzugriff zeigt die Bestätigung Ziel-Dateisystem, geplante
Dateiinhalte, eine Obergrenze zusätzlich benötigter Dateibytes und verfügbaren
Platz. Vollständig vorhandene Dateien eines gespeicherten Auftrags werden zur
erneuten Prüfung gezählt, nicht erneut als Kopierbedarf. Die bestehenden
Hashprüfungen bleiben erforderlich; die Größe allein bestätigt keinen Inhalt.

Die Angaben beruhen auf Metadaten. Dateisystem-Metadaten, Berichte und
Prüfsummen benötigen zusätzlichen Platz; die verfügbare Kapazität kann sich
ändern. Bei Platzmangel ist **Nein** vorausgewählt. Eine ausdrücklich bestätigte
Schätzung darf trotzdem starten. Erkanntes FAT/FAT32 erlaubt pro neuer Datei
höchstens 4 GiB minus 1 Byte; größere Dateien erfordern ein anderes Ziel.
Nicht verfügbare Werte stehen als **Nicht ermittelbar**. Die Grenzen mancher
VM-/Netzwerkfreigaben bleiben unbekannt und werden nicht als FAT32 geraten.

**Nein** und **Abbrechen** während der Zielprüfung verändern den Exportordner
nicht. Eine abgelehnte Wiederaufnahme bleibt fortsetzbar. Ohne neue Platzwarnung
fragt direktes Fortsetzen eines abgebrochenen Auftrags nicht zusätzlich nach.

## Export steuern

Das Fortschrittsfenster öffnet automatisch. **Schließen** blendet nur die Ansicht
aus; über **Fortschritt / Ergebnis** lässt sie sich wieder öffnen.
Die Ansicht bleibt über dem Hauptfenster und wird beim Öffnen daran zentriert,
soweit sie dadurch vollständig sichtbar bleibt. Das Hauptfenster bleibt bedienbar.
Während eines laufenden oder pausierten Auftrags öffnet auch **Stapel-Export**
dieselbe Ansicht erneut, ohne eine neue Zielabfrage oder einen zweiten Auftrag.
Beim normalen Verschieben und Vergrößern wird sie nicht ständig neu ausgerichtet.

| Aktion | Verhalten |
|---|---|
| Pause | Fordert eine Pause an der nächsten Lese-/Schreibgrenze an. Danach bleiben Teil-Datei, Zähler und laufende SHA256-Berechnung erhalten. |
| Fortsetzen nach Pause | Arbeitet im selben Hintergrundauftrag weiter, solange Tenshi geöffnet bleibt. |
| Abbrechen | Beendet kontrolliert und entfernt eine unvollständige Datei. Fertige Dateien bleiben erhalten. |
| Fortsetzen nach Abbrechen | Wird nach abgeschlossenem Abbruch aktiv. Übernimmt Quelle, Auswahl und Ziel des bisherigen Auftrags, prüft fertige Dateien und kopiert unvollständige von vorn. |

Eine inzwischen geänderte Dateiansicht ändert den gespeicherten Auftrag nicht.
Die direkte Wiederaufnahme meldet eine geänderte ursprüngliche Quelle oder einen
fehlenden bisherigen Exportordner. Eine vollständig kopierte Datei mit gespeichertem
Prüfwert kann eine unterbrochene Zielprüfung ohne erneutes Kopieren abschließen.

Die sechs Aktionen stehen als **Ergebnisbericht / Bericht speichern**,
**Pause bzw. Fortsetzen / Zielordner öffnen** und **Abbrechen / Schließen**.
**Bericht speichern** beginnt im zugehörigen Exportordner und schlägt einen
neuen Dateinamen vor.

## Export nach einem Programmneustart wieder öffnen

**Exportauftrag öffnen** neben **Export prüfen** öffnet den bisher erzeugten
`Tenshi_Export_…`-Unterordner. Neue Aufträge speichern ihre ursprüngliche Auswahl
und Scan-Einstellungen in der vorhandenen Statusdatei. Ein erneutes manuelles
Zusammenstellen der Dateiauswahl ist nicht erforderlich.

Vor Zugriff auf die gespeicherte Quelle zeigt Tenshi Quelle und Exportordner zur
Bestätigung. Nach **Ja** wird das Dateisystem schreibgeschützt erneut eingelesen;
Quelle und vollständiger Exportplan müssen zum Auftrag passen. Während dieser
Vorbereitung erscheint ein Textzähler. **Nein** oder **Abbrechen** während der
Vorbereitung verändert den bisherigen Exportordner nicht.

Fertige Dateien werden weiterhin per SHA256 geprüft. Nach kontrolliertem Abbruch
entfernte unvollständige Dateien werden von vorn kopiert; eine Pause innerhalb
einer Datei wird nicht über Programmneustarts gespeichert. Nicht zuordenbare
vorhandene Dateien, auch mögliche Absturzreste, werden nicht überschrieben.

Die ursprüngliche Quelle muss unverändert unter demselben Pfad erreichbar sein.
Gerätezugriffe benötigen dieselben Leserechte. Der begrenzte Quellfingerabdruck
ist kein vollständiger Inhaltsvergleich. Die erneute Dateisystemanalyse kann bei
großen Quellen dauern und zusätzliche Leselast verursachen.

**Ältere Aufträge ohne gespeicherte Auswahl** weiter manuell über **Stapel-Export**
fortsetzen: dieselbe Quelle und Auswahl sowie den ursprünglichen Zielordner
wählen, nicht den erzeugten Unterordner. Ein bestätigter manueller Lauf ergänzt
die Auswahlangaben. Nur dieser manuelle Weg verwendet den übergeordneten Zielordner.

Es entstehen keine Index-/Inhaltskopie und keine Auftragsliste im Benutzerprofil.
Die Statusdatei gehört zusammen mit `files` zum Export und kann private Pfade
enthalten. Quelle und Auftrag werden beim Programmstart nicht automatisch geöffnet.

## Raster und Prüfsummen

Jedes der 100 Felder steht für ein Prozent aller geplanten Dateigrößen. Bei
reinen Ordner-/Null-Byte-Plänen wird die Eintragszahl verwendet.

- Blau: kopiert, noch ungeprüft.
- Grün: Export bestätigt.
- Rot: Exportfehler; unbestätigte Anteile sind ebenfalls gesondert erkennbar.
- Gemischt: Das Feld enthält unterschiedlich bearbeitete Anteile. Dateigrenzen
  liegen oft mitten in einem Feld. Bestätigte Bytes der vorherigen Datei und
  noch ungeprüfte Bytes der laufenden Datei bleiben bis zu deren Bestätigung gemischt.

Die Felder sind keine physischen Sektoren. Ein bestätigter Export beweist nicht,
dass die ursprünglichen Inhalte wiederhergestellter Dateien vollständig waren.
SHA256-Berechnung und Zielprüfung erscheinen als Textphasen.

Nach jeder vollständig kopierten und bestätigten Datei entsteht eine `.sha256`
unter `Pruefsummen_Einzeln`. Nach vollständig erfolgreichem Export wird
`SHA256SUMS.sha256` gespeichert und rückgelesen. Erst danach entfernt Tenshi die
unveränderten eigenen Einzeldateien und den leeren Zwischenordner. Bei Abbruch
oder Fehlern bleiben bisherige Einzeldateien erhalten. Ein Ordner mit weiteren
fremden Dateien bleibt bestehen; geänderte Prüfsummen werden nicht überschrieben
oder entfernt. Pfade in den Prüfsummendateien gelten relativ zum Exportordner.
Unter Linux kann die Sammeldatei dort mit `sha256sum -c SHA256SUMS.sha256` geprüft werden.

## Image erstellen oder fortsetzen

**Image erstellen / fortsetzen** kopiert die Quelle lesend in eine separate
Image-Zieldatei. Bestehendes Image und Statusdateien `.recovery.json`/`.journal`
zusammen behalten; sie werden für die geprüfte Wiederaufnahme verwendet.

Das eigene Imaging-Fenster zeigt 100 Felder über die Quellbytes. Grün bedeutet
lesbar gespeichert, Rot kennzeichnet protokollierten Nullersatz. Schon ein kleiner
Fehleranteil kann ein ganzes Feld rot markieren. Grün allein bestätigt keinen
Vollvergleich; nur dessen erfolgreiches Endergebnis meldet bitgenaue Verifikation.

**Schließen** blendet auch hier nur die Ansicht aus. **Unterbrechen** hält
kontrolliert an; **Einstellungen / fortsetzen** führt zum bisherigen Auftrag.
Bericht, Speichern und Zielordner sind nach Abschluss oder Unterbrechung erreichbar.
Die Dateisystemanalyse behält ihren Fortschrittszähler im Hauptfenster.

Bei bestätigten Medienfehlern sind 0–3 zusätzliche Leseversuche möglich.
**Nullen + protokollieren** erzeugt Datenlücken; **Sicher anhalten** stoppt am
letzten gültigen Prüfpunkt. Zugriffsverweigerungen, Geräteabbrüche und unerwartet
kurze Leseantworten werden nicht als bestätigte defekte Sektoren behandelt.

## Hauptfenster schließen

Bei laufenden Export-, Image- oder Speichervorgängen fragt Tenshi nach.
**Nein** erhält den bisherigen Ausführungs- oder Pausenzustand. **Ja** fordert
die kontrollierte Unterbrechung an und wartet auf laufende Schreibvorgänge.
Abschlussfehler werden vor dem Schließen angezeigt. Im Leerlauf schließt das
Programm ohne zusätzliche Rückfrage.

## Analysesitzungen und Grenzen

**Analysesitzung** speichert bereits eingelesene Metadaten regulärer Images,
nicht physischer Datenträger. Beim Laden werden Größe, Änderungszeit und mehrere
SHA-256-Proben geprüft. Das ersetzt keinen vollständigen Vergleich. Eine
`.tenshi-session` enthält keine gesicherten Dateiinhalte und kann private Namen
und Pfade enthalten.

NTFS, FAT32, exFAT und ext2/3/4 bieten je nach erhaltenen Metadaten eingeschränkte
Löschrekonstruktion. Btrfs/XFS unterstützen nur einen begrenzten Funktionsumfang;
Löschhinweise sind nicht exportierbar. Quelle und ursprüngliche Daten bleiben
schreibgeschützt. Lesen kann defekte Hardware zusätzlich belasten; bei schweren
oder mechanischen Schäden weitere Versuche vermeiden und fachkundige Hilfe erwägen.

## Fehler und Kontakt

Exportmeldungen unterscheiden fehlenden Zugriff, schreibgeschützte Ziele,
Platzmangel und nicht unterstützte Dateioperationen. **Invalid argument** beweist
keine fehlenden Schreibrechte; VM-Freigaben können Einschränkungen haben.
Die Originaldiagnose bleibt sichtbar. Prüfsummendatei-Fehler stehen gesondert
im Bericht; bei blockierter Bereinigung bleibt die gespeicherte Sammeldatei erhalten.
Über **Fehlerprotokoll** lassen sich technische Meldungen ansehen. Vor dem Teilen
auf private Pfade prüfen.

### Über Tenshi

Tenshi ist kostenlose, quelloffene Datenrettungs- und Analysesoftware von
FreewareFuchs für Windows 10/11 (64 Bit) und Linux.

**Für Fragen und Verbesserungsvorschläge: kontakt@freewarefuchs.de**

[Website und Anleitungen](https://freewarefuchs.de/tenshi/) ·
[Quellcode und MIT-Lizenz](https://github.com/FreewareFuchs/Tenshi)
