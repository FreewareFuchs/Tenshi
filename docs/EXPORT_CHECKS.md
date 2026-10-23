# Aussagekraft der Export- und Dateiprüfung

| Anzeige | Tatsächlich geprüft | Nicht bestätigt |
| --- | --- | --- |
| Metadaten plausibel | Unterstützte, plausible Dateizuordnung und Größenangaben | Lesbarkeit oder ursprünglicher Dateiinhalte |
| Dateigröße vollständig gelesen | Der Datenstrom lieferte die gemeldete Bytezahl; SHA-256 wurde berechnet | Übereinstimmung mit einer bekannten Originaldatei |
| Exportiert – Originalinhalt ungeprüft | Export abgeschlossen; Zieldatei gelesen und SHA-256 im Exportstatus gespeichert | Ein separater erneuter Vergleich mit der Quelle oder einem Original |
| Export-Prüfsumme bestätigt | Vorhandenes Ziel hat beim Fortsetzen die gespeicherte Größe und SHA-256 des früheren Exports | Ein erneuter Vergleich mit dem aktuellen Quell-Dateistream oder einem Original |

Die zusätzlichen Hinweise erscheinen in allen sechs Oberflächensprachen. Der Exportbericht erläutert den Umfang neuer Exporte und der Wiederaufnahme; die Vorabprüfung nennt ausdrücklich ihre Beschränkung auf Metadaten. Interne Statuswerte und gespeicherte Aufträge bleiben kompatibel.

Diese Änderung führt keinen zusätzlichen vollständigen Quell-Lesevorgang ein. Die beim Export berechnete Ziel-Prüfsumme ist kein unabhängiger Nachweis, dass die Dateizuordnung richtig war oder gelöschte Daten unversehrt sind. Deshalb darf eine übereinstimmende Größe oder gespeicherte Prüfsumme nicht als Bestätigung der ursprünglichen Dateiinhalte verstanden werden.
