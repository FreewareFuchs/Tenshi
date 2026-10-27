# Experimenteller Flatpak-Build

Dieser Prototyp prüft, ob Tenshi einschließlich Datenträgererkennung und
Quell-/Zielschutz in Flatpak sinnvoll nutzbar ist. Er ist **kein stabiler Release**,
keine Flathub-Einreichung und noch nicht im Mint-Anwendungsmanager verfügbar.
Die vorhandenen Windows-/DEB-Pakete bleiben der geprüfte Installationsweg.

## Umfang und Grenzen

- Eigene Test-ID `de.freewarefuchs.Tenshi.Experimental`, Branch `test` und
  Menüeintrag „Tenshi (Flatpak-Test)“; das native DEB bleibt installiert.
- Die eingebettete Build-Kennung enthält den Quell-Commit und immer `+dev`,
  auch wenn der Snapshot von einem stabilen Tag stammt.
- Freedesktop **SDK 25.08 als vorläufige Laufzeit**: enthält Python und
  Gerätewerkzeuge. Tcl/Tk und tkinter werden aus festgelegten Quellen gebaut.
  Die große SDK-Laufzeit ist eine bewusste Einschränkung dieses Prototyps;
  vor einer Store-Einreichung ist eine schlankere Laufzeit zu prüfen.
- Der Snapshot enthält nur Anwendungscode, Assets, Lizenzhinweise und
  Paketdateien. Images, Sitzungen, beliebige JSON-Dateien und Git-Daten
  werden nicht in das Paket kopiert.
- Der Prototyp ändert weder Anwendungscode noch Geräteberechtigungen.
  Es gibt keinen `sudo`-/`pkexec`-Start und keinen Aufruf eines Hostprogramms
  über `flatpak-spawn --host`.

## Sandbox-Berechtigungen

| Berechtigung | Zweck |
| --- | --- |
| X11 und IPC | Tk-Oberfläche unter Cinnamon/X11 bzw. XWayland |
| `device=all` | Blockgeräte zur Auswahl und zum lesenden Öffnen sichtbar machen |
| `home`, `/media`, `/mnt`, `/run/media` | Images, Exporte und eingebundene Zielmedien mit Tk-Dateidialogen auswählen |
| `/run/udev:ro` | Nur lesender Zugriff auf Geräte-Metadaten für `lsblk` |

`device=all` ist eine breite Sichtbarkeitsfreigabe und **erzwingt keinen
Schreibschutz**. Tenshis unveränderte Quellenleser öffnen Quellen nur lesend;
die vorhandenen Linux-Geräterechte gelten zusätzlich. Fehlende Rechte werden
vom Paket nicht vergeben. Keine Netzwerk- oder System-D-Bus-Freigabe.
Benutzerdefinierte Mountpunkte außerhalb der genannten Verzeichnisse sind
noch nicht abgedeckt. Eine fehlende Geräte-/Zielzuordnung muss weiterhin
zum Abbruch der Schutzprüfung führen, nicht zu einer Umgehung.

## Lokal unter Linux Mint bauen

Benötigt werden Flatpak, flatpak-builder, Python >= 3.11 und der konfigurierte
Flathub-Remote. Als normaler Benutzer im Checkout:

```bash
flatpak --user remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak --user install flathub org.freedesktop.Sdk//25.08
python3 prepare_flatpak.py
flatpak-builder --user --disable-rofiles-fuse --install --repo=flatpak_output/repo flatpak_output/build flatpak_output/context/de.freewarefuchs.Tenshi.Experimental.json
flatpak run de.freewarefuchs.Tenshi.Experimental//test --version
flatpak run de.freewarefuchs.Tenshi.Experimental//test
```

Der Kontext wird nicht überschrieben. Für einen erneuten Bau einen neuen
Pfad mit `prepare_flatpak.py --output-dir flatpak_output/context-2` verwenden
und diesen Manifestpfad sowie ein neues Build-Verzeichnis angeben.

Das GitHub-Artefakt `Tenshi-experimental-Flatpak` enthält nach erfolgreichem
Prüflauf ein Test-Bundle und SHA256-Datei. Im entpackten Artefaktordner:

```bash
sha256sum -c Tenshi-experimental-x86_64.flatpak.sha256
flatpak --user install ./Tenshi-experimental-x86_64.flatpak
flatpak run de.freewarefuchs.Tenshi.Experimental//test
```

Entfernen (betrifft nur die experimentelle Flatpak-Anwendung):

```bash
flatpak --user uninstall de.freewarefuchs.Tenshi.Experimental
```

