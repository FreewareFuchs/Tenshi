# Tenshi 3.0.5 – Vorbereitung eines Wartungsupdates

Noch nicht veröffentlicht. Die öffentlichen Windows-/Linux-Downloads und die
signierte APT-Quelle bleiben bei 3.0.4. Die folgenden Änderungen sind im Quellcode
vorbereitet; eine Abnahme der endgültigen 3.0.5-Pakete steht noch aus.

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

## Vorgesehene Pakete und Abnahme

- `Tenshi_Setup_3.0.5_Win64.exe`
- `Tenshi_Portable_3.0.5_Win64.zip`
- `tenshi-recovery_3.0.5-1_all.deb`

Nach erfolgreicher CI ein gemeinsames Bundle eines festgehaltenen sauberen
Commits mit Kennung `stable` bauen. Das Manifest und `SHA256SUMS.txt` liefern
die endgültigen Dateigrößen, Prüfsummen und die Build-Kennung.

Vor Veröffentlichung stehen die manuellen Tests der endgültigen Pakete aus:
Windows-Installer und Portable getrennt starten, Version und Image-/Exportablauf
prüfen; unter Mint das DEB installieren beziehungsweise von der installierten
Vorversion aktualisieren und dieselben Grundfunktionen prüfen. Die gezielte
Linux-Prüfkorrektur ist automatisiert getestet, nicht durch eine neue vollständige
Hardwareabnahme bestätigt.

Erst nach Paketfreigabe GitHub-Release, signierte APT-Quelle und Website getrennt
aktualisieren, bestehende Daten sichern und die öffentlichen Dateien prüfen.
Die vorherigen 3.0.4-Dateien werden nicht ersetzt.

Quelldatenträger werden weiterhin ausschließlich lesend geöffnet. Images und
Exporte auf einem anderen physischen Medium speichern. Windows-Installer und
EXE sind weiterhin nicht digital signiert.
