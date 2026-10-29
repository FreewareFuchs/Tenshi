# Tenshi 3.0.9 – stabile Pakete in Vorbereitung

- Vor dem ersten Schreibzugriff geplante Inhalte, zusätzlich benötigte Dateibytes und verfügbaren Platz anzeigen; vollständige Dateien eines gespeicherten Auftrags zur erneuten Prüfung berücksichtigen.
- Vor knappem Speicherplatz warnen. Erkannte FAT/FAT32-Dateigrößenüberschreitungen vor dem Anlegen des Exportordners melden; unbekannte VM-/Netzwerkgrenzen ausdrücklich offenlassen.
- Zielprüfung läuft im Hintergrund. Ablehnen und Abbrechen während dieser Prüfung verändern den Zielordner nicht; eine abgelehnte Wiederaufnahme bleibt fortsetzbar. Sechs Oberflächensprachen und Offline-Hilfe sind berücksichtigt.
- Das Exportfortschrittsfenster bleibt über dem Hauptfenster und wird beim Öffnen daran zentriert. Ein erneuter Klick auf Stapel-Export zeigt einen laufenden oder pausierten Auftrag wieder an, ohne einen weiteren Export zu starten.

Die Funktionen sind im Testpaket bestätigt. Endgültige Installer-/Portable-/DEB-Pakete, Versionsabnahme und Veröffentlichung folgen getrennt.
[Versionshinweise und Prüfstand](RELEASE_NOTES_3.0.9.md).

# Tenshi 3.0.8 – stabil veröffentlicht (29.10.2026)

- Export mit Pause/Fortsetzen im selben Auftrag; Teil-Datei und laufende SHA256-Berechnung bleiben während der Pause erhalten.
- Nach kontrolliertem Abbrechen direkt fortsetzen: bisherige Quelle, Auswahl und Zielordner werden übernommen, fertige Dateien geprüft und unvollständige Dateien neu kopiert. Geänderte Quellen oder fehlende Exportordner erzeugen keinen neuen Auftrag stillschweigend.
- Nach jeder bestätigten Datei eine `.sha256`; nach vollständig erfolgreichem Export eine Sammeldatei. Eigene Einzeldateien und der leere Zwischenordner werden erst danach entfernt, fremde Dateien bleiben erhalten.
- Klar angeordnete Aktionen für Bericht, Speichern, Pause/Fortsetzen, Zielordner, Abbrechen und Schließen. Gemischte Rasterfelder an Dateigrenzen sind erläutert.
- Hauptfenster wartet beim bestätigten Beenden auf die kontrollierte Unterbrechung laufender Schreibvorgänge und meldet Abschlussfehler.
- Offline-Hilfe für den aktuellen Export-/Imaging-Ablauf in sechs Sprachen überarbeitet; Kontakt für Fragen und Verbesserungsvorschläge unter „Über Tenshi“ ergänzt.
- Funktionen, endgültige Installer-/Portable-/DEB-Paketstarts, Versionsanzeigen und aktualisierte Hilfe sind manuell bestätigt. GitHub, signierte APT-Quelle und Website sind veröffentlicht; alle 25 öffentlichen Abschlussvergleiche sind erfolgreich.

[Versionshinweise und Paketabnahme](RELEASE_NOTES_3.0.8.md).

# Tenshi 3.0.7 – stabil veröffentlicht (28.10.2026)

- Separate, wieder aufrufbare Export- und Imaging-Fenster mit Bereichsraster und Berichtaktionen. Schließen der Ansicht beendet den Auftrag nicht.
- SHA256 als Textstatus beim Export und je Datei im Ergebnisbericht. Bericht speichern beginnt im zugehörigen Zielordner und überschreibt keine vorhandenen Dateien.
- Verständlichere Exportfehler; Imagebereiche mit Nullersatz und noch nicht bestandene Vollvergleiche bleiben ausdrücklich erkennbar.
- Die Dateisystemanalyse behält ihre bisherige Fortschrittsanzeige im Hauptfenster.
- Linux-Dateilisten in Öffnen-, Speichern- und Ordnerdialogen folgen der aktiven Hell-/Dunkel-Darstellung, auch nach Markierungs- und Ordnerwechseln.
- Funktionen, Paketstarts und Versionsanzeigen sowie Linux-Dialogfarben sind manuell abgenommen. GitHub, Website und signierte APT-Quelle sind öffentlich geprüft; alle 25 Abschlussvergleiche sind erfolgreich.

[Release v3.0.7](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.7) · [Änderungen und bestätigter Prüfstand](RELEASE_NOTES_3.0.7.md).

