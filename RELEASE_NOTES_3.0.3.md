# Tenshi 3.0.3 – Release-Vorbereitung

Noch nicht veröffentlicht. Die Paketprüfung dieser Version steht aus.

- Die SHA256-Berechnung beim Stapel-Export und bei der Prüfung vorhandener Exporte lässt sich abbrechen. Vollständig geschriebene Dateien bleiben erhalten; unvollständige Prüfungen erhalten keinen Erfolgsstatus. Unbestätigte vorhandene Dateien werden weiterhin nicht überschrieben.
- Der Funktionsstand aus PR #47 wurde unter Linux und Windows automatisiert und manuell geprüft. Das ersetzt nicht die Abnahme der noch zu bauenden finalen Pakete 3.0.3.
- Windows-Installer und Portable-ZIP erhalten Version 3.0.3. Linux bleibt beim Paketnamen und Startbefehl `tenshi-recovery`, Paketversion 3.0.3-1. Diese sortiert nach 3.0.2-2.
- Die signierte APT-Quelle und ihre Einrichtung bleiben bestehen. Ein Update von 3.0.2-2 auf 3.0.3-1 muss vor der Veröffentlichung getestet werden.
- Quelle weiterhin ausschließlich lesend verwenden; Exporte und Images auf einem anderen physischen Datenträger speichern. Eine Prüfsumme garantiert keine erfolgreiche Wiederherstellung.
