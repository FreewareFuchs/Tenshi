# Tenshi 3.0.2 Beta – Benutzerhandbuch (Deutsch)

## 1. Zweck und Grenzen

Tenshi ist ein experimentelles Windows-Datenrettungsprogramm für **Windows 10/11 (64 Bit)**. Es untersucht Image-Dateien und – mit gegebenenfalls erhöhten Berechtigungen – physische Datenträger und Volumes. Die Quellmedien werden **nur lesend** geöffnet; Ergebnisse werden in einem getrennten Zielverzeichnis abgelegt. Auch lesende Zugriffe können physisch geschädigte Medien zusätzlich belasten. Keine Garantie, dass erkannte oder exportierte Dateien vollständig sind.

## 2. Start und Programmausgaben

- **Installer:** `Tenshi_Setup_3.0.2.exe` installieren, Tenshi im Startmenü öffnen.
- **Portable:** `Tenshi_Portable_3.0.2_Win64.zip` in einen Ordner entpacken und `Tenshi.exe` ausführen. Portable bedeutet *ohne Installation*; Einstellungen/Logs liegen teilweise weiterhin im Windows-Benutzerprofil.
- Unsignierte EXE: Windows kann eine Warnung anzeigen; Dateiherkunft und veröffentlichte SHA-256-Prüfsumme vor Nutzung vergleichen. Warnungen nicht ohne Prüfung umgehen.
- Sprache oben rechts wählen: Deutsch, Englisch, Spanisch, vereinfachtes Chinesisch, Russisch oder Japanisch. Oberflächendesign Hell/Dunkel umschaltbar.

## 3. Quelle auswählen und Partitionen untersuchen

1. Über **Image auswählen**, physisches Laufwerk oder Windows-Volume eine Quelle wählen. Unterstützte Image-Endungen umfassen `.raw`, `.img`, `.dd`.
2. Tenshi wechselt automatisch zum Reiter **Partitionen** und startet eine *Schnellanalyse* (anfänglicher Suchbereich bis 64 MiB und Partitionsmetadaten). Das ist kein vollständiger Datenträgerscan.
3. Ergebnis prüfen. Falls eine Partition nicht gefunden wird, optional die *Tiefensuche* starten.
4. Die gewünschte Partitionszeile **doppelklicken**. Tenshi wechselt nach **Dateien & Ordner** und liest das erkannte Dateisystem ein.
5. Auf dem Quellmedium keine Dateien anlegen, formatieren oder reparieren. Wenn Windows das Formatieren eines Laufwerks anbietet: abbrechen.

## 4. Dateien ansehen und wiederherstellen

- Dateisysteme: NTFS, FAT32, exFAT sowie ext2/3/4; Btrfs/XFS mit eingeschränktem Funktionsumfang.
- Suche nach Namen/Erweiterungen, Kategorien für Bilder, Video, Audio, Dokumente, Archive. Die Dateiansicht ist paginiert. `.tmp`-Dateien können in der Ansicht ausgeblendet sein, beim rekursiven Export jedoch weiterhin vorkommen.
- **Export prüfen** liefert eine Plausibilitätsbewertung anhand von Metadaten: `Bereit`, `Warnung` oder `Gesperrt`. `Bereit` bedeutet nicht, dass der Inhalt nachgewiesenermaßen korrekt ist.
- Mit dem grünen **Stapel-Export / fortsetzen** Dateien oder Ordner in ein **anderes physisches Laufwerk** exportieren.
- Neue Aufträge erhalten einen Ordner `Tenshi_Export_<Signatur>`. Die tatsächlich geretteten Dateien liegen darunter in `files/`. Vorherige Aufträge mit `RecoveryDesk_Export_*` bleiben unverändert und ggf. fortsetzbar.
- Die Ergebnisse möglichst gegen bekannte Originale, Dateiformate oder SHA-256-Vergleichswerte prüfen.

## 5. Gelöschte Dateien

NTFS unterstützt experimentelle Rekonstruktion aus MFT-Daten; FAT32/exFAT und ext2/3/4 haben eingeschränkte Methoden. Nachweislich überschrieben bzw. widersprüchliche Clusterbelegung kann zur Exportsperre führen. Btrfs/XFS-Löschhinweise sind nicht als rekonstruierbarer Export implementiert. Komprimierte, verschlüsselte oder Sparse-NTFS-Dateien können vom Export ausgeschlossen sein. Gelöscht erkannte Dateien sind nicht automatisch wiederherstellbar.

## 6. Imaging und Wiederaufnahme

1. Für wichtige Quelldatenträger zunächst überlegen, ob ein professionelles, schonendes Imaging geeigneter ist. Viele Leseversuche können den Zustand verschlechtern.
2. Über **Image erstellen / fortsetzen** ein Ziel auf einem **separaten physischen Datenträger** wählen.
3. Für die Bearbeitung von Lesefehlern gibt es optional 0–3 zusätzliche Wiederholungen. `Sicher anhalten` stoppt ohne künstliche Daten; `Nullen + protokollieren` erzeugt **fehlende Datenbereiche**, keine echte Rekonstruktion.
4. Bei Unterbrechungen lässt sich ein passender Auftrag anhand von Prüfpunkten fortsetzen. Statusdateien und bereits beschriebene Zielbereiche nicht manuell verändern.
5. Fertige Images nach Möglichkeit bitgenau mit dem Quell-Image vergleichen (z. B. SHA-256) – sofern die Quelle zuverlässig gelesen werden kann.

## 7. Sitzungen, Hilfe, Datenschutz

- **Analysesitzung**: Index einer regulären Image-Datei speichern/laden. Dabei werden Metadaten zur Imagezuordnung geprüft. Das ist *kein* Backup der Dateiinhalte. Sitzungen können persönliche Dateinamen enthalten und gehören nicht in öffentliche Fehlerberichte.
- **? Hilfe** oder **F1**: integrierte Offline-Hilfe mit neun Themen in sechs Sprachen.
- Fehlerprotokoll: `%LOCALAPPDATA%\Tenshi\Logs\tenshi-errors.log`. Auch bei technischen Logs vor der Weitergabe personenbezogene Informationen prüfen.
- Einstellungen werden teilweise im Benutzerprofil gespeichert; portable Nutzung bedeutet nicht, dass keinerlei Spuren hinterlassen werden.

## 8. Bei Problemen

Vorher prüfen: Originalmedium nicht verändern, keine Windows-Datenträgerreparatur am Original auslösen, andere Laufwerke/Exportordner benutzen, Quell- und Zielmedium nicht vertauschen. Für Fehlerbeschreibung Version, Dateisystem, Funktion, reproduzierbare Schritte und bereinigtes Fehlerprotokoll nennen. Bei wertvollen Daten oder offensichtlichem Hardwaredefekt anhalten und fachliche Hilfe nutzen.
