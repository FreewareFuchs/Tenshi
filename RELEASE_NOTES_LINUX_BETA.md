# Linux-Beta – vorläufige Versionshinweise

Stand: 23.10.2026. Noch nicht veröffentlicht; die Anwendungsversion bleibt 3.0.2. Bestehende Releases v3.0.2-beta und v3.0.2-beta.1 enthalten diese späteren Änderungen nicht automatisch.

## Neu auf main

- Linux-Geräteerkennung über sysfs und lesender Zugriff auf Blockgeräte; Ausgabe auf demselben physischen Quelldatenträger wird abgewiesen, unklare Zuordnungen führen zum Abbruch.
- Linux-Start über `bash start_linux.sh`; Voraussetzungen und Aktualisierung im README.
- Imaging mit Pause/Fortsetzung und vollständigem Bytevergleich. Physische Quellen werden nur nach bewusster Aktivierung nochmals vollständig geprüft.
- „Sicher anhalten“ als Vorauswahl im Imaging-Dialog; Nullersatz mit Protokollierung bleibt auswählbar.
- Abgesicherte Linux-Schreibpfade für Image-/Exportstatus und Berichte; geprüfte Wiederaufnahme und Datei-Verifikation.
- Kompaktes Layout, zunächst eingeklappte Warteschlange, gleich große Header-Schaltflächen, stabiler Themewechsel und korrigierte Dialogdarstellung.
- Leere normale Suche setzt erweiterte Filter zurück. FAT32-Backup-Bootsektoren werden nicht als zusätzliche identische Partition angeboten. Sitzungen melden abweichende Imagegrößen verständlich.
- Einzelne Prüffehler bei vorhandenen Exportdateien werden protokolliert, während der Stapel weitere Dateien prüft.

## Prüfung

- 569 lokale Tests erfolgreich; automatisierte Linux- und Windows-Prüfungen auf main erfolgreich.
- [Linux-CI](https://github.com/FreewareFuchs/Tenshi/actions/runs/39946664869) und [Windows-CI](https://github.com/FreewareFuchs/Tenshi/actions/runs/39946664773) für `ade614a`.
- Echte ext4-, Btrfs- und XFS-Standardimages: Navigation, Vorschau, bytegleicher Export und unveränderte Quelle.
- Linux Mint: 119,2-GiB-SSD-Image vollständig erstellt und bitgenau verifiziert; anschließend Dateien angezeigt und exportiert.
- Windows-Referenzexport, Vorschau, Sitzungen, Sprachen und Themewechsel während der Entwicklung praktisch bestätigt.

## Grenzen und Bereitstellung

Linux wird derzeit aus dem Quellcode gestartet; ein natives Linux-Installationspaket ist nicht vorbereitet. Die Windows-CI erstellt EXE, Portable-Paket und Installer; deren Bereitstellung als neuer öffentlicher Release ist ein separater Schritt.

Die Standard-Image-Tests belegen keine allgemeine Löschrettung und keine Unterstützung sämtlicher Btrfs-/XFS-Varianten, RAID oder Mehrgeräte-Dateisysteme. 4K-Hardware, weitere LVM-/Mount-Topologien, Hotplug und tatsächlich defekte Medien benötigen weitere Abnahme. Tenshi bleibt experimentelle Beta-Software.

[Ausführlicher Prüfverlauf](docs/LINUX_PORT_STATUS.md)
