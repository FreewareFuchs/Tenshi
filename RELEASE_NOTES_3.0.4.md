# Tenshi 3.0.4 – Release-Kandidat

Noch nicht veröffentlicht. Der Quellstand bereitet ein Wartungsupdate für Windows
und Linux Mint 22.x vor. Diese Datei ist keine Bestätigung eines fertigen Builds
oder einer manuellen Paketabnahme. Veröffentlichte Downloads bleiben bei 3.0.3.

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

## Geplante Pakete

- Windows-Installer: `Tenshi_Setup_3.0.4_Win64.exe`
- Windows Portable: `Tenshi_Portable_3.0.4_Win64.zip`
- Linux: `tenshi-recovery_3.0.4-1_all.deb`; Paketname und Startbefehl `tenshi-recovery`

Linux-Ziel: Mint 22.x (amd64), Python ≥ 3.11, Tkinter und util-linux.
Paketrevision 1 bleibt unabhängig von der Programmversion bestehen.
Endgültiger Commit, Dateigrößen und SHA256-Werte werden erst aus dem erfolgreich
zusammengestellten Release-Bundle übernommen; hier werden keine Werte vorweggenommen.

## Noch offene Abnahme vor Veröffentlichung

1. Linux-/Windows-CI für den endgültigen Kandidaten-Commit erfolgreich abschließen.
2. Mit `stable` ein gemeinsames Release-Bundle genau dieses sauberen Commits bauen;
   Manifest, drei Pakete, eingebettete Build-Kennungen und Prüfsummen abgleichen.
3. Die finalen Pakete unter Linux und Windows prüfen: Start, Versionsanzeige 3.0.4,
   Image einlesen und Export; Windows-Installer und Portable-Ausgabe getrennt prüfen.
4. SHA256-Fortschritt und Abbruch während der Zielprüfung prüfen. Danach mit derselben
   Quelle/Auswahl/demselben Ziel fortsetzen: vollständige Datei ohne Neukopieren bestätigen.
   Bei geändertem Inhalt muss die Bestätigung scheitern. Nur entbehrliche Testdateien verwenden.
5. Unter Windows in einem gewöhnlichen Ausgabeordner Image und Export prüfen; ein
   Junction-/Symlink-Ziel muss ohne externe Dateierstellung abgelehnt werden.
6. Linux-Paket installieren und den Versionswechsel von `tenshi-recovery 3.0.3-1`
   auf `3.0.4-1` prüfen. Ein lokaler DEB-Upgrade-Test bestätigt noch kein Upgrade über
   die später veröffentlichte öffentliche APT-Quelle.
7. Erst nach Freigabe veröffentlichen; signierte APT-Quelle und Website getrennt
   aktualisieren, vorher Backups anlegen und öffentliche Links/Prüfsummen prüfen.

Die automatisierten Prüfungen der vorhergehenden PRs gelten für deren Quellstände.
Sie ersetzen keine manuelle Bestätigung der noch zu bauenden 3.0.4-Pakete.

Quellen werden ausschließlich lesend geöffnet. Exporte und Images auf einem anderen
physischen Datenträger speichern. Lesen kann beschädigte Hardware zusätzlich belasten;
eine erfolgreiche oder vollständige Wiederherstellung ist nicht garantiert.
Windows-Installer und EXE sind weiterhin nicht digital signiert.
