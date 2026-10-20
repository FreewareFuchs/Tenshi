# Tenshi – Datenrettung und Datenträgeranalyse für Windows

Tenshi ist ein kostenloses, quelloffenes Programm von **FreewareFuchs** zum Untersuchen von Partitionen, Durchsuchen unterstützter Dateisysteme und Exportieren wiederherstellbarer Dateien auf einen separaten Datenträger.

**Windows 10/11 · 64 Bit · Experimentelle Beta**

[Website](https://freewarefuchs.de/tenshi/) · [Downloads](https://freewarefuchs.de/tenshi/#downloads) · [Bedienungsanleitung](https://freewarefuchs.de/tenshi/anleitung/) · [English](https://freewarefuchs.de/en/tenshi/)

> **Vor dem Einsatz:** Datenrettung ist nicht risikofrei. Auch reines Lesen kann einen beschädigten Datenträger zusätzlich belasten. Gerettete Dateien und Images immer auf einem anderen physischen Datenträger speichern. Eine erfolgreiche oder vollständige Wiederherstellung ist nicht garantiert.

[![Tenshi: Dateien, Ordner und Exportprüfung](https://freewarefuchs.de/tenshi/screenshots/dateien.png)](https://freewarefuchs.de/tenshi/#screenshots)

## Herunterladen und starten

Die [offiziellen GitHub-Releases](https://github.com/FreewareFuchs/Tenshi/releases) enthalten die veröffentlichten Downloads und Versionshinweise. Die [Website](https://freewarefuchs.de/tenshi/#downloads) führt direkt zu den beiden Windows-Varianten.

| Variante | Verwendung |
| --- | --- |
| Windows-Installer | Setup herunterladen und Tenshi auf dem PC installieren. |
| Portable ZIP | ZIP vollständig entpacken und die enthaltene `Tenshi.exe` starten. Keine Installation erforderlich. |

Die portable Variante kann Einstellungen und Fehlerprotokolle im Windows-Benutzerprofil speichern. Der GitHub-Quellcode-Download ist kein fertiges Windows-Programmpaket.

Installer und EXE sind nach dem dokumentierten Stand **nicht digital signiert**. Prüfe Herkunft und die SHA-256-Prüfsummen des jeweiligen Releases. Sicherheitsfunktionen nicht pauschal abschalten. [Download-Sicherheit und Prüfsummen](https://freewarefuchs.de/tenshi/sicherheit/)

## Was Tenshi kann

- GPT- und MBR-Partitionen untersuchen.
- Vorhandene Dateien und Ordner unterstützter Dateisysteme durchsuchen.
- Wiederherstellungsfunde anhand von Metadaten vor dem Export prüfen.
- Dateien und Ordner im Stapel auf einen separaten Datenträger exportieren; unterstützte Aufträge fortsetzen.
- RAW-, IMG- und DD-Abbilder lesen sowie Datenträger-Images erstellen, pausieren und fortsetzen.
- Analysesitzungen regulärer Image-Dateien speichern und wieder laden.
- Integrierte Offline-Hilfe mit F1, Hell-/Dunkelmodus und sechs Oberflächensprachen nutzen: Deutsch, Englisch, Spanisch, vereinfachtes Chinesisch, Russisch und Japanisch.

### Unterstützte Dateisysteme und Grenzen

| Dateisystem | Dokumentierter Funktionsumfang |
| --- | --- |
| NTFS | Vorhandene Dateien und experimentelle Wiederherstellung gelöschter MFT-Einträge. |
| FAT32 / exFAT | Vorhandene Dateien und eingeschränkte Rekonstruktion gelöschter Einträge. |
| ext2 / ext3 / ext4 | Vorhandene Dateien und experimentelle Wiederherstellung einzelner gelöschter Dateien. |
| Btrfs / XFS | Eingeschränkte Navigation und Export unterstützter vorhandener Dateistrukturen; Löschhinweise sind nicht exportierbar. |

„Bereit“ in der Exportprüfung bewertet plausible Metadaten, nicht die Unversehrtheit der Dateiinhalte. Überschriebene Daten lassen sich dadurch nicht zurückholen. Ein erfolgreicher Export garantiert **keine fehlerfreien Daten**. Exportierte Dateien anschließend selbst prüfen.

## Erste Schritte

1. Die [Hinweise zur Datensicherheit](https://freewarefuchs.de/tenshi/anleitung/#s1) lesen und möglichst mit einer geeigneten Kopie bzw. einem Image arbeiten.
2. Ein vorhandenes Image oder einen unterstützten Datenträger als Quelle auswählen. Für physischen Laufwerkszugriff können erhöhte Rechte nötig sein.
3. Eine erkannte Partition öffnen und die Dateien und Ordner untersuchen.
4. Gewünschte Dateien auswählen, **„Export prüfen“** verwenden und Hinweise beachten.
5. Über **„Stapel-Export / fortsetzen“** auf einen anderen physischen Datenträger exportieren und die Ergebnisse prüfen.

Die Quelle wird nur lesend geöffnet. Bei mechanischen Auffälligkeiten oder wertvollen Daten auf beschädigten Medien weitere Versuche vermeiden und professionelle Datenrettung erwägen.

[Ausführliche Bedienungsanleitung](https://freewarefuchs.de/tenshi/anleitung/) · [FAQ und Fehlerbehebung](https://freewarefuchs.de/tenshi/faq/)

## Entwicklungs- und Teststatus

Tenshi bleibt experimentelle Beta-Software. Automatisierte Tests mit synthetischen Images und simulierten Fehlerfällen ersetzen keine Prüfung auf beschädigter Hardware.

Nach den bisherigen Projektangaben wurden für **3.0.1** Windows-Praxistests gemeldet: Installation und Deinstallation, physischer Laufwerks- und USB-Zugriff, neun exportierte Prüffälle mit SHA-256-Abgleich sowie bitgenaues 4-MiB-Imaging. Für die Änderungen in **3.0.2** ist im bisherigen README noch kein Windows-Praxistest dokumentiert. Tatsächlich defekte Laufwerke wurden laut diesem Stand nicht geprüft. **Windows-Hardwaretest steht aus.**

Der [Windows-Abnahmeplan](WINDOWS_ABNAHME_3.0.0.md) ist ein Prüfplan, kein Nachweis einer abgeschlossenen Abnahme. Historische Testergebnisse beziehen sich jeweils auf die dort genannte Version.

## Änderungen und technische Dokumentation

- [Änderungsverlauf](CHANGELOG.md)
- [Versionshinweise zu 3.0.2](RELEASE_NOTES_3.0.2.md)
- [Dokumentation der Offline-Hilfe](HILFE_3.0.0.md)
- [Bisheriges README mit historischen Entwicklungsdetails](docs/README_HISTORY_2026-10-20.md)

## Aus dem Quellcode bauen

Voraussetzung: Windows und Python 3.11 oder neuer in 64 Bit, erreichbar über `py -3`.

1. Repository herunterladen oder klonen und in den Projektordner wechseln.
2. `check_windows.bat` für die nicht invasive Umgebungsprüfung ausführen.
3. `build_windows.bat` ausführen. Die Anwendung wird als `dist\Tenshi.exe` erstellt.
4. Automatisierte Tests separat mit `run_tests.bat` ausführen.
5. Optional mit `build_portable.bat` eine portable ZIP oder mit `build_installer.bat` einen Installer erstellen. Der Installer-Build benötigt Inno Setup 6.3 oder neuer.

`Tenshi.exe --smoke-test` prüft gebündelte Komponenten ohne Fenster und ohne Laufwerkszugriff. Ein erfolgreicher Build oder Smoke-Test ist kein Nachweis erfolgreicher Datenrettung.

Bei Build-Problemen: [Build-Fehlersuche](BUILD_FEHLERSUCHE.md). Bei Weitergabe von Protokollen private Pfade und andere sensible Angaben vorab prüfen.

## Fehler melden und mitarbeiten

Für Fehler und Verbesserungsvorschläge bitte ein [GitHub-Issue](https://github.com/FreewareFuchs/Tenshi/issues) erstellen. Nenne Version, Windows-Version, Schritte zur Reproduktion sowie erwartetes und tatsächliches Verhalten. Keine privaten Dateien, vollständigen Laufwerksabbilder oder ungeprüften Protokolle veröffentlichen.

[Beiträge zum Projekt](CONTRIBUTING.md) · [Sicherheitsmeldungen](SECURITY.md)

## Lizenz und Drittkomponenten

Die Datei [LICENSE](LICENSE) enthält die MIT-Lizenz mit Copyright-Vermerk für FreewareFuchs. Hinweise zu Drittkomponenten stehen in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Die bestehenden Hinweise zur Klärung von Rechten an Logos, Assets und Drittkomponenten bleiben in [OPEN_SOURCE_START_HIER.md](OPEN_SOURCE_START_HIER.md) dokumentiert. Die Überarbeitung dieses README bestätigt keine abgeschlossene Rechteprüfung.
