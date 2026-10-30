# Tenshi 3.0.11 – Vorschau und Inhaltsprüfung

Seit 30.10.2026 stabil [auf GitHub veröffentlicht](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.11).
Vorschau, Inhaltsprüfung und manuelles Durchblättern sind mit „Funktioniert alles“
bestätigt; die endgültigen Paketversionen mit „versionen stimmen“.
Website und signierte APT-Quelle bieten 3.0.11. Alle 25 öffentlichen
Abschlussvergleiche sind erfolgreich.

## Änderungen

- JPEG/PNG/BMP/GIF verkleinert und PDF mit der ersten Seite anzeigen.
- DOCX mit begrenztem Textauszug; XLSX/PPTX als strukturgeprüfte Office-Pakete.
- Mehrere ausgewählte Dateien mit **Zurück / Weiter** und Positionsanzeige
  manuell durchblättern. Kein automatischer Wechsel. Veraltete Ergebnisse
  überschreiben keine neu gewählte Datei; nur eine Verarbeitung je Fenster.
- **Datei prüfen → Inhalt prüfen** und **Exportierte Datei prüfen …** ergänzen
  die bisherige vollständige Leseprüfung. SHA256-Prüfungen bleiben getrennt.
- Hilfe, Hinweise und Bedienelemente in sechs Sprachen ergänzt.
- Pillow/PDFium/defusedxml für Windows/Flatpak festgelegt; das native DEB
  verwendet Pillow/defusedxml/Poppler aus den Distributionspaketen.
  Die vollständigen Lizenzhinweise liegen bei.

## Umfang und Grenzen

32 MiB Eingabe, 20 Millionen Bildpixel, begrenzte ZIP-/XML-Daten und beendbarer
Decoderprozess mit Zeit-/Speichergrenzen. PDF und Animation sind Teilprüfungen
mit erster Seite beziehungsweise erstem Bild. Keine vollständige Office-Ansicht,
keine Entschlüsselung. Links, Makros und Dokumentaktionen werden nicht ausgeführt.
Lesbare Struktur bestätigt keine vollständigen Originalinhalte. Quellen bleiben
schreibgeschützt; keine neuen Vorschau-Caches oder Dokumentkopien auf Platte.

[Benutzerhilfe](HILFE_3.0.11.md) · [Details und Grenzen](docs/CONTENT_PREVIEW.md) ·
[Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.11.json).

## Pakete und Prüfstand

- `Tenshi_Setup_3.0.11_Win64.exe`
- `Tenshi_Portable_3.0.11_Win64.zip`
- `tenshi-recovery_3.0.11-1_all.deb`

Die abgenommenen Pakete wurden mit Kennung `stable` aus dem sauberen Commit
`69ddc4658295ab65daa8b3ed0fdb7bb66522294c` gebaut
([gemeinsamer Release-Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/41071011412)).
Der Tag `v3.0.11` zeigt auf diesen Build-Commit. Integrationscommit
`d1617a8c8ec00cb1737aad2bdf89231725c58b9d` enthält denselben Dateistand.

Der Funktionsstand `8fc8ad87f2f835f4d838a24e41c2d5fd092aa97d` aus PR #119
ist mit identischem Dateistand als `2414916ed473389c407abb3f4e6eba770d495be8`
übernommen. Windows und Linux bestehen jeweils 934 Tests (84 beziehungsweise
sechs plattformbedingte Ausnahmen). Manifest, Paketgrößen, SHA-Dateien,
Windows-Ressourcen, Startprüfung, DEB-Buildidentität und enthaltene Hilfe sind
geprüft. Das installierte experimentelle Flatpak mit dem Funktionsstand ist
ebenfalls erfolgreich geprüft; es gehört nicht zu den drei regulären Paketen.

Das DEB `3.0.11-1` hat 883182 Bytes und SHA256:
`2fe0c478e7973bddca6b42084da374f5d2a90af4306486d5c666b6e1ebdfee3e`.
Die APT-Signatur wurde in Mint mit Archivschlüssel
`15D67DDA4D0D3BD1DD10A8C3B714CC0415B04529` geprüft. Alle 16 öffentlichen
APT-Dateien entsprechen diesem separat signaturgeprüften Export; der öffentliche
Schlüssel und acht ältere DEBs sind unverändert erhalten.

Alle sieben GitHub-Assets und die Website-/Download-Verweise sind geprüft.
Der Website-Katalog enthält die [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.11.json).
Die sechs Anleitungen erklären Vorschau, Inhaltsprüfung und manuelles
Durchblättern auf Grundlage der abgenommenen Hilfe. Der vorherige Serverstand
ist gesichert. Die vorbereiteten Manifestdateien mit `published: false` bleiben
unveränderte Buildnachweise; die tatsächliche Veröffentlichung steht in separaten
Abschlussberichten. Frühere Releases und Prüfsummen bleiben erhalten.
Dokumente und Bilder erhalten keine zusätzlichen Prüfsummendateien.
