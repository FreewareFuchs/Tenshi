# Aussagekraft der Export- und Dateiprüfung

| Anzeige | Tatsächlich geprüft | Nicht bestätigt |
| --- | --- | --- |
| Metadaten plausibel | Unterstützte, plausible Dateizuordnung und Größenangaben | Lesbarkeit oder ursprünglicher Dateiinhalte |
| Dateigröße vollständig gelesen | Der Datenstrom lieferte die gemeldete Bytezahl; SHA-256 wurde berechnet | Übereinstimmung mit einer bekannten Originaldatei |
| Exportiert – Originalinhalt ungeprüft | Export abgeschlossen; Zieldatei gelesen und SHA-256 im Exportstatus gespeichert | Ein separater erneuter Vergleich mit der Quelle oder einem Original |
| Export-Prüfsumme bestätigt | Vorhandenes Ziel hat beim Fortsetzen die gespeicherte Größe und SHA-256 des früheren Exports | Ein erneuter Vergleich mit dem aktuellen Quell-Dateistream oder einem Original |

Die zusätzlichen Hinweise erscheinen in allen sechs Oberflächensprachen. Der Exportbericht erläutert den Umfang neuer Exporte und der Wiederaufnahme; die Vorabprüfung nennt ausdrücklich ihre Beschränkung auf Metadaten. Interne Statuswerte und gespeicherte Aufträge bleiben kompatibel.

Diese Änderung führt keinen zusätzlichen vollständigen Quell-Lesevorgang ein. Die beim Export berechnete Ziel-Prüfsumme ist kein unabhängiger Nachweis, dass die Dateizuordnung richtig war oder gelöschte Daten unversehrt sind. Deshalb darf eine übereinstimmende Größe oder gespeicherte Prüfsumme nicht als Bestätigung der ursprünglichen Dateiinhalte verstanden werden.


## Für 3.0.4 vorbereitet: Prüfung nach Abbruch fortsetzen

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

## Für 3.0.4 vorbereitet: Windows-Ziele während des Schreibens sichern

Beim Öffnen von Image- und Exportdateien hält Tenshi unter Windows nun alle
Elternverzeichnisse vom Laufwerks- bzw. Freigabestamm bis zum Zielordner geöffnet.
Diese Handles erlauben weder Schreib- noch Löschfreigabe. Ein gewöhnlicher
Ordneraustausch oder das nachträgliche Umwandeln eines gehaltenen Verzeichnisses
in einen Reparse Point soll dadurch während des Schreibens scheitern.
Die physische Quell-/Zieltrennung wird bei Gerätequellen nochmals geprüft,
während diese Verzeichnisse gehalten werden.

Junctions, symbolische Links und andere Reparse Points werden am tatsächlich
geöffneten Handle abgelehnt, auch bei der Zieldatei selbst. Neue Dateien werden
weiterhin ausschließlich neu angelegt; bestehende Dateien werden beim Öffnen
nicht gekürzt. Dateiidentität und Ausschluss einer mit der Quelle identischen
Datei werden vor Übergabe an den schreibenden Aufrufer geprüft.

Als Ausgabeziel ist ein gewöhnlicher Ordner ohne solche Umleitungen zu wählen.
Der Schutz gilt für die Lebensdauer des Schreibhandles. Status-/Berichtsdateien,
Aufräumvorgänge nach dem Schließen und spätere erneute Öffnungen sind damit
nicht pauschal abgesichert. Er ist keine Sicherheitsgrenze gegen Administratoren,
veränderte Laufwerkszuordnungen, Mounts oder Dateisystemtreiber.
Diese Ergänzung ist noch nicht Bestandteil der veröffentlichten Version 3.0.3.
