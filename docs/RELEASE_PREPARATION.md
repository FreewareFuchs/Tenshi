# Release-Paket automatisch vorbereiten

Unter GitHub Actions **Prepare release bundle (no publishing)** manuell starten,
den gewünschten Branch und `stable` für eine stabile Ausgabe oder `beta.N` für
eine Vorabversion auswählen. Die Basisversion stammt aus `recoverydesk/__init__.py`. Es wird kein Tag oder Release angelegt.

Der Workflow führt die bestehenden vollständigen Linux- und Windows-Prüfungen
für denselben Commit aus. Beide Builds erhalten dieselbe explizite Release-Kennung;
das DEB erhält die dazu passende Debian-Version. Erst wenn beide Jobs erfolgreich
sind, entsteht das Actions-Artefakt `Tenshi-prepared-release` mit:

- Windows-Installer und Portable-ZIP; bei `stable` ohne Beta-Suffix, bei `beta.N` mit entsprechendem Suffix
- Linux-DEB
- SHA256SUMS.txt und release_manifest.json mit vollständigem Commit
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


## Release-Kandidat 3.0.4

Der Quellstand bereitet Version 3.0.4 mit Linux-Paketversion 3.0.4-1 vor.
Die [Versionshinweise](../RELEASE_NOTES_3.0.4.md) unterscheiden die übernommenen
Änderungen von der noch offenen Prüfung der finalen Pakete. Die veröffentlichten
3.0.3-Dateien, ihr Katalog und die APT-Paketquelle bleiben bis zur separaten
Veröffentlichung unverändert.

Nach erfolgreicher Versions-/Quellprüfung und CI den sauberen, festgehaltenen
Kandidaten-Commit über **Prepare release bundle (no publishing)** mit `stable`
bauen. Erwartete Dateinamen:

- `Tenshi_Setup_3.0.4_Win64.exe`
- `Tenshi_Portable_3.0.4_Win64.zip`
- `tenshi-recovery_3.0.4-1_all.deb`

Erst das daraus erzeugte `release_manifest.json` und `SHA256SUMS.txt` liefern die
endgültigen Dateigrößen und Prüfsummen. Ein normaler PR-Build oder ein erfolgreicher
Quelltest allein bestätigt kein fertig zusammengestelltes Release-Bundle.
Manuelle Abnahmepunkte stehen in den Versionshinweisen. Vor Veröffentlichung keine
neuen Downloadlinks in die öffentliche Website oder Paketquelle übernehmen.
