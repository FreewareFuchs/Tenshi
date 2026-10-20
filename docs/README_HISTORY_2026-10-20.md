# Historisches README – Stand vor der Überarbeitung am 20. Oktober 2026

Dieses Archiv bewahrt die bisherigen Entwicklungsdetails. Versions- und Testangaben sind historische Aussagen; den zusammengefassten Status enthält das aktuelle [README](../README.md).

# Tenshi 3.0.2 – Datenrettung für Windows

**Vorgesehene Open-Source-Lizenz: MIT.** Die Datei [`LICENSE`](LICENSE) nennt `FreewareFuchs` als Entwickler-Pseudonym. Vor der öffentlichen Freigabe sind die Rechte an Logos, Assets und Drittkomponenten sowie die Berechtigung zur Lizenzierung zu klären. Siehe [`OPEN\_SOURCE\_START\_HIER.md`](OPEN_SOURCE_START_HIER.md) und [`THIRD\_PARTY\_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Neu in Tenshi 3.0.2 – Quellenwechsel und Exportnamen

* Neue Exporte heißen `Tenshi\_Export\_<ID>` und behalten den Unterordner `files`. Alte `RecoveryDesk\_Export\_<ID>` werden bei identischer Quelle/Auswahl anhand des bisherigen Status korrekt fortgesetzt. Alte Exportordner werden nicht umbenannt.
* Nach Auswahl eines Images, physischen Datenträgers oder Windows-Laufwerks schaltet die Oberfläche automatisch zu **Partitionen** und führt die schreibgeschützte Schnellanalyse (bis zu 64 MiB) aus. Eine direkt eingetippte Quelle kann mit Eingabetaste übernommen werden.
* Beim Laden einer gespeicherten Analysesitzung wird der verifizierte Index wiederhergestellt, ohne ihn sofort durch einen neuen Scan zu ersetzen.
* Bei Quellenwechsel während einer laufenden Partitionsanalyse wird nur die zuletzt gewählte neue Quelle anschließend analysiert; alte Ergebnisse werden verworfen.

## Seit Tenshi 3.0.1 – GUI-Timer-Bereinigung

* `after`-Rückrufe beim Schließen von Tenshi und zeitgesteuerten Dialogen werden sauber abgemeldet, sodass keine verwaisten Tkinter-Kommandos ausgeführt werden.
* Zusätzliche GUI-Regressionstests; die Datenträger- und Exportlogik bleibt unverändert.
* Einzelheiten in `RELEASE\_NOTES\_3.0.1.md`.

Tenshi ist ein **experimentelles** Windows-Datenrettungsprogramm mit schreibgeschütztem Quellzugriff, Partitionsanalyse, Datei-/Ordnernavigation und Wiederherstellung in separate Zielverzeichnisse. Der aktuelle Schwerpunkt liegt auf der integrierten Benutzerhilfe und der Vorbereitung einer überprüfbaren Windows-Abnahme. Die Software ist weiterhin experimentell.

## Seit Tenshi 3.0.0 – Integrierte Hilfe und geführte Bedienung

* **Neue Offline-Hilfe:** Über **„? Hilfe“** rechts oben oder **F1** erscheint ein eigenständiges, durchsuchbares Hilfefenster. Es gibt **neun Themen**: Erste Schritte, Partitionen, Dateien \& Ordner, Imaging, Stapel-Export, Analysesitzungen, Sicherheit, Fehlerdiagnose und Über Tenshi. Die Hilfe ist auch ohne Internetverbindung verfügbar.
* **Kontextorientiertes F1:** Die F1-Taste öffnet automatisch das passende Kapitel zu dem gerade ausgewählten Hauptregister. Im Hilfefenster kann auf Wunsch wieder zum entsprechenden Register gewechselt werden. Es werden durch die Hilfe **keine Laufwerke geöffnet oder gelesen**.
* **Alle sechs Sprachen:** Die Hilfekapitel und die Hilfebedienung sind auf Deutsch, Englisch, Spanisch, vereinfachtem Chinesisch, Russisch und Japanisch vorhanden. Bei Änderung der Sprache wird ein geöffnetes Hilfefenster direkt aktualisiert.
* **Dokumentierte Grenzen:** Die Hilfe erläutert Teilrettbarkeit gelöschter Dateien, die eingeschränkten Btrfs-/XFS-Funktionen, die Stichprobenprüfung bei Analysesitzungen, beschädigte Medien und die fehlende Garantie der Dateiintegrität.
* **Abnahmeunterlagen:** `HILFE\_3.0.0.md` und `WINDOWS\_ABNAHME\_3.0.0.md` beschreiben die Bedienung und eine **nicht destruktive** Windows-Prüfung. Windows-Praxistests wurden für Tenshi 3.0.1 vom Anwender durchgeführt; siehe Status unten. Tests mit tatsächlich beschädigten Laufwerken stehen weiterhin aus.
* **Erhaltene Funktionen:** Tenshi-Logo, zwei Hauptregister, der grüne Stapel-Export, sechs Sprachen, Hell-/Dunkelmodus, Partitions-Doppelklick, Analysesitzungen und Imaging mit Wiederaufnahme.

**Wichtiger Status:** Die Versionsnummer 3.0.2 bezeichnet den Abschluss dieses Funktionsschritts, nicht eine zertifizierte oder bereits auf echter beschädigter Hardware freigegebene Version. Für Version 3.0.1 wurden vom Anwender Windows-Tests von Installer/Deinstallation, physischem Laufwerk, USB-Zugriff, 9 exportierten Prüffällen mit SHA-256-Abgleich und bitgenauem 4-MiB-Imaging gemeldet. Die geänderte Version 3.0.2 wurde noch nicht auf Windows getestet; reale defekte Laufwerke wurden nicht geprüft.

## Neu in Tenshi 2.9.0 – Windows-/USB-Stabilitaet und Vorabpruefung

* **Kurze USB-Leseantworten:** Erhaelt Tenshi von einem physischen Windows-Geraet weniger Bytes als den angeforderten sektorausgerichteten Leseauftrag, wird dies **als Fehler behandelt**, nicht als Dateiende oder bestaetigter defekter Sektor. Eine laufende Image-Erstellung stoppt ohne unbestätigte Datenbereiche mit Nullen zu ersetzen. Die letzte bestaetigte Fortschrittsdatei bleibt erhalten.
* **USB-Verbindungsabbrueche und Zugriffssperren:** Windows-Fehlercodes 21, 31, 55, 433 und 1167 erhalten eine aussagekraeftige Meldung zur nicht erreichbaren Quelle; Codes 5, 32 und 33 weisen auf Zugriffs-/Freigabeprobleme hin. Alle diese Faelle brechen das Imaging sicher ab. Nachgewiesene CRC-/Medienfehler 23/1117 werden weiterhin nach den eingestellten Imaging-Regeln behandelt.
* **Schonenderes Vorauslesen:** Kleine Datenbank-/Dateisystem-Metadatenabfragen lesen normalerweise nur einen logischen 4-KiB-Bereich (mindestens einen Sektor), statt pauschal 64 KiB vorauszulesen. Grosse Auftraege werden in sektorausgerichtete Teilauftraege von maximal 256 KiB zerlegt. Dies reduziert unnoetige Zugriffe auf benachbarte fehlerhafte Bereiche, beweist aber keine bessere Hardware-Recovery.
* **`check\_windows.bat`:** Ein neuer, nicht invasiver Windows-Vorabtest prueft Python-Architektur, Windows-Umgebung und Schreiben einer **gewoehnlichen** temporaeren Datei. Ausgabe: `tenshi-windows-check.log`. Er oeffnet **keine** physischen Datentraeger, erfasst keine Seriennummern und bestaetigt daher ausdruecklich **nicht**, dass ein bestimmtes USB-Laufwerk gelesen werden kann. Das Skript ist auch in der Windows-CI-Vorlage verankert.
* **Regressionstests:** USB-Verbindungsabbrueche, kurze Leseantworten, Zugriffsverweigerung, echte simulierte Medienfehler, minimale sektorweise Leseauftraege, sichere Exportziel-Zuordnung und Windows-Vorabtest.

**Grenzen:** Alle neuen Windows-Fehlerfaelle wurden mit synthetischen bzw. simulierten Geraeten getestet. Die Windows-CI-Vorlage wurde hier nicht auf echter Windows-Hardware ausgefuehrt. Physische Datentraeger werden nur lesend geoeffnet; Datenrettung auf beschaedigter Hardware kann diese zusaetzlich belasten. Sicherungsziele muessen auf einem getrennten physischen Datentraeger liegen. Vor Verteilung auf Freeware-Seiten reale Windows-Abnahmetests durchfuehren.

## Neu in Tenshi 2.8.0 – Sicherere Wiederherstellungsbewertung

* **Gelöschte NTFS-Dateien:** Tenshi vergleicht die physischen Clusterzuordnungen (LCNs) eines gelöschten NTFS-Datenstroms mit den im eingelesenen MFT-Index **noch vorhandenen Dateien**. Ist eine Überlappung nachweisbar, erscheint in **„Export prüfen“** der Zustand **„Gesperrt“** mit Begründung. Auch der tatsächliche **Stapel-Export überspringt** diesen Löschfund, statt die Daten einer anderen vorhandenen Datei als Originalinhalt auszugeben.
* **Widersprüchliche Datenläufe:** Überlappende physische Clusterbereiche innerhalb desselben NTFS-Datenstroms werden als Metadatenfehler klassifiziert. Ihr Export wird vorsorglich gesperrt.
* **Schnelle, begrenzte Prüfung:** Vorhandene Clusteransprüche werden einmal je Auswahl zu sortierten, zusammengeführten Intervallen aufbereitet. Abfragen einzelner Dateibereiche erfolgen per binärer Suche; die maximale Zahl analysierter Intervalle ist begrenzt. Eine erneute Vollauslesung des Datenträgers ist hierfür nicht notwendig.
* **Sechs Oberflächensprachen:** Die neuen Warnungen und die Zustände der Vorabprüfung sind für Deutsch, Englisch, Spanisch, Chinesisch (vereinfacht), Russisch und Japanisch übersetzt.
* **Bestehende Funktionen:** Partitions-Doppelklick, speicherbare Analysesitzungen, Imaging mit Wiederaufnahme, Hell-/Dunkelmodus und grüner Stapel-Export bleiben unverändert nutzbar.

**Wichtige Grenze:** Eine fehlende Überlappung bedeutet **nicht**, dass gelöschte Daten unversehrt sind. Der Scan kann unvollständig sein; bereits wieder freigegebene oder anderweitig belegte Cluster können in der Dateiliste fehlen. Die neue Prüfung ist ein **positiver Widerspruchsnachweis** anhand vorhandener Metadaten, keine Erfolgsprognose. Sie gilt nur für die unterstützten unkomprimierten NTFS-Datenzuordnungen; andere Dateisysteme behalten die bisherigen Bewertungen. Keine Originalprüfsummen, keine vollständige Integritätskontrolle und keine Garantie einer erfolgreichen Wiederherstellung. Am sichersten zuerst ein Image erstellen und nur in ein anderes physisches Ziel exportieren.

## Neu in Tenshi 2.7.0 – Imaging mit einstellbarer Medienfehlerbehandlung

* Im Dialog **„Image erstellen / fortsetzen“** können **0–3 zusätzliche Versuche** für einen tatsächlich fehlerhaften Sektorbereich eingestellt werden. Standardwert 0: keine zusätzlichen Zugriffe auf problematische Stellen. Es wird nur auf der kleinsten fehlgeschlagenen Leseeinheit erneut versucht, nicht auf großen bereits gesplitteten Blöcken. Zwischen Versuchen liegen 250 ms Wartezeit.
* Wahlweise **„Nullen + protokollieren“** (bisheriges Verhalten, **Datenlücken!**) oder **„Sicher anhalten“** (stoppt beim ersten bestätigten endgültigen Medien-Lesefehler ohne den aktuellen Block zu übernehmen). Zugriffsverweigerungen, Geräteverlust, ungültige Leseaufträge oder zu kurze Antworten physischer Laufwerke führen unabhängig von dieser Wahl zum Abbruch ohne Nullfüllung.
* Der Schalter **„Fehlerstellen-Bericht“** zeigt nach einer erfolgreichen oder pausierten Image-Erstellung Quellbyteoffset, Länge, Anzahl der Fehlerbereiche und tatsächlich durchgeführte zusätzliche Leseversuche. Der Bericht kann als neue Textdatei gespeichert werden, bereits vorhandene Dateien werden nicht überschrieben. Der Bericht nennt Fehlstellen, keine geretteten Inhalte.
* Beim **Unterbrechen während eines Leseversuchs** werden nur abgeschlossene, mit `fsync` bestätigte Blöcke übernommen. Ein unvollständiger Block wird verworfen; die vorhandene Statusdatei bleibt für das Fortsetzen gültig.
* Einstellungen bei einer Fortsetzung gelten **nur für noch nicht bestätigte Datenbereiche**. Frühere Nullfüllungen werden nicht nachträglich neu gelesen, und die Fortschritts-Datei wird nicht als vollständige kryptografische Prüfung des gesamten Images missverstanden.
* **Warnung:** Jeder zusätzliche Leseversuch belastet ein beschädigtes physisches Medium. Bei verdächtigen Geräuschen, sich verschlechternden Fehlern oder mechanischem Defekt nicht mit Wiederholungen experimentieren; schonendere Spezialwerkzeuge bzw. professionelle Datenrettung verwenden.
* Das Quelllaufwerk wird weiterhin **ausschließlich lesend** geöffnet, geschrieben wird nur in Image und Statusdateien. Der Archiv- und Dateiexport bleibt unverändert.

## Neu in Tenshi 2.6.0 – Analysesitzungen

Über **„Analysesitzung“** in der oberen Quellwerkzeugleiste lassen sich **„Sitzung speichern“** und **„Sitzung laden“** aufrufen. Nachdem du eine Partition oder das Dateisystem untersucht hast, speichert Tenshi die bisherige Partitionsliste, die Verzeichnisbeziehungen und die notwendigen Dateisystem-Metadaten in einer komprimierten Datei mit der Endung `.tenshi-session`. Die Dateiinhalte werden dabei nicht als gerettete Kopien gesichert. Nach einem Neustart kannst du diese Datei öffnen und im Browser weitermachen, ohne die gesamte MFT bzw. die Ordnerstruktur erneut einzulesen. Die zuvor ausgewählte Datei/der konkrete Ordner wird nicht als aktive Markierung rekonstruiert; Tenshi öffnet zunächst die Dateisystemwurzel.

**Sicherheitsprüfung:** Beim Laden öffnet Tenshi das zugehörige Image nur lesend. Dateigröße, Änderungszeit (beim ursprünglichen Pfad), Stichproben-Hashes an verschiedenen Stellen und der Dateisystem-Bootbereich werden geprüft. Passt etwas nicht, wird die Sitzung **nicht übernommen**; das Image muss neu analysiert werden. Fehlt der alte Image-Pfad, kann eine identische Image-Datei an einem neuen Pfad ausgewählt werden. Die Stichproben sind **keine vollständige Hashprüfung der gesamten Festplatte** und können Änderungen außerhalb der geprüften Bereiche nicht erkennen; bei Zweifel neu analysieren. Beim eigentlichen Export bleiben die bisherigen Prüfungen und Überschreibschutzregeln aktiv.

**Grenzen:** Sitzungen stehen zunächst ausschließlich für **reguläre Image-Dateien** zur Verfügung, nicht für aktive physische Datenträger, USB-Laufwerke oder eingebundene Laufwerksbuchstaben. Dies vermeidet gefährliche Verwechslungen mit dynamisch veränderlichen Geräten. Die Sitzungsdatei enthält analysierte **Dateinamen, Verzeichnisstrukturen, Offsets und den absoluten Quellpfad**; behandle sie deshalb vertraulich. Sitzungsdateien sind **nicht verschlüsselt oder digital signiert**. Unbekannte, beschädigte und übergroße Sitzungsdateien werden abgewiesen; keine Python-Pickle-Deserialisierung. Für eine sehr große Analyse kann die Speicherung zusätzlichen Arbeitsspeicher und freien Festplattenspeicher benötigen. Die neue Sitzungsfunktion ersetzt kein Image, keine Sicherung von Dateiinhalten und keine Integritätsprüfung geretteter Dateien.

**Windows:** `build\_windows.bat` baut `dist\\Tenshi.exe`; `run\_tests.bat` führt separat die automatischen Tests aus. Für eine portable ZIP `build\_portable.bat`, für einen Installer mit Inno Setup 6.3+ `build\_installer.bat` starten. Diese Schritte benötigen eine Windows-Umgebung und sind dort praktisch zu prüfen.

## Neu in Tenshi 2.5.1 – Partition per Doppelklick öffnen

* Im Hauptregister **„Partitionen“** doppelklickst du auf eine erkannte Partitionszeile. Tenshi übernimmt den Byte-Offset, wechselt zu **„Dateien \& Ordner“** und startet unmittelbar denselben schreibgeschützten Hintergrundscan wie die Schaltfläche **„Dateisystem einlesen“**.
* Unterstützt werden NTFS, FAT32, exFAT, ext2/3/4 sowie die eingeschränkten Btrfs-/XFS-Browserfunktionen. Bei unbekannten Dateisystemen folgt ein Hinweis statt eines irreführenden Scans.
* Doppelklicks auf Überschriften oder Leerraum werden ignoriert. Bei laufendem Scan oder veralteter Partitionsliste wird kein weiterer Scan begonnen.
* **„Partition übernehmen“** bleibt unverändert verfügbar, um den Offset zu setzen, ohne sofort zu scannen.
* Der neue Bedienhinweis ist in allen sechs Sprachen übersetzt. Die Quelle wird nie beschrieben.
* Diese Funktion wurde in Version 2.5.1 eingeführt und ist in 3.0.2 weiterhin enthalten. Eine Windows-EXE muss unter Windows durch `build\_windows.bat` erzeugt werden.

## Neu in Tenshi 2.5.0 – Windows-Veröffentlichung

**Drei Ausgaben aus demselben Quellcode:** Die aktuelle Version 3.0.2 erzeugt mit `build\_windows.bat` `dist\\Tenshi.exe` mit Dateiversion `3.0.2.0`. `build\_portable.bat` erstellt `portable\_output\\Tenshi\_Portable\_3.0.2\_Win64.zip` (SHA-256 der enthaltenen EXE). Mit **Inno Setup 6.3+** erstellt `build\_installer.bat` `installer\_output\\Tenshi\_Setup\_3.0.2.exe`. Für die reguläre Ausführung sind keine Administratorrechte nötig; direkter physischer Laufwerkszugriff kann sie erfordern.

**Eingebauter Starttest:** `Tenshi.exe --smoke-test` prüft gebündelte Assets und wesentliche Python-Module ohne Fenster oder Laufwerkszugriffe; dies ersetzt keinen Hardware- oder Datenrettungstest. Die ZIP-Datei enthält **keine** EXE, bis du sie unter Windows gebaut hast. Installer und fertige EXE sind in diesem Quellpaket nicht enthalten.

**Portable-Grenze:** „Portable“ bedeutet *ohne Installer*. Einstellungen unter `%APPDATA%\\Tenshi` und Fehlerlogs unter `%LOCALAPPDATA%\\Tenshi\\Logs` werden weiterhin im Benutzerprofil gespeichert. Das Setup und die EXE sind **nicht digital signiert**. Für die Build- und Prüfschritte gibt es eine GitHub-Actions-Vorlage unter `.github/workflows/windows-check.yml`; deren Ausführung ist noch nicht bestätigt.

Die bestehenden GUI-Funktionen (zwei Register, Logo, sechs Sprachen, Dunkelmodus, gespeicherte Fensteraufteilung und grüner Stapel-Export) bleiben erhalten. Ausführliche Hinweise stehen in `RELEASE\_NOTES\_2.5.0.md`.

## Neu in Tenshi 2.4.0 – Oberfläche und persönliche Darstellung

* **Hell-/Dunkelmodus:** Oben rechts über **„◐ Darstellung“** zwischen **Hell** und **Dunkel** wechseln. Die Auswahl wird sofort übernommen und beim nächsten Start wiederhergestellt. Die grüne Schaltfläche **„Stapel-Export / fortsetzen“** bleibt in beiden Modi grün.
* **Fenstergröße speichern:** Tenshi merkt sich die Größe und Position des Hauptfensters. Wenn ein zuvor genutzter Monitor nicht mehr verfügbar ist, wird eine unerreichbare gespeicherte Fensterposition zurückgesetzt.
* **Ordnerbaum-Breite:** Die Breite der linken Ordnerstruktur wird beim nächsten Start wiederhergestellt; bei einer neuen Installation beträgt sie etwa 38 % des Browserbereichs. Die Trennlinie bleibt frei verschiebbar.
* **Tabellen anpassen:** Durch Ziehen der Spaltengrenzen kannst du **Dateiliste und Partitionsübersicht** anpassen. Die Spaltenbreiten bleiben nach einem Neustart erhalten. Breite Tabellen lassen sich horizontal scrollen.
* **Partitionsfunde schneller beurteilen:** Unter der Partitionsübersicht erscheinen zusammenfassende Anzahlen nach Plausibilität und auffälligen Funden. Diese Bewertungen beziehen sich nur auf Metadaten, **nicht** auf die tatsächliche Rettbarkeit.
* **Sechs Sprachen:** Die Übersetzungen für die neuen Bedienelemente sind auf Deutsch, Englisch, Spanisch, Chinesisch (vereinfacht), Russisch und Japanisch vorhanden.
* **Datenschutz:** In `%APPDATA%\\Tenshi\\settings.json` (je nach Umgebung) werden nur Anzeige-Einstellungen und Sprache gespeichert, keine Dateinamen oder Datenträgerinhalte. Die Einstellungen können durch Schließen von Tenshi und Entfernen dieser Konfigurationsdatei zurückgesetzt werden. Export- und Imaging-Statusdateien bleiben davon unberührt.

**Hinweis:** Der Dunkelmodus gestaltet die Tenshi-eigenen Oberflächenelemente um. Manche systemeigenen Windows-Dateiauswahldialoge behalten ihre Windows-Farben. Dateien und Quellgeräte werden durch die Darstellungseinstellungen nicht verändert.

## Neu in Tenshi 2.3.0 – Export-Vorabprüfung und Metadatenkontrolle

* **Auswahl prüfen:** Im Register **„Dateien \& Ordner“**, in der sichtbaren Wiederherstellungswarteschlange, befindet sich jetzt die Schaltfläche **„Export prüfen“**. Markiere rechts eine oder mehrere Dateien/Ordner und klicke sie an. Tenshi untersucht dieselbe rekursive Dateiauswahl und dieselben relativen Exportpfade, die auch der Stapel-Export verwendet.
* **Einzelbewertung:** Die Vorabprüfung unterscheidet **Bereit** (Metadaten plausibel, Inhalt ungeprüft), **Warnung** (z. B. gelöscht oder verwaist), **Gesperrt** (z. B. fehlender Stream oder inkonsistente NTFS-Clusterzuordnung) sowie **Ordner**.
* **Zusätzliche NTFS-Prüfungen:** Bei residenten Daten wird die Metadatenlänge abgeglichen; bei nicht-residenten Daten werden Clusterbereich, Zuordnungsumfang und initialisierte Länge kontrolliert, soweit die MFT-Informationen dies erlauben.
* **Verwaiste Ordnerbeziehungen:** Fehlende Elternverzeichnisse, zyklische Referenzen und widersprüchliche NTFS-Record-Generationen werden als Warnung aufgeführt. Die tatsächlichen ursprünglichen Pfade können bei beschädigten Metadaten nicht immer rekonstruiert werden.
* **Bericht speichern:** Der Prüfbericht enthält pro geplantem Eintrag den relativen Exportpfad und die Hinweise. Vorhandene Berichtsdateien werden nicht überschrieben; die Sicherheit des Ziels wird vor dem Schreiben geprüft.
* **Stapel-Export-Härtung:** Bei erkannten, eindeutig inkonsistenten NTFS-Datenstrukturen wird der betreffende Export **übersprungen**, statt eine möglicherweise unvollständige Datei als erfolgreich zu protokollieren. Die anderen Dateien des Stapels werden weiterhin abgearbeitet.
* **Ohne zusätzliche Medienlast:** Die Vorabprüfung liest nur die bereits erfassten Metadaten des Dateisystemindexes. Sie führt keine erneuten Voll-Leseversuche auf dem Quelldatenträger durch; die vorhandene Einzeldatenprüfung über „Datei prüfen“ bleibt separat verfügbar.

**Wichtig:** Die Vorabprüfung verifiziert nicht den Inhalt gegen eine bekannte Originaldatei. Auch als „Bereit“ gekennzeichnete Dateien können beschädigt oder bereits überschrieben sein. Wiederherstellung nur auf ein anderes physisches Laufwerk, bevorzugt aus einem vorab erstellten Image.

## Seitennavigation (seit 2.2.0) – Große Datei- und Ordnerlisten

* **Seitennavigation:** Bei großen Datei- oder Suchergebnislisten zeigt Tenshi pro Seite höchstens **750 Einträge** an. Du kannst mit **„Vorherige Seite“** und **„Nächste Seite“** navigieren. Die Auswahl mit Strg+A betrifft **nur die aktuell angezeigte Seite**; die gesamte Datenmenge bleibt im Dateisystemindex für die Suche verfügbar.
* **Flüssigere Suche:** Bei umfangreichen Indizes wird die Dateinamen- und Erweiterungssuche in kleinen Portionen ausgeführt. Das Hauptfenster kann zwischendurch weiter reagieren. Eine neue Suche oder ein Ordnerwechsel verwirft ein noch laufendes Suchergebnis.
* **Hintergrundaufbereitung:** Pfade und Warnungszuordnungen werden nach einem Scan im Hintergrund vorbereitet. Bei einem Quellenwechsel werden veraltete Scanergebnisse nicht mehr angezeigt.
* **Schnellere Metadatensuche:** Suchkriterien werden nur einmal pro Suchlauf vorbereitet, statt für jeden Dateieintrag wiederholt geparst.
* **Sechs Sprachen:** Auch die Seitennavigation ist übersetzt; die Seitenanzeige passt sich beim Sprachwechsel an.
* **Bewusste Grenzen:** Die komplette Metadatenliste ist weiterhin im Arbeitsspeicher; für extrem große Dateisysteme ist noch keine speicherbasierte Datenbankindizierung implementiert. Die eigentliche sektorweise Lese- und Scanrate wurde nicht pauschal erhöht. Die Seitenaufteilung begrenzt die Anzahl der Tk-Tabellenzeilen, nicht die Größe des zugrunde liegenden Dateisystemindexes.

## Installation / Windows-EXE erstellen

1. Python 3.11 oder neuer (64 Bit) installieren. Python muss über den Windows-Befehl `py -3` erreichbar sein.
2. Das Projekt in einen neuen Ordner entpacken.
3. `build\_windows.bat` ausführen. Das Skript erstellt die EXE und protokolliert Baufehler in `tenshi-build.log`. Automatisierte Tests werden getrennt über `run\_tests.bat` gestartet.
4. `dist\\\\Tenshi.exe` starten. Eine vorab kompilierte EXE ist **nicht** im Quell-ZIP enthalten.
5. Optional `build\_portable.bat` für ein ZIP zum Start ohne Installation ausführen oder **Inno Setup 6.3+** installieren und mit `build\_installer.bat` einen Installer erzeugen.

## Bedienoberfläche

Zwei Hauptregister: **Partitionen** und **Dateien \& Ordner**. Oben rechts stehen die Sprachauswahl (Deutsch, Englisch, Spanisch, Chinesisch, Russisch, Japanisch) und die neue Schaltfläche **Fehlerprotokoll** bereit. Die Schaltfläche **Stapel-Export / fortsetzen** bleibt grün. Das Tenshi-Logo ist in die Oberfläche und das Windows-Programmsymbol integriert.

## Unterstützte Dateisysteme

* NTFS: vorhandene Dateien und experimentelle Wiederherstellung gelöschter MFT-Einträge.
* FAT32 / exFAT: vorhandene Dateien und eingeschränkte Recovery gelöschter Einträge.
* Linux ext2 / ext3 / ext4: vorhandene Dateien und experimentelle Recovery einzelner gelöschter Dateien.
* Btrfs / XFS: experimentelle Verzeichnisnavigation und Export unterstützter Dateistrukturen. Löschhinweise sind nicht exportierbar.

Eine erfolgreiche Leseprüfung beweist **nicht**, dass gerettete Dateien unverändert oder inhaltlich vollständig sind. Auch ein erfolgreicher Export garantiert **keine fehlerfreien Daten**.

## Imaging und Lesefehler

* Die Quelle wird nur gelesen; Image und Statusdatei werden auf dem ausgewählten Ziel gespeichert.
* Ein bestehendes Image kann mit seiner `.recovery.json`/`.journal` fortgesetzt werden, wenn es zur ursprünglichen Quelle passt.
* Bestätigte Medien-Lesefehler können als Nullbereiche im Image landen und werden protokolliert. Andere Fehler wie Zugriff verweigert, Geräteabbruch oder ungültige Anforderung führen zum Stopp, statt ein falsch vollständiges Image zu erzeugen.
* Bei Anzeichen für Hardwaredefekte nach Möglichkeit ein geeignetes, schonendes Imaging-Verfahren nutzen. Jeder Lesezugriff kann belastend sein.
* **Nicht** auf denselben physischen Datenträger exportieren. Tenshi prüft die Zuordnung bei direktem Windows-Datenträgerzugriff und verweigert sie bei Unklarheit.

## Stapel-Export

Mehrfachauswahl, Verzeichnisexport und Wiederaufnahme anhand gespeicherter Prüfpunkte und SHA-256 der vollständigen Exportdateien. Statusupdates nutzen einzigartige temporäre Dateien und wiederholen den Dateiaustausch bei kurzen Windows-Sperren. Alte Jobs verwenden weiterhin `recoverydesk\_status.json`, um eine Fortsetzung bisheriger Aufträge zu erlauben. Eine unterbrochene Einzeldatei beginnt beim Wiederaufnehmen erneut; vorhandene fremde Dateien werden nicht überschrieben.

## Fehlerprotokoll

Schaltfläche **Fehlerprotokoll** oben rechts. Auf Windows liegt die Datei standardmäßig unter:

`%LOCALAPPDATA%\\\\Tenshi\\\\Logs\\\\tenshi-errors.log`

Die Aufzeichnungen werden rotiert (bis 1 MiB je Datei, drei Sicherungen) und enthalten nur technische Fehlerart, Codes und optionale numerische Offsets. Keine Dateiinhalte, keine vollständigen Dateinamen. Fehlerprotokolle sind best effort: ist das Protokollziel unzugänglich, wird die Datenrettung nicht zusätzlich blockiert.

## Tests und Grenzen

Unter Linux: `xvfb-run -a python -m unittest discover -s tests -q`. Auf Windows: `py -3 -m unittest discover -s tests -q`. Die Python-Anwendung wurde mit synthetischen Testabbildern und simulierten Windows-Sperren überprüft. **Ein Praxistest des fertigen Windows-Builds steht aus. Der Windows-Hardwaretest steht aus.**

Weitere technische Einzelheiten siehe `RELEASE\_NOTES\_2.1.0.md` und den Build-Hotfix `RELEASE\_NOTES\_2.1.1.md`.



## Build-Fehler und Testprotokolle (2.1.1)

* **`build\_windows.bat`** erstellt die EXE, ohne vorher die komplette Testsuite auszuführen. Dadurch verhindern plattformspezifische Tests nicht mehr den Bau.
* **`run\_tests.bat`** führt die 289+ automatisierten Tests getrennt aus und schreibt `tenshi-tests.log`. Die absichtlich simulierten Fehler werden in einem temporären Test-Logverzeichnis gespeichert.
* Wenn `build\_windows.bat` abbricht, enthält **`tenshi-build.log`** den tatsächlichen Fehler beim Python-, venv-, pip- oder PyInstaller-Schritt. Bitte die letzten 30–50 Zeilen prüfen.
* `tenshi-errors.log` ist das **Anwendungsfehlerprotokoll**, kein zuverlässiges Build-Protokoll. Einträge aus Regressionstests wie `ImagingError` oder `PermissionError` sind oft absichtlich ausgelöst.
* Bei der Weitergabe von Build-Protokollen auf persönlich identifizierbare Windows-Benutzernamen und Pfade achten.

**Wichtig:** Eine erfolgreich gebaute EXE ist keine Bestätigung für sichere Datenrettung. Für produktive Nutzung Tests und vorsichtige Prüfungen mit Kopien vornehmen.



## Test-Hotfix 2.1.2 (Windows WinError 32)

`run\_tests.bat` konnte beim Test `test\_imaging\_failure\_reports\_operation\_only\_without\_filename`
unter Windows beim Aufräumen eines temporären Diagnoseordners mit `\[WinError 32]`
fehlschlagen, da der Logger `tenshi-errors.log` geöffnet hielt.
Die Logdatei wird jetzt nach jedem einzelnen Eintrag geschlossen. Der neue Test
`test\_logfile\_is\_closed\_between\_records\_for\_windows\_cleanup` sichert diese Eigenschaft ab.
Die absichtlichen Fehlersimulationen erzeugen weiterhin erwartete Protokolleinträge.
Der EXE-Bau ist weiterhin unabhängig von den Tests.

## Tests und Grenzen

305 automatisierte Tests bestanden (Linux + virtueller Bildschirm). Zusätzliche Tests prüfen Seitennavigation, Suche über Seiten hinweg, TMP-Ausblendung, Exportauswahl, Sprachwechsel, Quellenwechsel und unveränderte Kernfunktionen. **Der Windows-EXE-Build muss auf Windows ausgeführt und auf realen Laufwerken weiter validiert werden.**

### Regressionstests 2.3.0

316 automatisierte Tests bestanden (synthetische Images, Linux mit virtuellem Display). Die neuen Tests decken Dateiauswahl, Ordnerrekursion, NTFS-Extent-Prüfung, verwaiste MFT-Beziehungen, Exportverweigerung bei klar inkonsistenten Datenstrukturen und den neuen GUI-Dialog ab. **Windows-Hardwaretest steht aus**; die Windows-EXE muss mit `build\_windows.bat` gebaut werden.

### Regressionstests 2.4.0

322 automatisierte Tests bestanden (synthetische Abbilder, Linux mit virtuellem Display). Neue Tests überprüfen den direkten Hell-/Dunkelwechsel, die unveränderte grüne Export-Schaltfläche, gespeicherte Geometrie, Trennposition, Tabellenbreiten, den Sprachwechsel ohne Verlust der Darstellungseinstellungen sowie die neue Plausibilitätsübersicht. Ein echter Windows-EXE-Test steht weiterhin aus.