# Tenshi 3.0.6 – stabil veröffentlicht

- Sun-Valley-Farben mit System/Hell/Dunkel, gemeinsame Quellenauswahl und schnellere Fensteranpassung.
- Windows-Volumes einschließlich C: lassen sich bis zum ermittelten Partitionsende über den vorhandenen Read-only-Handle lesen.
- Release-Prüfsummen verwenden `.sha256`; bestehende ältere Archive bleiben unverändert.

[GitHub-Release v3.0.6](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.6).

# Tenshi 3.0.5 – damaliger Vorbereitungsstand (inzwischen veröffentlicht)

- Linux: Die vorgelagerte Quell-/Zielprüfung lehnt leere Gerätezuordnungen ab. Mitglieder zusammengesetzter Geräte werden einmal eingelesen; fehlende Informationen führen zum Abbruch. Die bestehende Prüfung am geöffneten Ausgabeordner bleibt erhalten.
- Ein gemeinsames Werkzeug prüft öffentliche Website-, Download- und APT-Dateien gegen den lokalen geprüften Stand.
- Zusätzliche Tests für Linux-Fenstergrößen, sechs Sprachen, Gerätewechsel und Imaging mit simulierten 4-KiB-Sektoren. Die installierte experimentelle Flatpak-Oberfläche wird ebenfalls geprüft.
- Vorgesehen: Windows-Installer und Portable-ZIP 3.0.5 sowie `tenshi-recovery 3.0.5-1`. Die veröffentlichten Downloads bleiben bis zur Paketfreigabe bei 3.0.4.

[Änderungen und ausstehende Paketabnahme](RELEASE_NOTES_3.0.5.md).

# Tenshi 3.0.4 – stabil veröffentlicht (27.10.2026)

- Stapel-Export: Die SHA256-Zielprüfung zeigt einen eigenen Lesefortschritt. Prüfbytes werden nicht als Kopierbytes oder Kopierrate gezählt.
- Vollständig geschriebene Exporte mit gespeichertem Prüfstand lassen sich nach einem Prüfungsabbruch erneut bestätigen, ohne sie nochmals zu kopieren. Geänderte oder unbekannte Dateien bleiben gesperrt.
- Windows: Beim erneuten Öffnen einer Image-Zieldatei werden Dateiidentität und Ausschluss einer Quellalias-Datei vor dem Schreiben geprüft. Ausgabe-Elternverzeichnisse werden während des Schreibens gehalten; Junctions, Symlinks und andere Reparse Points werden abgelehnt.
- Build- und Installer-Versionen werden zentral abgeglichen. Lokale Werkzeuge bereiten Website-Kataloge aus geprüften Release-Bundles vor und prüfen statische Website-Releasefelder.
- Veröffentlicht: Windows-Installer und Portable-ZIP 3.0.4 sowie Linux-Paket `tenshi-recovery 3.0.4-1`. Die finalen Pakete sind manuell abgenommen; die öffentlichen Downloads, die signierte APT-Quelle und die Website in sechs Sprachen sind geprüft. Das Upgrade über APT ist durch den Anwender bestätigt.

Details und bestätigter Prüfstand: [Versionshinweise 3.0.4](RELEASE_NOTES_3.0.4.md).

# Tenshi 3.0.3 – stabil veröffentlicht (26.10.2026)

[GitHub-Release v3.0.3](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.3)

- Die SHA256-Berechnung beim Stapel-Export und bei der Prüfung vorhandener Exporte lässt sich abbrechen. Vollständig geschriebene Dateien bleiben erhalten; unvollständige Prüfungen erhalten keinen Erfolgsstatus. Unbestätigte vorhandene Dateien werden weiterhin nicht überschrieben.
- Windows-Installer und Portable-ZIP verwenden Version 3.0.3. Linux verwendet Paketname und Startbefehl `tenshi-recovery`, Paketversion `3.0.3-1`. Diese sortiert nach `3.0.2-2`.
- Die signierte FreewareFuchs-APT-Quelle bietet das geprüfte Paket an; die [Einrichtung](docs/APT_REPOSITORY.md) bleibt unverändert.


Details: [Versionshinweise und Pakettests](RELEASE_NOTES_3.0.3.md).

# Tenshi 3.0.2 – stabil veröffentlicht (26.10.2026)

