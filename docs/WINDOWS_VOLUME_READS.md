# Windows: letzte Sektoren logischer Laufwerke lesen

Bei einem direkten Volume wie `C:` kann der Dateisystemtreiber Leseaufträge am
Ende der Partition verkürzen. Der von NTFS nutzbare Bereich kann kleiner sein
als die gesamte Partition. Das betrifft unter anderem die Prüfung am letzten
Sektor bei der Partitionsanalyse und ein vollständiges Volume-Image.

Tenshi setzt deshalb `FSCTL_ALLOW_EXTENDED_DASD_IO` auf dem bereits mit `rb`
geöffneten Volume-Handle, bevor es den sektorausgerichteten Leser bereitstellt.
Die Einstellung gilt nur für dieses Handle. Es werden keine Schreibrechte
angefordert und keine Locks, Dismounts oder persistenten Geräteänderungen
vorgenommen. Physische Datenträger, Image-Dateien und Linux-Geräte erhalten
diese Windows-Volume-Einstellung nicht.

Die eigene Größenbegrenzung bleibt erhalten: Jeder Auftrag liegt innerhalb
der durch `source_size()` ermittelten Partitionsgröße. Unerwartet kurze oder
leere Antworten bleiben Fehler; fehlende Bytes werden nicht durch Nullen
ersetzt. Schlägt die Handle-Einstellung fehl, wird der Handle geschlossen und
der Fehler gemeldet, statt einen vollständigen Zugriff vorzutäuschen.

Regression: simulierter Volume-Treiber mit einem Dateisystembereich, der vor
dem Partitionsende endet; vollständige Partitionsanalyse, unveränderte letzte
Bytes und Grenzen bei 512-Byte- sowie 4Kn-Sektoren; Konfigurationsfehler,
unveränderte physische/Image-Zugriffe und echte Short Reads.

Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_allow_extended_dasd_io
