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
Die Linux-Geräteliste wird ausschließlich aus sysfs-Metadaten erstellt und öffnet dabei keine Blockgeräte. Unter Linux ist auch beim physischen Datenträger **keine Vorauswahl** gesetzt: ein Zugriff erfordert die ausdrückliche Markierung und Bestätigung. Fehlende Leserechte werden nicht verändert.

Die Linux-CI führt die vollständige Python-Testsuite unter virtuellem X11 sowie zusätzliche Geräte- und Layouttests bei 1024×650 aus. Geprüft werden nur simulierte Geräte: gleiches/anderes Zielmedium, überlappende Geräteverbünde, unklare Abbildung, blockierte Imagerstellung/Export vor Dateianlage, die O_RDONLY-Geräteabfrage und sysfs-Partition-/Virtuellgeräte-Zuordnung. CI-Ergebnisse je Commit unter GitHub Actions prüfen.

## Reproduzierbarer Linux-Start und Tests

```bash
sudo apt install python3-tk util-linux
python3 -m unittest discover -s tests -p 'test_linux*.py' -v
bash start_linux.sh --smoke-test
bash start_linux.sh
```

Das Testen des normalen Startbefehls und der Linux-Volumenauswahl erfolgt ohne `sudo` oder Änderungen der Gerätegruppen. Fehlt die Leseerlaubnis für ein Blockgerät, muss Tenshi den Zugriff ablehnen; stattdessen ein vorher erstelltes RAW-Image verwenden.

## Image-basierte Dateisystem-Abnahme ohne Hardware

- **ext4 (auf Linux Mint praktisch bestätigt, 22.10.2026):** `tests/test_real_ext4_image.py` erzeugt ein echtes 64-MiB-ext4-Dateisystem mit `mke2fs -d` in einem zuvor neu angelegten **regulären** temporären Image, ohne Loopgerät, Mount oder sudo. Prüft Dateisystemerkennung, Ordnerbaum, Datei-Vorschau, verschachtelten Export, exakten Bytevergleich und unveränderte Quelle. Für die Linux-CI wird `e2fsprogs` installiert. Dies ist ein Test aktueller Dateien, **kein** Beweis allgemeiner ext4-Löschrettung.
- **Btrfs/XFS (8/8 Tests auf Linux Mint bestanden, 22.10.2026):** Bisherige `tests/test_linux_advanced.py` decken parserkonforme **handkonstruierte** Verzeichnis-/Extent-Metadaten und Dateiexporte sowie einige Fehlerfälle ab. Es fehlt weiterhin ein Importtest mit real mittels `mkfs.btrfs` bzw. `mkfs.xfs` erzeugten, gefüllten Datenträger-Images. Insbesondere moderne Btrfs-/XFS-Varianten und Btrfs mit mehreren Geräten sind **nicht allgemein freigegeben**.

Für den echten ext4-Test unter Linux Mint:

```bash
sudo apt install e2fsprogs
python3 -m unittest discover -s tests -p 'test_real_ext4_image.py' -v
python3 -m unittest discover -s tests -p 'test_linux_advanced.py' -v
```

Der Test formatiert **niemals** ein vorhandenes Gerät. `mke2fs` wird ausschließlich mit einem neu erstellten Image-Pfad unter `TemporaryDirectory` aufgerufen. Ein Exitstatus ungleich null muss als Fehler behandelt werden.

## Bereits manuell nachvollzogen

- Linux Mint Cinnamon/X11: kompakte Oberfläche und einklappbare Warteschlange bei 1024×650 (Screenshots).
- RAW-Testimage: Partitionssuche, exFAT-Ordnernavigation, Dateisuche sowie Einzeldatei-Export mit geöffnetem PNG.
- Export-Vorabprüfung: **nur Metadaten**, kein Nachweis vollständiger Dateiintegrität.
- Linux Mint: vollständiger 256-MiB-Imaging-Test mit SHA-256- und `cmp`-Bestätigung bitgenauer Kopie; 16/16 Imaging-Tests bestanden (Unterbrechung/Wiederaufnahme dort simuliert).
- Analysesitzung nach Programmneustart erfolgreich wieder geladen, ohne Dateisystem erneut einzulesen.
- `test_real_ext4_image.py`: 1/1 auf Linux Mint bestanden; reguläres, temporäres ext4-Image mit Datei- und Unterordnerexport.
- Linux Mint: `test_linux_destination_safety.py` **11/11 bestanden** (22.10.2026). Simulierte sysfs-/Blockgeräte, Quellzugriff nur lesend, gleiche bzw. andere physische Ziellaufwerke, fail-closed bei unsicherer Zuordnung und Unterbindung unsicherer Ausgabedateien. **Kein Ersatz für `strace`-/Hardwareprüfung**.
- Linux Mint, 22.10.2026: Mit `strace -f -e trace=open,openat,openat2` um `list_physical_sources()` wurden `/dev/nvme0n1` und `/dev/sda` in den Geräteinformationen erkannt. Ein `grep` nach den beiden exakten `/dev/...`-Pfaden im Trace ergab **keinen Öffnungsaufruf**. Dies bestätigt die reine Metadatenauflistung für diese beiden Geräte, jedoch **nicht** den Lesezugriff auf physische Quellen. Test ohne `sudo`.
- Linux Mint, 22.10.2026: Realer `strace -f -e trace=open,openat,openat2`-Nachweis für `open_source()` auf **regulärer RAW-Testdatei**, nicht auf Blockgerät: `openat(..., ".../testquelle.raw", O_RDONLY|O_CLOEXEC) = 3`; 512 Bytes gelesen; `reader.writable()` ergibt `False`. Bestätigt ausschließlich lesendes Öffnen dieses Image-Quellpfads. Direkte physische Quelle weiterhin ungeprüft.
- Quellen- und Exportdatei lagen bei diesem **Image-Datei-Test** auf demselben Dateisystem. Für physische Geräte gelten strengere Trennungsprüfungen.