- Stabile Build-Kennung `stable`, Versionsanzeige ohne Beta-Zusatz und Tag `v3.0.2` ergänzt. Entwicklungsstände bleiben als `+dev` erkennbar.
- DEB-Version `3.0.2-1` sortiert nach den bisherigen Beta-Paketen. Windows-Installer und Portable-ZIP erhalten Dateinamen ohne Beta-Suffix.
- Gemeinsamer Release-Workflow prüft weiterhin Commit, sauberen Quellstand, Paketidentitäten und SHA-256-Werte; Veröffentlichung bleibt ein separater Schritt.
- Der geprüfte Beta.6-Funktionsstand bleibt erhalten. Der automatische Start am Ende des Windows-Installers nutzt die Windows-Shell für erforderliche UAC-Abfragen (Fehler 740 korrigiert).
- [Veröffentlichtes Release](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.2), Commit `abfd4c973a253c2a8571d238e15a0fb77b013dec`. [Versionshinweise und Teststand](RELEASE_NOTES_3.0.2.md).

# Tenshi 3.0.2 Beta.4 – veröffentlicht (23.10.2026)

- FAT32: Bei deaktivierter Spiegelung wird die aktive FAT für Datei- und Verzeichnisketten berücksichtigt. Dadurch werden gleich große, aber inhaltlich falsche Exporte aus veralteten inaktiven FAT-Ketten vermieden.
- Ungültige aktive FAT-Nummern werden abgewiesen; Regressionstests für Export, Vorschau und Verzeichnisfortsetzungen ergänzt.
- Linux-Paketversion auf `3.0.2~beta.4-1` erhöht. Details: [Beta.4-Versionshinweise](RELEASE_NOTES_3.0.2_BETA4.md).

# Linux-Unterstützung – historischer Entwicklungsstand (23.10.2026)

- Linux-Blockgeräte, lesender Quellzugriff und geprüfte Quell-/Zieltrennung integriert.
- Imaging-Vollvergleich, abgesicherte Statusdateien und verbesserte Export-Wiederaufnahme.
- Kompakte Oberfläche, Suche, Sitzungen und Themewechsel korrigiert.
- Echte ext4-/Btrfs-/XFS-Tests und automatische Linux-Prüfung auf main ergänzt.
- 569 lokale Tests sowie Linux-/Windows-CI erfolgreich; Einzelheiten und Grenzen in [vorläufigen Versionshinweisen](RELEASE_NOTES_LINUX_BETA.md).

# Tenshi 3.0.2 – Quellenwechsel und Exportnamen (2026-10-18)

- Neue Stapel-Exportordner heißen `Tenshi_Export_<Prüfsignatur>` (bisher `RecoveryDesk_Export_*`). Bereits angelegte alte Aufträge werden beim Fortsetzen weiterhin unter ihrem bisherigen Namen gefunden und anhand ihrer Statusdatei geprüft.
- Bei Auswahl eines Image, physischen Datenträgers oder logischen Windows-Laufwerks: automatischer Wechsel zum Register „Partitionen“ und Start der Schnellanalyse (64 MiB, nur lesend). Bei manuell eingetragener Quelle genügt die Eingabetaste.
- Ein laufender Partitionsscan erhält beim Quellenwechsel keine Möglichkeit, veraltete Ergebnisse zu veröffentlichen. Die letzte Quellenwahl wird nach Abschluss des älteren Scans automatisch untersucht.
- Das Laden einer validierten Analysesitzung stellt weiterhin die zwischengespeicherten Ergebnisse wieder her, statt neu zu scannen.
- Neue GUI-/Kompatibilitätstests und Versionsangleichung für Windows-Build, Installer, portable ZIP und CI.

# Tenshi 3.0.1 – Windows GUI-Timer-Hotfix (2026-10-18)

- Geplante Tcl/Tk-Callbacks werden beim Schließen des Hauptfensters vollständig abgemeldet.
- Noch aktive Timer in Imaging-, Export-Vorabprüfungs- und Dateiprüfungsfenstern werden beim Schließen des jeweiligen Dialogs abgemeldet.
- Ein später Rückruf aus einem Hintergrundthread darf nach dem Schließen des Hauptfensters keinen neuen GUI-Timer erzeugen.
- Regressionstests für Suchlauf-Abbruch, Root-Timer und Dialog-Timer hinzugefügt.
- Versionen für Windows-EXE, Installer, portable ZIP-Datei und CI auf 3.0.1 abgestimmt.
- Datenrettungs- und Imaging-Funktionen sind unverändert; Quelldatenträger bleiben schreibgeschützt.

# Tenshi 3.0.0 – Offline-Hilfe und Benutzerführung (2026-10-18)

