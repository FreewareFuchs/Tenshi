# Separates Export-Fortschrittsfenster

Das Fenster öffnet beim Start eines Stapel-Exports ohne modale Sperre. Schließen
beendet nur die Ansicht; der Export läuft weiter. Über „Fortschritt / Ergebnis“
im Hauptfenster lässt sich der aktuelle Zustand wieder öffnen. Dort bleiben nur
dieser Einstieg und die bisherige Export-Vorprüfung; die sichtbare Warteschlange,
ihre Dateiliste und ihre Fortschrittsbalken entfallen vollständig.
„Pause“ und „Fortsetzen“ steuern denselben laufenden Exportauftrag. Die interne
Planung, Abbruchbehandlung und Wiederaufnahme nach einem Neustart bleiben erhalten.
„Abbrechen“ beendet den Auftrag kontrolliert, auch während einer Pause. Eine
unvollständige Datei wird dabei entfernt; fertige Dateien und Einzel-Prüfsummen
bleiben erhalten. „Schließen“ blendet weiterhin nur die Fortschrittsansicht aus.
Die Aktionen stehen in drei Reihen: Ergebnisbericht / Bericht speichern,
Pause bzw. Fortsetzen / Zielordner öffnen, Abbrechen / Schließen.

## Pause und Fortsetzen

„Pause“ fordert eine Unterbrechung am nächsten vorhandenen Lese-/Schreibprüfpunkt
an. Bis zur Bestätigung zeigt das Fenster „Export-Pause angefordert …“, danach
„Export pausiert.“. Die Schaltfläche wechselt zu „Fortsetzen“. Bereits geschriebene
Bytes und eine laufende SHA256-Berechnung bleiben im selben Hintergrundauftrag
erhalten; „Fortsetzen“ startet keinen zweiten Auftrag und kopiert den Anfang
der Datei nicht erneut. Die Fortschrittszähler bleiben stehen. Kopiertempo und
Restzeit verwenden nach dem Fortsetzen ausschließlich neue Messwerte.

Die Pause gilt innerhalb der geöffneten Programmsitzung. Ein laufender Lese-/
Schreibaufruf oder atomarer Speichervorgang wird nicht gewaltsam unterbrochen.
Das Fortschrittsfenster darf geschlossen und wieder geöffnet werden; der Auftrag
bleibt dabei pausiert. Neue Exporte und Sitzungsvorgänge bleiben solange gesperrt.

Beim bestätigten Beenden des Hauptfensters wird auch ein pausierter Auftrag über
das vorhandene Abbruchsignal kontrolliert beendet. Eine unvollständige Datei wird
dabei weiterhin entfernt und nach einem Programmneustart von vorn kopiert.
„Nein“ in der Beenden-Abfrage lässt den pausierten Auftrag unverändert bestehen.

## Bedeutung des Rasters

100 quadratische Felder stehen für jeweils ein Prozent der geplanten
Dateigrößen, keine physischen Datenträgersektoren. Bei reinen Ordner-/Null-Byte-
Plänen wird ausdrücklich auf die Anzahl der Einträge umgeschaltet.

- Offen: noch nicht bearbeitet.
- Kopiert, noch ungeprüft: tatsächlich übertragene Bytes, noch kein bestätigter
  Zieldatei-Prüfsummenvergleich.
- Export bestätigt: der Export meldet die erfolgreiche Zielprüfung oder die
  Bestätigung eines vorhandenen Exports. Verzeichnisse bestätigen ihre Erstellung.
- Fehler im Export: geplante Anteile einer fehlgeschlagenen Datei. Das bedeutet
  nicht, dass jeder entsprechende physische Sektor fehlerhaft gelesen wurde.
- Nicht bestätigt: übersprungene, abgebrochene oder unbekannte Dateiergebnisse.
- Gemischt / teilweise: ein Prozentfeld enthält unterschiedlich bearbeitete Anteile.