## Zusätzliche automatisierte Sicherheitsprüfung (22.10.2026)

- `tests/test_linux_block_readonly.py`: für simulierte Blockgeräte mit 512/4096-Byte-Sektoren wird `open_source()` auf `rb` ohne Schreibfunktion geprüft. Unausgerichtete Anfragen werden vom `AlignedDeviceReader` in sektorausgerichtete Lesezugriffe übersetzt. Unter Linux melden Lesefehler/Gerätetrennung keinen Windows-Administratorhinweis; ein abgezogenes simuliertes Gerät wird nicht stillschweigend mit Nullbytes ersetzt.
- `tests/test_linux_topology.py`: sysfs-Auflösung über simulierte gestapelte Blockgeräte mit zwei physischen Trägern. Fehlende Slaves und Zyklen führen zum Abbruch statt zu einer geratenen Zuordnung. Die Tests verändern **keine** realen Blockgeräte.
- GitHub Actions: Linux-Spezialtests 35/35, davon drei ohne Display übersprungen; gesamte Python-Suite 475 Tests erfolgreich, zusätzlich echter ext4-Image-Test und virtuelles X11 1024×650 erfolgreich (Commit `8bda3ffd`). Windows-Tests separat.
- **Grenzen:** Lesend geöffnete, aber gleichzeitig unter Linux beschriebene Dateisysteme können inkonsistente Daten liefern. Ein bereits ausgewählter Zielpfad könnte zwischen Prüfung und Dateiöffnung durch andere Prozesse verändert werden (Pfad-/Symlink-Race). Quelle/Ziel auf physischer Hardware und dynamische Mount-Topologien erfordern eine zusätzliche Abnahme; niemals hierfür wichtige Originaldatenträger verwenden.

## Ausstehende Pflichtprüfungen auf Linux-Cinnamon/X11

1. Weitere Schrift-/DPI-Skalierungen, alternative Sprachen und Modaldialoge auf echtem Cinnamon/X11 testen; Hauptfenster bei **1024×650** ist bereits visuell geprüft.
2. Vor dem Öffnen eines Testdatenträgers Berechtigungen prüfen. Mit einem entbehrlichen USB-Laufwerk nur lesen, abziehen, erneut anstecken und Fehlermeldungen prüfen.
3. **Noch offen: tatsächlichen physischen Lesezugriff** mit `strace -f -e trace=open,openat,openat2,ioctl` kontrollieren: Quelle nie mit `O_WRONLY`/`O_RDWR` öffnen; nur lesende ioctls verwenden. Die reine Datenträgerauflistung ohne Geräteöffnung ist auf Cinnamon/X11 bereits überprüft. Diese echte Blockgeräte-Abnahme nur auf entbehrlicher Testhardware mit sauberem Geräteplan durchführen.
4. Linux-Datenträger- und Partitionsgröße, 512/4096-Byte-Sektoren, GPT/MBR, NTFS/ext4/exFAT/Btrfs/XFS mit Referenzabbildern verifizieren. GUI-Laufwerksauswahl an echter Hardware mit fehlenden Rechten, ext4/NTFS und Linux Mint prüfen.
5. Image-Erstellung/Pause/Fortsetzen, Export-Checksums und gespeicherte Sitzungen nach Neustart prüfen; Fehlersimulation (kurze Lesevorgänge, I/O-Fehler, Verbindungsabbruch).
6. **Schutz vor Ziel=Quelle:** Ausgabe auf dieselbe Platte und auf deren andere Partition, via Symlink, LVM, dm-crypt, mdraid und USB-Gerät testen; alle unklaren Zuordnungen müssen blockiert werden.
7. Separate physische Ziellaufwerke, externe USB-HDDs/SSDs, loop-Geräte und verschiedene Mountpoints prüfen. Loop-/virtuelle Geräte werden bei nicht nachweisbarer physischer Abstammung absichtlich gesperrt.
8. Windows-Regressionstests auf echter Windows-Hardware durchführen; Windows-Installer und ZIP bleiben unverändert.

**Freigabestatus:** Entwicklungskandidat, kein verifizierter Linux-Release. Die vollständige Gleichwertigkeit zum Windows-Funktionsumfang, weitere Skalierungen und die Sicherheit an realen Linux-Blockgeräten sind noch nicht bestätigt. Bei beschädigten Originaldatenträgern zunächst keine belastenden Tests durchführen.
