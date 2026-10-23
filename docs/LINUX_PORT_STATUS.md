# Linux-Portierung – Stand und Hardware-Abnahme

## Aktueller Stand vom 23.10.2026

Geprüfter Programmstand: `bb5c374828b626ff3e7bad00bd3f3dc78fc503e0` auf `feature/linux-readonly-port`.
[PR #2](https://github.com/FreewareFuchs/Tenshi/pull/2) ist ein Entwurf; Zusammenführung und Veröffentlichung sind noch nicht erfolgt.

### Bestätigte Prüfungen

| Bereich | Ergebnis und Umfang |
| --- | --- |
| Automatisierte Suite | 566 Tests unter virtuellem X11 bestanden, keine Überspringungen (22,595 s). |
| Linux-CI | [Lauf 39934009137](https://github.com/FreewareFuchs/Tenshi/actions/runs/39934009137) vollständig erfolgreich, einschließlich realer ext4-, Btrfs- und XFS-Images und 1024×650-GUI-Test. |
| Windows-CI | [Lauf 39934009162](https://github.com/FreewareFuchs/Tenshi/actions/runs/39934009162) erfolgreich: Tests, EXE-Smoke-Test, Versionsprüfung, Portable-Paket und Installer. Die Linux-Formatierungstests laufen unter Linux. |
| Linux Mint Cinnamon | FAT32-, NTFS- und ext4-Referenzimages: Navigation und jeweils fünf SHA-256-identische Exporte. Vorschau, Suche, Sitzungen, sechs Sprachen und Layout praktisch bestätigt. |
| Physische USB-SSD | LITEON, 128.035.676.160 Bytes (119,2 GiB): Image vollständig erstellt, keine unlesbaren/ersetzten Bytes, Strategie `stop`, Vollvergleich mit Quelle bitgenau bestanden. |
| SSD-Image lesen | exFAT/YUMI-Inhalt sichtbar; kleine und größere Datei aus dem Image exportiert und erfolgreich geöffnet. Für diese beiden Dateien wurde kein zusätzlicher Hashvergleich berichtet. |
| Windows-Nutzerprüfung | exFAT-Referenzexport mit fünf passenden SHA-256-Werten, Vorschau, Sitzungen, Sprachen und Themewechsel mit dem damaligen aktuellen Build bestanden. |

Beim SSD-Test stieg die beobachtete Kopiergeschwindigkeit nach Kabelwechsel von rund 41 auf 221 MiB/s. Zuvor meldete `lsusb -t` für das Mass-Storage-Gerät 480M; dies ist kein allgemeiner Linux-Leistungsfehler.

### Integritätsstörung und Absicherung

[Issue #3](https://github.com/FreewareFuchs/Tenshi/issues/3) ist geschlossen. Beim Einzeltest im gleichen A2-Steckplatz zeigte ein DIMM sofort Fehler, der verbleibende Riegel bestand vier Memtest-Durchläufe. Nach Entfernung des defekten Riegels bestand Imaging mit Pause/Fortsetzung und Vollvergleich. Die Ergebnisse sprechen für den Hardwarefehler als Ursache der beobachteten Instabilität; sie beweisen nicht rückwirkend die Ursache jedes ursprünglichen Bytefehlers.

Die vollständige Image-Prüfung erkennt auch Abweichungen innerhalb eines Blocks und bestätigt Bitgenauigkeit nur nach erfolgreichem Vollvergleich. Physische Quellen werden dafür nur nach bewusster Aktivierung zusätzlich vollständig gelesen.

Linux-Exportstatus, Berichte und das Hashen exportierter Dateien verwenden sowohl für Blockquellen als auch für reguläre Image-Quellen geprüfte Verzeichnisdeskriptoren. Tests simulieren Symlinks und den Austausch von Elternverzeichnissen. Vorübergehende Dateisperren werden begrenzt erneut versucht, mit erneuter Zielprüfung unter demselben Verzeichnisdeskriptor. Dies ist keine pauschale Absicherung aller Nebenpfade.

### Echte Btrfs- und XFS-Images

`tests/test_real_advanced_images.py` erzeugt ausschließlich neue reguläre Dateien in temporären Verzeichnissen:
- Btrfs mit `mkfs.btrfs -r` und XFS mit `mkfs.xfs -p`, jeweils Standardformat der installierten Werkzeuge.
- Erkennung, UTF-8-Vorschau, Unterordner, exakter Export einer kleinen Textdatei und einer Binärdatei von mehr als 1 MiB.
- SHA-256 des gesamten Quell-Images vor und nach Analyse/Export identisch.
- Kein Mount, Loopgerät, sudo oder physischer Datenträgerzugriff. Linux-CI installiert beide Formatierungswerkzeuge und führt die Tests ausdrücklich aus.

### Verbleibende Testgrenzen

- Weitere Btrfs-/XFS-Varianten, Kompression, RAID und Mehrgeräte-Dateisysteme sind durch diese beiden Standard-Image-Tests nicht abgenommen.
- Allgemeine Löschrettung ist durch erfolgreiche Exporte aktueller Dateien nicht nachgewiesen.
- Weitere Hardwarevarianten (4K-Sektoren, LVM/dmraid), Hotplug-/Mountwechsel und tatsächlich defekte Medien benötigen zusätzliche Abnahme.
- Tenshi-Imaging bietet keine mit GNU ddrescue gleichzusetzende mehrphasige Strategie für beschädigte Medien.
- Der Imaging-Dialog wählt standardmäßig „Sicher anhalten“; Nullersatz bleibt ausdrücklich auswählbar. Beim Fortsetzen gilt die bestätigte Dialogauswahl für verbleibende Blöcke, vorhandene Fehlerbereiche bleiben erhalten. Der API-Standardwert wurde nicht geändert.

## Historischer Prüfverlauf

Die folgenden Abschnitte dokumentieren frühere Zwischenstände. Aussagen wie „Issue #3 offen“, „CI queued“ oder „Hardware-/Windows-Abnahme ausstehend“ sind historische Angaben und werden durch den aktuellen Stand oben ersetzt.


## Plattformprüfung

- **Plattformneutral:** RAW-Abbild, Partitionssuche, NTFS/FAT/exFAT/ext2–4/Btrfs/XFS-Parser, Suchfunktionen, Export, Sitzungen und Imaging-Kern.
- **Windows-spezifisch:** CreateFileW, DeviceIoControl, physische Laufwerksnummern, Laufwerksbuchstaben, Windows-Builds/Installer.
- **Linux-Backend (neu):** Blockgeräte aus sysfs, O_RDONLY für Quellen, BLKGETSIZE64 und BLKSSZGET, Quell-/Zielgerät über sysfs-Abstammung trennen. Ungeklärte Abbildung wird abgewiesen.
- **GUI:** Linux-Blockgeräte über vorhandenen Auswahldialog; fünf Quellenaktionen in einer Zeile; kompakter Kopfbereich und einklappbare Wiederherstellungswarteschlange. Bei 1024×650 unter Cinnamon/X11 anhand von Anwender-Screenshots visuell geprüft, weitere Skalierungen offen.
- **Linux-Laufwerksauswahl (neu):** `Laufwerk auswählen` listet eingehängte Blockpartitionen über `lsblk` (util-linux) und öffnet nach **ausdrücklicher Auswahl und Bestätigung** das zugrunde liegende `/dev/...` ausschließlich lesend. Die Gerätedatei wird vollständig angezeigt; unter Linux ist aus Sicherheitsgründen zunächst keine Zeile vorgewählt. Linux-Geräteberechtigungen werden nicht verändert. Gemountete, beschreibbare Dateisysteme können durch **andere Prozesse** weiter verändert werden; für zuverlässige Rettung bevorzugt Offline-Image. `Physischer Datenträger` listet weiterhin ganze Blockgeräte.
- **GUI-Blockgeräteklassifikation:** Partitionssuche, Dateisystemanalyse, Fehlertoleranz-Sperre, Sitzungsfunktionen und Dateiprüfung verwenden `is_device_source()` auch für Linux-Blockgeräte (zuvor wurden `/dev/...`-Quellen in einzelnen GUI-Pfaden irrtümlich als Image-Dateien behandelt). Bei fehlenden Rechten liefert bereits die Linux-Gerätegeometrie-Abfrage einen verständlichen Berechtigungsfehler. Regressionsprüfungen mit simulierten Blockgeräten sowie **reale GUI-Zugriffsverweigerung unter Cinnamon/X11 bestätigt**.

## Tests (ohne Hardware)
```bash
python3 -m unittest discover -s tests -p 'test_linux*.py' -v
python3 main.py --smoke-test
```
Die Linux-Geräteliste wird ausschließlich aus sysfs-Metadaten erstellt und öffnet dabei keine Blockgeräte. Unter Linux ist auch beim physischen Datenträger **keine Vorauswahl** gesetzt: ein Zugriff erfordert die ausdrückliche Markierung und Bestätigung. Fehlende Leserechte werden nicht verändert.

Die Linux-CI führt die vollständige Python-Testsuite unter virtuellem X11 sowie zusätzliche Geräte- und Layouttests bei 1024×650 aus. Geprüft werden nur simulierte Geräte: gleiches/anderes Zielmedium, überlappende Geräteverbünde, unklare Abbildung, blockierte Imagerstellung/Export vor Dateianlage, die O_RDONLY-Geräteabfrage und sysfs-Partition-/Virtuellgeräte-Zuordnung. CI-Ergebnisse je Commit unter GitHub Actions prüfen.

## Reproduzierbarer Linux-Start und Tests

```bash
sudo apt install python3-tk util-linux
python3 -m unittest discover -s tests -p 'test_linux*.py' -v
bash start_linux.sh --smoke-test
bash start_linux.sh
```

Das Testen des normalen Startbefehls und der Linux-Volumenauswahl erfolgt ohne `sudo` oder Änderungen der Gerätegruppen. Fehlt die Leseerlaubnis für ein Blockgerät, muss Tenshi den Zugriff ablehnen; stattdessen ein vorher erstelltes RAW-Image verwenden.

## Image-basierte Dateisystem-Abnahme ohne Hardware

- **ext4 (auf Linux Mint praktisch bestätigt, 22.10.2026):** `tests/test_real_ext4_image.py` erzeugt ein echtes 64-MiB-ext4-Dateisystem mit `mke2fs -d` in einem zuvor neu angelegten **regulären** temporären Image, ohne Loopgerät, Mount oder sudo. Prüft Dateisystemerkennung, Ordnerbaum, Datei-Vorschau, verschachtelten Export, exakten Bytevergleich und unveränderte Quelle. Für die Linux-CI wird `e2fsprogs` installiert. Dies ist ein Test aktueller Dateien, **kein** Beweis allgemeiner ext4-Löschrettung.
- **Btrfs/XFS (8/8 Tests auf Linux Mint bestanden, 22.10.2026):** Bisherige `tests/test_linux_advanced.py` decken parserkonforme **handkonstruierte** Verzeichnis-/Extent-Metadaten und Dateiexporte sowie einige Fehlerfälle ab. Es fehlt weiterhin ein Importtest mit real mittels `mkfs.btrfs` bzw. `mkfs.xfs` erzeugten, gefüllten Datenträger-Images. Insbesondere moderne Btrfs-/XFS-Varianten und Btrfs mit mehreren Geräten sind **nicht allgemein freigegeben**.

Für den echten ext4-Test unter Linux Mint:

```bash
sudo apt install e2fsprogs
python3 -m unittest discover -s tests -p 'test_real_ext4_image.py' -v
python3 -m unittest discover -s tests -p 'test_linux_advanced.py' -v
```

Der Test formatiert **niemals** ein vorhandenes Gerät. `mke2fs` wird ausschließlich mit einem neu erstellten Image-Pfad unter `TemporaryDirectory` aufgerufen. Ein Exitstatus ungleich null muss als Fehler behandelt werden.

## Bereits manuell nachvollzogen

- Linux Mint Cinnamon/X11: kompakte Oberfläche und einklappbare Warteschlange bei 1024×650 (Screenshots).
- RAW-Testimage: Partitionssuche, exFAT-Ordnernavigation, Dateisuche sowie Einzeldatei-Export mit geöffnetem PNG.
- Export-Vorabprüfung: **nur Metadaten**, kein Nachweis vollständiger Dateiintegrität.
- Linux Mint: vollständiger 256-MiB-Imaging-Test mit SHA-256- und `cmp`-Bestätigung bitgenauer Kopie; 16/16 Imaging-Tests bestanden (Unterbrechung/Wiederaufnahme dort simuliert).
- Analysesitzung nach Programmneustart erfolgreich wieder geladen, ohne Dateisystem erneut einzulesen.
- `test_real_ext4_image.py`: 1/1 auf Linux Mint bestanden; reguläres, temporäres ext4-Image mit Datei- und Unterordnerexport.
- Linux Mint: `test_linux_destination_safety.py` **11/11 bestanden** (22.10.2026). Simulierte sysfs-/Blockgeräte, Quellzugriff nur lesend, gleiche bzw. andere physische Ziellaufwerke, fail-closed bei unsicherer Zuordnung und Unterbindung unsicherer Ausgabedateien. **Kein Ersatz für `strace`-/Hardwareprüfung**.
- Linux Mint, 22.10.2026: Mit `strace -f -e trace=open,openat,openat2` um `list_physical_sources()` wurden `/dev/nvme0n1` und `/dev/sda` in den Geräteinformationen erkannt. Ein `grep` nach den beiden exakten `/dev/...`-Pfaden im Trace ergab **keinen Öffnungsaufruf**. Dies bestätigt die reine Metadatenauflistung für diese beiden Geräte, jedoch **nicht** den Lesezugriff auf physische Quellen. Test ohne `sudo`.
- Linux Mint, 22.10.2026: Realer `strace -f -e trace=open,openat,openat2`-Nachweis für `open_source()` auf **regulärer RAW-Testdatei**, nicht auf Blockgerät: `openat(..., ".../testquelle.raw", O_RDONLY|O_CLOEXEC) = 3`; 512 Bytes gelesen; `reader.writable()` ergibt `False`. Bestätigt ausschließlich lesendes Öffnen dieses Image-Quellpfads. Direkte physische Quelle weiterhin ungeprüft.
- Quellen- und Exportdatei lagen bei diesem **Image-Datei-Test** auf demselben Dateisystem. Für physische Geräte gelten strengere Trennungsprüfungen.

## Zusätzliche automatisierte Sicherheitsprüfung (22.10.2026)

- `tests/test_linux_block_readonly.py`: für simulierte Blockgeräte mit 512/4096-Byte-Sektoren wird `open_source()` auf `rb` ohne Schreibfunktion geprüft. Unausgerichtete Anfragen werden vom `AlignedDeviceReader` in sektorausgerichtete Lesezugriffe übersetzt. Unter Linux melden Lesefehler/Gerätetrennung keinen Windows-Administratorhinweis; ein abgezogenes simuliertes Gerät wird nicht stillschweigend mit Nullbytes ersetzt.
- `tests/test_linux_topology.py`: sysfs-Auflösung über simulierte gestapelte Blockgeräte mit zwei physischen Trägern. Fehlende Slaves und Zyklen führen zum Abbruch statt zu einer geratenen Zuordnung. Die Tests verändern **keine** realen Blockgeräte.
- GitHub Actions: Linux-Spezialtests: 35 ausgeführt (32 bestanden, drei ohne Display übersprungen); gesamte Python-Suite: 475 Tests erfolgreich, zusätzlich echter ext4-Image-Test und virtuelles X11 1024×650 erfolgreich (Commit `8bda3ffd`). Windows-Tests separat.
- **Grenzen:** Lesend geöffnete, aber gleichzeitig durch Linux veränderte Dateisysteme können inkonsistente Daten liefern. Die neu eingeführten Deskriptorprüfungen schützen wichtige Image-/Export-Schreibpfade, jedoch noch nicht jede Status-/Berichtsdatei und jeden Pfadwechsel. Weitere Abnahme von Mount-Topologien und kritischen Rennen erforderlich; niemals hierfür wichtige Originaldatenträger verwenden.

## GUI-Tkinter-Threading-Fehler im neuen Test entdeckt und korrigiert (22.10.2026)

- Linux-Mint-Gegenprobe `python3 -m unittest discover -s tests -p 'test_imaging_gui.py' -v`: **2 Tests fehlgeschlagen**. Ein Test protokollierte `main thread is not in main loop`, statt des absichtlich induzierten `INTEGRITÄTSFEHLER`; beim Erfolgsfall blieb `messagebox.showinfo` aus.
- Ursache in `recoverydesk/gui.py`: Der Imaging-Hintergrundthread führte `verify_var.get()` direkt auf einer Tkinter-Variable aus. Das ist bei Tests mit `app.update()` ohne dauerhaft laufendes `mainloop()` nicht zulässig und auch als GUI-Threading-Verhalten unnötig riskant.
- Korrektur (Commit `2ff17356`): `verify_requested = bool(verify_var.get())` wird **im GUI-Hauptthread vor dem Start** erfasst; der Worker erhält nur noch den unveränderlichen Python-Wert. Imaging-Integritätslogik wurde nicht geändert. **Linux-Mint-Gegenprobe am 22.10.2026 bestanden:** `python3 -m unittest discover -s tests -p 'test_imaging_gui.py' -v` → **2/2 Tests `OK`**; der positive und negative GUI-Pfad samt Statusspeicherung wurden automatisiert bestätigt.

## Imaging-Leseversuche und Sicherheitsstrategie – Linux-Mint-Regressionslauf (22.10.2026)

- Der Nutzer hat `python3 -m unittest discover -s tests -p 'test_imaging_retries_270.py' -v` im aktualisierten Linux-Zweig ausgeführt: **12/12 Tests `OK`**. Die Testgruppe deckt insbesondere Imaging-Leseversuche, Medienfehler-Strategien und die Weitergabe der GUI-Imaging-Parameter ab. Zusammen mit den separat bestätigten **7/7** Integritätstests und **2/2** GUI-Imaging-Tests sind alle drei zuletzt gezielt ausgeführten Testgruppen erfolgreich.
- **Grenze:** Dies ist keine vollständige plattformübergreifende Freigabeprüfung. GitHub-CI stand bei der letzten Kontrolle für den aktuellen Commit noch auf `queued`; ursprüngliche Ursache des 8-GiB-Fehlers bleibt unbekannt.

## CI-Entstauung und automatischer GUI-Negativtest (22.10.2026)

- **Auffälliger Actions-Status:** Zahlreiche ältere `feature/linux-readonly-port`-Läufe stehen seit längerer Zeit auf `in_progress` in den kompletten GUI-/Regressionstests; nachfolgende Workflows wurden `queued`. Eine tatsächliche Testursache ist anhand der noch nicht abrufbaren Joblogs nicht bestätigt.
- **Neue CI-Grenzen:** Linux-Job maximal 20 Minuten, GUI-Gesamtprüfung maximal 8 Minuten; Windows-Job maximal 60 Minuten, Haupttests maximal 10 Minuten. `concurrency` bricht überholte neue Runs pro Branch automatisch ab. `paths` vermeidet bei *Push*-Ereignissen reine Dokumentations-Workflows; bei PR-Ereignissen wird der gesamte PR-Diff berücksichtigt, sodass Dokumentationscommits in einer noch codehaltigen PR weiterhin Prüfungen auslösen können. Bereits vor der Einführung gestartete Workflows werden dadurch möglicherweise nicht rückwirkend beendet.
- **Stabilere GUI-Tests:** `test_imaging_gui.py` wartet bis zur abgeschlossenen Prüfung und kontrolliert `verification.status == verified`; sämtliche Tk-Messageboxen werden im GUI-Test abgefangen, damit ein unerwartetes modales Dialogfenster nicht unbemerkt hängen bleibt. `test_imaging_retries_270.py` prüft analog die Weitergabe von `verify=True` und keine falsche GUI-Warnung.
- **Automatischer GUI-Integritätsfehler:** Neuer Fall in `test_imaging_gui.py` verfälscht auf einer temporären 512-KiB-Datei ein Byte unmittelbar vor der Vollprüfung. Erwartet: Fehlerdialog mit korrektem Byteoffset, keine Erfolgsmeldung, dauerhafter `integrity_failed`-Status und unveränderte Quelle. Test ist auf Linux Mint noch manuell auszuführen, neueste CI-Läufe stehen aus. Dies erklärt **nicht** die Ursache des ersten 8-GiB-Fehlers.

## Neu: Vollständige Imaging-Integritätsprüfung vor Erfolgsmeldung (22.10.2026)

- **Normale RAW-Quelldateien:** Nach dem Kopieren überprüft Tenshi automatisch mit einem eigenständigen zweiten lesenden Durchlauf alle Bytes gegen das erstellte Image. Ein Abschlussstatus `complete` mit `verification.status=verified` wird erst nach bestandenem Vergleich gespeichert. Die GUI zeigt eine eigene Prüfphase und bestätigt `bitgenau verifiziert` nur bei Erfolg.
- **Abweichung oder Fehler:** Bei unterschiedlichen Bytes wird `state=integrity_failed` und `verification.status=failed` mit Fehleroffset im Statusmanifest gesichert; der Imaging-Aufruf meldet einen Fehler statt falscher Erfolgsmeldung. Der Inhalt der Quelle wird dabei nie beschrieben. Ein Abbruch während der Prüfphase speichert den Status `paused` und kann durch erneute Prüfung nach Resume fortgesetzt werden.
- **Physische Geräte und schonender Zugriff:** Ein vollständiger zweiter Lesevorgang auf einem möglicherweise defekten Datenträger wird **nicht** automatisch gestartet. Die GUI zeigt eine explizite Option mit zusätzlicher Sicherheitsnachfrage. Wird kein Vollvergleich durchgeführt oder enthält das Image wegen Medienfehlern Nullersatz, steht ausdrücklich **NICHT bitgenau verifiziert** im Ergebnis. Nullersatz kann nicht als bitgenaue Sicherung ausgegeben werden.
- **Tests:** `tests/test_image_verification.py` prüft automatische Datei-Verifikation, erkannten Bytefehler im Inneren des Images, erneute Prüfung bereits abgeschlossener Images, Unterbrechung/Fortsetzung der Prüfphase sowie sichere Voreinstellung für simulierte Blockgeräte. Nutzer-Gegenprobe vom 22.10.2026: fünf Tests bestanden, der simulierte physische Quelldatenträger wurde wegen nicht durch 512 teilbarer Testdateigröße korrekt abgewiesen. Die Testfixture wurde auf ein vollständiges 512-Byte-Vielfaches korrigiert (Code-Commit `458af7df`), ohne die produktive Sektorausrichtungsprüfung zu lockern. Der Nutzer hat nach Korrektur der 512-Byte-Testfixture am 22.10.2026 **6/6 Tests** unter Linux Mint mit `OK` bestätigt. Die GitHub-CI-Läufe für den neuen Stand standen bei der letzten Kontrolle noch aus.
- **Echter GUI-Vollvergleich auf Linux Mint bestanden (Nutzer, 22.10.2026):** Die Quelle `~/Tenshi-Test/testquelle.raw` (256 MiB) wurde in ein neues Test-Image `~/Tenshi-Test/gui-integrity-check-20261022.img` kopiert. GUI-Erfolgsmeldung: `Image erstellt und geprüft`, `Status: complete`, `bearbeitet: 256.0 MiB`, `nicht lesbar: 0 B`, `BITGENAU VERIFIZIERT: Vollvergleich mit Quelle bestanden.` Anschließend ergab der unabhängige `cmp`-Gesamtvergleich **`GUI-INTEGRITAETSPRUEFUNG BESTANDEN`**. Damit ist der GUI-Erfolgsfall der neuen Verifikation auf Linux Mint nachgewiesen.
- **Negativer GUI-Integritätstest auf Linux Mint bestanden (Nutzer, 22.10.2026):** Aus einem separat erfolgreich verifizierten 256-MiB-Test-Image `~/Tenshi-Test/gui-integrity-negativ.img` wurde an Byteoffset `134217851` (0-basiert) genau ein Byte absichtlich geändert; die Quelle wurde nicht verändert. Beim erneuten Öffnen/Verifizieren erschien statt einer Erfolgsmeldung: **`INTEGRITÄTSFEHLER: Image weicht bei Byteoffset 134217851 von der Quelle ab. Image nicht als bitgenaue Sicherung verwenden.`** Der GUI-Fehlerpfad ist damit manuell bestätigt. Die anschließende rein lesende Kontrolle der Datei `gui-integrity-negativ.img.recovery.json` bestätigte zusätzlich **`state=integrity_failed`**, **`verification.status=failed`**, den korrekt gespeicherten Fehleroffset **134217851** und die Meldung **`INTEGRITAETSFEHLER DAUERHAFT GESPEICHERT`**. Damit ist auch das dauerhafte Speichern des Fehlers auf Linux Mint praktisch abgenommen.
- **Wichtig:** Die Schutzfunktion **entdeckt** abweichende Bytes, repariert sie aber nicht und erklärt nicht die Ursache des ersten 8-GiB-Fehlers. [Issue #3](https://github.com/FreewareFuchs/Tenshi/issues/3) bleibt offen; Linux-Freigabe weiterhin gesperrt.

## Offener Freigabeblocker: GUI-Imaging-Pause/Fortsetzen, 8 GiB (22.10.2026)

- Nach kontrollierter GUI-Unterbrechung bei **26,5 %** wurde die 8-GiB-Sparse-Testquelle `gui-pause-source-8g.raw` auf `gui-pause-copy-8g.img` fortgesetzt. Die GUI meldet **`complete`, 8.0 GiB, 0 B nicht lesbar**; die Statusdatei bestätigt `state=complete`, `processed=8589934592`, `unreadable_bytes=0`, `bad_ranges=[]`. Quelle und Image sind jeweils 8.589.934.592 Bytes groß.
- **Sicherheitsrelevanter Fehler:** `cmp` zeigt reproduzierbar Unterschiede ab **Byte 1.625.391.251** (1-basiert). Eine anschließende 4096-Byte-Stichprobe an Offset 1.625.391.250 enthält in der Quelle nur Nullbytes, im Image dagegen nichtnullige `08`-Bytes; die SHA-256-Stichproben stimmen nicht überein.
- **Status: nicht bestanden; Linux-Release gesperrt, bis Ursache und Gegenprüfung geklärt.** Eine GUI-Erfolgsmeldung ist in diesem Fall kein Beweis für Bitidentität. Kein weiterer Test auf wertvollen Quelllaufwerken. Quelle, Ziel und Statusdateien vorerst aufbewahren.
- **Ergänzte Lokalitätsprüfung (Nutzer, 22.10.2026):** Je 4096 Bytes am Anfang, bei 1 GiB, direkt vor/nach dem bekannten Fehlerbereich, bei 2 GiB und 4 GiB sowie am Dateiende waren mit der Quelle identisch. **Nur** das geprüfte 4096-Byte-Fenster um Offset 1.625.391.250 wich mit **fünf Bytes** ab. Dies war eine **Stichprobe**; die nachfolgende Gesamtprüfung hat zusätzliche Abweichungen gefunden.
- **Vollständige 8-GiB-Integritätsprüfung (Nutzer, 22.10.2026):** Die gesamten 8.589.934.592 Bytes wurden in 1-MiB-Blöcken verglichen. **Genau ein Block** von 8192 weicht ab, darin **25 Bytes** (Quelle jeweils `00`, Image-Werte `08`/`10`). Die Abweichungen liegen in einem Bereich von grob 16 KiB um den ersten Fehleroffset 1.625.391.250 (0-basiert). Der Fall ist damit ein nachgewiesener, von GUI und Statusdatei nicht erkannter Datenintegritätsfehler; Zeitpunkt und Ursache der Veränderung sind weiterhin unbekannt. Das Testmaterial bleibt erhalten, Freigabesperre unverändert.
- **Wiederholte 1-MiB-Blockprüfung (Nutzer, 22.10.2026):** Zwei aufeinanderfolgende lesende Durchläufe lieferten denselben SHA-256-Wert je Datei und dasselbe Muster aus **26 Bytes**, jeweils bei `Offset % 8 == 2` (Quelle `00`, Image `08` oder `10`). Größe und Änderungszeit blieben während dieser beiden Durchläufe unverändert. Der vorherige vollständige Vergleich hatte **25 Bytes** gemeldet; die abweichende Anzahl über die Messungen hinweg ist ungeklärt. Zeitpunkt und Ursache der Beschädigung sind weiterhin nicht nachgewiesen.
- **Unabhängige Kontrollkopie unter Linux (Nutzer, 22.10.2026):** Dieselbe 8-GiB-Sparse-Quelldatei wurde mit `cp --reflink=never --sparse=always` in einen neu angelegten Testordner kopiert und danach mit `cmp -s` vollständig verglichen. Ausgabe: **`LINUX-KONTROLLKOPIE BITGENAU IDENTISCH`**. Der reguläre Linux-Kopiervorgang reproduziert den Fehler nicht. Das grenzt den Verdacht ein, beweist aber keine alleinige Ursache im Tenshi-Code. Die fehlerhafte Tenshi-Kopie bleibt als Beweismaterial unverändert.
- **Kontrollierter 2-GiB-CLI-Wiederaufnahmetest auf Linux Mint bestanden (Nutzer, 22.10.2026):** Neue sparse RAW-Quelle und neues Image mit `create_image` (1 MiB Blockgröße, `stop`). Kontrolliertes Pausieren bei **1.879.048.192 Bytes (1,75 GiB)**; vollständiger byteweiser Vergleich des bestätigten Teilbereichs war identisch. Fortsetzung bis **2.147.483.648 Bytes**, `complete`; anschließender Gesamtabgleich ebenfalls **identisch** (`DIAGNOSETEST VOLLSTAENDIG BESTANDEN`). Der Fehler tritt in diesem Gegenversuch nicht auf. Wegen unterschiedlicher Quelldatei/Größe/Pausenposition ist der 8-GiB-Fehler damit **nicht entkräftet**; Release-Sperre bleibt bestehen.
- **Zweiter 8-GiB-GUI-Test (Unterbrechung, Nutzer, 22.10.2026):** Derselbe 8-GiB-Sparse-Quellinhalt wurde in ein **neues** Ziel `gui-diagnose-8g-zweiterlauf.img` kopiert. GUI-Anhalten bei `state=paused`, `processed=2.242.904.064` Bytes (ca. 2,09 GiB). Der vollständige byteweise Vergleich des bis dahin bestätigten Bereichs mit der Quelle ergab **`VOR WIEDERAUFNAHME: BITGENAU IDENTISCH`**. Der frühere Fehleroffset liegt innerhalb des korrekt verglichenen Bereichs. **Anschließende GUI-Wiederaufnahme bis zum Ende mit vollständigem `cmp`-Vergleich vom Nutzer als bitgenau bestanden bestätigt.** Der zweite 8-GiB-Durchlauf ist erfolgreich; die Ursache des Datenfehlers im ersten Durchlauf bleibt ungeklärt, daher bleibt die Freigabesperre vorerst bestehen.
- **Gezielter Regressionsfall für den ursprünglichen Fehler (neu):** Der Test `test_resume_detects_silent_corruption_in_earlier_committed_block` in `tests/test_image_verification.py` pausiert eine entbehrliche Null-Testquelle nach drei 1-MiB-Blöcken, verändert künstlich drei Bytes (`08`/`10`/`08`) im **inneren bestätigten Block**, der weder vom ersten noch vom letzten Prüfpunkt-Hash abgedeckt wird, und setzt danach fort. Erwartet wird ein dauerhafter `integrity_failed`-Status statt einer falschen Erfolgsmeldung. Das im ursprünglichen 8-GiB-Vorfall gefundene Byte-Raster (`Offset % 8 == 2`) wird dabei simuliert. **Der Nutzer hat den vollständigen Satz `test_image_verification.py` auf Linux Mint am 22.10.2026 mit 7/7 Tests (`OK`) bestätigt**, einschließlich dieses gezielten Regressionstests. Er beweist die Erkennung und korrekte Fehlerbehandlung, **nicht** die Ursache des ursprünglichen 8-GiB-Vorfalls. GitHub-Actions-Checks für den aktuellen Stand sind zum Zeitpunkt der Abfrage noch `queued`.
- Tracking: [Issue #3](https://github.com/FreewareFuchs/Tenshi/issues/3). Weitere Tests sollen zunächst nur kleinräumige, lesende Vergleiche und danach isolierte Reproduktion auf Wegwerfdateien verwenden.

## Schutz gegen Zielpfad-Austausch (Linux)

- **Neue Ausgabeschicht:** `recoverydesk/secure_target.py` öffnet das Zielverzeichnis mit `O_DIRECTORY|O_NOFOLLOW`. Der tatsächlich geöffnete Verzeichnisdeskriptor wird mit `fstat` auf seine physische Abstammung geprüft, bevor über `dir_fd` neue Ausgabedateien mit `O_EXCL|O_NOFOLLOW` angelegt oder bestehende Image-Dateien ohne `O_TRUNC` wieder geöffnet werden. Sonderdateien (Blockgeräte, FIFOs usw.) sind als offene Ziele unzulässig. Bei neuem Imaging wird der `st_dev/st_ino`-Wert der ursprünglich angelegten Datei vor erneutem Öffnen abgeglichen.
- **Export:** Die Dateiexporte für NTFS/FAT/exFAT/ext und die geprüfte Ordneranlage verwenden ebenfalls den an das Verzeichnis gebundenen Schreibzugriff. `batch_export` prüft die neu angelegten Ordner auf diesem Weg.
- **Physische Linux-Imaging-Prüfpunkte:** Statusdateien für Blockquellen werden durch einen temporären, exklusiv angelegten Dateinamen und `os.replace(..., src_dir_fd=..., dst_dir_fd=...)` im bereits geprüften Verzeichnis aktualisiert. Auch das alternative Imaging-Journal wird nur als reguläre Datei mit `O_NOFOLLOW` zum Schreiben geöffnet.
- **Regressionstests:** `tests/test_secure_target.py` und `tests/test_secure_checkpoint.py` simulieren ausgetauschte Dateien, symbolische Links, FIFOs, identische Quell-/Ziel-Hintergrundmedien und einen Austausch des Zielordners unmittelbar vor dem Umbenennen einer Statusdatei. Die Tests öffnen keine realen Blockgeräte. Linux-CI und Windows-Regression müssen je Commit überprüft werden.
- **Zusätzlicher Linux-Mint-Nachweis (22.10.2026):** `python3 -m unittest discover -s tests -p 'test_secure*.py' -v` wurde mit **8 bestandenen Tests** abgeschlossen. Dazu gehören Verzeichniswechsel unmittelbar vor atomarer Statusdatei-Aktualisierung, Symlinks, FIFO-/Sonderdatei-Verbote und erneutes Öffnen einer ausgetauschten Imaging-Datei. Alle Fälle verwenden ausschließlich temporäre Testdaten.
- **Linux Mint bestätigte Stapel-Export-Tests (22.10.2026):** `python3 -m unittest discover -s tests -p 'test_secure_batch_metadata.py' -v` meldete **3/3 Tests bestanden** (`OK`, 0,011 s). Bestätigt wurden die an Verzeichnisdeskriptoren gebundenen Status-/Berichtsschreibvorgänge, die Ablehnung von Symlinks sowie die sichere Berichterstellung nach Austausch des benannten Zielordners. Es kamen nur simulierte Blockquellen und temporäre Dateien zum Einsatz; keine echte Hardware wurde dafür geöffnet.
- **Stapel-Export-Metadaten (neu):** Für physische Linux-Blockquellen schreiben `batch_export.py` und `secure_target.py` die Export-Statusdatei und den Exportbericht nun über einen an die geprüfte Verzeichnis-FD gebundenen atomaren Dateiwechsel. Export-Stammordner und `files` werden ebenfalls per geprüfter FD angelegt. Zusätzliche Regressionstests (`test_secure_batch_metadata.py`) simulieren den Austausch des Berichtszielverzeichnisses und Symlinks; CI-Status auf dem letzten Commit kontrollieren.
- **Einlesen bestehender Export-Statusdateien (neu):** Bei physischen Linux-Quellen öffnet `open_regular_input` die vorhandene Manifestdatei jetzt mit `O_RDONLY|O_NOFOLLOW|O_NONBLOCK` relativ zu einem verifizierten Verzeichnisdeskriptor und bestätigt `S_ISREG` am geöffneten Handle. Drei zusätzliche Regressionstests (`test_secure_batch_metadata.py`) prüfen Linkablehnung, einen Zielverzeichniswechsel während des Einlesens und einen tatsächlichen Wiederaufnahme-Durchlauf. **Linux Mint: 6/6 Tests bestanden**, gemeldet am 22.10.2026 (`Ran 6 tests in 0.032s`, `OK`). Alle CI-Prüfungen für Commit `a528cd6c` sind abgeschlossen und sowohl Linux als auch Windows erfolgreich; durch nachfolgende Dokumentationsänderungen können neue CI-Läufe ausgelöst werden.
- **Prüfsummenlesungen beim Stapel-Export (neu):** Die SHA-256-Prüfung vorhandener und neu exportierter Dateien nutzt jetzt für Linux-Blockquellen `open_regular_input` mit geprüfter Elternverzeichnis-FD, `O_NOFOLLOW` und `S_ISREG`. Zwei neue Regressionstests prüfen die Zurückweisung eines Symlinks und das korrekte Hashen einer Datei bei gleichzeitigem Austausch des benannten Elternordners. Linux-CI für Commit `cf1d5851` hat beide Läufe erfolgreich abgeschlossen; die Windows-CI wurde zuletzt als noch laufend gesehen. Tests verwenden nur simulierte Quellgeräte.
- **Linux-Mint-Gegenprobe auf dem neuesten Prüfsummen-Code (22.10.2026):** Der Nutzer hat `python3 -m unittest discover -s tests -p 'test_secure_batch_metadata.py' -v` mit **8/8 erfolgreich abgeschlossenen Tests** bestätigt (`Ran 8 tests in 0.032s`, `OK`). Die beiden zusätzlich bestandenen Tests decken Symlinks bei SHA-256-Lesezugriffen sowie einen während des Hashens ausgetauschten Verzeichnispfad ab. Diese Testreihe nutzt ausschließlich temporäre Dateien und simulierte Blockgeräte. GitHub-Linux- und Windows-CI für den geprüften Code-Commit `cf1d5851` wurden beide erfolgreich abgeschlossen.
- **GUI-Imaging-Test auf Linux Mint erfolgreich (22.10.2026, Nutzerbestätigung):** In der grafischen Oberfläche wurde die reguläre Testquelle `~/Tenshi-Test/testquelle.raw` nach `~/Tenshi-Test/gui-test-20261022.img` kopiert. Der Nutzer bestätigt den anschließenden Bytevergleich per `cmp` als **identisch**. Damit ist die GUI-Image-Erstellung für eine normale RAW-Testdatei auf Linux Mint erfolgreich gegengeprüft. Der separat getestete 8-GiB-GUI-Pause/Fortsetzen-Pfad zeigt dagegen eine reproduzierbare Byteabweichung (Freigabeblocker, siehe oben).
- **GUI-Unterbrechung auf Linux Mint nachgewiesen (22.10.2026):** Bei der neu erstellten 8-GiB-Sparse-Testquelle `~/Tenshi-Test/gui-pause-source-8g.raw` und Ziel `~/Tenshi-Test/gui-pause-copy-8g.img` wurde die Image-Erstellung im GUI-Dialog mit Blockgröße 1 MiB, 0 Wiederholungen und `Sicher anhalten` kontrolliert unterbrochen. Screenshot: **26,5 %**, Status `paused`, etwa **2,1 GiB bearbeitet**, **0 B nicht lesbar**. GUI-Fortsetzung, vollständiger Abschluss und Bytevergleich für **dieses** 8-GiB-Image sind noch offen. Kein Blockgerät wurde bei diesem GUI-Test geöffnet.
- **Bewusst verbleibende Grenzen:** Andere konkurrenzanfällige Operationen (insbesondere verschachtelte Zwischenverzeichnisse, Mount-/Hot-Plug-Wechsel und die Zeitspanne zwischen Verifikation und späterer Verwendung der Ausgabe) gelten nicht als vollständig gelöst. Ein kontrollierter Sicherheitstest auf weiterer Linux-Hardware ist noch ausstehend; keinesfalls wichtige Originaldatenträger hierfür verwenden.

## Direkter USB-Quellenzugriff – Hardwaretest unter Linux Mint (22.10.2026)

- Nutzerbestätigtes **entbehrliches** USB-Testgerät: LITEON L8H-128V2G-HP, ca. 119,2 GiB, während des Tests unter `/dev/sda` identifiziert. Achtung: Gerätenamen sind dynamisch und müssen vor jedem weiteren Test erneut gegen Modell, Transport, Größe und ggf. Seriennummer geprüft werden. Die interne NVMe-SSD ist **keine Testquelle**.
- Partition `/dev/sda1` vor dem Test über `udisksctl unmount -b /dev/sda1` ausgehängt. Nur für `/dev/sda` wurde dem normalen Nutzer per ACL Leserecht ohne Schreibrecht eingeräumt. `test -r` ergab **JA**, `test -w` **NEIN**. Diese ACL ist keine hardwareseitige Schreibsperre und soll nach Abschluss entfernt werden.
- `strace -f -e trace=open,openat,openat2,ioctl` überwachte `open_source('/dev/sda')` nach ausdrücklichem Modell-/USB-Identitätscheck. Es wurden erfolgreich **512 Bytes** gelesen; `reader.writable()` war `False`.
- Im gefilterten Trace zeigten die **drei** Öffnungen von `/dev/sda` nur `O_RDONLY|O_CLOEXEC` bzw. `O_RDONLY|O_NONBLOCK|O_CLOEXEC`, keine schreibenden Öffnungsflags. Dies ist ein **realer Hardware-Nachweis** für diesen konkreten 512-Byte-Quellenzugriff, nicht für alle Programmwege.
- Zusätzlicher Hardware-Lesetest unter Linux Mint vom 22.10.2026: Das bestätigte LITEON-USB-Gerät meldete 128.035.676.160 Bytes und **512 Bytes logische Sektorgröße**. Mit `open_source('/dev/sda')` wurden jeweils 512 Bytes an den Offsets **0, 511, 1031 und 128035675136** gelesen, inklusive ungerader Sektorgrenzen und nahe dem Ende. `quelle.writable()` war `False`; Abschlussmeldung `ALLE LESETESTS ERFOLGREICH`. Quelle war nicht eingehängt; der Test führte keine Schreiboperationen aus.
- Echte physische Quell-/Zielzuordnung am 22.10.2026 überprüft: `ensure_safe_destination('/dev/sda', '/home/torsten/Tenshi-Test/usb-sicherung.img')` wurde nach erneuter LITEON-USB-Modellprüfung erfolgreich ausgeführt. Ausgabe bestätigte `QUELLE UND ZIEL SIND PHYSISCH GETRENNT` und `KEINE DATEI ERSTELLT`. Ziel liegt auf der internen Linux-Systempartition, Quelle auf separater USB-Hardware. Dies ist die Prüfung **einer erlaubten Trennung**, noch kein negativer physischer Test auf demselben Laufwerk.
- **Physische Block-/Partitionszuordnung auf dem LITEON-Testgerät (22.10.2026):** Nach Identitätskontrolle mit `lsblk -bndo SIZE,MODEL,TRAN /dev/sda` wurde `_backing_disks(os.stat('/dev/sda').st_rdev)` mit `_backing_disks(os.stat('/dev/sda1').st_rdev)` verglichen. Beide ergeben denselben physischen sysfs-Datenträgerpfad; Ausgabe `GLEICHER PHYSISCHER DATENTRAEGER ERKANNT`. Dies ist eine **reale Topologieprüfung ohne Lesezugriff auf Rohdaten**, noch kein vollständiger GUI-Export-Abnahmetest. Zusätzlich verweigert `ensure_separate_device` jetzt ausdrücklich `/dev/...`-Blockgeräte und Symlinks darauf als Zielpfade; automatisierte Tests ergänzen dies.
- **Hardware-Negativtest Blockgerät als Ziel (22.10.2026):** Nach Identitätsprüfung von `/dev/sda` (128.035.676.160 Bytes, LITEON, USB) führte `ensure_safe_destination('/dev/sda', '/dev/sda1')` zu `ValueError: Linux-Blockgerät darf niemals als Ausgabeziel verwendet werden.`; ausgegebene Bestätigung: `USB-PARTITION ALS ZIEL KORREKT ABGELEHNT`. Prüfung ohne Dateierstellung und ohne Schreibzugriffe. **Symlink-Alias auf Blockgerät** wurde ebenfalls unter Linux Mint tatsächlich getestet; siehe nachfolgenden Hardwaretest.
- **Hardware-Negativtest symbolischer Link auf Blockgerät (22.10.2026):** Ein temporärer Link `usb-test.img` auf `/dev/sda1` wurde erstellt und mit `ensure_safe_destination('/dev/sda', link)` geprüft. Der Sicherheitscheck verweigerte das Ziel mit `Linux-Blockgerät darf niemals als Ausgabeziel verwendet werden.`; Konsolenausgabe: `SYMLINK ALS ZIEL KORREKT ABGELEHNT` und `TEMPORAERER TESTLINK ENTFERNT`. Weder Blockgerät geöffnet noch Zieldaten geschrieben. Dies bestätigt den statischen Linkfall, **nicht** die Sicherheit gegen Zielpfad-Austausch zwischen Vorprüfung und Schreiben (TOCTOU).
- **Echter USB-Imaging-Test mit Wiederaufnahme:** Unter Linux Mint wurde `create_image('/dev/sda', '~/Tenshi-Test/usb-pausentest.img', block_size=1 MiB, bad_sector_policy='stop', cancel=...)` erfolgreich nach genau **8.388.608 Bytes (8 MiB)** am Prüfpunkt angehalten. Danach wurde mit `resume=True` derselbe Imaging-Vorgang fortgesetzt und bei **16.777.216 Bytes (16 MiB)** erneut kontrolliert pausiert. Beide Durchläufe: `state=paused`, `unreadable_bytes=0`; der byteweise Vergleich der ersten **8 MiB vor** und **16 MiB nach** der Wiederaufnahme gegen `/dev/sda` bestand. Die Testquelle war ausgehängt und für den Benutzer nicht beschreibbar; Ziel lag auf einer anderen physischen Platte. **Kein vollständiges 119-GiB-Abbild; GUI- und Langzeittest offen.**
- **ACL-Rücknahme bestätigt (22.10.2026):** Nach erneuter Geräteidentitätskontrolle wurde die temporäre nutzerspezifische Leseberechtigung von `/dev/sda` per `sudo setfacl -x "u:$(id -un)" /dev/sda` entfernt. Eine anschließende `test -r`-Prüfung ergab **keine Leseberechtigung** (`TESTBERECHTIGUNG ENTFERNT`). Es erfolgten keine Schreibzugriffe auf den Datenträger.
- **Negativer Zugriffstest auf echter USB-Hardware bestanden (22.10.2026):** Nach Entfernung der ACL wurde mit normalem Benutzer `open_source('/dev/sda')` auf dem zuvor identifizierten LITEON-USB-Testdatenträger getestet. Der Zugriff wurde mit `PermissionError` abgelehnt; Konsole meldete `ZUGRIFF KORREKT VERWEIGERT`. Tenshis Fehlermeldung verweist korrekt auf Linux-Geräteberechtigungen oder ein RAW-Image statt auf Windows-Administratorrechte. Kein `sudo` für Tenshi, keine Quelldatenänderung.
- **GUI-Berechtigungstest auf echter Hardware erfolgreich (22.10.2026):** Nach bewusster Auswahl von `/dev/sda` im Cinnamon/X11-Gerätedialog und weiterhin entfernter Geräte-ACL zeigt Tenshi einen sichtbaren **Partitionsanalyse**-Fehlerdialog: `[Errno 13] Linux-Blockgerät kann nicht lesend geöffnet werden`. Der Text verweist auf Linux-Geräteberechtigungen/RAW-Image statt auf erhöhte Rechte. Das fehlende Zugriffsrecht wurde nicht umgangen; GUI-Screenshot bestätigt. Kein Nachweis aller Fehlerfälle.

- Noch offen: GUI-Imaging-Wiederaufnahme an echter Hardware, längere Leselast, echte Hardware-Lese-/USB-Abbruchfehler und weitere negative Quell-/Zielkonfliktfälle (z. B. Zielordner auf der Quellpartition und Zielpfad-Austausch/TOCTOU) auf echter Hardware. Die Originalquellen weiterer Datenträger bleiben unangetastet.

## Ausstehende Pflichtprüfungen auf Linux-Cinnamon/X11

1. Weitere Schrift-/DPI-Skalierungen, alternative Sprachen und Modaldialoge auf echtem Cinnamon/X11 testen; Hauptfenster bei **1024×650** ist bereits visuell geprüft.
2. Vor dem Öffnen eines Testdatenträgers Berechtigungen prüfen. Mit einem entbehrlichen USB-Laufwerk nur lesen, abziehen, erneut anstecken und Fehlermeldungen prüfen.
3. **Teilweise bestanden:** `strace`-Nachweis des LITEON-USB-Quellenzugriffs mit ausschließlich `O_RDONLY`-Öffnungen und erfolgreiche Lesetests unter Cinnamon/Linux; weitere Geräte, IOCTL-Details, längere Last und Fehlerfälle bleiben offen.
4. Linux-Datenträger- und Partitionsgröße, 512/4096-Byte-Sektoren, GPT/MBR, NTFS/ext4/exFAT/Btrfs/XFS mit Referenzabbildern verifizieren. GUI-Laufwerksauswahl an echter Hardware mit fehlenden Rechten, ext4/NTFS und Linux Mint prüfen.
5. Image-Erstellung/Pause/Fortsetzen, Export-Checksums und gespeicherte Sitzungen nach Neustart prüfen; Fehlersimulation (kurze Lesevorgänge, I/O-Fehler, Verbindungsabbruch).
6. **Schutz vor Ziel=Quelle:** Ausgabe auf dieselbe Platte und auf deren andere Partition, via Symlink, LVM, dm-crypt, mdraid und USB-Gerät testen; alle unklaren Zuordnungen müssen blockiert werden.
7. Separate physische Ziellaufwerke, externe USB-HDDs/SSDs, loop-Geräte und verschiedene Mountpoints prüfen. Loop-/virtuelle Geräte werden bei nicht nachweisbarer physischer Abstammung absichtlich gesperrt.
8. Windows-Regressionstests auf echter Windows-Hardware durchführen; Windows-Installer und ZIP bleiben unverändert.

**Freigabestatus:** Entwicklungskandidat, kein verifizierter Linux-Release. Die vollständige Gleichwertigkeit zum Windows-Funktionsumfang, weitere Skalierungen und die Sicherheit für **alle** realen Linux-Blockgerätetypen sind noch nicht bestätigt. Der LITEON-Test hat nur die dokumentierten Teilfälle abgedeckt. Bei beschädigten Originaldatenträgern zunächst keine belastenden Tests durchführen.

## Imaging-Status beim Fortsetzen sicher einlesen (22.10.2026)

- `_load_manifest()` liest die Statusdatei jetzt mit `open_regular_input()` statt einem normalen pfadbasierten `open()`. Auch Journal-Lesezugriffe erhalten im Imaging-Ablauf die ausgewählte Quelle für die Prüfung des geöffneten Elternverzeichnisses.
- Unter Linux bleiben die Lesezugriffe an den geöffneten Verzeichnisdeskriptor gebunden; finale Symlinks und Sonderdateien werden abgewiesen, FIFOs ohne blockierendes Warten geöffnet und anschließend verworfen. Windows verwendet weiterhin den vorhandenen normalen Lesezugriff.
- Vier neue Tests in `tests/test_secure_imaging_metadata.py`: Verzeichnisaustausch bei Statusdatei und Journal, Symlink-Austausch nach Vorprüfung und FIFO-Statusdatei. Beim Austausch des Zielverzeichnisses wird die ursprüngliche Statusdatei gelesen und die Fortsetzung wegen der geänderten Zielzuordnung verweigert.
- Lokale Prüfung in der Entwicklungsumgebung: 20 Sicherheits-/Metadatentests bestanden; 36 Imaging-Tests erfolgreich (3 GUI-Tests übersprungen); 7 Image-Integritätstests bestanden. Gesamtsuite: 510 Tests, 25 Fehler ausschließlich wegen fehlendem X11-Display, 78 übersprungen. Dies ersetzt keinen vollständigen Cinnamon-/Xvfb-Lauf und keine Hardware-Abnahme. Der frühere Linux-Mint-Nachweis mit 506 Tests bezieht sich auf den vorherigen Stand.

## Begrenztes und strukturell geprüftes Imaging-Journal (22.10.2026)

- Journalzeilen werden jetzt bereits beim Lesen auf 32 MiB plus ein Erkennungsbyte begrenzt. Übergroße Einträge werden auch ohne abschließenden Zeilenumbruch abgewiesen; ein kleiner, bei Stromausfall abgerissener letzter Eintrag wird weiterhin ignoriert.
- Ein Prüfpunkt muss ein JSON-Objekt mit nichtnegativem ganzzahligem Fortschritt sein. Listen, null, boolesche Werte und andere ungültige Strukturen führen kontrolliert zu `ImagingError`, auch bei korrekter Prüfsumme.
- Fünf neue Tests in `tests/test_imaging_journal_validation.py`, darunter eine Prüfung der tatsächlich begrenzten `readline()`-Anforderung. Lokal: Imaging-Gruppe 41 Tests erfolgreich (3 GUI-Tests ohne Display übersprungen), 20 Sicherheits-/Metadatentests und 7 Image-Integritätstests bestanden. Windows-Journal-Fallback und Wiederaufnahme sind in der Imaging-Gruppe enthalten; keine Hardwareprüfung.
- GitHub-Prüfung für Vorgänger `9364443`: erster Push-Lauf abgebrochen, nachfolgender Linux-PR-Lauf und Windows-Lauf bei Kontrolle noch `queued`. Kein neuer CI-Erfolg behauptet.

## Blockprüfpunkte vor Wiederaufnahme validieren (22.10.2026)

- Statusdateien müssen für bestätigten Fortschritt gültige erste und letzte Blockprüfpunkte mit exakten Startpositionen/Längen und einer 64-stelligen hexadezimalen SHA-256-Prüfsumme enthalten. Typfalsche, fehlende, negative oder übergroße Angaben werden vor dem schreibenden Öffnen des Images abgewiesen.
- Prüfpunkte ohne bestätigten Fortschritt werden ebenfalls abgewiesen. Reguläre letzte Teilblöcke bleiben zulässig; die vorhandene Pause-/Fortsetzungslogik ist unverändert.
- Vier neue Tests in `tests/test_imaging_checkpoint_validation.py` mit mehreren Fehlerfallvarianten prüfen den Abbruch vor dem Öffnen zum Schreiben, unveränderte Quell-/Zielbytes und erfolgreiche erneute Vollverifikation eines Images mit letztem Teilblock.
- Lokal: Imaging-Testgruppe 45 Tests erfolgreich (3 GUI-Tests ohne Display übersprungen); 20 Sicherheits-/Metadatentests und 7 Image-Integritätstests bestanden. Kompilierung und Diff-Prüfung erfolgreich. Vollständige GUI-/Hardware-Abnahme und aktuelle GitHub-CI-Bestätigung weiterhin ausstehend.

## Konsistente Imaging-Statusdaten vor Schreibzugriff (22.10.2026)

- Die Wiederaufnahme verlangt nun alle später verwendeten Pflichtfelder und einen bekannten Zustand. Abschluss-/Verifikationszustände sind nur bei vollständig bestätigtem Fortschritt zulässig.
- Fehlerbereiche müssen aus echten ganzzahligen Start-/Längenpaaren bestehen, positiv lang, geordnet, überschneidungsfrei und vollständig innerhalb des bestätigten Fortschritts liegen. Der Fehlerzähler muss exakt der Summe dieser Bereiche entsprechen; boolesche Werte gelten nicht als Bytezahlen.
- Fünf ergänzte Regressionstests prüfen fehlende Felder, ungültige Bereiche, widersprüchliche Zähler/Zustände, Wiederaufnahme nach null kopierten Bytes sowie die weiterhin zulässige konsistente Fehlerkarte ohne falsche Bitgenauigkeitsbestätigung. Abgewiesene Metadaten führen zu keinem schreibenden Öffnen des Images.
- Lokal: 50 Imaging-Tests erfolgreich (3 GUI-Tests mangels Display übersprungen), 20 Sicherheits-/Metadatentests und 7 Image-Integritätstests bestanden. Vollständige GUI-/Hardware-Freigabe weiterhin offen. GitHub Linux für Vorgänger `2cce4be` bei Kontrolle `pending`, Windows `queued`.

## Begrenztes Einlesen beschädigter Statusdateien (22.10.2026)

- Die Imaging-Statusdatei wird mit einer begrenzten Leseanforderung (32 MiB plus ein Erkennungsbyte) gelesen. Größere Dateien werden vor JSON-Verarbeitung und vor schreibendem Öffnen des Images abgewiesen.
- Ungültiges, abgeschnittenes oder übermäßig tief verschachteltes JSON wird kontrolliert als `ImagingError` gemeldet; Rekursionstiefenfehler sind auch beim Journal abgefangen.
- Vor dem Fortschrittsvergleich zwischen Basisstatus und Journal wird der Basiswert auf einen nichtnegativen echten Integer geprüft. Typfalsche Werte verursachen keine unkontrollierte Vergleichsausnahme.
- Fünf neue Tests prüfen begrenzte Leseanforderung, Größenlimit, beschädigte/verschachtelte Statusdaten, ungültigen Basisfortschritt mit vorhandenem Journal und verschachtelte Journaldaten. Bestehender Pfadaustausch-Test an die begrenzte JSON-Verarbeitung angepasst.
- Lokal: Imaging-Gruppe 55 Tests erfolgreich (3 GUI-Tests ohne Display übersprungen), 20 Sicherheits-/Metadatentests und 7 Integritätstests bestanden; Kompilierung und Diff-Prüfung erfolgreich. Aktuelle Linux-/Windows-CI bei Kontrolle weiterhin `queued`; vollständige GUI-/Hardware-Abnahme offen.

## Vollständige virtuelle X11-Abnahme und Scan-Callbacks (22.10.2026)

- Virtuelles X11 wurde in der Entwicklungsumgebung bereitgestellt. Der erste vollständige Lauf auf `56ea8d5` führte 529 Tests aus und zeigte zwei reproduzierbare GUI-Fehler: `test_real_readonly_scan_from_double_click` und `test_real_small_image_autoscans_in_background`. Die Worker berechneten ihre Ergebnisse, ihre direkten Tkinter-`after()`-Rückmeldungen wurden in dieser Umgebung jedoch nicht vom GUI-Hauptthread ausgeführt.
- Partitions- und Dateisystemscan übermitteln Fortschritt, Ergebnisse, Fehler und Abschluss jetzt ausschließlich über eine Python-Queue. Ein im Hauptthread registrierter 20-ms-Poll führt bis zu 100 Rückmeldungen je Durchlauf aus. Worker dieser Scanpfade rufen dafür kein Tcl/Tk mehr auf; die vorhandene Generationserkennung bleibt erhalten.
- Drei zusätzliche Tests in `tests/test_scan_callback_queue.py` prüfen Reihenfolge und Ausführung im abarbeitenden Hauptthread, keine Tk-Timerregistrierung im Worker, Schließen des Fensters und begrenzte Verarbeitung bei vielen Fortschrittsmeldungen.
- **Abschließende vollständige Suite unter virtuellem X11 (1024×650): 532 Tests in 18,327 s, `OK`, Exitcode 0, keine Überspringungen.** Isolierte Einstellungen und Logs. Beide zuvor fehlgeschlagenen GUI-Integrationstests bestehen. Zusätzlich besteht der unveränderte 1024×650-Layoutprüfcode aus `.github/workflows/linux-check.yml`.
- Kompilierung und Diff-Prüfung bestanden. Dies ist ein lokaler automatisierter X11-Nachweis; reale Cinnamon-/Hardware- und Windows-Abnahme bleiben gesondert. GitHub-CI noch nicht grün bestätigt: Bei Kontrolle warten neueste Linux-/Windows-Läufe, während 20 ältere Läufe als `in_progress` gemeldet werden.

## Partitions-Metadatenprüfung über Hauptthread-Queue (22.10.2026)

- Auch `check_selected_partition()` stellt Erfolg und Fehler jetzt in die bestehende Callback-Queue. Der Worker ruft für diese Rückmeldungen kein Tkinter-`after()` mehr auf. Die vorhandene Prüfung auf veraltete Quellen/Partitionslisten bleibt bestehen.
- Neuer GUI-Integrationstest `tests/test_partition_details_worker.py`: simulierte Metadatenprüfung mit Erfolgs- und Fehlerfall; Rückmeldungen müssen im Hauptthread ankommen, die reguläre Testquelle bleibt bytegleich.
- **Vollständige Suite unter virtuellem X11 bei 1024×650: 533 Tests in 18,190 s, `OK`, Exitcode 0, keine Überspringungen.** Isolierte Einstellungen/Logs. Dies ist keine reale Hardware- oder Windows-Freigabe.
- GitHub-Prüfung des Vorgängers `51858ae`: Linux `pending`, Windows `queued` bei Kontrolle; kein GitHub-CI-Erfolg bestätigt.

## Sitzungs-Worker liefern Ergebnisse im Hauptthread (22.10.2026)

- `save_analysis_session()` und `load_analysis_session()` übermitteln Erfolg/Fehler jetzt über die vorhandene Hauptthread-Callback-Queue statt über Tkinter-`after()` aus dem Worker. Quelldatenprüfung, veraltete Ergebnisse und gespeicherte Metadaten werden weiterhin wie bisher behandelt.
- Drei neue GUI-Integrationstests in `tests/test_session_worker_gui.py`: reale FAT32-Analysesitzung speichern und wieder laden, Speicherfehler sowie Ladefehler im Worker. Geprüft werden wieder freigegebene Bedienelemente, unveränderte Quelldatei, wiederhergestellter Dateibaum und Erhalt der bestehenden Analyse beim Ladefehler.
- **Vollständige Suite unter virtuellem X11 bei 1024×650: 536 Tests in 21,607 s, `OK`, Exitcode 0, keine Überspringungen.** Kompilierung und Diff-Prüfung bestanden. GitHub-CI für Vorgänger `ae1cef4` bei Kontrolle Linux `pending`, Windows `queued`; reale Hardware-/Windows-Abnahme weiterhin offen.

## Dateivorschau ohne Tkinter-Aufrufe im Worker (22.10.2026)

- `preview_entry()` übermittelt gelesene Daten und Lesefehler über die bestehende Hauptthread-Callback-Queue. Ein inzwischen geschlossenes Vorschaufenster verwirft verspätete Ergebnisse weiterhin über die vorhandene Existenzprüfung.
- Drei neue GUI-Tests in `tests/test_preview_worker_gui.py`: echte README-Datei aus synthetischem FAT32-Image als Text anzeigen, Lesefehler sichtbar machen und Vorschaufenster während einer verzögerten Leseoperation schließen. Quellen bleiben bytegleich; verspätete Rückmeldung verursacht keinen GUI-Callbackfehler.
- **Vollständige Suite bei virtuellem X11 1024×650 mit frisch angelegter Testkonfiguration: 539 Tests in 18,300 s, `OK`, Exitcode 0, keine Überspringungen.** Kompilierung und Diff-Prüfung bestanden.
- Testgrenze: Wiederverwendung einer zuvor von Sprachtests veränderten Konfigurationsdatei verursachte Beschriftungsfehler in älteren deutschabhängigen Tests. Für reproduzierbare Gesamtprüfungen eine neue isolierte Testkonfiguration verwenden. GitHub-CI bei Kontrolle weiterhin Linux `pending` und Windows `queued`; reale Hardware-/Windows-Abnahme offen.

## Wiederholbare GUI-Gesamtprüfung ohne Sprachreste (22.10.2026)

- Ursache der sprachabhängigen Fehler bei wiederholten Testläufen eingegrenzt: `SessionGuiTests` wechselte alle sechs Sprachen und schrieb dabei in die äußere Test-/Benutzerkonfiguration. Diese Testklasse erhält jetzt eine eigene temporäre Einstellungsdatei; Fenster werden vor Rücknahme der Umgebungsüberschreibung geschlossen.
- `NoticeGuiTests` verwendet statt einer fest benannten `/tmp`-Datei ebenfalls eine eigene temporäre Konfiguration. Das vermeidet Rückstände und ist auch unter Windows portabel.
- **Zwei vollständige unmittelbar aufeinanderfolgende Läufe mit derselben äußeren Einstellungsdatei unter virtuellem X11 1024×650 bestanden: jeweils 539 Tests, `OK`, Exitcode 0, keine Überspringungen (18,528 s / 18,099 s).** Sprachwechsel-/Persistenztests bleiben enthalten. Keine Änderung am Sprachverhalten der Anwendung.
- Kompilierung und Diff-Prüfung bestanden. GitHub-CI bei Kontrolle weiterhin Linux `pending`, Windows `queued`; reale Hardware-/Windows-Abnahme offen.

## Gezielte 8-GiB-GUI-Abnahme auf Wegwerfdateien (22.10.2026)

Getesteter Code: `ea2075a` unter virtuellem X11 bei 1024×650 in der Entwicklungsumgebung. Keine Originaldateien und keine Blockgeräte geöffnet; neue reguläre Quelldateien und neue Zieldateien in temporären Verzeichnissen. Steuerung über den echten Imaging-Dialog einschließlich Pause-Button, Fortsetzungsbestätigung und Abschlussmeldung; Dialogantworten automatisiert. Blockgröße 1 MiB, null Leseversuche, automatische vollständige Integritätsprüfung.

| Prüfung | Lauf 1 | Lauf 2 |
| --- | --- | --- |
| Quellgröße | 8.589.934.592 Bytes | 8.589.934.592 Bytes |
| Quelldaten | Sparse-Datei mit Nullbytes | Sparse-Datei mit eindeutigen Datenmarkierungen in jedem MiB und an Offset 1.625.391.250 |
| Medienfehlerstrategie | Nullersatz mit Protokollierung | Sicher anhalten (`stop`) |
| Bestätigtes Präfix bei GUI-Pause ab ca. 26,5 % | 2.311.061.504 Bytes | 2.298.478.592 Bytes |
| Vollständiges Präfix vor Fortsetzung (`cmp -n`) | bytegleich | bytegleich |
| GUI-Abschluss nach Fortsetzung | `complete`, `verified` | `complete`, `verified` |
| Vollständiger unabhängiger `cmp` nach Abschluss | bytegleich | bytegleich |
| Unlesbare Bytes / Fehlerbereiche | 0 / leer | 0 / leer |
| Quellgröße und Änderungszeit unverändert | ja | ja |

SHA-256 jeweils für die vollständige Quelle und das vollständige Ergebnis identisch:

- Lauf 1: `ebfb4ef19ae410f190327b5ebd312711263bc7579970e87d9c1e2d84e06b3c25`
- Lauf 2: `9d4ff82ae41a0157d7db1ba2dc63efbd3d9b22d69b738a65ef6cfc7c6019ca9b`

**Beide gezielten Tests bestanden.** Die Quelldaten der beiden Läufe unterscheiden sich bewusst; deshalb unterscheiden sich ihre Hashwerte. Temporäre Testdateien nach Ende entfernt. Keine Änderung am Programmcode erforderlich. Diese Ergebnisse ergänzen die bereits bestandenen zweimal 539 Tests, ersetzen aber keine reale Cinnamon-/Hardware-/Windows-Abnahme.

**Issue #3 bleibt offen und die Linux-Freigabesperre bestehen:** Der ursprüngliche Bytefehler wurde mit dem aktuellen Code auf neuen Dateien hier nicht reproduziert. Die ursprüngliche Ursache und der Zeitpunkt der Veränderung im aufbewahrten fehlerhaften Image sind damit nicht erklärt. Neueste GitHub-Läufe bei Kontrolle weiter Linux `pending`, Windows `queued`.

## Lesende Diagnose des aufbewahrten Fehlerimages (22.10.2026)

- Neues CLI `diagnose_image_integrity.py`: reguläre Dateien nur lesend öffnen, keine Reparatur, keine Berichts-/Image-Datei schreiben. Statische Symlinks/Sonderdateien werden vor Öffnen abgewiesen; der geöffnete Deskriptor wird nochmals auf regulären Dateityp geprüft. Keine Rohdaten von Geräten lesen.
- Vollvergleich oder begrenztes Fenster, standardmäßig zwei Durchläufe, maximal fünf. Ausgabe als JSON: Hashwerte je Durchlauf, Byte-/Blockabweichungen, erste/letzte Position, höchstens 32 Bytebeispiele samt `Offset % 8`, Größen/Metadaten und Wiederholbarkeit. Byteoffsets sind 0-basiert. Ein Fenstervergleich bescheinigt ausschließlich den gewählten Bereich; unveränderte Metadaten sind kein Beweis unveränderter Daten zwischen Messzeitpunkten. Wiederholtes Lesen kann aus dem Betriebssystemcache bedient werden.
- Sechs Tests prüfen Bytegleichheit, das ursprüngliche `08/10`-Muster, Größenunterschiede/Fenster, nur lesende Öffnungsflags, geänderte Daten zwischen Durchläufen sowie CLI-Exitcodes und Sonderdateiablehnung.
- **Vollständige Suite unter virtuellem X11 1024×650: 545 Tests in 19,498 s, `OK`, Exitcode 0, keine Überspringungen.** Kompilierung und Diff-Prüfung bestanden.

Nächste Untersuchung auf dem Rechner mit den erhaltenen Original-Testdateien, aus dem aktualisierten Tenshi-Projektordner:

```bash
python3 diagnose_image_integrity.py   "$HOME/Tenshi-Test/gui-pause-source-8g.raw"   "$HOME/Tenshi-Test/gui-pause-copy-8g.img"   --offset 1625292800 --length 1048576 --passes 2
```

Der Aufruf untersucht zweimal den betroffenen 1-MiB-Block. Exitcode 0: im gewählten Bereich gleich, wiederholbar, Metadaten unverändert; 1: Unterschiede oder instabile Beobachtung; 2: Aufruf-/Lesefehler. Der erwartete Unterschied im ursprünglichen defekten Image darf daher Exitcode 1 ergeben. Originale bleiben unangetastet; das Werkzeug wurde hier nur auf synthetischen Testdateien geprüft. Die vorhandenen Dateien auf dem Nutzerrechner sind von dieser Entwicklungsumgebung aus nicht zugänglich. Issue #3 und Freigabesperre bleiben offen; CI bei Kontrolle Linux `pending`, Windows `queued`.
