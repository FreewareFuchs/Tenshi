# Linux-Portierung – Stand und Hardware-Abnahme

## Plattformprüfung

- **Plattformneutral:** RAW-Abbild, Partitionssuche, NTFS/FAT/exFAT/ext2–4/Btrfs/XFS-Parser, Suchfunktionen, Export, Sitzungen und Imaging-Kern.
- **Windows-spezifisch:** CreateFileW, DeviceIoControl, physische Laufwerksnummern, Laufwerksbuchstaben, Windows-Builds/Installer.
- **Linux-Backend (neu):** Blockgeräte aus sysfs, O_RDONLY für Quellen, BLKGETSIZE64 und BLKSSZGET, Quell-/Zielgerät über sysfs-Abstammung trennen. Ungeklärte Abbildung wird abgewiesen.
- **GUI:** Linux-Blockgeräte über vorhandenen Auswahldialog; Quellaktionen auf zwei Zeilen verteilt. 1024×650 unter Cinnamon/X11 weiterhin visuell zu prüfen.
- **Bewusste Einschränkung:** Linux-Laufwerksauswahl per gemountetem Pfad (statt Blockgerät) ist noch nicht implementiert; vorhandener Windows-Laufwerksdialog bleibt für Laufwerksbuchstaben. Über „Physischer Datenträger“ sind Linux-Whole-Disk-Geräte auswählbar.

## Tests (ohne Hardware)
```bash
python3 -m unittest discover -s tests -p 'test_linux_devices.py' -v
python3 main.py --smoke-test
```
Diese Tests sind neu hinzugefügt, wurden im GitHub-Connector aber noch **nicht ausgeführt**.

## Ausstehende Pflichtprüfungen auf Linux-Cinnamon/X11

1. Tk installieren und UI bei exakt **1024×650**, 100 % sowie erhöhter Schrift-/DPI-Skalierung starten; beide Register, Aktionen, Status, Modaldialoge, Tabs, Ordnerbaum und Export prüfen. Keine verdeckten Schaltflächen.
2. Vor dem Öffnen eines Testdatenträgers Berechtigungen prüfen. Mit einem entbehrlichen USB-Laufwerk nur lesen, abziehen, erneut anstecken und Fehlermeldungen prüfen.
3. Mit `strace -e openat,ioctl` kontrollieren, dass die Quelle nie mit O_WRONLY/O_RDWR geöffnet wird; zugelassene ioctls auf Lesen beschränken.
4. Linux-Datenträger- und Partitionsgröße, 512/4096-Byte-Sektoren, GPT/MBR, NTFS/ext4/exFAT/Btrfs/XFS mit Referenzabbildern verifizieren.
5. Image-Erstellung/Pause/Fortsetzen, Export-Checksums und gespeicherte Sitzungen nach Neustart prüfen; Fehlersimulation (kurze Lesevorgänge, I/O-Fehler, Verbindungsabbruch).
6. **Schutz vor Ziel=Quelle:** Ausgabe auf dieselbe Platte und auf deren andere Partition, via Symlink, LVM, dm-crypt, mdraid und USB-Gerät testen; alle unklaren Zuordnungen müssen blockiert werden.
7. Separate physische Ziellaufwerke, externe USB-HDDs/SSDs, loop-Geräte und verschiedene Mountpoints prüfen. Loop-/virtuelle Geräte werden bei nicht nachweisbarer physischer Abstammung absichtlich gesperrt.
8. Windows-Regressionstests auf echter Windows-Hardware durchführen; Windows-Installer und ZIP bleiben unverändert.

**Freigabestatus:** Entwicklungskandidat, kein verifizierter Linux-Release. Eine durchgehende Gleichwertigkeit zum Windows-Funktionsumfang und Behebung aller Cinnamon-Layoutüberläufe sind noch nicht bestätigt. Bei beschädigten Originaldatenträgern zunächst keine belastenden Tests durchführen.
