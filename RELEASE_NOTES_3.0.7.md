# Tenshi 3.0.7 – Export- und Imaging-Fenster

Vorbereitet, noch nicht veröffentlicht. Die öffentliche Ausgabe bleibt 3.0.6.
Die Export- und Imaging-Funktionen wurden in den Entwicklungspaketen manuell
abgenommen. Die endgültigen Installer-, Portable- und DEB-Pakete benötigen
noch ihre Paketabnahme.

## Export

- Eigenes, wieder aufrufbares Fortschrittsfenster mit 100 quadratischen Feldern.
  Jedes Feld fasst ein Prozent der geplanten Dateigrößen zusammen; bei reinen
  Ordner-/Null-Byte-Plänen gilt ausdrücklich die Eintragsanzahl. Die Felder sind
  keine physischen Datenträgersektoren.
- Kopierte, bestätigte, fehlgeschlagene und unbestätigte Anteile bleiben
  unterscheidbar. Die sichtbare Warteschlange entfällt im Hauptfenster.
- SHA256-Berechnung und Zielprüfung erscheinen als Textmeldung. Das Raster
  bleibt beim Gesamtumfang und startet für die Prüfung nicht neu.
- Ergebnisberichte enthalten SHA256-Werte je Datei und unterscheiden bestätigte
  Zieldateien von noch unbestätigten kopierten Datenströmen.
- Bericht speichern beginnt im Exportordner, schlägt einen neuen Namen vor und
  überschreibt keine vorhandenen Berichte.

## Imageerstellung

- Eigene, nicht modale Fortschrittsansicht mit einem Raster über die Quellbytes.
  Grün bedeutet lesbar gespeichert, Rot kennzeichnet Anteile mit protokolliertem
  Nullersatz. Noch offene und teilweise gespeicherte Bereiche bleiben sichtbar.
  Schon ein kleiner Fehleranteil macht das betroffene Prozentfeld rot.
- Schließen der Fortschritts- oder Einstellungsansicht beendet den Auftrag nicht.
  Über den bisherigen Hauptfenster-Einstieg lässt sich die laufende Sitzung
  wieder öffnen. Unterbrechen und Fortsetzen bleiben eigene Aktionen.
- Grün bestätigt keinen Vollvergleich. Nur das erfolgreiche Prüfergebnis darf
  das Image als bitgenau verifiziert bezeichnen. Der Vollvergleich erscheint als
  separate Textphase. Ein nicht übernommener Block bleibt bei sicherem Stopp offen.
- Bericht und Zielordner sind direkt erreichbar; Bericht speichern verwendet
  exklusives Anlegen und die vorhandenen Zielschutzprüfungen.
- Das Raster verwendet bereits vorhandene Fortschritts- und Fehlerdaten. Keine
  zusätzlichen Lesezugriffe für die Darstellung. Beim Fortsetzen werden die
  gespeicherten Bereiche erst nach den vorhandenen Prüfpunkt-Prüfungen angezeigt.

## Bedienung und Sicherheit

Exportfehler erläutern verweigerten Zugriff, schreibgeschützte Einbindung,
fehlenden Speicherplatz und nicht unterstützte Dateioperationen getrennt.
„Invalid argument“ ist kein eindeutiger Nachweis fehlender Schreibrechte;
gemeinsame VM-Ordner können Dateioperationen einschränken. Die Originaldiagnose
bleibt sichtbar. Tenshi erweitert keine Rechte oder Flatpak-Freigaben.

Alle sechs Oberflächensprachen sowie Hell/Dunkel werden unterstützt.
Unter Linux folgen auch Dateilisten in den Tk-Öffnen-/Speichern-/Ordnerdialogen
der aktiven Farbgestaltung. Windows-native Dateidialoge bleiben unverändert.
Die Dateisystemanalyse behält ihre bestehende Fortschrittsanzeige im Hauptfenster;
dafür wird kein separates Fenster eingeführt. Quellmedien bleiben schreibgeschützt.
Wiederaufnahme, Retry- und Nullersatz-Regeln bleiben erhalten. Ein Export oder
lesbarer Imagebereich garantiert keine intakten ursprünglichen Dateiinhalte.

## Pakete und Abnahme

- `Tenshi_Setup_3.0.7_Win64.exe`
- `Tenshi_Portable_3.0.7_Win64.zip`
- `tenshi-recovery_3.0.7-1_all.deb`

Alle drei Pakete stammen aus demselben sauberen Commit mit Kennung `stable`.
Das Release-Manifest enthält Dateinamen, Größen, SHA256 und Quellcommit.
Prüfsummen werden wie bisher als `.sha256` mitgeliefert; keine zusätzlichen
Prüfsummendateien für Bilder oder Dokumente.

Vor Veröffentlichung Installer und Portable unter Windows sowie das DEB unter
Mint starten, Version, Fenster, einen bekannten Export und einen Imaging-Ablauf
prüfen. Das installierte DEB ist vor der späteren APT-Veröffentlichung zusätzlich
über den bestehenden VM-Ablauf zu signieren und zu prüfen. Downloads, Website
und APT werden in diesem Vorbereitungsschritt nicht geändert.
