# Tenshi 3.0.5 – veröffentlichtes Wartungsupdate

Am 28.10.2026 als [v3.0.5](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.5)
veröffentlicht. Die endgültigen Windows-/Linux-Pakete wurden vom Anwender
abgenommen. Website, Downloads und APT-Dateien bestehen alle 25 öffentlichen
Vergleichsprüfungen. Release-Commit: `d8a215fa34ce9be4c9653c1f11f337c7a4377a1b`;
[gemeinsamer Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40509422383).
Die neueren Oberflächenänderungen werden separat für 3.0.6 vorbereitet.

## Linux-Gerätezuordnung

Die vorgelagerte Zielprüfung lehnt leere Quell- oder Zielzuordnungen ausdrücklich
ab. Sie verwendet damit dieselbe Regel wie die bereits bestehende Prüfung am
geöffneten Ausgabeordner. Ein Ziel muss weiterhin nachweislich auf einem anderen
physischen Datenträger liegen.

Bei zusammengesetzten Geräten wird die Mitgliederliste einmal eingelesen.
Damit kann sie nicht zwischen zwei aufeinanderfolgenden Verzeichnisabfragen
unbemerkt leer werden. Fehlende Geräteinformationen führen zum Abbruch; eine
Teilzuordnung wird nicht als vollständiger Nachweis akzeptiert. Dies ist keine
atomare Sperre gegen sämtliche späteren Geräte- oder Mountwechsel. Die bestehende
Prüfung unmittelbar am geöffneten Ausgabeordner bleibt erhalten.

## Release-Prüfung und zusätzliche Tests

- `check_public_release.py` vergleicht Website, Downloads und öffentliche
  APT-Dateien mit dem geprüften lokalen Stand und schreibt einen neuen Bericht.
  Es veröffentlicht nichts und ersetzt keine kryptografische APT-Signaturprüfung.
  [Aufruf und Grenzen](docs/PUBLIC_RELEASE_CHECK.md).
- Linux-Layouttests prüfen vier Fenster-/Schriftkombinationen in sechs Sprachen,
  einschließlich Dateiliste, zentraler Aktionen und Exportwarteschlange.
- Zusätzliche Gerätewechseltests prüfen fehlende/unklare Zuordnungen ohne echte
  Datenträger zu öffnen.
- Sechs Integrationstests prüfen Imaging mit simulierten 4-KiB-Sektoren:
  Kopie, Pause/Fortsetzung, vollständiger Bytevergleich, beschädigte Prüfpunkte
  und ungültige Geometrien. Dies ist keine neue Abnahme echter 4Kn-Hardware.
- Die experimentelle Flatpak-Prüfung startet die tatsächlich installierte
  Tenshi-Oberfläche in sechs Sprachen und prüft Export sowie Imaging.
  Der bisherige Flatpak-Testaufbau ist vom Anwender unter Mint bestätigt;
  das ist keine Abnahme neuer 3.0.5-Pakete. Flatpak bleibt experimentell und ist
  kein Bestandteil der drei regulären Release-Pakete.

Diese Testverbesserungen erweitern weder die unterstützten Dateisystemvarianten
noch die nachgewiesene Rettungsfähigkeit auf beschädigten Medien.

## Veröffentlichte Pakete und Ablauf

- `Tenshi_Setup_3.0.5_Win64.exe`
- `Tenshi_Portable_3.0.5_Win64.zip`
- `tenshi-recovery_3.0.5-1_all.deb`

Ein gemeinsames Bundle eines festgehaltenen sauberen Commits wurde mit Kennung
`stable` gebaut. Das Manifest und `SHA256SUMS.sha256` liefern
die endgültigen Dateigrößen, Prüfsummen und die Build-Kennung.

Zur Paketabnahme gehören:
Windows-Installer und Portable getrennt starten, Version und Image-/Exportablauf
prüfen; unter Mint das DEB installieren beziehungsweise von der installierten
Vorversion aktualisieren und dieselben Grundfunktionen prüfen. Die gezielte
Linux-Prüfkorrektur ist automatisiert getestet, nicht durch eine neue vollständige
Hardwareabnahme bestätigt.

Nach Paketfreigabe wurden GitHub-Release, signierte APT-Quelle und Website
getrennt aktualisiert, bestehende Daten gesichert und öffentliche Dateien geprüft.
Die vorherigen 3.0.4-Dateien wurden nicht ersetzt.

Quelldatenträger werden weiterhin ausschließlich lesend geöffnet. Images und
Exporte auf einem anderen physischen Medium speichern. Windows-Installer und
EXE sind weiterhin nicht digital signiert.
