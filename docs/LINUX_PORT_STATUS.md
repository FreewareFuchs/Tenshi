# Linux-Portierung – Stand und Hardware-Abnahme

## Plattformprüfung

- **Plattformneutral:** RAW-Abbild, Partitionssuche, NTFS/FAT/exFAT/ext2–4/Btrfs/XFS-Parser, Suchfunktionen, Export, Sitzungen und Imaging-Kern.
- **Windows-spezifisch:** CreateFileW, DeviceIoControl, physische Laufwerksnummern, Laufwerksbuchstaben, Windows-Builds/Installer.
- **Linux-Backend (neu):** Blockgeräte aus sysfs, O_RDONLY für Quellen, BLKGETSIZE64 und BLKSSZGET, Quell-/Zielgerät über sysfs-Abstammung trennen. Ungeklärte Abbildung wird abgewiesen.
- **GUI:** Linux-Blockgeräte über vorhandenen Auswahldialog; fünf Quellenaktionen in einer Zeile; kompakter Kopfbereich und einklappbare Wiederherstellungswarteschlange. Bei 1024×650 unter Cinnamon/X11 anhand von Anwender-Screenshots visuell geprüft, weitere Skalierungen offen.
- **Linux-Laufwerksauswahl (neu):** `Laufwerk auswählen` listet eingehängte Blockpartitionen über `lsblk` (util-linux) und öffnet nach **ausdrücklicher Auswahl und Bestätigung** das zugrunde liegende `/dev/...` ausschließlich lesend. Die Gerätedatei wird vollständig angezeigt; unter Linux ist aus Sicherheitsgründen zunächst keine Zeile vorgewählt. Linux-Geräteberechtigungen werden nicht verändert. Gemountete, beschreibbare Dateisysteme können durch **andere Prozesse** weiter verändert werden; für zuverlässige Rettung bevorzugt Offline-Image. `Physischer Datenträger` listet weiterhin ganze Blockgeräte.

## Tests (ohne Hardware)
```bash
python3 -m unittest discover -s tests -p 'test_linux*.py' -v
python3 main.py --smoke-test
```
Die Linux-CI führt die vollständige Python-Testsuite unter virtuellem X11 sowie zusätzliche Geräte- und Layouttests bei 1024×650 aus. Geprüft werden nur simulierte Geräte: gleiches/anderes Zielmedium, überlappende Geräteverbünde, unklare Abbildung, blockierte Imagerstellung/Export vor Dateianlage, die O_RDONLY-Geräteabfrage und sysfs-Partition-/Virtuellgeräte-Zuordnung. CI-Ergebnisse je Commit unter GitHub Actions prüfen.

## Reproduzierbarer Linux-Start und Tests

```bash
sudo apt install python3-tk util-linux
python3 -m unittest discover -s tests -p 'test_linux*.py' -v
python3 main.py --smoke-test
python3 main.py
```

Das Testen des normalen Startbefehls und der Linux-Volumenauswahl erfolgt ohne `sudo` oder Änderungen der Gerätegruppen. Fehlt die Leseerlaubnis für ein Blockgerät, muss Tenshi den Zugriff ablehnen; stattdessen ein vorher erstelltes RAW-Image verwenden.

## Bereits manuell nachvollzogen

- Linux Mint Cinnamon/X11: kompakte Oberfläche und einklappbare Warteschlange bei 1024×650 (Screenshots).
- RAW-Testimage: Partitionssuche, exFAT-Ordnernavigation, Dateisuche sowie Einzeldatei-Export mit geöffnetem PNG.
- Export-Vorabprüfung: **nur Metadaten**, kein Nachweis vollständiger Dateiintegrität.
- Quellen- und Exportdatei lagen bei diesem **Image-Datei-Test** auf demselben Dateisystem. Für physische Geräte gelten strengere Trennungsprüfungen.

## Ausstehende Pflichtprüfungen auf Linux-Cinnamon/X11

1. Weitere Schrift-/DPI-Skalierungen, alternative Sprachen und Modaldialoge auf echtem Cinnamon/X11 testen; Hauptfenster bei **1024×650** ist bereits visuell geprüft.
2. Vor dem Öffnen eines Testdatenträgers Berechtigungen prüfen. Mit einem entbehrlichen USB-Laufwerk nur lesen, abziehen, erneut anstecken und Fehlermeldungen prüfen.
3. Mit `strace -e openat,ioctl` kontrollieren, dass die Quelle nie mit O_WRONLY/O_RDWR geöffnet wird; zugelassene ioctls auf Lesen beschränken.
4. Linux-Datenträger- und Partitionsgröße, 512/4096-Byte-Sektoren, GPT/MBR, NTFS/ext4/exFAT/Btrfs/XFS mit Referenzabbildern verifizieren. GUI-Laufwerksauswahl an echter Hardware mit fehlenden Rechten, ext4/NTFS und Linux Mint prüfen.
5. Image-Erstellung/Pause/Fortsetzen, Export-Checksums und gespeicherte Sitzungen nach Neustart prüfen; Fehlersimulation (kurze Lesevorgänge, I/O-Fehler, Verbindungsabbruch).
6. **Schutz vor Ziel=Quelle:** Ausgabe auf dieselbe Platte und auf deren andere Partition, via Symlink, LVM, dm-crypt, mdraid und USB-Gerät testen; alle unklaren Zuordnungen müssen blockiert werden.
7. Separate physische Ziellaufwerke, externe USB-HDDs/SSDs, loop-Geräte und verschiedene Mountpoints prüfen. Loop-/virtuelle Geräte werden bei nicht nachweisbarer physischer Abstammung absichtlich gesperrt.
8. Windows-Regressionstests auf echter Windows-Hardware durchführen; Windows-Installer und ZIP bleiben unverändert.

**Freigabestatus:** Entwicklungskandidat, kein verifizierter Linux-Release. Die vollständige Gleichwertigkeit zum Windows-Funktionsumfang, weitere Skalierungen und die Sicherheit an realen Linux-Blockgeräten sind noch nicht bestätigt. Bei beschädigten Originaldatenträgern zunächst keine belastenden Tests durchführen.
