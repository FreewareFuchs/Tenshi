# Natives Linux-DEB – Umstellung auf tenshi-recovery

Die veröffentlichte stabile Version ist `tenshi-recovery_3.0.8-1_all.deb` mit Paketname
und Startbefehl `tenshi-recovery`. Der sichtbare Name bleibt Tenshi.
Dieses Paket ist seit 29.10.2026 in der signierten [APT-Quelle](APT_REPOSITORY.md)
veröffentlicht; Installation, stabile Versionskennung und Start sind unter Mint bestätigt.
Die Umstellung vermeidet eine Kollision mit Ubuntus unabhängigem
Logüberwachungsprogramm `tenshi`.

Die folgenden Release-Dateien dokumentieren den bisherigen Stand 3.0.2;
das veröffentlichte `tenshi_3.0.2-1_all.deb` wird nicht stillschweigend ersetzt.
Für Umstieg und eigene APT-Quelle: [Paketwechsel](DEB_PACKAGE_RENAME.md).

## Aktuelle stabile Version 3.0.8

[Gemeinsamer stabiler Paketbuild](https://github.com/FreewareFuchs/Tenshi/actions/runs/40878364119)
aus Commit `461fce51792c37903c2ce6b45c6810ba02f693c7`.
Veröffentlicht als [v3.0.8](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.8).
Paketgröße: 817954 Bytes; SHA256:
`3678ead73af9d0797cc21541db8f43e7f5cd3b67af8ba8911f7400b8ee7d1926`.
Paketstart, Versionsanzeige unter Mint und die aktualisierte Hilfe sind
manuell bestätigt. Signierter Index und DEB wurden über den VM-Ablauf geprüft;
die 13 öffentlichen APT-Dateien entsprechen diesem Export.
[Änderungen und Prüfgrenzen](../RELEASE_NOTES_3.0.8.md).

## Historische stabile Version 3.0.4

[Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40466932499)
aus Commit `b1caea8b40f7b29d401e85a3e51a2916fc5f9e0e` mit Kennung `stable`.
Veröffentlicht als [v3.0.4](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.4).
Die finale Paketabnahme und das Upgrade über APT sind vom Anwender bestätigt.
Die öffentliche Quelle liefert das geprüfte DEB; in Mint sind installierte Version
und Kandidat `3.0.4-1` bestätigt. [Details und Grenzen](../RELEASE_NOTES_3.0.4.md).

## Historischer Release 3.0.3

[Finaler Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40363573058) aus Commit `18d973dd88346157da8e3bbf9856bc44ebe71f25` mit Kennung `stable`.
Veröffentlicht als [v3.0.3](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.3). Die finalen Mint-Pakettests und die erneute Installation aus der öffentlichen Quelle sind bestätigt. [Details und Grenzen](../RELEASE_NOTES_3.0.3.md).

## Historischer Release 3.0.2

Der veröffentlichte [GitHub-Release `v3.0.2`](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.2) enthält:

| Datei | Plattform |
| --- | --- |
| `tenshi_3.0.2-1_all.deb` | Linux Mint 22.x / kompatible Debian-Systeme mit Python >= 3.11 |
| `Tenshi_Setup_3.0.2_Win64.exe` | Windows 10/11 64 Bit |
| `Tenshi_Portable_3.0.2_Win64.zip` | Windows 10/11 64 Bit |

`all` bezeichnet architekturunabhängigen Python-Code und ersetzt keine Hardwareabnahme. Das bisherige Linux-Praxistestgerät war ein 64-Bit-System mit Linux Mint. Linux Mint 21.x verwendet standardmäßig Python 3.10 und ist kein unterstütztes Paket-Ziel. Die Programmversion ist 3.0.2; die Debian-Paketversion `3.0.2-1` sortiert nach `3.0.2~beta.6-1` und erlaubt ein Update der installierten Beta.

Bei älteren Beta-Paketen ersetzte der Download-Dateiname die Debian-Tilde durch einen Punkt. Das stabile Paket verwendet im Dateinamen und in den DEB-Metadaten `3.0.2-1`.

## Installation, Start und Entfernung

Über die eingerichtete [APT-Quelle](APT_REPOSITORY.md):

```bash
sudo apt update && sudo apt install tenshi-recovery
```

Oder nach Prüfsummenvergleich des direkten DEB-Downloads:

```bash
sudo apt install ./tenshi-recovery_3.0.8-1_all.deb
tenshi-recovery
```

Alternativ den neuen Tenshi-Eintrag im Anwendungsmenü verwenden. Für die Paketinstallation sind Administratorrechte erforderlich, die Anwendung selbst ohne `sudo` starten. Das Paket enthält weder Installationsskripte zur Rechtevergabe noch Gruppenänderungen oder udev-Regeln. Leserechte für physische Quellen müssen bei Bedarf gezielt außerhalb der Anwendung eingerichtet werden.

Zum Entfernen:

```bash
sudo apt remove tenshi-recovery
```

Eigene Images, Exporte und Benutzereinstellungen werden nicht vom Paket verwaltet. Mit separat eingerichteter APT-Quelle sind Updates über APT möglich. Ein lokal installiertes DEB allein fügt die Quelle nicht hinzu. Anleitung und geprüfter Stand: [APT-Paketquelle](APT_REPOSITORY.md).

## Bauen

Im ausgecheckten Quellcode auf einem Debian-/Ubuntu-System mit Python 3.11+ und `dpkg-deb`:

```bash
python3 build_deb.py
cd deb_output
sha256sum -c *.deb.sha256
```

Der Bau benötigt weder root noch pip. Die Anwendung wird unter `/usr/share/tenshi-recovery` installiert; `/usr/bin/tenshi-recovery` verwendet den Systeminterpreter, ignoriert benutzerdefinierte Python-Modulpfade und schreibt keine Bytecode-Dateien in die Installation. Der Menüeintrag und das 256-Pixel-Icon werden an den üblichen Systemorten installiert. Die Laufzeitabhängigkeiten sind `python3 (>= 3.11)`, `python3-tk` und `util-linux`.

Für identische Quellen verwendet der Bau den Zeitstempel des letzten Git-Commits (oder `SOURCE_DATE_EPOCH`). Der Pakettest vergleicht zwei Builds byteweise und kontrolliert Dateiinhalte, Eigentümer und fehlende Installationsskripte. Bereits vorhandene DEB-Zieldateien werden nicht überschrieben.

## CI und Release

Der Linux-Workflow stellt das Artefakt `Tenshi-3.0.8-Linux-DEB` bereit. Er installiert das Paket, startet die installierte Anwendung ohne Gerätezugriff, prüft Logo, Offline-Hilfe und GUI unter virtuellem X11 und entfernt das Paket anschließend wieder. Diese Tests laufen unter Ubuntu und ersetzen den manuellen Pakettest auf Linux Mint nicht.

Am 23.10.2026 wurde das lokal gebaute DEB unter Linux Mint erfolgreich installiert und gestartet. Die Anzeige des vorhandenen `liteon-test.img` sowie der Export einer kleinen und einer größeren Datei wurden bestätigt. Anschließend wurde das Paket mit `apt remove tenshi` erfolgreich entfernt. Die früheren Linux-Praxistests bezogen sich auf den Quellcodestart; dieser zusätzliche Test bezieht sich auf das DEB-Paket. Die Linux-CI einschließlich DEB-Bau, Installation, Startprüfung und Entfernung ist inzwischen erfolgreich, zuletzt für [`a96d584`](https://github.com/FreewareFuchs/Tenshi/actions/runs/40104529828). Der manuelle Mint-Test bleibt dem damals getesteten Entwicklungsstand zugeordnet.

Der Workflow `.github/workflows/prepare-release.yml` bereitet Windows- und Linux-Pakete aus demselben Commit vor. Die Kennung `stable` erzeugt die stabile Version, `beta.N` bleibt für Vorabversionen möglich. Die Zusammenstellung prüft Build-Kennungen und erstellt das gemeinsame Paket mit `SHA256SUMS.sha256`; die Veröffentlichung bleibt ein eigener Schritt. Ältere Pakete mit `SHA256SUMS.txt` bleiben unverändert.

Der [Release-Build für 3.0.2](https://github.com/FreewareFuchs/Tenshi/actions/runs/40242121217) für Commit `abfd4c973a253c2a8571d238e15a0fb77b013dec` ist erfolgreich. Das daraus erzeugte DEB ist im stabilen Release verfügbar. Die lokalen 665 Tests der stabilen Vorbereitung bestanden ohne Fehler; zwei Tests wurden übersprungen. Die dokumentierten älteren Mint-Hardwaretests gelten weiterhin nur für die jeweils getesteten Stände.

## Paketkennung

`python3 build_deb.py` baut standardmäßig `tenshi-recovery_3.0.8-1_all.deb`. Ein solcher lokaler Bau ist nicht automatisch eine offizielle Veröffentlichung. Für einen ausdrücklich gekennzeichneten Release-Build sind ein bekannter sauberer Git-Commit und eine passende Paketversion erforderlich:

```bash
python3 build_deb.py --package-version 3.0.8-1 --release stable
```

Ohne explizite saubere Release-Kennung oder passenden Git-Tag zeigt die Anwendung weiterhin `+dev`. Einzelheiten: [Build-Kennung](BUILD_IDENTITY.md) und [Release-Vorbereitung](RELEASE_PREPARATION.md).

## Abnahme des umbenannten Pakets am 26.10.2026

Der [Vorbereitungs-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40316163730)
aus `ba9576020c` ist erfolgreich. Das finale DEB zeigt `3.0.2 (ba9576020c)` ohne
`+dev`. Mint-Installation und Start sowie erneuter Download/Installation
von freewarefuchs.de wurden bestätigt. Der fehlende Menüeintrag wurde auf
eine alte persönliche Desktop-Datei mit `Exec=tenshi` zurückgeführt und durch
Sichern dieser Datei behoben.

Am 26.10.2026 wurde zusätzlich der vollständige Installationsweg in einem
frischen Mint-Live-System vom Nutzer bestätigt: Einrichtung der Paketquelle
nach der Webseiten-Anleitung, Aktualisierung der Paketliste in der
Anwendungsverwaltung, Auffinden von `tenshi-recovery`, Installation und Start.
Der Test bestätigt diesen Installationsweg; Neustartverhalten und ein Update
zwischen zwei verschiedenen Paketversionen wurden damit nicht geprüft.

Zur Suche in der Mint-Anwendungsverwaltung deren Paketliste aktualisieren
und nach `tenshi-recovery` suchen. Einzelheiten: [APT-Quelle](APT_REPOSITORY.md#installation-über-die-mint-anwendungsverwaltung).