- Neues lokal eingebautes und durchsuchbares Hilfefenster mit neun Kapiteln.
- Tastenkürzel F1 für Hilfe zum jeweils geöffneten Hauptregister; ? Hilfe oben rechts.
- Vollständige Inhalte in Deutsch, Englisch, Spanisch, vereinfachtem Chinesisch, Russisch und Japanisch.
- Sprachwechsel und Hell-/Dunkelmodus aktualisieren ein geöffnetes Hilfefenster.
- Hilfe öffnet keine Laufwerke und verändert weder Quelle noch Exportziele.
- Smoke-Test kontrolliert jetzt auch die vorhandene Offline-Hilfe aller sechs Sprachen ohne GUI.
- Windows-Build, Installer, portable Datei und CI-Vorlage auf 3.0.0 abgeglichen.
- HILFE_3.0.0.md und WINDOWS_ABNAHME_3.0.0.md hinzugefügt.
- Vollständige Windows-Hardwareabnahme weiter ausstehend; keine vorschnelle Freigabeempfehlung.

# Tenshi 2.9.0 – Windows-/USB-Stabilitaet (2026-10-18)

- Sektorausgerichtete Windows-Rohdaten-Lesefunktionen auf kleine Metadatenanforderungen optimiert: keine grossen, unnoetigen Read-ahead-Blöcke; grosse Leseauftraege maximal 256 KiB je Zugriff.
- Unerwartet kurze und leere Leseantworten von physischen Geraeten fuehren zu einem klaren Abbruch statt irrefuehrender Daten/Nullfuellung.
- USB-Abziehen/Geraet nicht bereit, Berechtigungs-/Sharingfehler und nachgewiesene Medienfehler getrennt klassifiziert; Lesepfade bleiben schreibgeschuetzt.
- `check_windows.bat` / `windows_preflight.py`: nicht invasive Voraussetzungen-Pruefung ohne physischen Laufwerkszugriff, als Windows-CI-Schritt verfuegbar.
- Automatisierte Regressionstests fuer diese Fehlerfaelle und fuer die geteilte Quell-/Zieldatentraeger-Sicherheit.
- EXE-, Installer-, portable Versionsangaben und CI-Vorlage auf 2.9.0 synchronisiert (einschliesslich zuvor veraltetem numerischem VERSIONINFO-Tupel).
- Alle vorherigen Oberflaechenfunktionen und Datenrettungsmodule beibehalten.

# Tenshi 2.8.0 – Metadatenabgleich für Wiederherstellungsfunde

- Gelöschte NTFS-Dateien werden gegen den belegten Clusterraum der **vorhandenen** erkannten NTFS-Dateieinträge abgeglichen.
- Eindeutige Clusterüberlappungen mit vorhandenen Dateien werden in der Vorabprüfung als „Gesperrt“ erklärt und beim Batch-Export übersprungen.
- Interne Clusterüberlappungen desselben NTFS-Datenstroms werden als widersprüchliche Zuordnung gesperrt.
- Sortierte und zusammengeführte Clusterintervalle: Aufbereitung einmal je Vorabprüfung bzw. Stapel-Export; Abfragen mit binärer Suche.
- Zusätzliche Warntexte und Bewertungszustände in sechs Sprachen.
- Negatives Prüfergebnis bedeutet ausdrücklich **nicht**, dass gelöschte Dateiinhalte unversehrt sind.
- 15 neue Tests für Überlappungen, Grenzen, Sparse-Bereiche, Hardlink-Wiederholungen, gesperrten Export und Quellschreibschutz.
- Windows-Build, Installer, portable Ausgabe, GitHub-Windows-Workflow und Versionsressourcen auf 2.8.0 synchronisiert.

# Tenshi 2.7.0 – sicheres Imaging

- Einstellbare zusätzliche Medien-Leseversuche (0–3) auf minimaler Leseeinheit; kein Wiederholen großer Datenbereiche.
- Medienfehler-Behandlung: mit dokumentierten Nullbytes auffüllen oder sicher beim letzten Prüfpunkt stoppen.
- Unterbrechungsprüfung während langwieriger fehlgeschlagener Lesevorgänge; unvollständiger Block wird nie bestätigt.
- Erweiterter Fehlerstellen-Bericht mit gesondertem Wiederholungszähler und Textdatei-Ausgabe.
- Imaging-Statusdateien um Strategie, Einstellungen und Wiederholungszähler erweitert; bestehende 2.6.0-Prüfpunkte bleiben ladbar.
- Neue Tests für Abbruch, Wiederaufnahme, defekte Sektoren, Windows-Zugriffsfehler und Übersetzungen.
- Windows EXE, Installer, portable Ausgabe und Workflow auf Version 2.7.0 synchronisiert.

# Tenshi 2.6.0 – neue Analysesitzungen