Dateigrenzen liegen häufig innerhalb eines Prozentfeldes. Dieses kann bestätigte
Bytes der vorherigen Datei und bereits kopierte, noch ungeprüfte Bytes der gerade
laufenden Datei enthalten. Es bleibt dann bis zur Bestätigung der laufenden Datei
gemischt. Bei 34,3 % Bestätigung betrifft das beispielsweise das Feld von 34 bis
35 %. Das bedeutet keinen festhängenden oder fehlerhaften ersten Dateiblock.

Fehler und nicht bestätigte Anteile bleiben in gemischten Feldern sichtbar.
Die Darstellung arbeitet mit ganzzahligen Intervallen und konstant 100 Zellen;
auch Einträge außerhalb der intern begrenzten Vorschau gehen ein.
100 % Bestätigung setzt die Bestätigung sämtlicher geplanter Anteile voraus.
Ein vollständiger SHA-Lesestand vor dem Digestvergleich wird nicht grün.
Die Bestätigung betrifft den Export, nicht die ursprüngliche Dateiintegrität.
Der Ergebnisbericht erläutert den Prüfumfang; eine eigene Schaltfläche dafür
ist im Fortschrittsfenster nicht vorhanden.

## Weitere Angaben und Aktionen

Nach jeder vollständig kopierten und per SHA256 bestätigten Datei wird sofort
eine `.sha256` unter `Pruefsummen_Einzeln` im Exportordner gespeichert. Die Namen
enthalten eine Plannummer und den Dateinamen. Inhalt und spätere Sammeldatei
verwenden relative Pfade ab dem Exportordner (`files/...`). So kollidieren die
Prüfsummendateien nicht mit exportierten Dateien gleichen Namens.

Nur ein vollständig erfolgreicher Lauf erzeugt `SHA256SUMS.sha256` im
Exportordner. Erst nach Schreiben, Synchronisieren und Rücklesen dieser Datei
werden die unveränderten, als eigene Ausgaben erfassten Einzeldateien entfernt.
Die Prüfung der Einzeldateien erfolgt über Dateiidentität und erwarteten Inhalt;
die Bereinigung sucht nicht pauschal nach der Dateiendung. Windows löscht über
den geprüften geöffneten Handle, Linux relativ zum geprüften Elternverzeichnis.
Anschließend wird auch der leere Unterordner entfernt. Enthält er noch andere
Dateien, bleibt er mitsamt diesen Dateien erhalten; es gibt kein rekursives Löschen.

Bei Abbruch, Exportfehlern oder ausgelassenen Einträgen bleiben die bisherigen
Einzeldateien erhalten. Vollständig kopierte, aber noch ungeprüfte Dateien
erhalten keine bestätigte Prüfsummendatei. Beim Fortsetzen werden vorhandene
Exportdateien wie bisher erneut geprüft; alte Statusdateien ohne Prüfsummen-
Zusatzdaten bleiben verwendbar. Fremde oder veränderte Prüfsummendateien werden
nicht ersetzt oder gelöscht. Fehler beim Speichern oder Bereinigen erscheinen
im Ergebnisbericht und als Hinweis. Sie behaupten keinen fehlgeschlagenen
Dateiinhalt, sondern betreffen die zusätzlichen Prüfsummendateien.

Speichern und Zusammenfassen werden als Textphase angezeigt, ohne weiteres
Raster. Die Prüfsummen stammen aus dem vorhandenen bestätigten Ergebnis;
es wird keine zusätzliche vollständige Prüfung der Quelldateien gestartet.

