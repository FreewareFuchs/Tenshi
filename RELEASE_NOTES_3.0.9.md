# Tenshi 3.0.9 – Exportziel prüfen und Fortschritt sichtbar halten

Stabile Pakete in Vorbereitung. Die Funktionen aus PR #109 sind im Windows-/
Flatpak-Testpaket manuell bestätigt. Endgültige Installer-, Portable- und
Mint-DEB-Paketstarts und Versionsanzeigen stehen nach dem gemeinsamen Neubau
noch aus. Veröffentlicht ist weiterhin 3.0.8.

## Zielprüfung vor dem Export

- Die Bestätigung zeigt Dateisystem des Ziels, geplante Dateiinhalte, eine
  Obergrenze zusätzlich benötigter Dateibytes und aktuell verfügbaren Platz.
- Vollständig vorhandene Dateien eines gültigen Auftrags werden für die erneute
  Prüfung berücksichtigt. Die bestehenden Hashprüfungen müssen sie weiter bestehen.
- Bei voraussichtlich zu wenig Platz ist Nein vorausgewählt. Eine ausdrücklich
  bestätigte Schätzung darf trotzdem starten. Dateisystem-Metadaten, Berichte und
  Prüfsummen brauchen zusätzlichen Platz; freie Kapazität kann sich ändern.
- Erkannte FAT/FAT32-Dateigrößenüberschreitungen über `2**32 - 1` Bytes stoppen
  vor dem ersten Anlegen des Exportordners. Unbekannte VM-/Netzwerkgrenzen werden
  nicht geraten. Die Prüfung legt keine Testdateien an und erweitert keine Rechte.
- Ablehnen oder Abbrechen während der Zielprüfung verändert den Zielordner nicht.
  Eine abgelehnte Wiederaufnahme bleibt fortsetzbar. Nach der Bestätigung wird
  die Quellidentität erneut geprüft. Eine normale Ablehnung erzeugt keinen
  Fehlerprotokoll-Eintrag.

## Sichtbares Exportfenster

Die Fortschrittsansicht bleibt über dem Hauptfenster und wird beim Öffnen oder
Wiederöffnen daran zentriert. An kleinen Bildschirmrändern hat vollständige
Sichtbarkeit Vorrang. Das Hauptfenster bleibt bedienbar. Die Position wird beim
normalen Verschieben oder Vergrößern nicht ständig zurückgesetzt.

Während eines laufenden oder pausierten Auftrags öffnet Stapel-Export dieselbe
Ansicht erneut. Dabei entstehen weder eine neue Zielabfrage noch ein zweiter
Exportauftrag. Schließen der Ansicht verändert weder den Auftrag noch die Pause.

Dialoge und Offline-Hilfe sind in allen sechs Sprachen ergänzt.
[Benutzerhilfe](HILFE_3.0.9.md) · [Zielprüfung und Grenzen](docs/EXPORT_TARGET_CHECK.md) ·
[Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.9.json).

## Pakete und Prüfstand

- `Tenshi_Setup_3.0.9_Win64.exe`
- `Tenshi_Portable_3.0.9_Win64.zip`
- `tenshi-recovery_3.0.9-1_all.deb`

Die endgültigen Pakete werden gemeinsam mit Kennung `stable` aus einem sauberen
Commit gebaut. Manifest und `.sha256`-Dateien dokumentieren Größen, Prüfsummen
und Quellstand. Die abgenommenen Funktionen liegen in Quellcommit
`7ef3aae2a4ec7f6468d31d850ca9fe124ac374c7`, übernommen als Hauptcommit
`4d0d4820eba2be2f039c2664fc2b54f4a1f0ffaf` mit identischem Dateistand.
Windows und Linux bestehen jeweils 874 Tests (82 beziehungsweise 6 Skips).
Auch das installierte experimentelle Flatpak, die Windows-Fensterreihenfolge
und das erneute Öffnen echter laufender/pausierter Aufträge sind geprüft.

Der Anwender bestätigt das Testpaket mit „ok, funktioniert alles“. Die endgültige
stabile Paketabnahme und Veröffentlichung werden gesondert dokumentiert.
Quell-/Zielschutz, Hashprüfung und Exportsteuerung bleiben erhalten. Diese
Prüfungen sind keine Garantie für andere Hardware oder beschädigte Medien.
Frühere Releases bleiben unverändert erhalten. Dokumente und Bilder erhalten
keine zusätzlichen Prüfsummen-Sidecars.
