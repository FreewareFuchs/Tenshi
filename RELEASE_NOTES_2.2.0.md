# Tenshi 2.2.0 – Performance und große Trefferlisten

Tenshi 2.2.0 reduziert die Belastung der grafischen Datei- und Ordneransicht bei großen Dateisystemindizes. Die Fensterliste wird seitenweise aufgebaut: maximal 750 Dateieinträge auf einmal. Suchen in sehr großen Indizes geben dem GUI-Ereignisloop regelmäßig Zeit zur Verarbeitung; laufende Suchen werden bei Navigation oder einer neuen Suche ignoriert. Metadatenaufbereitung erfolgt nach dem Auslesen im Hintergrund. Der aktuelle komplette Dateisystemindex bleibt weiterhin im RAM, und die Arbeit an einer eigenen On-Disk-Indexdatenbank ist für eine spätere Version vorgesehen.

**Bedienung:** Die zwei Pfeiltasten in der Zeile über dem Dateifenster blättern durch die Treffer. Die Gesamtzahl und der Bereich der sichtbaren Einträge werden angezeigt. Die Auswahl oder der Export einer Seite wirkt nur auf dort markierte Dateien. Ein vollständiger Ordnerexport umfasst weiterhin alle Dateien im betreffenden Ordner, unabhängig von der Seitendarstellung.

**Sicherheit:** Quelldatenträger werden weiterhin ausschließlich gelesen. Der grüne Stapel-Export und die Wiederaufnahme sind unverändert. Kein neues Reparatur-/Schreibwerkzeug wurde hinzugefügt.

**Validierung:** 305 automatisierte Tests auf Linux (mit virtueller grafischer Anzeige). Es liegt weiterhin keine unter Windows gebaute und auf realer Windows-Hardware geprüfte EXE vor. Erstelle die EXE mit `build_windows.bat` und führe bei Bedarf mit `run_tests.bat` die Windows-Regressionstests aus.
