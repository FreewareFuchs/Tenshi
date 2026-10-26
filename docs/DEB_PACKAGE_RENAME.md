# Linux-Paketwechsel: tenshi → tenshi-recovery

Status: vorbereitete Änderung, noch kein neuer Release und noch kein neuer
Upload in die eigene APT-Quelle. Windows und Flatpak bleiben unverändert.

Ubuntu liefert bereits das unabhängige Logüberwachungsprogramm `tenshi`.
Unser bisheriges Datenrettungs-DEB hatte versehentlich denselben Paketnamen.
Die eigene Quelle würde aufgrund der höheren Versionsnummer ein unerwünschtes
Update für dieses andere Programm anbieten. Deshalb nicht allgemein bewerben,
solange der alte Eintrag noch in der Quelle steht.

## Neue Kennungen

| Eigenschaft | Neuer Stand |
| --- | --- |
| Sichtbarer Name | Tenshi |
| Debian-Paket / Terminalbefehl | `tenshi-recovery` |
| Paketdatei | `tenshi-recovery_3.0.2-2_all.deb` |
| Anwendungscode | `/usr/share/tenshi-recovery` |
| Paketdokumentation | `/usr/share/doc/tenshi-recovery` |
| Desktop-Icon | `tenshi-recovery` |

Die App-Version bleibt 3.0.2; die Paketrevision steigt auf 2.
Kein Alias `/usr/bin/tenshi` und keine `Provides`, `Conflicts`, `Replaces`
oder `Breaks` gegen das unabhängige Ubuntu-Paket werden eingerichtet.
Die Datenrettung beansprucht dessen Namen und Dateien nicht mehr.
Benutzereinstellungen und Exportpfade des Programms ändern sich nicht.

## Betreiber: alten APT-Eintrag zurückziehen

Im bekannten lokalen Repository auf dem eigenen Rechner:

```bash
cd ~/tenshi-apt
reprepro --basedir . remove stable tenshi
reprepro --basedir . export stable
reprepro --basedir . list stable
gpg --verify dists/stable/InRelease
```

Die Liste darf danach keinen alten `tenshi`-Eintrag mehr enthalten.
Den neu signierten Ordner `dists` auf dem Server ersetzen. Falls möglich atomar
veröffentlichen; vorhandene Pool-Dateien zunächst behalten, damit alte Indizes
nicht auf fehlende Downloads zeigen. Niemals Schlüsselprüfung deaktivieren.
Dadurch wird ein bereits installiertes altes Datenrettungs-DEB nicht deinstalliert.

Das neue Paket erst nach grüner CI und manueller Mint-Abnahme importieren,
mit veröffentlichtem SHA256 prüfen und als `tenshi-recovery` bereitstellen.
Nicht beide Paketnamen dauerhaft in der Quelle lassen. Der öffentliche
Signaturschlüssel und die bestehende Quellenkonfiguration können bestehen bleiben.

## Nutzer: bisheriges Datenrettungs-DEB wechseln

Zuerst die Identität des installierten alten Pakets feststellen:

```bash
dpkg-query -W -f='${Package} ${Version}\n${Maintainer}\n${Homepage}\n' tenshi
```

**Nur** wenn es unser Datenrettungs-DEB mit FreewareFuchs als Maintainer und
`https://github.com/FreewareFuchs/Tenshi` als Homepage ist, Tenshi schließen und
das alte Paket entfernen:

```bash
sudo apt remove tenshi
```

Ein installiertes Ubuntu-Logüberwachungsprogramm gleichen Namens nicht entfernen.
Keine automatische Übergangspaket-Lösung verwenden, da die gemeinsame alte
Paketkennung den Ursprung nicht eindeutig unterscheidet.

Nach Veröffentlichung des neuen Pakets in der aktualisierten Quelle:

```bash
sudo apt update
apt-cache policy tenshi-recovery
sudo apt install tenshi-recovery
tenshi-recovery
```

Ohne eingerichtete Quelle die neue DEB-Datei nach Prüfsummenvergleich lokal
mit `sudo apt install ./tenshi-recovery_3.0.2-2_all.deb` installieren.
Der alte GUI-Menüeintrag muss vor diesem Wechsel durch Entfernen des alten
Datenrettungspakets verschwinden; beide Datenrettungspaketgenerationen werden
nicht als parallele Installationen unterstützt.

Das veröffentlichte GitHub-DEB 3.0.2-1 und seine Prüfsumme bleiben historische
Release-Artefakte. Keine alten Downloads oder Prüfsummen durch neue Dateien ersetzen.

Referenz: https://packages.ubuntu.com/noble/tenshi
