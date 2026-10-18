# Tenshi 3.0.0 – Benutzerhilfe

## Grundregel

Tenshi öffnet Quellmedien nur lesend. Verwende bei wertvollen Daten möglichst ein **vorher erstelltes Image**, sichere Ergebnisse auf einem **anderen physischen Datenträger** und arbeite nicht unnötig auf einem mechanisch beschädigten Laufwerk. Bereits das Lesen belastet defekte Hardware. Für schwere Fälle professionelle Datenrettung erwägen.

## Erster Durchgang

1. `Image auswählen` anklicken und eine eigene, sichere Image-Datei öffnen.
2. Im Register **Partitionen** die Schnellanalyse ausführen; Tiefensuche nur bei Bedarf.
3. Eine gefundene Partition doppelklicken: Der Byte-Offset wird übernommen, das Register **Dateien & Ordner** geöffnet und das Dateisystem eingelesen.
4. Dateien und Ordner auswählen. Bei großen Listen mit **Vorherige Seite** / **Nächste Seite** blättern (maximal 750 Einträge je Seite; Strg+A betrifft die aktuelle Seite).
5. `Export prüfen` ausführen. **Bereit** bestätigt nur plausible Metadaten; der Inhalt bleibt ungetestet. **Warnung** steht für Unsicherheit; **Gesperrt** für einen festgestellten Metadatenkonflikt.
6. Grünen **Stapel-Export / fortsetzen** starten. Das Exportziel muss auf einem anderen physischen Datenträger liegen.

## Imaging

`Image erstellen / fortsetzen` kopiert das Quellmedium in eine separate Zieldatei. Statusdateien erlauben eine kontrollierte Wiederaufnahme. Ein laufendes Image darf in seinem Ziel weitergeschrieben werden; die Quelle bleibt unangetastet. Bei bestätigten Medienfehlern sind 0–3 zusätzliche Leseversuche möglich. Jeder Wiederholungsversuch belastet das Medium. `Nullen + protokollieren` erzeugt **Datenlücken**; `Sicher anhalten` belässt den letzten gültigen Prüfpunkt. Zugriffsverweigerung oder Geräteabbruch stoppen unabhängig davon.

## Analysesitzung

Über das Menü **Analysesitzung** eine vorhandene Analyse speichern oder laden. Das ist **nur bei regulären Images** möglich. Das Laden kontrolliert Imagegröße, Änderungszeit und mehrere SHA-256-Proben; es ersetzt keinen vollständigen Vergleich. Eine `.tenshi-session` ist **kein Backup** und kann **private Dateinamen und Pfade** enthalten.

## Unterstützte Dateisysteme und Einschränkungen

- **NTFS:** Dateinavigation, MFT- und eingeschränkte Löschrekonstruktion; erkannte Zuordnungskonflikte verhindern riskanten Export.
- **FAT32/exFAT:** Navigation und eingeschränkte Löschrekonstruktion, unter Umständen mit erhaltener FAT-Kette. Freie Cluster können überschrieben sein.
- **ext2/3/4:** Navigation und experimentelle Löschrekonstruktion, abhängig von erhaltenen Inodes/Blöcken.
- **Btrfs/XFS:** Eingeschränkte Navigation und Export vorhandener unterstützter Dateien; Löschhinweise sind nicht exportierbar.

Ein erfolgreicher Export beweist **keine vollständige oder fehlerfreie Wiederherstellung**.

## Such- und Anzeigeoptionen

Die Suche unterstützt Dateitypen und Schnellkategorien, einschließlich Office-Formaten und Image-Endungen. TMP-Dateien sind standardmäßig nur **ausgeblendet**, nicht gelöscht; bei rekursiven Ordnerexporten können sie vorkommen. Die Ordnerbaum-Breite, Spaltenbreiten, Fenstergeometrie und Hell-/Dunkelmodus werden gespeichert.

## Diagnose, Installation und Hilfe

- **? Hilfe** öffnet die lokale Hilfe. **F1** zeigt den Kontext des aktiven Registers.
- **Fehlerprotokoll** zeigt technische Fehlermeldungen; vor dem Teilen nach privaten Pfaden prüfen.
- `check_windows.bat` prüft Windows-Voraussetzungen **ohne** physische Laufwerkszugriffe.
- `run_tests.bat` führt Tests separat aus, `build_windows.bat` erstellt unter Windows die EXE, `build_portable.bat` das portable ZIP und `build_installer.bat` mit Inno Setup den Installer.
- Die portable Variante speichert Einstellungen weiterhin im Benutzerprofil. EXE und Installer sind nicht digital signiert.

**Status:** Windows-Tests mit echter Hardware und die Prüfung eines Installationspakets müssen noch durchgeführt werden. Testimages und simulierte Fehlerfälle ersetzen diese Prüfungen nicht.
