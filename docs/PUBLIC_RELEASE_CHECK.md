# Öffentliche Release-Prüfung

`check_public_release.py` fasst die öffentliche Abschlussprüfung einer stabilen
Veröffentlichung zusammen. Es baut und veröffentlicht nichts und verändert weder
Website-Dateien noch Pakete. Es benötigt nur Python 3.11+ und dessen Standardbibliothek.

## Eingaben vorbereiten

1. Das ursprüngliche, geprüfte Release-Bundle mit `release_manifest.json`, den drei
   Paketen und `SHA256SUMS.txt` bereithalten. Das Manifest nicht nachträglich ändern.
2. Den Website-Katalog mit `prepare_website_catalog.py` aus diesem Bundle vorbereiten;
   die freigegebenen Änderungen müssen weiterhin in allen sechs Sprachen vorliegen.
3. Die zwölf Programm-/Anleitungsseiten aktualisieren und zusammen mit
   `programme/software.json` in einem eigenen Website-Uploadordner ablegen.
   `check_website_release.py` prüft die statischen Releasefelder; diese Prüfung
   führt das neue Werkzeug ebenfalls vor jedem Netzwerkzugriff aus.
4. Die bestehende APT-Verwaltung vor dem Import sichern. Mit dem bisherigen
   Archivschlüssel signieren und **Signatur, signierte Indexprüfsummen und Paket
   separat prüfen**. Der öffentliche Export enthält `dists/`, `pool/` und
   `tenshi-archive-keyring.gpg`; private Schlüssel und die Verwaltungsdaten bleiben
   auf dem Signierrechner.

Build und Katalogvorbereitung: [Release-Vorbereitung](RELEASE_PREPARATION.md).
Signierung und Veröffentlichung: [APT-Quelle](APT_REPOSITORY.md).

## Nach dem Upload prüfen

Zuerst das neue APT-Paket, dann Indexdateien und zuletzt die zusammengehörigen
signierten Release-Metadaten veröffentlichen. Ältere Pool-Dateien behalten.
Website-Dateien erst nach Bereitstellung der Downloads hochladen; betroffene
Serverdateien vorher sichern.

Beispiel mit getrennten Eingabeordnern und einem neuen Bericht:

```bash
python check_public_release.py \
  --bundle release_bundle \
  --site website_upload \
  --apt apt_export \
  --report website_outputs/public-release-check.json
```

`--site` bezeichnet die Wurzel der vorbereiteten Website-Struktur, also den Ordner
mit `programme/`, `tenshi/`, `en/` usw. `--apt` zeigt direkt auf den öffentlichen
APT-Export mit `dists/`, `pool/` und Keyring. Nicht die alte lokale Website-Kopie
oder den übergeordneten Transferordner angeben.

Der Bericht muss außerhalb der drei Eingabeordner liegen, sein Elternordner
bereits existieren und der Dateiname neu sein. Für jeden Lauf einen neuen Namen
verwenden; ein bestehender Bericht wird nicht überschrieben. Website-Prüfberichte
gehören in den Website-Output-Ordner. `--timeout` begrenzt die Wartezeit je Anfrage
(Standard 30 Sekunden, höchstens 300).

## Was geprüft wird

- Alle drei lokalen Pakete gegen Manifest und Prüfsummenliste; Version, Tag,
  Größen, Paket-Hashes und Linux-Commit müssen zum aktuellen Katalog passen.
- Alle zwölf lokalen Seiten durch den bestehenden statischen Seitenprüfer.
- Öffentlich: Katalog und zwölf Seiten über ihre Besucher-URLs, die vier Downloads
  sowie sieben APT-Metadatendateien und das aktuelle DEB. Das Linux-DEB wird sowohl
  als Download als auch als APT-Paket verglichen: insgesamt 25 Dateiprüfungen.
- Öffentliche Dateien müssen bytegenau den lokalen Referenzen entsprechen.
  Downloads werden gestreamt und verworfen; Größenüberschreitungen brechen die
  jeweilige Anfrage ab. Eine HTML-Fehlerseite mit HTTP 200 gilt nicht als Erfolg.
- HTTPS und Weiterleitungen sind auf FreewareFuchs sowie die verwendeten
  GitHub-Downloadhosts begrenzt. Signierte temporäre Weiterleitungs-URLs werden
  nicht in den Bericht übernommen. Es werden keine Anmeldedaten benötigt.

Exitcodes: **0** bei vollständig erfolgreicher Prüfung, **1** bei öffentlichen
Abruf-/Inhaltsfehlern, **2** bei ungültigen lokalen Eingaben oder Berichtspfaden.
Bei lokalen Eingabefehlern wird vor dem ersten Netzwerkzugriff abgebrochen.
Bei öffentlichen Fehlern werden die weiteren Dateien trotzdem geprüft und die
fehlgeschlagenen Prüfungen im Bericht mit `all_passed: false` festgehalten.

Ein positiver Dateivergleich führt **keine neue kryptografische Signaturprüfung**
aus. Er setzt den separat signaturgeprüften lokalen APT-Export voraus. Das Feld
`apt_signature_reverified` bleibt deshalb `false`. Der Bericht bestätigt auch
keinen tatsächlichen Versionswechsel einer Installation, keine visuelle
Layoutprüfung und keine neuen Programm-/Hardwaretests.

Abschließend auf Mint `sudo apt update` und `apt-cache policy tenshi-recovery`
prüfen. Einen tatsächlichen Upgrade-Test von einer älteren installierten Version
gesondert durchführen und dessen Ausgangs-/Zielversion dokumentieren.
