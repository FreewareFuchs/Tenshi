# Tenshi 3.0.12 – stabil veröffentlicht (30.10.2026)

Veröffentlicht als [v3.0.12](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.12). Bildsignatursuche und endgültige Paketversionen sind manuell bestätigt. GitHub-Downloads, signierte APT-Quelle und Website sind öffentlich geprüft.

## Änderungen

- Dateien & Ordner → Diagnose… → Bildsignaturen suchen durchsucht ein reguläres
  Image nach zusammenhängenden JPEG-/PNG-Strukturen, unabhängig vom Dateisystem.
- Bestätigung, MiB-Fortschritt, Abbruch und begrenzte Marker-/Chunk-/CRC-Prüfungen.
- Fundnamen enthalten Bildtyp und hexadezimalen Byte-Offset. Vorschau,
  Inhaltsprüfung, Export-Vorabprüfung und sicherer Stapel-Export unterstützen sie.
- Gespeicherte Exportaufträge werden nach Quellenbestätigung durch erneute
  Signatursuche und Vergleich des vollständigen Plans rekonstruiert.
- Hilfe und Oberfläche erklären Bedienung und Grenzen in sechs Sprachen.

## Grenzen

Nur reguläre Images, kein direkter physischer Gerätescan. Der Partitionsoffset
wird nicht verwendet. Belegte und freie Bereiche bleiben ununterschieden;
auch vorhandene, eingebettete Bilder und Vorschaubilder können erscheinen.
Originalname, Ordner und Löschstatus sind unbekannt. Keine Zusammensetzung von
Fragmenten und kein Nachweis unversehrter Originalinhalte. Geänderte Quellen und
manipulierte Fundbereiche werden abgewiesen. Es entsteht kein Fundinhalts-Cache.
Speicherung als Analysesitzung ist für diese Fundart noch nicht unterstützt.

Maximal 32 MiB pro Fund, 1000 Funde, 5000 Anfangssignaturen und 512 MiB zusätzliche
Strukturlesevorgänge. PNG ist auf 4096 Chunks begrenzt, JPEG auf 65536 Marker.
Globale Prüfgrenzen werden als unvollständiges Ergebnis angezeigt. Lesefehler
führen zum Abbruch. Die separate Inhaltsprüfung behält ihre eigenen Grenzen.

[Benutzerhilfe](HILFE_3.0.12.md) · [Details und Grenzen](docs/IMAGE_SIGNATURE_SEARCH.md) ·
[Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.12.json).

## Pakete und Prüfstand

- `Tenshi_Setup_3.0.12_Win64.exe`
- `Tenshi_Portable_3.0.12_Win64.zip`
- `tenshi-recovery_3.0.12-1_all.deb`

Alle Pakete wurden gemeinsam mit Kennung `stable` aus einem sauberen Commit
gebaut. Manifest und `.sha256`-Dateien dokumentieren Größen, Prüfsummen und
Quellstand. Dokumente und Beispielimages erhalten keine eigenen Prüfsummendateien.

Abgenommener Funktionsstand: `f7856af44e17f2c5ab3de983a48764b94aeb3eb3`,
übernommen als `2edd89a10c77826db54a0e21eeb5d2b8b4fce213` mit identischem Dateistand.
Windows und Linux bestehen jeweils 955 Tests (84 beziehungsweise sechs Skips).
Das installierte experimentelle Flatpak ist ebenfalls erfolgreich geprüft.
Die endgültigen stabilen Pakete erhalten eine gesonderte Start-/Versionsabnahme.

GitHub veröffentlichte sieben geprüfte Assets. Der signierte APT-Index und das
DEB wurden in Mint geprüft; alle 17 öffentlichen APT-Dateien stimmen mit dem
signierten Export überein. Die Website wurde mit 25 öffentlichen Vergleichen
abgeschlossen. Frühere veröffentlichte Pakete und Prüfsummen bleiben erhalten.
