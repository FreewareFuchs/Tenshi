# Tenshi 3.0.13 – stabil veröffentlicht (03.11.2026)

Die Erweiterungen aus PR #126–#131 und die endgültigen Paketversionen sind manuell bestätigt. GitHub-Release, signierte APT-Quelle und Website sind veröffentlicht und öffentlich geprüft. Die Pakete stammen unverändert aus dem sauberen Commit `cfac39d9d5af856000e37060ccbea819f402380c` ([gemeinsamer Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/41708439214)).

## Änderungen

- Eigener Reiter **Dateisignaturen** mit gleichwertigen Suchbuttons für Bilder, Office/PDF, Archive, Audio und Video.
- Mehrere Kategorien in einem Durchgang durchsuchen und die Funde gemeinsam anzeigen, prüfen und exportieren.
- Zusätzlich zu JPEG/PNG: BMP, GIF, TIFF, WebP; moderne Office-/ODF-Dateien und PDF; ZIP, RAR 4/5, 7z und TAR; WAV, MP3 mit ID3v2 und Ogg/Opus; AVI und MP4.
- Für JPEG/PNG/GIF/TIFF/PDF und Office/ZIP eine Prüfgrenze von **32, 64, 128 oder 256 MiB** wählen. Große PDF-/ZIP-Strukturen werden mit begrenzten Leseblöcken untersucht; andere Formate haben eigene Grenzen.
- **Suchstand speichern**, **Anhalten** und **Suchstand öffnen…** ermöglichen das Fortsetzen nach einem Programmneustart. Kategorien, Prüfgrenze, abgeschlossene Suchabschnitte und Fundmetadaten bleiben erhalten; Quelle und gespeicherte Funde werden erneut geprüft. Ein unvollständiger Abschnitt wird wiederholt.
- Gespeicherte Exportaufträge übernehmen Suchkategorien und Prüfgrenze. Ältere Suchstände und Exportaufträge behalten ihren ursprünglichen Formatumfang; für PDF/RAR im bereits durchsuchten Bereich eine neue Suche starten.
- Unter **Dateien & Ordner → Scanoptionen…** bleiben fehlertolerante Suche und Analysebericht erreichbar. Der frühere Signatursuch-Aufruf im Diagnosedialog entfällt.
- Oberfläche und Offline-Hilfe in sechs Sprachen aktualisiert.

## Umfang und Grenzen

Die Signatursuche liest reguläre Images schreibgeschützt und benötigt kein lesbares Dateisystem. Der Partitionsoffset wird ignoriert. Belegte und freie Bereiche werden durchsucht; Originalnamen, Verzeichnisse und Löschstatus sind unbekannt. Strukturkandidaten bestätigen keine vollständigen Originalinhalte. Fragmente werden nicht zusammengesetzt und Dokumentaktionen nicht ausgeführt.

RAR-Mehrteiler und verschlüsselte RAR-Header, ZIP64, BigTIFF sowie klassische DOC/XLS/PPT-Dateien werden nicht unterstützt. Archive werden bei der Signatursuche nicht entpackt. PDF-Prüfung ist begrenzt; ungewöhnliche oder beschädigte Varianten können unerkannt bleiben. Vorschau und Inhaltsprüfung behalten ihre eigenen Grenzen.

Je Suchlauf gelten weiterhin höchstens 1000 Funde, 5000 Anfangssignaturen und 512 MiB zusätzliche Strukturlesevorgänge. Größere Fundgrenzen können längere Lesezeiten erfordern. Der Quellenvergleich gespeicherter Suchstände verwendet Stichproben, keinen vollständigen Image-Hash.

[Benutzerhilfe](HILFE_3.0.13.md) · [Formatumfang und technische Grenzen](docs/IMAGE_SIGNATURE_SEARCH.md) · [Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.13.json)

## Pakete und Freigabestand

- `Tenshi_Setup_3.0.13_Win64.exe`
- `Tenshi_Portable_3.0.13_Win64.zip`
- `tenshi-recovery_3.0.13-1_all.deb`

Der gemeinsame Vorbereitungsworkflow baut alle Pakete mit Kennung `stable` aus demselben sauberen Commit. `release_manifest.json`, `SHA256SUMS.sha256` und die Paket-Prüfsummendateien dokumentieren Herkunft und Inhalt. Flatpak bleibt experimentell und ist nicht Bestandteil dieses stabilen Dreierpakets.

Funktionsabnahmen, endgültige Paketstarts und Versionsanzeigen sind bestätigt. Die Veröffentlichung von Downloads, signierter APT-Quelle und Website wurde am 03.11.2026 abgeschlossen; die öffentlichen Abschlussvergleiche sind erfolgreich. Die nachfolgenden Erweiterungen werden getrennt in 3.0.14 gebündelt.

Fragen und Verbesserungsvorschläge: **kontakt@freewarefuchs.de**.
