# Aussagekraft der Export- und Dateiprüfung

| Anzeige | Tatsächlich geprüft | Nicht bestätigt |
| --- | --- | --- |
| Metadaten plausibel | Unterstützte, plausible Dateizuordnung und Größenangaben | Lesbarkeit oder ursprünglicher Dateiinhalte |
| Dateigröße vollständig gelesen | Der Datenstrom lieferte die gemeldete Bytezahl; SHA-256 wurde berechnet | Übereinstimmung mit einer bekannten Originaldatei |
| Exportiert – Originalinhalt ungeprüft | Export abgeschlossen; Zieldatei gelesen und SHA-256 im Exportstatus gespeichert | Ein separater erneuter Vergleich mit der Quelle oder einem Original |
| Export-Prüfsumme bestätigt | Vorhandenes Ziel hat beim Fortsetzen die gespeicherte Größe und SHA-256 des früheren Exports | Ein erneuter Vergleich mit dem aktuellen Quell-Dateistream oder einem Original |

Die zusätzlichen Hinweise erscheinen in allen sechs Oberflächensprachen. Der Exportbericht erläutert den Umfang neuer Exporte und der Wiederaufnahme; die Vorabprüfung nennt ausdrücklich ihre Beschränkung auf Metadaten. Interne Statuswerte und gespeicherte Aufträge bleiben kompatibel.

Diese Änderung führt keinen zusätzlichen vollständigen Quell-Lesevorgang ein. Die beim Export berechnete Ziel-Prüfsumme ist kein unabhängiger Nachweis, dass die Dateizuordnung richtig war oder gelöschte Daten unversehrt sind. Deshalb darf eine übereinstimmende Größe oder gespeicherte Prüfsumme nicht als Bestätigung der ursprünglichen Dateiinhalte verstanden werden.


## Entwicklungsstand: Prüfung nach Abbruch fortsetzen

Neue Stapel-Exporte berechnen während des Kopierens zusätzlich SHA256 über
exakt die vom Leser bereitgestellten und geschriebenen Daten. Nach erfolgreichem
Schreiben wird die Zieldatei gelesen und mit dieser Prüfsumme verglichen.
Die Prüfsumme belegt keine ursprüngliche Integrität gelöschter Daten.

Wird die anschließende Zielprüfung abgebrochen oder tritt dabei ein Fehler auf,
bleibt die vollständige Datei erhalten. Die Statusdatei enthält den Prüfwert
des kopierten Datenstroms, die Byteanzahl und eine Markierung der offenen Prüfung.
Bei derselben Quelle, Auswahl und demselben Ziel **Stapel-Export / fortsetzen**
erneut starten: Nur passend markierte Dateien werden erneut gelesen und bei
passender Größe und SHA256 bestätigt. Es erfolgt kein erneutes Kopieren oder
Überschreiben. Die Quelle wird für diesen Inhaltsvergleich nicht erneut gelesen;
die bestehenden Identitäts- und Metadatenprüfungen bleiben aktiv.

Ein erneuter Abbruch erhält den Prüfstand. Abweichende Dateien werden als Fehler
gemeldet; ihre neue Prüfsumme wird nicht als Vergleichswert übernommen. Während
der Zielprüfung erkannte Dateiänderungen oder ein ausgetauschter Pfad verhindern
die Bestätigung. Fremde Dateien und ältere abgebrochene Exporte ohne diesen
maschinenlesbaren Prüfstand bleiben gesperrt; gleiche Dateigröße genügt nicht.
Ein Prozessabsturz vor dem Speichern des Prüfstands kann weiterhin eine Datei
hinterlassen, die mangels Nachweis nicht automatisch bestätigt werden darf.

Diese Ergänzung ist noch nicht Bestandteil der veröffentlichten Version 3.0.3.