## Prüfungen

Der Workflow `Experimental Flatpak checks` prüft Desktop-/AppStream-Dateien,
Snapshot-Grenzen und Build-Kennung, baut und installiert das Paket und prüft
Smoke-Test, das tatsächliche installierte Tenshi-Hauptfenster samt Logo sowie den Export aus einem unabhängig mit dosfstools/mtools
erstellten FAT32-Image. Original-/Export- und Imaging-SHA256 werden verglichen;
der Quell-Image-Hash muss unverändert bleiben. Die CI verwendet keine echten
USB-Quellen. Ein grüner Build bestätigt daher keine Hardware-Funktionsparität.

Die Oberflächenprüfung startet `RecoveryDeskApp` aus `/app/share/tenshi` mit
temporären Einstellungen und Logs. Sie prüft alle sechs Sprachen, beide
Hauptbereiche, die Dateiliste und das Ein-/Ausklappen der Exportwarteschlange.
Dabei bleibt die Quellauswahl leer; Geräte- und Volume-Auflistung sind im Test
gesperrt. Der Test prüft die tatsächliche Flatpak-Laufzeit einschließlich des
gebündelten Tcl/Tk, nicht nur die Oberfläche des nativen DEB.

Vor einer Veröffentlichung unter Mint mit einem entbehrlichen USB-Testmedium:

1. Oberfläche, sechs Sprachen und Laden eines bekannten Images prüfen.
2. Eine große Datei aus dem Image exportieren und SHA256 vergleichen.
3. Physische Geräte anzeigen: Modell/Größe mit dem nativen DEB vergleichen.
4. Ohne Leserechte muss die verständliche Zugriffsfehlermeldung erscheinen.
5. Mit bereits gezielt vergebenen Leserechten vom Testmedium exportieren;
   Original-/Export-SHA256 müssen identisch sein.
6. Exportziel auf demselben physischen Quellmedium muss abgelehnt werden.
7. Export auf ein getrenntes Medium sowie Imaging und Abbruch prüfen.
8. USB-Wechsel muss alte Geräteidentität verwerfen und erneuten Scan verlangen.

## Vor Flathub

Erst nach erfolgreichen Hardwaretests: Laufzeit verkleinern, Rechte begründen,
aktuelle Abhängigkeiten und Lizenzmitlieferung prüfen, Store-Metadaten um
Screenshots/Releaseinformationen ergänzen, Linter ausführen und finale App-ID
festlegen. Flathub entscheidet über die Aufnahme; insbesondere Systemwerkzeuge
und Anwendungen mit notwendigen Host-Berechtigungen unterliegen Einschränkungen.
Eine vorherige Klärung der Eignung ist sinnvoll, bevor weitere Store-Arbeit erfolgt.
Die Herausgeber-Verifizierung über `freewarefuchs.de` ist ein späterer separater
Schritt und wurde nicht eingerichtet.

Quellen:
- https://docs.flatpak.org/en/latest/sandbox-permissions.html
- https://docs.flathub.org/docs/for-app-authors/requirements
- https://docs.flathub.org/docs/for-app-authors/verification

## Stand nach PR #43 (26.10.2026)

Flatpak-, Linux- und Windows-CI für `886be30f95` sind erfolgreich.
Unter Mint wurden Start, Image-Einlesen, USB-Export mit identischem SHA256
und die Ablehnung eines Exportziels auf dem Quelldatenträger bestätigt.
Dies ist eine Abnahme des getesteten Aufbaus, keine allgemeine Hardwaregarantie.

Die aktuelle Flathub-Richtlinie verbietet KI-generierte oder KI-unterstützte
Manifeste sowie automatisierte Einreichungs-PRs und entsprechende KI-generierte
Einreichungstexte. Das experimentelle Manifest wurde mit KI erstellt und ist
somit keine zulässige Flathub-Einreichung. Andere bekannte KI-Anteile müssen
mit Umfang offengelegt werden; über die Aufnahme entscheidet Flathub.
Zusätzlich ist die Eignung als Systemwerkzeug mit Datenträgerzugriff ungeklärt.
Ein menschlicher Paketbetreuer müsste eine regelkonforme Einreichung übernehmen.

Quelle: https://docs.flathub.org/docs/for-app-authors/requirements#generative-ai-policy

Eine eigene native Paketquelle ist in [APT_REPOSITORY.md](APT_REPOSITORY.md) dokumentiert und seit
26.10.2026 mit dem umbenannten Paket `tenshi-recovery` veröffentlicht.
