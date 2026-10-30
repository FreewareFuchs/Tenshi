# Release-Paket automatisch vorbereiten

In Vorbereitung: **3.0.10** mit dem Wiederöffnen gespeicherter Exportaufträge
nach einem Programmneustart aus PR #115. Der Funktionsstand ist manuell abgenommen.
Installer, Portable und DEB werden gemeinsam mit expliziter Kennung `stable`
gebaut. Die endgültige Paketabnahme steht noch aus.
[Änderungen und Grenzen](../RELEASE_NOTES_3.0.10.md).

Aktueller veröffentlichter Stand: [Tenshi 3.0.9](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.9),
seit 29.10.2026. Zielprüfung und sichtbare, wieder aufrufbare Fortschrittsansicht
stammen aus dem manuell bestätigten PR #109. Die Hilfe ist in allen sechs Sprachen
ergänzt. Die endgültigen Pakete stammen unverändert vom sauberen Commit
`b433b2bb7f53c259c546c16e475b89c773e3cf4b` aus dem
[gemeinsamen stabilen Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40914147249).
Funktionen, Paketstarts und Versionsanzeigen sind manuell bestätigt.
Alle sieben GitHub-Assets, 14 APT-Dateien und 25 abschließenden öffentlichen
Vergleiche sind erfolgreich. [Versionshinweise und Abnahme](../RELEASE_NOTES_3.0.9.md).
Frühere Releases und ihre Prüfsummen bleiben unverändert erhalten.

Unter GitHub Actions **Prepare release bundle (no publishing)** manuell starten,
den gewünschten Branch und `stable` für eine stabile Ausgabe oder `beta.N` für
eine Vorabversion auswählen. Die Basisversion stammt aus `recoverydesk/__init__.py`. Es wird kein Tag oder Release angelegt.

Der Workflow führt die bestehenden vollständigen Linux- und Windows-Prüfungen
für denselben Commit aus. Beide Builds erhalten dieselbe explizite Release-Kennung;
das DEB erhält die dazu passende Debian-Version. Erst wenn beide Jobs erfolgreich
sind, entsteht das Actions-Artefakt `Tenshi-prepared-release` mit:

- Windows-Installer und Portable-ZIP; bei `stable` ohne Beta-Suffix, bei `beta.N` mit entsprechendem Suffix
- Linux-DEB
- SHA256SUMS.sha256, je Paket eine weitere .sha256-Datei und release_manifest.json mit vollständigem Commit
- RELEASE_NOTES.md mit beschrifteten Download-Links als Entwurf

Die Zusammenstellung prüft die Windows-Build-Metadaten, den Portable-Inhalt und
dessen Übereinstimmung mit der separat gebauten EXE sowie Paketname, Architektur,
Version und eingebettete Build-Metadaten des DEB. Fehlende, doppelte oder abweichende
Pakete brechen den Vorgang ab. Windows-Metadaten stammen als Begleitdatei aus dem
Buildjob; die Zusammenstellung liest sie nicht erneut aus der PyInstaller-EXE.
Der Windows-Job testet die gebaute EXE separat per Smoke-Test.

Lokal auf Linux mit installiertem `dpkg-deb` lassen sich heruntergeladene,
entpackte Build-Artefakte ebenfalls prüfen:

```sh
python3 prepare_release.py --artifacts artifacts --output release_bundle \
  --release stable --commit VOLLSTAENDIGER_COMMIT_HASH
```

Das Ausgabeziel darf noch nicht existieren. Die bisherigen Windows-Skripte
bleiben verwendbar. Die Vorbereitung ersetzt keine manuellen Gerätetests.
Vor dem späteren Veröffentlichen die Änderungen in den Release-Notizen ergänzen,
die Pakete auf Windows/Linux testen und die Prüfsummen kontrollieren. Die beschrifteten Download-Links verweisen auf die vorgesehenen späteren
Release-Assets und funktionieren erst nach deren Veröffentlichung. Actions-Artefakte innerhalb ihrer Aufbewahrungsfrist
herunterladen. Der Workflow besitzt ausschließlich lesende Repository-Rechte.

## Versionsangaben zentral abgleichen

Die Programmversion wird ausschließlich in `recoverydesk/__init__.py` geändert.
Danach die abgeleiteten Windows-/Installer-/CI-Angaben erzeugen:

```bash
python3 sync_release_version.py --write
python3 sync_release_version.py --check
```

