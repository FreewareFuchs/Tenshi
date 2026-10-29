# Exportziel vor dem Kopieren prüfen

Für 3.0.9 vorgesehen; Funktionen manuell abgenommen, endgültige Pakete noch in Vorbereitung. Der bestehende
Exportplan einschließlich Unterordnern liefert die Dateigrößen. Die Zielprüfung
läuft im Export-Hintergrundauftrag und wird vor dem ersten Anlegen eines
Exportordners, einer Statusdatei oder einer Ausgabedatei bestätigt.

Der Dialog ersetzt die bisherige Exportbestätigung. Er nennt das Ziel und sein
Dateisystem, die geplanten Dateiinhalte, eine Obergrenze zusätzlich benötigter
Dateibytes sowie den aktuell für den Benutzer verfügbaren Platz.

Vollständige reguläre Dateien mit passendem Wiederaufnahme-Status und passender
Größe werden zur erneuten Prüfung gezählt. Sie benötigen zunächst keine erneute
Kopie. Das ist keine Inhaltsbestätigung: Die vorhandenen Hash-Prüfungen laufen
weiter; fremde, beschädigte oder ausgetauschte Dateien werden nicht überschrieben.
Fehlende und unvollständige Dateien benötigen ihre gesamte geplante Größe.

Die Schätzung kann wegen nicht exportierbarer Metadaten zu hoch ausfallen.
Dateisystem-Metadaten, Berichte und Prüfsummendateien benötigen zusätzlichen
Platz. Kompression, Speicherquoten und gleichzeitige Änderungen können die
tatsächlich verfügbare Kapazität beeinflussen. Es wird keine erfolgreiche
Ausführung allein aufgrund einer Platzangabe zugesichert.

## Warnungen und Grenzen

- Bei voraussichtlich zu wenig Platz ist Nein vorausgewählt. Ein ausdrücklich
  bestätigter Start bleibt möglich, da der Bedarf eine Obergrenze darstellt.
- Ein erkanntes FAT/FAT32-Ziel darf keine neu zu kopierende Datei über
  `2**32 - 1` Bytes aufnehmen. Der Auftrag wird davor angehalten; ein anderes
  Ziel oder eine andere Auswahl ist erforderlich.
- Nicht verfügbare Werte stehen als „Nicht ermittelbar“, statt als null oder
  vermeintlich ausreichender Platz. Bei manchen VM-/Netzwerkfreigaben ist das
  darunterliegende Dateisystem unbekannt; Tenshi errät keine FAT32-Eigenschaft.
- Die Prüfung schreibt keine Testdatei, öffnet keine Rohgeräte und erweitert
  keine Rechte. Der bisherige Schutz gegen das Schreiben auf das Quellmedium
  sowie sichere Zielzugriffe bleiben bestehen.

Windows verwendet den tatsächlichen Einhängepunkt über
[GetVolumePathNameW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumepathnamew)
und den Dateisystemnamen über
[GetVolumeInformationW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw).
Ein Ordner-Mount wird somit nicht allein anhand seines Laufwerksbuchstabens
beurteilt. Die FAT-Grenze entspricht der von Microsoft dokumentierten
[FAT/FAT32-Behandlung](https://devblogs.microsoft.com/oldnewthing/20140806-00/?p=323).
Linux verwendet `/proc/self/mountinfo` aus dem eigenen Mount-Namensraum, den
längsten passenden Einhängepunkt und die Gerätekennung des ausgewählten Ordners.
Für freien Platz dient `shutil.disk_usage`, ohne zusätzliche Geräteabfragen.

## Bedienung prüfen

1. Einen bekannten kleinen Export wählen. Der Dialog zeigt Bedarf und freien
   Platz. Nein darf keinen neuen Exportordner erzeugen; Ja startet den Export.
2. Export pausieren, fortsetzen und abbrechen. Die bisherigen Funktionen bleiben
   erhalten. Während der Zielprüfung ist Pause deaktiviert; Abbrechen bleibt
   verfügbar. Schließen des Hauptfensters beendet auch die wartende Prüfung.
3. Einen abgebrochenen Auftrag fortsetzen. Ohne neue Platzwarnung erfolgt keine
   zusätzliche Bestätigung. Bei einer abgelehnten Warnung bleibt der bisherige
   Auftrag fortsetzbar und die Statusdatei unverändert.
4. Soweit ein FAT32-Ziel verfügbar ist, eine Datei größer als dessen Grenze
   auswählen. Die Meldung muss vor dem ersten Kopieren erscheinen. Für diesen
   Test keine Daten von beschädigten Originalmedien verwenden.
5. Die Freigabe einer VM und alle sechs Sprachen prüfen. Pfade und Dateinamen
   dürfen durch Übersetzungen nicht verändert werden.

Das Exportfortschrittsfenster gehört zum Hauptfenster und bleibt darüber, ohne
das Hauptfenster zu sperren. Beim Öffnen und Wiederöffnen wird es am Hauptfenster
zentriert; es springt beim Verschieben oder Vergrößern nicht ständig zurück.
Ein Klick auf Stapel-Export während eines laufenden oder pausierten Auftrags
öffnet dieselbe Fortschrittsansicht erneut. Schließen der Ansicht verändert
weder den Auftrag noch die Pause. Es wird kein zweiter Export gestartet und
kein neuer Zielordner abgefragt.

Die automatischen Tests verwenden normale temporäre Dateien und simulierte
Zielmetadaten. Sie ersetzen keine praktische Prüfung unterschiedlicher realer
Zieldatenträger oder Freigaben.