Das Fenster zeigt Arbeitsschritt, Laufzeit, neu übertragene Bytes, Kopiertempo,
Dateizähler und bekannte Fehler/Überspringungen. Die SHA-Anzeige ist rein textlich:
Beim Kopieren wird SHA256 für den kopierten Datenstrom berechnet. Anschließend
wird die Zieldatei gelesen und ihre Prüfsumme verglichen. Währenddessen erscheint
„SHA256-Prüfung der Zieldatei läuft …“, ohne eigenen Balken oder Prüfprozentsatz.
Das 100-Felder-Raster bleibt unverändert beim Gesamtumfang und startet nicht neu.
Die vorhandene Restzeitschätzung gilt ausschließlich für das Kopieren,
wird während der Prüfung unterdrückt und ist ohne belastbare Rate nicht sichtbar.

Bei einer Wiederaufnahme meldet das Fenster „Bestehender Export erkannt“.
„Vorhandene Datei prüfen“ unterscheidet das Lesen einer bereits exportierten
Datei von der Zielprüfung unmittelbar nach neuem Kopieren. Dafür kennzeichnet
das vorhandene Prüfereignis nur seine Herkunft; es werden keine zusätzlichen
Quell- oder Zielzugriffe ausgeführt. Geprüfte Bytes zählen nicht als neu kopiert.
Die Anzeige startet pro Lauf bei null und bestätigt vorhandene Dateien erst
nach dem erneuten Prüfsummenvergleich.

Vor dem Start und im Fortschrittsfenster steht ausdrücklich: Unvollständige
Dateien beginnen beim Fortsetzen von vorn. Für das Fortsetzen sind dieselbe
Quelle und Auswahl sowie der ursprüngliche übergeordnete Zielordner nötig,
nicht der darin erzeugte Export-Unterordner. Eine Wiederaufnahme innerhalb
einzelner Exportdateien wird dadurch nicht eingeführt.

Nach dem Abschluss lassen sich der bestehende Ergebnisbericht ansehen oder eine
unveränderte Kopie speichern. Das Kopieren läuft außerhalb des GUI-Threads, lehnt
bestehende Zieldateien ab und verwendet die bestehenden Ziel-/Handle-Prüfungen.
Der Speicherdialog startet im zugehörigen Exportordner und schlägt einen Namen
mit Zeitstempel und Zufallskennung vor. Der Ergebnisbericht enthält pro Datei
die vorhandene SHA256: bestätigte Zieldatei oder ausdrücklich noch nicht bestätigter
kopierter Datenstrom. Ordner und Ergebnisse ohne verfügbaren Hash werden entsprechend
gekennzeichnet; für den Bericht werden keine Daten erneut gelesen.
Die ursprüngliche Quellzuordnung wird für diesen Schutz festgehalten. Ein späterer
Quellenwechsel im Hauptfenster ändert sie nicht. Die Schaltfläche für den Zielordner
öffnet lediglich den bereits vorhandenen Exportordner, ohne Shell-Befehlsverkettung.

Das Canvas erzeugt 100 Rechtecke und 100 Symbole einmalig; unveränderte Zustände
werden nicht neu gezeichnet. Größenänderungen werden gebündelt verarbeitet.
Fenstertimer enden mit dem Schließen der Ansicht. Alle sechs UI-Sprachen und
beide Farbvarianten werden geprüft. Scanner und Export-I/O bleiben unverändert.

Die Dateisystemanalyse behält ihre Fortschrittsanzeige im Hauptfenster.
Ein separates Analysefenster ist auf Wunsch des Anwenders nicht vorgesehen.
Das Exportraster behauptet keine zusätzlichen Informationen über Lesefehler
physischer Datenträger.

Exportfehler unterscheiden verweigerten Zugriff, schreibgeschützte Einbindung,
fehlenden Speicherplatz und ungültige/nicht unterstützte Dateioperationen.
Insbesondere EINVAL ist kein Nachweis fehlender Schreibrechte: gemeinsam genutzte
VM-Ziele können Dateioperationen einschränken. Die Originaldiagnose bleibt sichtbar.
Tenshi erweitert weder Flatpak-Freigaben noch umgeht es Zielschutz oder Synchronisierung.

## Imageerstellung