Die Änderungen prüfen und gemeinsam committen, bevor ein Release-Build mit
sauberem Git-Stand gestartet wird. Der Abgleich ändert keine Tags, Releases,
Quellgeräte oder bereits veröffentlichten Pakete. Historische Release-Notizen
und Abhängigkeiten werden nicht umnummeriert. Die Debian-Paketrevision bleibt
als separate Paketierungsangabe in `build_deb.py` bestehen.

Der Windows-Build und die drei CI-Workflows prüfen den Abgleich vor dem Bau.
Veraltete oder fehlende Versionsfelder stoppen den Vorgang. Die Tests für
Build-Kennung und Paketinhalt verwenden die Programmversion statt einer
separaten festen Release-Nummer. Zusätzliche Tests simulieren eine künftige
Version und prüfen die daraus entstehenden Windows-Ressourcen, Dateinamen
und Actions-Artefakte sowie den Abbruch ohne Teiländerungen bei ungültigen
Eingaben. Die bekannten Build-Einstiegspunkte bleiben verwendbar.

## Stabile Version 3.0.2

Die [veröffentlichte 3.0.2](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.2) wurde mit `stable` vom Commit `abfd4c973a253c2a8571d238e15a0fb77b013dec` erstellt ([Workflow](https://github.com/FreewareFuchs/Tenshi/actions/runs/40242121217)). Sie enthält `Tenshi_Setup_3.0.2_Win64.exe`, `Tenshi_Portable_3.0.2_Win64.zip`, `tenshi_3.0.2-1_all.deb` und `SHA256SUMS.txt`. Die Debian-Metadaten enthalten Version `3.0.2-1`, der Git-Tag ist `v3.0.2`. Der Workflow selbst erstellt weiterhin weder Tags noch Veröffentlichungen.


## Stabile Version 3.0.3

[Finaler Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40363573058) aus Commit `18d973dd88346157da8e3bbf9856bc44ebe71f25` mit Kennung `stable`.
Veröffentlicht als [v3.0.3](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.3).
Das Release enthält `Tenshi_Setup_3.0.3_Win64.exe`, `Tenshi_Portable_3.0.3_Win64.zip`, `tenshi-recovery_3.0.3-1_all.deb` und `SHA256SUMS.txt`. [Pakettests und Grenzen](../RELEASE_NOTES_3.0.3.md).

Die finalen Pakete wurden manuell bestätigt. Die APT-Quelle ist veröffentlicht und die erneute Installation daraus geprüft. Ein gesonderter Upgrade-Test von installierter 3.0.2-2 über die öffentliche Quelle bleibt offen. Bestehende Dateien älterer Releases wurden nicht ersetzt.

## Öffentliche Abschlussprüfung wiederverwenden

Nach der getrennten Veröffentlichung von Downloads, signierter APT-Quelle und
Website vergleicht `check_public_release.py` die öffentlichen Dateien mit dem
geprüften lokalen Stand. Es prüft zuerst Bundle, Katalog und zwölf lokale Seiten,
lädt dann die öffentlichen Referenzen und schreibt einen neuen JSON-Bericht.
Die vorgelagerte GPG-Prüfung des APT-Exports bleibt erforderlich.
[Aufruf, Voraussetzungen und Grenzen](PUBLIC_RELEASE_CHECK.md).

## Website-Katalog aus dem geprüften Bundle vorbereiten

`prepare_website_catalog.py` erzeugt eine neue lokale `software.json` für eine
**neuere stabile Version**. Es arbeitet ohne Netzwerk und veröffentlicht nichts.
Als Eingabe dienen das unveränderte vorbereitete Release-Bundle, eine aktuelle
Kopie von `/programme/software.json` der Website und freigegebene Änderungsnotizen
als JSON-Objekt mit genau den Schlüsseln `de`, `en`, `es`, `zh`, `ru`, `ja`.
Jeder Sprachwert ist eine nicht leere Liste nicht leerer Texte. Das Datum wird
explizit als `YYYY-MM-DD` übergeben, nicht vom Buildzeitpunkt abgeleitet.

```bash
python3 prepare_website_catalog.py --bundle release_bundle \
  --catalog software-current.json --notes website-notes.json \
  --date 2026-10-26 --output software-new.json
```

Das Ausgabeziel darf noch nicht existieren. Die drei Paketdateien werden erneut
vollständig gelesen und mit Byteanzahl und SHA256 aus `release_manifest.json`
verglichen; auch `SHA256SUMS.txt` muss inhaltlich exakt zum Manifest passen.
LF- und Windows-CRLF-Zeilenenden werden dabei gleich behandelt. Dies setzt das
vertrauenswürdige, zuvor mit `prepare_release.py` geprüfte Bundle voraus. Das
Werkzeug bestätigt weder eine digitale Signatur noch die öffentliche Erreichbarkeit
der Downloads und prüft die eingebetteten Build-Metadaten nicht ein zweites Mal.
Die Kennung `published: false` im vorbereiteten Manifest bleibt unverändert;
sie wird nicht als Nachweis einer Veröffentlichung behandelt.

Aus dem Manifest stammen Version, Tag, Paketnamen, Dateigrößen, Prüfsummen und
Quellcommit. Die Windows-Links und der Prüfsummenlink verwenden das zugehörige
GitHub-Release; der Linux-Link verwendet den festen FreewareFuchs-APT-Pool und
die Paketversion aus dem geprüften DEB-Dateinamen. Alte Release-Einträge, andere
Programme und sonstige Katalogfelder werden erhalten. Bereits vorhandene
Release-Einträge dürfen nicht verändert werden; identische Wiederholungen erzeugen
keinen doppelten Eintrag. Downgrades und Beta-Bundles werden abgelehnt.

Die neue JSON-Datei vor dem Upload prüfen. Erst wenn Release und signierte
APT-Paketquelle tatsächlich veröffentlicht und erreichbar sind, die geprüfte
Datei als `/programme/software.json` hochladen. Die sechs Programmseiten und
sechs Anleitungsseiten enthalten zusätzlich statische Versions-/Downloadangaben;
diese HTML-Dateien werden von diesem Werkzeug noch nicht angepasst und müssen
weiterhin abgeglichen werden. Anschließend öffentliche Download-Links, Versionen
und Prüfsummen kontrollieren. Ein vorbereiteter Katalog ist keine Freigabe zum
Veröffentlichen eines Releases oder zum Ändern der Website.


## Statische Website-Seiten vor dem Upload prüfen

Nach dem Abgleich der sechs Programmseiten und sechs Anleitungen den neuen
Katalog zusammen mit dem lokalen Website-Stand prüfen:

```bash
python3 check_website_release.py --site /pfad/zu/httpdocs --catalog software-new.json
```

Das Werkzeug liest nur und benötigt keine Netzwerkverbindung. Es prüft alle
Vorkommen der markierten Versions-, Tag- und Größenfelder, die markierten
Installer-/Portable-/Linux-/Prüfsummen-/Release-Links sowie genau einen gültigen
Tenshi-SoftwareApplication-JSON-LD-Block pro Programmseite. In diesem Block
müssen Version und Release-URL zum Katalog passen. Jede Anleitung benötigt ein
`linux-install`-Element; auf den Programmseiten wird die Linux-Prüfsummenangabe
in einem `ff-secondary`-Element erwartet. Die dort genannten Paketversionen und
SHA256-Werte sowie explizite aktuelle `tenshi-recovery_...deb`-Links werden geprüft.
Fehlende Seiten, Felder, ungültiges JSON-LD und widersprüchliche Wiederholungen
werden mit dem jeweiligen Seitenpfad gemeldet. Die Seitenstruktur entspricht
den sechs Sprachversionen `de`, `en`, `es`, `ru`, `zh`, `ja`.

Exitstatus: `0` bei passenden Release-Feldern, `1` bei Seitenabweichungen und `2`
bei ungültigem oder fehlendem Katalog. Historische Versionshinweise außerhalb
der geprüften Release-Felder werden nicht pauschal als Fehler gewertet.
Redaktionelle Fließtexte und Meta-Beschreibungen, allgemeine HTML-Gültigkeit,
Layout, Paketdateien und die öffentliche Erreichbarkeit von Links sind damit
nicht bestätigt. Der Katalog muss zuvor mit dem geprüften Bundle vorbereitet
worden sein; das Prüfwerkzeug ersetzt dessen Paketprüfung nicht.

Vor jeder HTML-Änderung die betroffenen Originaldateien mit ihrer relativen
Ordnerstruktur in einem datierten Backup sichern. Auch bei erfolgreicher Prüfung
vor dem Upload etwaige zwischenzeitliche Änderungen auf dem Server berücksichtigen.


## Stabile Version 3.0.4 (27.10.2026)

[Release v3.0.4](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.4)
aus Commit `b1caea8b40f7b29d401e85a3e51a2916fc5f9e0e`, gebaut mit `stable`
im erfolgreichen [gemeinsamen Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40466932499).
Die finalen Pakete wurden gegen Manifest und Prüfsummenliste geprüft und vom
Anwender manuell abgenommen. [Paketnamen, Größen, SHA256 und Testgrenzen](../RELEASE_NOTES_3.0.4.md).

Nach der Veröffentlichung wurden alle vier GitHub-Dateien öffentlich heruntergeladen
und geprüft. Die bestehende APT-Verwaltung wurde gesichert, das neue DEB aufgenommen
und mit dem bestehenden Archivschlüssel signiert. GPG hat die Signatur in Mint
bestätigt; anschließend wurden die signierten Indexdaten und der Paketinhalt geprüft.
Alle neun hochgeladenen APT-Dateien stimmen öffentlich bytegenau mit diesem Stand
überein. Ältere Pool-Dateien bleiben erhalten; private Schlüssel wurden nicht übertragen.

Erst nach der öffentlichen APT-Prüfung wurden die Website-Dateien hochgeladen.
Die zwölf Programm-/Anleitungsseiten und der Katalog wurden anschließend öffentlich
mit dem vorbereiteten Stand verglichen; alle 13 Dateien und vier verlinkten Downloads
sind geprüft. Die vorherigen lokalen Website-Dateien sind gesichert.

In Mint sind `sudo apt update` ohne Signaturfehler sowie installierte Version und
APT-Kandidat `3.0.4-1` bestätigt. Der Anwender bestätigt zusätzlich das Upgrade über
APT. Die genaue Ausgangsversion wurde nicht angegeben; daraus folgt kein gesonderter
Nachweis des älteren Paketwechsels von `3.0.2-2`.

Das ursprüngliche Build-Manifest bleibt als Herkunftsnachweis unverändert: Sein
Vorbereitungsstatus beschreibt den Zeitpunkt des Builds, nicht den heutigen
Veröffentlichungsstatus. Die Dokumentationsänderung erzeugt keine neuen Pakete
und verschiebt weder Tag noch Release-Commit.

## Stabile Version 3.0.5

[v3.0.5](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.5) ist seit
28.10.2026 veröffentlicht. Die abgenommenen Pakete stammen vom Commit
`d8a215fa34ce9be4c9653c1f11f337c7a4377a1b` und dem
[gemeinsamen Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40509422383).
GitHub, die signierte APT-Quelle und die Website sind öffentlich geprüft;
alle 25 Vergleichsprüfungen sind erfolgreich. [Release-Hinweise](../RELEASE_NOTES_3.0.5.md).

## Historischer Vorbereitungsstand des Oberflächenupdates 3.0.6

Dieser Abschnitt beschreibt die damalige Vorbereitung. 3.0.6 ist inzwischen
veröffentlicht; der aktuelle Stand ist die oben verlinkte 3.0.7.

Der Quellstand verwendet Version 3.0.6 und die abgeleiteten Windows-/CI-Felder.
Die öffentliche Ausgabe bleibt bis zur Paketabnahme und Veröffentlichung 3.0.5.
[Änderungen und Paketabnahme](../RELEASE_NOTES_3.0.6.md).

Nach erfolgreicher Prüfung den festgehaltenen sauberen Commit über
**Prepare release bundle (no publishing)** mit `stable` bauen. Das Bundle enthält
Installer, Portable-ZIP und DEB mit Version 3.0.6 beziehungsweise 3.0.6-1 sowie
Manifest und Prüfsummenliste. Die Erstellung legt weder Tag noch Release an.
Die finalen Pakete vor Veröffentlichung manuell abnehmen; bereits bestätigte
3.0.5- oder Flatpak-Testpakete ersetzen diese Abnahme nicht.

## Prüfsummenformat

Neue Bundles und Portable-Archive verwenden SHA256SUMS.sha256; die drei Pakete erhalten zusätzlich jeweils eine eigene .sha256-Datei. Katalog- und Abschlussprüfer unterstützen unveränderte ältere SHA256SUMS.txt weiterhin. Sind beide Listen vorhanden, müssen beide zum Manifest passen. Bestehende Release-Einträge und bereits abgenommene Binärpakete werden nicht umgeschrieben.
