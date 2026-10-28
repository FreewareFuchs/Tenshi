# Separates Export-Fortschrittsfenster

Das Fenster öffnet beim Start eines Stapel-Exports ohne modale Sperre. Schließen
beendet nur die Ansicht; der Export läuft weiter. Über die ausgeklappte
Wiederherstellungswarteschlange und „Fortschrittsfenster“ lässt sich der aktuelle
Zustand wieder öffnen. Nur „Abbrechen“ setzt das vorhandene Export-Abbruchsignal.

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
auch Einträge außerhalb der auf 4.000 Zeilen begrenzten UI-Vorschau gehen ein.
100 % Bestätigung setzt die Bestätigung sämtlicher geplanter Anteile voraus.
Ein vollständiger SHA-Lesestand vor dem Digestvergleich wird nicht grün.
Die Bestätigung betrifft den Export, nicht die ursprüngliche Dateiintegrität;
der vollständige Prüfumfang ist über eine eigene Schaltfläche erreichbar.

## Weitere Angaben und Aktionen

Das Fenster zeigt Arbeitsschritt, Laufzeit, neu übertragene Bytes, Kopiertempo,
Dateizähler und bekannte Fehler/Überspringungen. SHA-Lesefortschritt wird separat
angezeigt. Die vorhandene Restzeitschätzung gilt ausschließlich für das Kopieren,
wird während der Prüfung unterdrückt und ist ohne belastbare Rate nicht sichtbar.

Nach dem Abschluss lassen sich der bestehende Ergebnisbericht ansehen oder eine
unveränderte Kopie speichern. Das Kopieren läuft außerhalb des GUI-Threads, lehnt
bestehende Zieldateien ab und verwendet die bestehenden Ziel-/Handle-Prüfungen.
Die ursprüngliche Quellzuordnung wird für diesen Schutz festgehalten. Ein späterer
Quellenwechsel im Hauptfenster ändert sie nicht. Die Schaltfläche für den Zielordner
öffnet lediglich den bereits vorhandenen Exportordner, ohne Shell-Befehlsverkettung.

Das Canvas erzeugt 100 Rechtecke und 100 Symbole einmalig; unveränderte Zustände
werden nicht neu gezeichnet. Größenänderungen werden gebündelt verarbeitet.
Fenstertimer enden mit dem Schließen der Ansicht. Alle sechs UI-Sprachen und
beide Farbvarianten werden geprüft. Scanner und Export-I/O bleiben unverändert.

Analyse- und Imaging-Bereichskarten folgen separat. Dieser Schritt behauptet
keine zusätzlichen Informationen über Lesefehler physischer Datenträger.
