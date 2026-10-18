# Tenshi 2.5.1 – Doppelklick-Navigation

**Neu:** Ein Doppelklick auf eine Zeile in „Partitionen“ übernimmt die Partition, wechselt sofort zu „Dateien & Ordner“ und startet das Einlesen. Die Auswahl nutzt die Byte-Offsets des Partitionsberichts (auch bei 4-KiB-Sektoren), nicht die Nummer der Zeile oder eine bereits markierte andere Partition.

Für nicht unterstützte Dateisysteme erscheint ein Hinweis. Leere Zeilen und Tabellenüberschriften lösen nichts aus. Während einer laufenden Partitions- oder Dateisystemanalyse wird kein zweiter Scan gestartet; ist zwischenzeitlich die Quelle geändert worden, muss zuerst eine neue Partitionsanalyse durchgeführt werden. Die manuelle Funktion „Partition übernehmen“ startet weiterhin keinen Scan.

Nur-Lese-Zugriff, die zwei Register, das Tenshi-Logo, alle sechs Sprachen, Hell-/Dunkelmodus, das Fensterlayout, Imaging und der grüne Stapel-Export bleiben erhalten.

`build_windows.bat` erstellt `dist\Tenshi.exe`, `run_tests.bat` führt die Tests separat aus. `build_portable.bat` und `build_installer.bat` erzeugen optional die versionierten Pakete 2.5.1. Nicht auf physischer Windows-Hardware getestet; synthetische Test-Images ersetzen keine echte Wiederherstellungsprüfung.
