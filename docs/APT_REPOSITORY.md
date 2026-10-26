# Eigene APT-Paketquelle – Vorbereitung

Status: Entwurf, nicht eingerichtet oder veröffentlicht. Diese Anleitung wurde
noch nicht auf dem Webserver oder mit einem echten Signaturschlüssel ausgeführt.

## Ziel

Geprüfte native Tenshi-DEBs über eine zusätzlich eingerichtete APT-Quelle
aktualisieren. Nutzer müssen die Quelle einmal bewusst hinzufügen.
Dies ist keine Aufnahme in die offiziellen Mint-/Ubuntu-Paketquellen und
macht Tenshi nicht auf allen Mint-Installationen automatisch sichtbar.

Ziel bleibt Linux Mint 22.x; die Python-Abhängigkeit des DEB wird nicht umgangen.
Das bisher getestete System ist x86_64 (APT-Architektur amd64).
Das Paket selbst ist architekturunabhängig (`all`).

## Vor Veröffentlichung festlegen

- Dauerhaft erreichbarer HTTPS-Basispfad auf dem eigenen Webserver.
  Vorschlag: `https://freewarefuchs.de/tenshi/apt/`; noch keine aktive Quelle.
- Dedizierter OpenPGP-Signaturschlüssel mit Ablaufdatum und sicherer Sicherung.
  Privater Schlüssel und Passphrase bleiben beim Betreiber, niemals im
  Repository oder im öffentlichen Webverzeichnis.
- Verantwortlichkeit für neue Pakete, Erneuerung der Metadaten und Schlüsselwechsel.

Der öffentliche Schlüssel und sein vollständiger Fingerabdruck müssen über
vertrauenswürdige Projektkanäle veröffentlicht und vor Import geprüft werden.

## Betreiber: lokale Erstellung

Empfohlenes Werkzeug: `reprepro` aus der Distribution. Es verwaltet Indizes,
Paketdateien und Signaturen. Arbeitsverzeichnis außerhalb des Webroots verwenden.

Benötigte Werkzeuge unter Mint/Ubuntu:

```bash
sudo apt install reprepro gnupg
```

Vorhandenen dedizierten Schlüssel lokal anzeigen:

```bash
gpg --list-secret-keys --keyid-format long --with-fingerprint
```

Falls noch keiner existiert, lokal interaktiv erzeugen:

```bash
gpg --full-generate-key
```

Einen aktuellen Signaturalgorithmus, eine passende Betreiberkennung, ein
Ablaufdatum und eine geschützte Passphrase wählen. Kein unbeaufsichtigter
Schlüssel ohne Passphrase für den Produktionsbetrieb.

In einem neuen Arbeitsverzeichnis `conf/distributions` anlegen. Vor Ausführung
`VOLLSTAENDIGER_FINGERABDRUCK` durch den eigenen Fingerabdruck ersetzen:

```text
Origin: FreewareFuchs
Label: Tenshi
Suite: stable
Codename: stable
Architectures: amd64
Components: main
Description: Tenshi packages for Linux Mint 22.x
SignWith: VOLLSTAENDIGER_FINGERABDRUCK
```

`amd64` ist hier die Client-Architektur. `reprepro` ordnet das `all`-DEB
dem entsprechenden Index zu; weitere Architekturen benötigen eigene Abnahme.

Das veröffentlichte, bereits getestete Paket verwenden, nicht neu bauen.
Zuerst seinen SHA256 gegen `SHA256SUMS.txt` aus demselben Release prüfen.
Für 3.0.2 ist der erwartete Paket-Hash:

```text
4a1aa67f870e3b98c676e11e1e6f96c8e48e787bbdc6697fae1d032212e90070  tenshi_3.0.2-1_all.deb
```

Im Arbeitsverzeichnis mit angelegter Konfiguration:

```bash
reprepro --basedir . includedeb stable /ABSOLUTER/PFAD/tenshi_3.0.2-1_all.deb
reprepro --basedir . export stable
reprepro --basedir . check
reprepro --basedir . list stable
gpg --export-options export-minimal --export VOLLSTAENDIGER_FINGERABDRUCK > tenshi-archive-keyring.gpg
gpg --show-keys --with-fingerprint tenshi-archive-keyring.gpg
```

Nicht leere Schlüsseldatei, korrekten Fingerabdruck und signierte Release-Dateien
kontrollieren. Falls nur `Release`/`Release.gpg` statt `InRelease` erzeugt werden,
ist auch das ein von APT unterstütztes Signaturformat. Ohne gültige Signatur
nicht veröffentlichen.

## Prüfen und hochladen

Vor dem öffentlichen Upload eine Mint-Test-VM mit isoliertem Test-Repository
verwenden. Installation, Update von der bisherigen DEB-Version und Entfernung
prüfen; APT muss Manipulationen an Index/Paket ablehnen.
Diese Repository-Tests stehen noch aus.

Öffentlich benötigt werden ausschließlich:

- `dists/`
- `pool/`
- `tenshi-archive-keyring.gpg`

Nicht `conf/`, `db/`, GnuPG-Verzeichnisse oder private Schlüssel hochladen.
Der Webserver muss Dateien unverändert über HTTPS ausliefern.
Neue Pool-Dateien zuerst hochladen, dann Indizes und zuletzt die signierten
Release-Metadaten. Alte Paketdateien zunächst behalten, damit bereits geladene
Indizes weiterhin gültige Downloadziele haben. Ein atomarer Verzeichniswechsel
auf dem Server ist vorzuziehen.

## Nutzeranleitung erst nach Freigabe veröffentlichen

Die folgenden Inhalte sind eine Vorlage, noch keine Installationsanweisung für
eine existierende Quelle. `BASIS_URL` durch den geprüften HTTPS-Pfad ersetzen.

1. Öffentlichen Schlüssel als Datei herunterladen, Fingerabdruck gegen die
   veröffentlichte Betreiberangabe prüfen.
2. Schlüssel mit Modus 0644 unter
   `/etc/apt/keyrings/tenshi-archive-keyring.gpg` installieren.
3. `/etc/apt/sources.list.d/tenshi.sources` mit diesem Inhalt anlegen:

```text
Types: deb
URIs: BASIS_URL
Suites: stable
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/tenshi-archive-keyring.gpg
```

Danach `sudo apt update`, mit `apt-cache policy tenshi` Quelle und Version
kontrollieren und `sudo apt install tenshi` verwenden.
Kein `trusted=yes`, keine Abschaltung der Signaturprüfung und kein `apt-key`.
Die Quellenkonfiguration und Schlüsseldatei lassen sich später gezielt entfernen.
Das entfernt ein bereits installiertes Tenshi nicht automatisch.

## Wartung

Jede neue geprüfte DEB-Version wird lokal importiert und die aktualisierte
signierte Quelle veröffentlicht. Neue Pakete nicht automatisch aus ungetesteten
Commits übernehmen. Ablaufdatum und Widerruf des Signaturschlüssels überwachen;
Schlüsselwechsel rechtzeitig über einen vertrauenswürdigen Kanal ankündigen.

Referenzen:
- https://wiki.debian.org/DebianRepository/SetupWithReprepro
- https://wiki.debian.org/DebianRepository/UseThirdParty
- https://wiki.debian.org/DebianRepository/Format
