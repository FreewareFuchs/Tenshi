# Linux-Beta – vorläufige Versionshinweise

Stand: 23.10.2026. Noch nicht veröffentlicht; die Anwendungsversion bleibt 3.0.2. Bestehende Releases v3.0.2-beta und v3.0.2-beta.1 enthalten diese späteren Änderungen nicht automatisch.

## Neu auf main

- Linux-Geräteerkennung über sysfs und lesender Zugriff auf Blockgeräte; Ausgabe auf demselben physischen Quelldatenträger wird abgewiesen, unklare Zuordnungen führen zum Abbruch.
- Linux-Start über `bash start_linux.sh`; Voraussetzungen und Aktualisierung im README.
- Natives DEB-Paket für Linux Mint 22.x mit Menüeintrag, Logo und Systemabhängigkeiten; Start über `tenshi` ohne Administratorrechte. Paketinstallation ändert keine Geräteberechtigungen.
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

Für `v3.0.2-beta.2` sind das Linux-DEB `tenshi_3.0.2~beta.2-1_all.deb`, der Windows-Installer und das Windows-Portable-Paket vorgesehen. Linux benötigt Python ab 3.11; Linux Mint 21.x mit Python 3.10 wird vom Paket nicht unterstützt. Alternativ bleibt der Start aus dem Quellcode möglich. Der vorbereitete Linux-Workflow baut das DEB und prüft Installation, Start und Entfernung unter Ubuntu; sein erster CI-Lauf steht noch aus. Das lokal gebaute Paket wurde am 23.10.2026 unter Linux Mint erfolgreich installiert, gestartet, mit einem vorhandenen Image und Dateiexport geprüft und anschließend entfernt. Die Bereitstellung als öffentlicher Release ist ein separater Schritt. Der direkte DEB-Download richtet keine Paketquelle für automatische Updates ein.

Die Standard-Image-Tests belegen keine allgemeine Löschrettung und keine Unterstützung sämtlicher Btrfs-/XFS-Varianten, RAID oder Mehrgeräte-Dateisysteme. 4K-Hardware, weitere LVM-/Mount-Topologien, Hotplug und tatsächlich defekte Medien benötigen weitere Abnahme. Tenshi bleibt experimentelle Beta-Software.

[Ausführlicher Prüfverlauf](docs/LINUX_PORT_STATUS.md)
