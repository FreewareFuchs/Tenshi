# Separates Export-Fortschrittsfenster

Das Fenster öffnet beim Start eines Stapel-Exports ohne modale Sperre. Schließen
beendet nur die Ansicht; der Export läuft weiter. Über „Fortschritt / Ergebnis“
im Hauptfenster lässt sich der aktuelle Zustand wieder öffnen. Dort bleiben nur
dieser Einstieg und die bisherige Export-Vorprüfung; die sichtbare Warteschlange,
ihre Dateiliste und ihre Fortschrittsbalken entfallen vollständig.
Nur „Abbrechen“ setzt das vorhandene Export-Abbruchsignal. Die interne Planung,
Abbruchbehandlung und Wiederaufnahme bleiben unverändert erhalten.

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

Fehler und nicht bestätigte Anteile bleiben in gemischten Feldern sichtbar.
Die Darstellung arbeitet mit ganzzahligen Intervallen und konstant 100 Zellen;
auch Einträge außerhalb der intern begrenzten Vorschau gehen ein.
100 % Bestätigung setzt die Bestätigung sämtlicher geplanter Anteile voraus.
Ein vollständiger SHA-Lesestand vor dem Digestvergleich wird nicht grün.
Die Bestätigung betrifft den Export, nicht die ursprüngliche Dateiintegrität;
der vollständige Prüfumfang ist über eine eigene Schaltfläche erreichbar.

## Weitere Angaben und Aktionen

Das Fenster zeigt Arbeitsschritt, Laufzeit, neu übertragene Bytes, Kopiertempo,
Dateizähler und bekannte Fehler/Überspringungen. Die SHA-Anzeige ist rein textlich:
Beim Kopieren wird SHA256 für den kopierten Datenstrom berechnet. Anschließend
wird die Zieldatei gelesen und ihre Prüfsumme verglichen. Währenddessen erscheint
„SHA256-Prüfung der Zieldatei läuft …“, ohne eigenen Balken oder Prüfprozentsatz.
Das 100-Felder-Raster bleibt unverändert beim Gesamtumfang und startet nicht neu.
Die vorhandene Restzeitschätzung gilt ausschließlich für das Kopieren,
wird während der Prüfung unterdrückt und ist ohne belastbare Rate nicht sichtbar.

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
