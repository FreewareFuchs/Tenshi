# Tenshi 2.6.0 – Sitzungen speichern und laden

- Neue Menüfunktion **Analysesitzung > Sitzung speichern / Sitzung laden** in allen sechs Sprachen.
- Speichert die Partitionsliste und analysierte NTFS-/FAT32-/exFAT-/ext2/3/4-/Btrfs-/XFS-Dateisystemindizes für die spätere Wiederaufnahme einer Analyse auf **Image-Dateien**.
- Wiederherstellung von Verzeichnisbeziehungen, Dateimetadaten und verwalteten Exportinformationen (nicht: fertige Exportdateien, Fortschritt einer laufenden Operation oder Auswahlzustand).
- Prüfung der Quelle vor dem Wiederherstellen: Imagegröße, Änderungszeit am ursprünglichen Pfad, mehrere SHA-256-Stichproben und Dateisystem-Bootbereich. Bei einer verschobenen Image-Datei kann eine andere Pfadangabe gewählt werden, sofern Stichproben und Größe übereinstimmen.
- Metadaten in einem komprimierten JSON-basierten ZIP-Container; keine ausführbare Deserialisierung. Formatversion, Prüfsumme, Archivgröße und interne Struktur werden geprüft. Existierende Sitzungsdateien werden nicht überschrieben.
- Speicherung läuft in einem Hintergrundthread, um die Tkinter-Oberfläche zu entlasten.
- **Einschränkungen:** Kein Sitzungsimport für aktive physische Datenträger; keine vollständige Hashprüfung von TB-großen Images; bei Änderungen außerhalb der geprüften Stichproben sind nicht alle Manipulationen erkennbar. Analysedaten enthalten Dateinamen und ursprüngliche Dateipfade und sind weder verschlüsselt noch signiert. Niemals ohne Prüfung auf echte, defekte Datenträger vertrauen.
- Beibehalten: Tenshi-Logo, sechs Sprachen, zwei Register, grüner Stapel-Export, Doppelklick von Partition zu Dateisystem, Imaging, Fehlerprotokoll, Hell-/Dunkelmodus, gespeichertes Layout, Windows-EXE-Build, portable ZIP und Installer.

## Prüfung

Automatisierte GUI- und Logiktests mit synthetischen NTFS-/FAT32-/ext4-Images; Windows-EXE und echte Hardware sind in dieser Umgebung **nicht** ausgeführt worden. `run_tests.bat` bitte auf Windows prüfen.
