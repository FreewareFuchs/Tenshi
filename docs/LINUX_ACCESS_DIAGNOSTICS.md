# Diagnose fehlender Linux-Leserechte

Kann Tenshi ein Linux-Blockgerät mangels Berechtigung nicht öffnen, nennt die Meldung den ausgewählten Gerätepfad. Soweit verfügbar erscheinen außerdem Major:Minor-Gerätekennung, Modell und Größe des ausgewählten Geräts in Bytes. Bei einer Partition stammt die Modellbezeichnung vom übergeordneten Laufwerk; die Größe bleibt die der ausgewählten Partition.

Die zusätzlichen Angaben stammen ausschließlich aus dem Geräteknoten und begrenzten sysfs-Textabfragen. Sie benötigen keinen weiteren Leseversuch auf dem Datenträger. Fehlende oder beim Abziehen verschwundene Angaben werden ausgelassen und ersetzen nicht die eigentliche Zugriffsmeldung. Die Kennung beschreibt die aktuelle Auswahl; Gerätepfade können sich nach erneutem Anschließen ändern.

Die Meldung erklärt, dass nur Leserechte erforderlich sind und alternativ ein vorhandenes Image genutzt werden kann. Geräteberechtigungen müssen gezielt außerhalb von Tenshi durch die Systemverwaltung geprüft werden. Tenshi führt weder Berechtigungs- oder Gruppenänderungen noch einen privilegierten Neustart durch.

Geräte-Geometrieabfrage und Datei-Lesepfad verwenden dieselbe Diagnose. Der Fehler bleibt ein `PermissionError` mit `errno=EACCES` und der ausgewählten Quelle als `filename`. Die Oberfläche übersetzt die statischen Hinweise in alle sechs Sprachen und lässt Gerätepfad und Metadaten unverändert.