Die Imageerstellung öffnet eine eigene, nicht modale Fortschrittsansicht mit
100 quadratischen Feldern. Sie fassen jeweils ein Prozent der Quellbytes zusammen,
keine einzelnen Sektoren. Grün steht für lesbar gespeicherte Bereiche, Rot für
Bereiche mit protokolliertem Nullersatz. Ein einzelner defekter Teil macht das
ganze betroffene Feld rot; das bedeutet nicht, dass das ganze Prozent defekt ist.
Noch offene und nur teilweise gespeicherte Felder sind getrennt sichtbar.

Die Engine gibt ausschließlich bereits gespeicherte Fehlerbereiche weiter:
Beim Fortsetzen einmalig die bestehende Karte, danach nur neue Bereiche des
jeweils übernommenen Blocks. Die Ansicht hält 100 Zähler, keine zusätzliche
Liste sämtlicher Sektoren. Zusammengeführte Fehlerbereiche im Prüfpunkt bleiben
unverändert. Bei fehlender Zuordnung werden Anteile nicht fälschlich grün.
Mit „Sicher anhalten“ nicht übernommene Blöcke bleiben offen; der Fehler wird
gesondert gemeldet. Read-only-Zugriff, Wiederholungen, Nullersatz-Regeln,
Schreibsynchronisierung und Checkpoint-Prüfungen bleiben unverändert.

Das Schließen beider Imaging-Ansichten beendet den Auftrag nicht. Über „Image
erstellen / fortsetzen“ im Hauptfenster wird der laufende Auftrag wieder geöffnet;
ein zweiter Imaging-Auftrag startet dadurch nicht. Zum Unterbrechen dient die
eigene Schaltfläche. Das Einstellungsfenster bleibt intern für Steuerung und
Ereignisverarbeitung erhalten, wenn es ausgeblendet wird. Die Quelle des laufenden
Auftrags bleibt fest zugeordnet, auch wenn sich die Auswahl im Hauptfenster ändert.

Der Vollvergleich wird ausdrücklich als Textphase angezeigt. Das Raster bleibt
beim gespeicherten Umfang; Grün allein bestätigt keinen Vollvergleich. Nur das
abschließende Prüfergebnis darf „bitgenau verifiziert“ melden. Fehler oder eine
unterbrochene Prüfung bleiben ungeprüft. Die Fehlerstellen-Berichte nennen den
Status des Vollvergleichs und die tatsächlich verglichenen Bytes.

Nach Abschluss oder Unterbrechung lassen sich Bericht und Zielordner öffnen.
„Bericht speichern“ beginnt beim Image-Zielordner, schlägt einen neuen Namen vor
und läuft außerhalb des GUI-Threads. Es verwendet Zielschutz und exklusives
Dateianlegen; keine vorhandenen Dateien, Quellen oder Geräte werden überschrieben.

## Hauptfenster schließen

Ohne laufenden Auftrag schließt Tenshi sofort. Laufen noch Export, Imageerstellung
oder Speichervorgänge, fragt das Hauptfenster vor dem Beenden nach. „Nein“ ist
vorausgewählt und lässt die Aufträge weiterlaufen. „Ja“ fordert die kontrollierte
Unterbrechung von Export und Imageerstellung an. Tenshi wartet auf die Rückmeldung
der laufenden Vorgänge, bevor das Fenster geschlossen wird. Währenddessen werden
keine neuen Export-, Image- oder Sitzungsvorgänge und Berichtsspeicherungen gestartet.

Fehler beim Abschließen werden gesammelt und vor dem Schließen einmal angezeigt;
Erfolgsmeldungen werden während des Beendens nicht zusätzlich geöffnet. Ein Fehler
bestätigt keine vollständige Speicherung von Bericht oder Prüfpunkt. Die bestehenden
Prüfungen beim Fortsetzen bleiben erforderlich. Das Schließen einer einzelnen
Fortschrittsansicht blendet weiterhin nur diese Ansicht aus.
