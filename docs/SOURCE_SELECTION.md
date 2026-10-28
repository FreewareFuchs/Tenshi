# Datenträger und Laufwerke auswählen

Die gemeinsame Schaltfläche **Datenträger oder Laufwerk auswählen** zeigt
gesamte Geräte und die ermittelten logischen Laufwerke in einer Übersicht.
Ein gesamter Datenträger umfasst die Partitionstabelle und alle Partitionen;
ein Laufwerk öffnet nur das ausgewählte Volume. Ein logisches Volume beginnt
für Tenshi weiterhin bei Byte-Offset 0.

Ein Laufwerk steht nur dann unter einem Gerät, wenn genau ein bekanntes Gerät
ermittelt wurde. Unbekannte Zuordnungen, verschwundene Geräte und Volumes über
mehrere Datenträger bleiben gesondert sichtbar. Die Liste enthält die bereits
bekannten Laufwerke mit Buchstaben bzw. eingehängten Linux-Blockvolumes; weitere
Partitionen können über die Analyse des gesamten Datenträgers gesucht werden.

Die Erkennung erfolgt nach Öffnen der Auswahl im Hintergrund. Sie liest unter
Windows Gerätedaten mit einem Handle ohne Datenlese-/Schreibrechte sowie
Volume-Metadaten. Unter Linux werden sysfs-/lsblk-/Geräteknoten-Metadaten genutzt.
Die Auflistung bestätigt keine Leseberechtigung. Beide Quellentypen werden
erst nach expliziter Auswahl und Bestätigung mit dem vorhandenen schreibgeschützten
Leser geöffnet; ein erster Leseversuch prüft den Zugriff. Bei einem Fehler bleiben
Auswahlfenster und bisherige Quelle erhalten.

Unter Windows können für beide Quellentypen Administratorrechte erforderlich
sein. Unter Linux gelten die vorhandenen Leseberechtigungen; Tenshi verändert
keine Geräteberechtigungen und startet sich nicht automatisch erhöht.

Die Gruppierung ist ausschließlich eine Anzeige. Export-, Imaging- und
Resume-Sicherheitsprüfungen ermitteln die tatsächliche Zuordnung weiterhin
unabhängig neu und lehnen unbekannte Quelle/Ziel-Trennung ab. Die bisherige
Windows-Prüfung `volume_disk_numbers()` verwendet standardmäßig weiterhin den
ursprünglichen Lesezugriff; nur die Anzeigeliste fordert Metadatenabfragen an.
