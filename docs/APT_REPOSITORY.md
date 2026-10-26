# APT-Quelle für Linux Mint 22.x

Stand 26.10.2026: Die eigene signierte Quelle unter
https://freewarefuchs.de/tenshi/apt/ bietet `tenshi-recovery 3.0.2-2` für
Mint 22.x (amd64). Benötigt werden Python >= 3.11, Tkinter und util-linux.
Mint 21.x mit Python 3.10 ist kein unterstütztes Paket-Ziel.

Die Quelle muss auf jedem Rechner einmal bewusst hinzugefügt werden.
Sie ist keine offizielle Mint-/Ubuntu-Quelle. Ein DEB-Download richtet sie
nicht automatisch ein. Bei älteren Datenrettungspaketen zuerst den
[Paketwechsel](DEB_PACKAGE_RENAME.md) lesen: Ubuntu hat ein unabhängiges
Logüberwachungsprogramm namens `tenshi`.

## Einmalige Einrichtung

Falls nötig, `curl` und `gnupg` über die Distribution installieren.
Im selben Terminal zunächst den öffentlichen Schlüssel herunterladen:

```bash
TENSHI_KEY_DIR=$(mktemp -d) &&
curl --fail --location --proto '=https' \
  https://freewarefuchs.de/tenshi/apt/tenshi-archive-keyring.gpg \
  --output "$TENSHI_KEY_DIR/tenshi-archive-keyring.gpg" &&
gpg --show-keys --with-fingerprint "$TENSHI_KEY_DIR/tenshi-archive-keyring.gpg"
```

Erwarteter vollständiger Fingerabdruck:

```text
15D6 7DDA 4D0D 3BD1 DD10 A8C3 B714 CC04 15B0 4529
```

Die folgende automatische Prüfung akzeptiert genau diese primäre Kennung.
Bei Abweichungen wird die Quelle nicht eingerichtet:

```bash
TENSHI_KEY_FPR=$(gpg --show-keys --with-colons "$TENSHI_KEY_DIR/tenshi-archive-keyring.gpg" |
  awk -F: '$1 == "pub" { primary=1; next } primary && $1 == "fpr" { print $10; primary=0 }') &&
test "$TENSHI_KEY_FPR" = "15D67DDA4D0D3BD1DD10A8C3B714CC0415B04529" &&
sudo install -d -m 0755 /etc/apt/keyrings &&
sudo install -m 0644 "$TENSHI_KEY_DIR/tenshi-archive-keyring.gpg" \
  /etc/apt/keyrings/tenshi-archive-keyring.gpg &&
sudo tee /etc/apt/sources.list.d/tenshi.sources >/dev/null <<'SOURCE'
Types: deb
URIs: https://freewarefuchs.de/tenshi/apt/
Suites: stable
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/tenshi-archive-keyring.gpg
SOURCE
```

Kein `apt-key`, kein `trusted=yes` und keine Abschaltung der Signaturprüfung.
Der Schlüssel ist ausschließlich dieser Quelle zugeordnet.

## Installieren, starten und aktualisieren

```bash
sudo apt update &&
apt-cache policy tenshi-recovery &&
sudo apt install tenshi-recovery
```

APT muss als Quelle `https://freewarefuchs.de/tenshi/apt/` anzeigen.
Danach **Tenshi** im Menü öffnen oder ohne sudo starten:

```bash
tenshi-recovery --version
tenshi-recovery
```

Das veröffentlichte Paket zeigt `Tenshi 3.0.2 (ba9576020c)`.
Das Paket vergibt keine Geräteberechtigungen. Leserechte für physische
Quellen müssen bei Bedarf gezielt außerhalb der Anwendung eingerichtet werden.

Nachdem der Betreiber eine neue geprüfte Version veröffentlicht hat:

```bash
sudo apt update &&
sudo apt install --only-upgrade tenshi-recovery
```

Entfernen: `sudo apt remove tenshi-recovery`.
Eigene Images und Exporte werden nicht vom Paket verwaltet.
Die Quelle separat deaktivieren, indem
`/etc/apt/sources.list.d/tenshi.sources` aus dem Verzeichnis verschoben wird;
das deinstalliert Tenshi nicht.

## Menüeintrag fehlt nach dem Paketwechsel

Eine im Menüeditor angepasste oder ausgeblendete persönliche Desktop-Datei
kann den Systemstarter überlagern. Bekanntes Beispiel:
`~/.local/share/applications/de.freewarefuchs.Tenshi.desktop` mit altem
`Exec=tenshi`. Der aktuelle Systemstarter nutzt `Exec=tenshi-recovery`.

Zuerst prüfen:

```bash
cat ~/.local/share/applications/de.freewarefuchs.Tenshi.desktop
gtk-launch de.freewarefuchs.Tenshi
```

Enthält die persönliche Datei tatsächlich den veralteten Starter, Menüeditor
schließen und genau diese Datei sichern. Das Beispiel überschreibt keine
vorhandene Sicherung; wenn der Zielname schon existiert, einen neuen wählen:

```bash
mv -n ~/.local/share/applications/de.freewarefuchs.Tenshi.desktop \
  ~/.local/share/applications/de.freewarefuchs.Tenshi.desktop.bak
```

Danach ab- und anmelden. Das Paket ändert persönliche Menüanpassungen nicht.

## Betreiber: Wartung

Der private Signaturschlüssel bleibt lokal. Öffentlich benötigt werden
nur `pool/`, `dists/` und `tenshi-archive-keyring.gpg`.
`conf/`, `db/`, private Schlüssel und Widerrufsdaten nicht hochladen.

Nach CI, manueller Abnahme und Vergleich gegen die freigegebene SHA256:

```bash
reprepro --basedir "$HOME/tenshi-apt" includedeb stable /ABSOLUTER/PFAD/ZUM/GEPRUEFTEN.deb &&
reprepro --basedir "$HOME/tenshi-apt" check &&
reprepro --basedir "$HOME/tenshi-apt" list stable &&
gpg --verify "$HOME/tenshi-apt/dists/stable/InRelease"
```

Neue Pool-Dateien zuerst hochladen, dann Indizes und zuletzt signierte
Release-Metadaten; möglichst atomar veröffentlichen. Alte Downloadziele
zunächst behalten. Den alten Paketnamen `tenshi` nicht wieder anbieten.
Schlüsselablauf: 25.10.2028; rechtzeitig Verlängerung bzw. Wechsel planen.

## Geprüfter Stand und Grenzen

[Vorbereitungs-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40316163730)
aus Commit `ba9576020ca020210e44fe70984e78f8e9efe852`.
SHA256 des DEB `tenshi-recovery_3.0.2-2_all.deb`:

```text
cc1f65e169f7a4759728153ea5a94cd3d51d9df40ae7a6905911892afccf2dd6
```

Öffentlich geprüft: erwarteter Fingerabdruck, InRelease-Signatur, Index-Hash,
DEB-Hash und Dateigröße; alter Paketeintrag entfernt.
Unter Mint manuell bestätigt: Installation, stabile Versionsanzeige,
Programmstart und erneuter Download/Installation direkt von der APT-Quelle.
Der Menüstart funktionierte nach Sicherung einer alten persönlichen Starterdatei.

Dies belegt noch kein Update zwischen zwei verschiedenen Versionen und keine
neue allgemeine Hardwareabnahme. Das DEB wird separat über diese Quelle
angeboten; die GitHub-Release-Dateien von v3.0.2 bleiben unverändert.

Referenzen:
- https://wiki.debian.org/DebianRepository/UseThirdParty
- https://wiki.debian.org/DebianRepository/SetupWithReprepro
