# Tenshi 3.0.4 – stabil veröffentlicht

Veröffentlicht am 27.10.2026 für Windows und Linux Mint 22.x.
[GitHub-Release v3.0.4](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.4).
Die finalen Pakete wurden vom Anwender manuell getestet und bestätigt.

## Änderungen gegenüber 3.0.3

### Stapel-Export und Prüfung fortsetzen

Während der SHA256-Zielprüfung zeigt die Warteschlange die gelesenen Bytes und
einen eigenen Prozentwert. Diese Prüfbytes erhöhen weder die Kopiermenge noch
die Kopierrate. Die Kopier-Restzeit wird nicht als Dauer der Zielprüfung ausgegeben.

Neue Exporte berechnen bereits beim Schreiben eine SHA256 über den kopierten
Datenstrom. Wird die anschließende Zielprüfung abgebrochen oder schlägt sie fehl,
bleibt die vollständige Datei erhalten. Mit passendem gespeichertem Prüfstand
kann „Stapel-Export / fortsetzen“ die Datei erneut prüfen, ohne sie neu zu kopieren
oder zu überschreiben. Gleiche Dateigröße allein genügt nicht; geänderte Dateien,
fremde Dateien und ältere Abbrüche ohne diesen Nachweis bleiben gesperrt.
Ein erneuter Abbruch erhält den Prüfstand. Ein Prozessabsturz vor dessen Speicherung
kann weiterhin eine Datei ohne automatisch nutzbaren Bestätigungsnachweis hinterlassen.

Die Prüfung vergleicht das Ziel mit dem kopierten Datenstrom. Sie bestätigt weder
die ursprüngliche Integrität gelöschter Inhalte noch eine korrekte Dateizuordnung.
Für diesen Vergleich erfolgt kein erneutes vollständiges Lesen der Quelle.

### Windows-Ausgabedateien

Vor dem erneuten schreibenden Öffnen einer Image-Zieldatei werden die tatsächlich
geöffnete Dateiidentität und der Ausschluss einer mit der Quelle identischen Datei
geprüft. Eine dazwischen ausgetauschte Zieldatei wird vor dem Schreiben abgelehnt.

Beim Öffnen von Image- und Exportdateien hält Tenshi die Ausgabe-Elternverzeichnisse
bis zum Schließen des Schreibhandles fest. Junctions, symbolische Links und andere
Reparse Points werden abgelehnt; Ausgabeordner müssen gewöhnliche Ordner ohne solche
Umleitungen sein. Die physische Quell-/Zieltrennung wird bei Gerätequellen erneut
geprüft, während die Verzeichnisse gehalten werden.

Der Schutz betrifft `open_regular_output` während der Lebensdauer des Schreibhandles.
Status-/Berichtsdateien, Aufräumvorgänge nach dem Schließen und spätere Öffnungen
sind damit nicht pauschal abgesichert. Er ist keine Sicherheitsgrenze gegen
Administratoren, geänderte Laufwerkszuordnungen, Mounts oder Dateisystemtreiber.

### Build und Website-Vorbereitung

Build-/Installer-/CI-Versionsfelder werden aus der Programmversion abgeglichen.
`prepare_website_catalog.py` übernimmt Release-Daten aus einem zuvor geprüften Bundle
und prüft dessen drei Pakete erneut gegen Manifest und Prüfsummenliste.
`check_website_release.py` kontrolliert die statischen Releasefelder der zwölf
lokalen Programm-/Anleitungsseiten. Beide Werkzeuge veröffentlichen nichts.

## Veröffentlichte Pakete

- Windows-Installer: `Tenshi_Setup_3.0.4_Win64.exe`
- Windows Portable: `Tenshi_Portable_3.0.4_Win64.zip`
- Linux: `tenshi-recovery_3.0.4-1_all.deb`; Paketname und Startbefehl `tenshi-recovery`

Linux-Ziel: Mint 22.x (amd64), Python ≥ 3.11, Tkinter und util-linux.
Paketrevision 1 bleibt unabhängig von der Programmversion bestehen.

## Build, Prüfsummen und bestätigte Abnahme

Der erfolgreiche [gemeinsame Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40466932499)
verwendet Commit `b1caea8b40f7b29d401e85a3e51a2916fc5f9e0e` und Kennung `stable`.
Tag `v3.0.4` verweist auf diesen Commit. Linux- und Windows-Prüfungen sowie die
Zusammenstellung des Release-Bundles sind erfolgreich abgeschlossen.

| Datei | Bytes | SHA256 |
| --- | ---: | --- |
| `Tenshi_Setup_3.0.4_Win64.exe` | 17047965 | `b098c252ae1ef431d2faeaa465296e71d12c8fce70830f1bbc08f476600cbc31` |
| `Tenshi_Portable_3.0.4_Win64.zip` | 15138973 | `231d37a831efd8d92e9a670fab5847005f052ffd184e01fdc3180e5697e185a8` |
| `tenshi-recovery_3.0.4-1_all.deb` | 744178 | `cbb4b862996781b95fb7a36e41228fdc9ae9a6a2758602628d2f55b624fad86e` |

- Die Pakete wurden gegen Release-Manifest und `SHA256SUMS.txt` abgeglichen.
  Installer, Portable-Paket und Linux-DEB sind vom Anwender manuell abgenommen.
  Der lokale Windows-Smoke-Test ist erfolgreich; die Versionsanzeige lautet
  `Tenshi 3.0.4 (b1caea8b40)`.
- Alle vier GitHub-Release-Dateien wurden öffentlich heruntergeladen und auf
  Byteanzahl und SHA256 geprüft. Die auf der Website verlinkten Downloads wurden
  nach dem Website-Upload erneut vollständig geprüft.
- Die bestehende APT-Verwaltung wurde gesichert und das neue DEB mit dem bisherigen
  Archivschlüssel veröffentlicht. GPG hat die Signatur in der Mint-VM bestätigt;
  die signierten Indexprüfsummen und das DEB wurden abgeglichen. Alle neun
  veröffentlichten APT-Dateien stimmen bytegenau mit den geprüften Dateien überein.
  Schlüssel und Paket 3.0.3 sind unverändert; ältere Pool-Dateien bleiben erhalten.
- `sudo apt update` lädt die Quelle in Mint ohne Signaturfehler.
  `apt-cache policy tenshi-recovery` zeigt installierte Version und Kandidat
  `3.0.4-1`. Das Upgrade über APT ist zusätzlich vom Anwender bestätigt;
  die genaue zuvor installierte Paketversion wurde dabei nicht angegeben.
- Die zwölf Programm-/Anleitungsseiten in sechs Sprachen und `programme/software.json`
  wurden nach dem Upload gegen die vorbereiteten Dateien geprüft. Alle 13 Dateien
  stimmen überein; ältere Katalogeinträge bleiben erhalten.

Die Paketabnahme ist eine Anwenderbestätigung. Sie belegt keine neue Einzelprüfung
jeder Hardware- oder Fehlerkonstellation. Die Windows-/Linux-Schutztests gelten für
ihren dokumentierten Build; weitere Dateisystem- und Hardwarevarianten benötigen
eigene Prüfungen. Insbesondere ist kein gesonderter Paketwechsel von `3.0.2-2`
auf diese Version dokumentiert.

Quellen werden ausschließlich lesend geöffnet. Exporte und Images auf einem anderen
physischen Datenträger speichern. Lesen kann beschädigte Hardware zusätzlich belasten;
eine erfolgreiche oder vollständige Wiederherstellung ist nicht garantiert.
Windows-Installer und EXE sind weiterhin nicht digital signiert.
