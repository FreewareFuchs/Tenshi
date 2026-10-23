# Natives Linux-DEB – Beta-Paket

Das Paket ist für den gemeinsamen GitHub-Release `v3.0.2-beta.3` vorgesehen:

| Datei | Plattform |
| --- | --- |
| `tenshi_3.0.2.beta.3-1_all.deb` | Linux Mint 22.x / kompatible Debian-Systeme mit Python >= 3.11 |
| `Tenshi_Setup_3.0.2.exe` | Windows 10/11 64 Bit |
| `Tenshi_Portable_3.0.2_Win64.zip` | Windows 10/11 64 Bit |

`all` bezeichnet architekturunabhängigen Python-Code und ersetzt keine Hardwareabnahme. Das bisherige Linux-Praxistestgerät war ein 64-Bit-System mit Linux Mint. Linux Mint 21.x verwendet standardmäßig Python 3.10 und ist kein unterstütztes Paket-Ziel. Die Programmversion bleibt 3.0.2; die Debian-Paketversion `3.0.2~beta.3-1` sortiert vor einer späteren stabilen Version 3.0.2.

Der Download-Dateiname verwendet Punkte, damit GitHub ihn beim Hochladen nicht verändert. Die Paketversion im DEB behält die Debian-Tilde bei; Beta.3 wird dadurch als neuer als Beta.2 erkannt.

## Installation, Start und Entfernung

Im Ordner mit dem heruntergeladenen Paket:

```bash
sudo apt install ./tenshi_3.0.2.beta.3-1_all.deb
tenshi
```

Alternativ den neuen Tenshi-Eintrag im Anwendungsmenü verwenden. Für die Paketinstallation sind Administratorrechte erforderlich, die Anwendung selbst ohne `sudo` starten. Das Paket enthält weder Installationsskripte zur Rechtevergabe noch Gruppenänderungen oder udev-Regeln. Leserechte für physische Quellen müssen bei Bedarf gezielt außerhalb der Anwendung eingerichtet werden.

Zum Entfernen:

```bash
sudo apt remove tenshi
```

Eigene Images, Exporte und Benutzereinstellungen werden nicht vom Paket verwaltet. Neue Tenshi-Versionen müssen als DEB heruntergeladen und wieder mit `apt install ./DATEINAME.deb` installiert werden. Es wird keine zusätzliche Paketquelle eingerichtet; das Paket erscheint durch den Download nicht automatisch im allgemeinen Katalog des Mint-Anwendungsmanagers.

## Bauen

Im ausgecheckten Quellcode auf einem Debian-/Ubuntu-System mit Python 3.11+ und `dpkg-deb`:

```bash
python3 build_deb.py
cd deb_output
sha256sum -c *.deb.sha256
```

Der Bau benötigt weder root noch pip. Die Anwendung wird unter `/usr/share/tenshi` installiert; `/usr/bin/tenshi` verwendet den Systeminterpreter, ignoriert benutzerdefinierte Python-Modulpfade und schreibt keine Bytecode-Dateien in die Installation. Der Menüeintrag und das 256-Pixel-Icon werden an den üblichen Systemorten installiert. Die Laufzeitabhängigkeiten sind `python3 (>= 3.11)`, `python3-tk` und `util-linux`.

Für identische Quellen verwendet der Bau den Zeitstempel des letzten Git-Commits (oder `SOURCE_DATE_EPOCH`). Der Pakettest vergleicht zwei Builds byteweise und kontrolliert Dateiinhalte, Eigentümer und fehlende Installationsskripte. Bereits vorhandene DEB-Zieldateien werden nicht überschrieben.

## CI und Release

Der Linux-Workflow stellt das Artefakt `Tenshi-3.0.2-Linux-DEB` bereit. Er installiert das Paket, startet die installierte Anwendung ohne Gerätezugriff, prüft Logo, Offline-Hilfe und GUI unter virtuellem X11 und entfernt das Paket anschließend wieder. Diese Tests laufen unter Ubuntu und ersetzen den manuellen Pakettest auf Linux Mint nicht.

Am 23.10.2026 wurde das lokal gebaute DEB unter Linux Mint erfolgreich installiert und gestartet. Die Anzeige des vorhandenen `liteon-test.img` sowie der Export einer kleinen und einer größeren Datei wurden bestätigt. Anschließend wurde das Paket mit `apt remove tenshi` erfolgreich entfernt. Die früheren Linux-Praxistests bezogen sich auf den Quellcodestart; dieser zusätzliche Test bezieht sich auf das DEB-Paket. Die CI-Prüfung des neuen Paket-Workflows steht noch aus.

Windows und Linux für den Release möglichst aus demselben geprüften Commit beziehen. Die beiden Windows-Downloads und das DEB entpackt aus den CI-Artefakten an denselben GitHub-Release anhängen. `SHA256SUMS.txt` muss die Prüfsummen genau dieser drei Dateien enthalten; eine ältere Prüfsummendatei erfasst das neue DEB noch nicht. Die Veröffentlichung bleibt ein eigener Schritt.
