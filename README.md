# Tenshi – Datenrettung und Datenträgeranalyse für Windows und Linux

Tenshi ist ein kostenloses, quelloffenes Programm von **FreewareFuchs** zum Untersuchen von Partitionen, Durchsuchen unterstützter Dateisysteme und Exportieren wiederherstellbarer Dateien auf einen separaten Datenträger.

**Windows 10/11 · 64 Bit · Linux Mint 22.x: DEB-Paket oder Quellcode**

[Website](https://freewarefuchs.de/tenshi/) · [Downloads](https://freewarefuchs.de/tenshi/#downloads) · [Bedienungsanleitung](https://freewarefuchs.de/tenshi/anleitung/) · [English](https://freewarefuchs.de/en/tenshi/)

> **Vor dem Einsatz:** Datenrettung ist nicht risikofrei. Auch reines Lesen kann einen beschädigten Datenträger zusätzlich belasten. Gerettete Dateien und Images immer auf einem anderen physischen Datenträger speichern. Eine erfolgreiche oder vollständige Wiederherstellung ist nicht garantiert.

[![Tenshi: Dateien, Ordner und Exportprüfung](https://freewarefuchs.de/tenshi/screenshots/dateien.png)](https://freewarefuchs.de/tenshi/#screenshots)

**3.0.8 ist seit 29.10.2026 stabil veröffentlicht.** Pause/Fortsetzen, Wiederaufnahme nach Abbruch und einzelne sowie zusammengefasste Prüfsummendateien sind manuell abgenommen. Die endgültigen Paketstarts, Versionsanzeigen und die Hilfe in sechs Sprachen sind bestätigt. Website und signierte APT-Quelle sind öffentlich geprüft.
[Änderungen und bestätigter Prüfstand](RELEASE_NOTES_3.0.8.md).

Export und Imageerstellung haben eigene, wieder aufrufbare Fortschrittsfenster mit
Bereichsraster und Berichtaktionen. Die Dateisystemanalyse zeigt ihren Fortschritt
weiterhin im Hauptfenster. Die folgenden Download- und APT-Angaben gelten für 3.0.8.

## Herunterladen und starten

Die [offiziellen GitHub-Releases](https://github.com/FreewareFuchs/Tenshi/releases) enthalten die veröffentlichten Downloads und Versionshinweise. Das [stabile Release v3.0.8](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.8) enthält Windows-Installer, Portable-ZIP, Linux-DEB und `SHA256SUMS.sha256`.

| Variante | Verwendung |
| --- | --- |
| Windows-Installer | Setup herunterladen und Tenshi auf dem PC installieren. |
| Portable ZIP | ZIP vollständig entpacken und die enthaltene `Tenshi.exe` starten. Keine Installation erforderlich. |
| Linux-DEB | Unter Linux Mint 22.x mit APT installieren; Start über das Anwendungsmenü oder `tenshi-recovery`. |

Die portable Variante kann Einstellungen und Fehlerprotokolle im Windows-Benutzerprofil speichern. Der GitHub-Quellcode-Download ist kein fertiges Windows-Programmpaket.

Installer und EXE sind nach dem dokumentierten Stand **nicht digital signiert**. Prüfe Herkunft und die SHA-256-Prüfsummen des jeweiligen Releases. Sicherheitsfunktionen nicht pauschal abschalten. [Download-Sicherheit und Prüfsummen](https://freewarefuchs.de/tenshi/sicherheit/)

## Unter Linux starten

Seit `v3.0.2-beta.2` wird zusätzlich zu Windows-Installer und Portable-ZIP ein natives DEB-Paket angeboten. Die stabile Version [`v3.0.8`](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.8) ist veröffentlicht. [Versionshinweise](RELEASE_NOTES_3.0.8.md).

### DEB-Paket für Linux Mint 22.x

Die signierte [FreewareFuchs-APT-Quelle](docs/APT_REPOSITORY.md) bietet
`tenshi-recovery 3.0.8-1` an. Die [Installationsanleitung](docs/APT_REPOSITORY.md)
beschreibt die einmalige Einrichtung und Prüfung des Schlüsselfingerabdrucks.
Danach:

```bash
sudo apt update &&
sudo apt install tenshi-recovery
tenshi-recovery
```

Alternativ das [DEB direkt herunterladen](https://freewarefuchs.de/tenshi/apt/pool/main/t/tenshi-recovery/tenshi-recovery_3.0.8-1_all.deb).
SHA256: `3678ead73af9d0797cc21541db8f43e7f5cd3b67af8ba8911f7400b8ee7d1926`.
Nach Prüfsummenvergleich im Downloadordner installieren:

```bash
sudo apt install ./tenshi-recovery_3.0.8-1_all.deb
```

Danach **Tenshi** im Anwendungsmenü öffnen. Ohne sudo starten;
das Paket ändert keine Geräteberechtigungen.
Deinstallation: `sudo apt remove tenshi-recovery`.

Voraussetzungen: Python >= 3.11, Tkinter und util-linux; Ziel ist Linux Mint
22.x auf amd64. Mint 21.x mit Python 3.10 wird nicht unterstützt.
Ein direkter DEB-Download bindet keine Quelle ein. Die eigene Quelle muss
auf jedem Rechner hinzugefügt werden; sie ist keine Aufnahme in die
offiziellen Mint-Paketquellen.

Das neue Paket vermeidet die Kollision mit Ubuntus unabhängigem `tenshi`-
Logüberwachungsprogramm. Bei einer alten Datenrettungsinstallation zuerst
die [Umstiegsanleitung](docs/DEB_PACKAGE_RENAME.md) lesen.
Das bisherige DEB im GitHub-Release 3.0.2 bleibt unverändert.

[Paketbau und Prüfung](docs/LINUX_DEB.md)

### Aus dem Quellcode starten

Voraussetzungen: Python 3.11 oder neuer, Tkinter und util-linux. Unter Linux Mint:

```bash
sudo apt install git python3-tk util-linux
git clone https://github.com/FreewareFuchs/Tenshi.git Tenshi
cd Tenshi
bash start_linux.sh
```

Zum Aktualisieren im geklonten Projektordner `git pull --ff-only` ausführen und Tenshi neu starten. Ein entpackter ZIP-Quellcodeordner besitzt keine Git-Verwaltung; dort funktionieren Git-Aktualisierungen nicht.

Tenshi ohne `sudo` starten. Der Start verändert keine Geräteberechtigungen. Ist der lesende Zugriff auf ein physisches Gerät nicht erlaubt, ein vorhandenes RAW-Image verwenden oder gezielt die Geräteberechtigung außerhalb der Anwendung einrichten. Für konsistente Daten eine nicht mehr beschreibbar eingebundene Quelle oder ein Offline-Image verwenden.

Der Imaging-Dialog wählt „Sicher anhalten“ bei Medienfehlern. Die zusätzliche bitgenaue Prüfung liest Quelle und Image vollständig; bei physischen Quellen wird sie ausdrücklich aktiviert. Für beschädigte Medien ersetzt Tenshi keine spezialisierte mehrphasige Rettungsstrategie wie GNU ddrescue.

[Linux-Prüfstand und Grenzen](docs/LINUX_PORT_STATUS.md) · [Vorläufige Linux-Versionshinweise](RELEASE_NOTES_LINUX_BETA.md)

## Was Tenshi kann

- GPT- und MBR-Partitionen untersuchen.
- Vorhandene Dateien und Ordner unterstützter Dateisysteme durchsuchen.
- Wiederherstellungsfunde anhand von Metadaten vor dem Export prüfen.
- Dateien und Ordner im Stapel auf einen separaten Datenträger exportieren; unterstützte Aufträge fortsetzen.
- RAW-, IMG- und DD-Abbilder lesen sowie Datenträger-Images erstellen, pausieren und fortsetzen.
- Analysesitzungen regulärer Image-Dateien speichern und wieder laden.
- Exportierte ZIP-Dateien im Ergebnisbericht optional auf lesbare ZIP-Struktur und interne CRC-Prüfsummen prüfen. Die Prüfung vergleicht nicht mit einem Original und validiert keine enthaltenen Dokumentformate.
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

Fenstertitel, Offline-Hilfe unter „Über Tenshi“ und `tenshi-recovery --version` zeigen die Programmversion und die kurze Git-Commit-Kennung. Die stabile Version wird beispielsweise als `3.0.4 (b1caea8b40)` angezeigt; Beta-Pakete enthalten zusätzlich ihre Beta-Kennung. Entwicklungsstände erhalten `+dev`, lokal geänderte Quellen zusätzlich `+dirty`; ohne bekannte Build-Information steht beim Commit `?`. Details: [Build-Kennung](docs/BUILD_IDENTITY.md).

3.0.4 ist als stabile Version veröffentlicht. Die dokumentierten Einschränkungen einzelner Dateisystemfunktionen bleiben bestehen. Automatisierte Tests mit synthetischen Images und simulierten Fehlerfällen ersetzen keine Prüfung auf beschädigter Hardware.

Aktueller Stand 27.10.2026: [Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40466932499) aus Commit `b1caea8b40f7b29d401e85a3e51a2916fc5f9e0e` mit Kennung `stable`. Die finalen Pakete und das Upgrade über die öffentliche APT-Quelle wurden vom Anwender bestätigt. [Prüfumfang und Grenzen](RELEASE_NOTES_3.0.4.md).

Historischer Prüfstand 3.0.2: Die vollständige lokale Suite der stabilen Vorbereitung lief mit 665 Tests ohne Fehler unter virtuellem X11; zwei Tests wurden übersprungen. Der [gemeinsame Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40242121217) für den veröffentlichten Commit `abfd4c973a253c2a8571d238e15a0fb77b013dec` ist erfolgreich: Linux- und Windows-Prüfungen, EXE-/Portable-/Installer-Bau, DEB-Installation und gemeinsame Paket-/Prüfsummenprüfung. Die Linux-CI prüft unabhängig formatierte FAT32-, NTFS-, exFAT-, ext4-, Btrfs- und XFS-Images.

Beta.6 wurde unter Linux und Windows manuell geprüft: Paketstart/Versionsanzeige, Export-Abbruch und erneuter Export, passende Original-/Export-SHA-256-Werte, Bestätigung vorhandener Exporte, Erkennung veränderter Zieldateien und sichtbare Fehlerwarnungen. Für die stabilen Pakete wurden die Versionsanzeigen sowie der automatische Windows-Start nach der Installer-Korrektur bestätigt.

Zusätzliche Windows-Praxistests bestätigten Quellwechsel während einer Analyse, das Verwerfen alter Dateilisten, die Bedienung großer Dateibäume sowie Export und Fortsetzen mit passenden SHA-256-Werten. Für den Build aus `a96d584` wurde außerdem die verständlichere Bewertung der Partitionserkennung in Anzeige und gespeichertem Partitionsbericht bestätigt. Diese Ergebnisse beziehen sich auf die jeweiligen Entwicklungsstände. Sie sind keine nachträgliche Abnahme der unveränderten Beta.5-Downloads.

Auf Linux Mint wurde eine physische USB-SSD mit 128.035.676.160 Bytes vollständig in ein Image kopiert und bitgenau verglichen, ohne unlesbare Bytes. Navigation und Exporte aus dem erstellten exFAT-Image wurden bestätigt. Windows-Praxistests mit dem während der Linux-Entwicklung erzeugten Build umfassen Referenzexport, Vorschau, Sitzungen, Sprachen und Themewechsel. Diese Prüfungen beziehen sich auf die getesteten Entwicklungsstände, nicht rückwirkend auf bestehende Release-Downloads.

Tatsächlich defekte Laufwerke, weitere Geräte-/Mount-Topologien und allgemeine Löschrettung sind damit nicht abgenommen. Details und historische Ergebnisse: [Linux-Portierungsstatus](docs/LINUX_PORT_STATUS.md).

Der [Windows-Abnahmeplan](WINDOWS_ABNAHME_3.0.0.md) ist ein Prüfplan, kein Nachweis einer abgeschlossenen Abnahme. Historische Testergebnisse beziehen sich jeweils auf die dort genannte Version.

## Änderungen und technische Dokumentation

- [Änderungsverlauf](CHANGELOG.md)
- [Versionshinweise zu 3.0.4](RELEASE_NOTES_3.0.4.md)
- [Versionshinweise zu 3.0.3](RELEASE_NOTES_3.0.3.md)
- [Versionshinweise zu 3.0.2](RELEASE_NOTES_3.0.2.md)
- [Aktuelle Benutzerhilfe](HILFE_3.0.8.md)
- [Bisheriges README mit historischen Entwicklungsdetails](docs/README_HISTORY_2026-10-20.md)

## Aus dem Quellcode bauen

Voraussetzung: Windows und Python 3.11 oder neuer in 64 Bit, erreichbar über `py -3`.

1. Repository herunterladen oder klonen und in den Projektordner wechseln.
2. `check_windows.bat` für die nicht invasive Umgebungsprüfung ausführen.
3. `build_windows.bat` ausführen. Die Anwendung wird als `dist\Tenshi.exe` erstellt.

4. Automatisierte Tests separat mit `run_tests.bat` ausführen.
5. Optional mit `build_portable.bat` eine portable ZIP oder mit `build_installer.bat` einen Installer erstellen. Der Installer-Build benötigt Inno Setup 6.3 oder neuer.

Die Windows-Bauwerkzeuge sind in `requirements-build-windows.txt` mit festen Versionen und SHA-256-Prüfsummen hinterlegt. Das Build-Skript installiert diese Pakete bei jedem Build erneut und prüft ihre Hashes. `build/windows-build-requirements.txt` und `build/windows-build-python.txt` dokumentieren die verwendeten Python-Pakete und die Python-Version; die Windows-CI liefert beide Dateien im Build-Artefakt mit. Python, pip, Inno Setup und das Betriebssystem sind damit noch nicht festgeschrieben; die EXE ist dadurch nicht automatisch bitidentisch reproduzierbar.

`Tenshi.exe --smoke-test` prüft gebündelte Komponenten ohne Fenster und ohne Laufwerkszugriff. Ein erfolgreicher Build oder Smoke-Test ist kein Nachweis erfolgreicher Datenrettung.

Bei Build-Problemen: [Build-Fehlersuche](BUILD_FEHLERSUCHE.md). Bei Weitergabe von Protokollen private Pfade und andere sensible Angaben vorab prüfen.

## Fehler melden und mitarbeiten

Für Fehler und Verbesserungsvorschläge bitte ein [GitHub-Issue](https://github.com/FreewareFuchs/Tenshi/issues) erstellen. Nenne Version, Betriebssystem, Schritte zur Reproduktion sowie erwartetes und tatsächliches Verhalten. Keine privaten Dateien, vollständigen Laufwerksabbilder oder ungeprüften Protokolle veröffentlichen.

[Beiträge zum Projekt](CONTRIBUTING.md) · [Sicherheitsmeldungen](SECURITY.md)

## Lizenz und Drittkomponenten

Die Datei [LICENSE](LICENSE) enthält die MIT-Lizenz mit Copyright-Vermerk für FreewareFuchs. Hinweise zu Drittkomponenten stehen in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Die bestehenden Hinweise zur Klärung von Rechten an Logos, Assets und Drittkomponenten bleiben in [OPEN_SOURCE_START_HIER.md](OPEN_SOURCE_START_HIER.md) dokumentiert. Die Überarbeitung dieses README bestätigt keine abgeschlossene Rechteprüfung.
