# Tenshi 3.0.10 – Benutzerhilfe

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

Große Listen zeigen bis zu 750 Einträge pro Seite. Strg+A wählt nur die angezeigte
Seite. Verborgene TMP-Dateien werden nicht gelöscht und können bei rekursiven
Ordnerexporten enthalten sein.

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