- Gespeicherte Analyseindizes und Partitionslisten, Wiederladen nach Image-Fingerabdruckprüfung.
- Sicheres, komprimiertes Sitzungsformat ohne Pickle; gesonderte GUI-Aktionen mit sechs Übersetzungen.
- Zusätzliche Tests für Wiederladen, Quelle geändert, Archive manipuliert, Export danach und GUI-Abmessungen.
- Quellcode, Build-Tools und Versionsressourcen auf 2.6.0 aktualisiert.
- Einschränkungen siehe `RELEASE_NOTES_2.6.0.md`.

# Änderungen in Tenshi 2.5.1

- Doppelklick auf eine erkannte Partitionszeile übernimmt den Byte-Offset, öffnet „Dateien & Ordner“ und startet die schreibgeschützte Dateisystemanalyse automatisch.
- Doppelklick auf Tabellenkopf/Leerraum löst keine Aktion aus; genau die angeklickte Zeile wird übernommen.
- Laufende Analysen werden nicht durch eine weitere Doppelklickaktion überschrieben; veraltete Partitionsdaten nach Quellenwechsel werden abgewiesen.
- Unbekannte Dateisysteme werden nicht automatisch gescannt; Bedienhinweis in allen sechs Sprachen.
- Manuelle „Partition übernehmen“-Funktion bleibt erhalten, ohne Autostart des Scans.
- Alle Release-Werkzeuge und EXE-Metadaten auf Version 2.5.1 abgestimmt; neue UI- und Integrationstests.

---

# Änderungen in Tenshi 2.5.0

- Windows-Veröffentlichungswerkzeuge: EXE mit Versionsinformationen, Installer 2.5.0, optionales portables ZIP.
- Portables ZIP enthält nur Tenshi.exe, Startanleitung und SHA-256-Prüfsumme; nach dem Erstellen wird das Ergebnis geprüft.
- Build-Skripte mit nachvollziehbaren Ausgaben, fehlerfreiem Versionsnamen und nicht-interaktivem Modus für Windows CI.
- Nicht-destruktiver `--smoke-test` zur Prüfung gebündelter Assets ohne Datenträgerzugriffe oder Fenster.
- Neuer Windows-CI-Workflow für vollständige Tests, EXE-Startprüfung, Version und beide Ausgabepakete; auf Windows noch nicht ausgeführt.
- 13 neue Release-Regressionstests, insgesamt 335 bestanden unter Linux/xvfb.
- Weiterhin experimentelle Datenrettung; keine Änderungen am Nur-Lese-Quellzugriff oder den Datenrettungsmodulen.

---

# Änderungen in Tenshi 2.4.0

- Umstellbarer Hell-/Dunkelmodus über „◐ Darstellung“ oben rechts.
- Dauerhafte Fenstergeometrie, anpassbare/speicherbare Spaltenbreiten und Ordnerbaum-Aufteilung.
- Zusätzliche horizontale Bildlaufleiste für breite Partitionsübersichten.
- Sichtbare, sprachabhängige Zusammenfassung der Partitionsplausibilität und Warnungen.
- Tenshi-Logo bleibt auch bei dunklem Hintergrund durch eine kontrastreiche Fläche lesbar.
- Persönliche Anzeige-Einstellungen werden zusammen mit der bestehenden Sprachwahl gespeichert, ohne Datenrettungsquellen oder Dateiinhalte in der Konfiguration abzulegen.
- 322 automatisierte Tests, einschließlich neuer UI-/Persistenztests, bestanden unter Linux/xvfb.
- Keine Änderungen am Quellschreibschutz, Imaging und Stapel-Export.

---

# Änderungen in Tenshi 2.3.0

- Erweiterte, schreibgeschützte Export-Vorabprüfung direkt in der Wiederherstellungswarteschlange.
- Bewertet gesamte Auswahl einschließlich Unterordnern vor dem Export nach Metadatenzustand.
- Identifiziert unvollständige residente und nicht-residente NTFS-Datenzuordnungen sowie unsichere Eltern-/Ordnerreferenzen.
- Zeigt Bereit / Warnung / Gesperrt / Ordner und eine Zusammenfassung sowie einen speicherbaren Prüfbericht.
- Verhindert im Stapel-Export die Ausgabe nachweislich inkonsistenter NTFS-Dateistreams; andere Dateien werden weiter exportiert.
- Beibehaltung von zwei Hauptregistern, grüner Export-Schaltfläche, Logo, sechs Sprachen, Quell-Nur-Lese-Modus und Imaging.
- Elf neue automatisierte Tests; insgesamt 316 bestanden.
- Keine Behauptung vollständiger Wiederherstellung aus beschädigten Originaldaten; Quellhardware nicht getestet.
