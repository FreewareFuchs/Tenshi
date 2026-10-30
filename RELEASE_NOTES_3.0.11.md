# Tenshi 3.0.11 – Vorschau und Inhaltsprüfung

Stabile Pakete in Vorbereitung. Der vollständige Funktionsstand aus PR #119
ist mit „Funktioniert alles“ manuell bestätigt. Die endgültige Paketabnahme
und Veröffentlichung folgen getrennt.

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

Alle drei Pakete werden gemeinsam mit Kennung `stable` aus einem sauberen Commit
gebaut. Manifest und `.sha256`-Dateien dokumentieren Größen, Prüfsummen und
Quellstand. Dokumente erhalten keine eigenen Prüfsummendateien.

Abgenommener Funktionsstand: `8fc8ad87f2f835f4d838a24e41c2d5fd092aa97d`,
übernommen als `2414916ed473389c407abb3f4e6eba770d495be8` mit identischem Dateistand.
Windows und Linux bestehen jeweils 933 Tests (84 beziehungsweise sechs Skips).
Das installierte experimentelle Flatpak ist ebenfalls erfolgreich geprüft.
Die endgültigen stabilen Pakete erhalten eine gesonderte Start- und Versionsabnahme.

GitHub-Veröffentlichung, signierte APT-Quelle und Website folgen nach der
Paketabnahme. Frühere veröffentlichte Pakete und Prüfsummen bleiben erhalten.
