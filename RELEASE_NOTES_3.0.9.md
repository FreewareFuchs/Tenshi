# Tenshi 3.0.9 – Exportziel prüfen und Fortschritt sichtbar halten

Seit 29.10.2026 stabil [auf GitHub veröffentlicht](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.9).
Funktionen und endgültige Installer-/Portable-/Mint-DEB-Paketstarts einschließlich
Versionsanzeigen sind manuell bestätigt. Die Website und die signierte APT-Quelle
bieten 3.0.9; alle 25 öffentlichen Abschlussvergleiche sind erfolgreich.

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

Die abgenommenen Pakete wurden mit Kennung `stable` unverändert aus dem sauberen
Commit `b433b2bb7f53c259c546c16e475b89c773e3cf4b` gebaut
([gemeinsamer Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40914147249)).
Der Tag `v3.0.9` zeigt auf diesen Build-Commit. Der Integrationscommit
`b181041d7475216ff1afef472bfb66d385e6419c` enthält denselben Dateistand.

Windows und Linux bestehen jeweils 874 Tests (82 beziehungsweise 6 plattformbedingte
Skips). Manifest, Paketgrößen, SHA-Dateien, Windows-Ressourcen, Programmstarttest,
DEB-Buildidentität sowie enthaltene Exportmodule und Hilfe sind geprüft.
Der Anwender bestätigt die endgültigen Pakete mit „Funktioniert alles“.
Der Funktionsstand war zuvor im Windows-/Flatpak-Testpaket bestätigt; auch die
Windows-Fensterreihenfolge und das Wiederöffnen echter laufender/pausierter
Aufträge sind geprüft. Diese Abnahme ist keine Garantie für andere Hardware
oder beschädigte Medien.

Das DEB `3.0.9-1` hat 824286 Bytes und SHA256:
`829758afc3b612cc6428936b02cc7fdcbd5daac3fe5b108e64a0a9ad45e12f0b`.
Die APT-Signatur wurde in Mint mit Archivschlüssel
`15D67DDA4D0D3BD1DD10A8C3B714CC0415B04529` geprüft. Alle 14 öffentlichen
APT-Dateien entsprechen dem VM-Export; der öffentliche Schlüssel und sechs ältere
DEBs sind unverändert erhalten. Die öffentliche Prüfung vergleicht Bytes und
Prüfsummen mit diesem separat signaturgeprüften Export.

Alle sieben GitHub-Assets und die Website-/Download-Verweise sind geprüft.
Der Website-Katalog enthält die [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.9.json);
die sechs Anleitungen erklären Zielprüfung und Fensterbedienung. Der vorherige
Serverstand ist gesichert. Die vorbereiteten Manifestdateien mit `published: false`
bleiben unveränderte Buildnachweise; die tatsächliche Veröffentlichung steht in
separaten Abschlussberichten. Frühere Releases und ihre Prüfsummen bleiben
erhalten. Dokumente und Bilder erhalten keine zusätzlichen Prüfsummen-Sidecars.
Flatpak bleibt experimentell und gehört nicht zu den drei regulären Paketen.
