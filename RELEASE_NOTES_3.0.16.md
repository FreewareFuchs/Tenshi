# Tenshi 3.0.16 – Veröffentlichung in Vorbereitung

Das Update bündelt die abgenommenen Verbesserungen aus PR #148, #149, #152
und #153. Der gemeinsame stabile Paketbau und die endgültige Paketabnahme
folgen. Die veröffentlichte Version ist derzeit 3.0.15.

## Änderungen

- **Dateiprüfung verständlicher erklärt.** Bei Signaturfunden stehen erzeugter
  Fundname, erkannter Typ, Größe und Fundposition im Dialog. Die Erklärung
  unterscheidet erkannte Dateistruktur, vollständigen Lesetest und Inhaltsprüfung.
  Die Hilfe erläutert den jeweiligen Prüfumfang.
- **Lesbare Größen.** Die Signaturfundliste verwendet B, KiB, MiB und größere
  Einheiten. Neben der Anzahl markierter Funde steht deren Gesamtgröße.
  Dateiprüfung und CSV-Fundliste zeigen exakte Bytewerte.
- **Möglicher Originalname für gelöschte FAT32-Dateien.** Bei plausiblen
  erhaltenen Langnamenfragmenten zeigt „Datei prüfen“ einen Namenshinweis.
  Die Namenssuche berücksichtigt ihn, und Analysesitzungen speichern ihn.
  Die Zuordnung bleibt unsicher. Der Export verwendet den bisherigen Kurznamen.
- **Namenshinweis im Exportbericht.** Der mögliche Originalname steht beim
  jeweiligen Einzelergebnis. Beim Fortsetzen wird der Hinweis aus dem aktuellen
  Exportplan ergänzt.

## Prüfung und Grenzen

Unabhängig mit dosfstools/mtools und exfatprogs/FATtools erstellte Images
prüfen gelöschte Dateien über Verzeichniseinträge. Die FAT32- und exFAT-Fälle
exportieren jeweils 9.001 Bytes identisch zum bekannten Original. Weitere
FAT32-Fälle prüfen erhaltene Langnamenreste und unterschiedliche Inhalte
bei gleichem Kurznamen. Das Verhalten bei anderen Datenträgern hängt von
ihren noch lesbaren Metadaten und Daten ab.

Ein möglicher Originalname kann falsch zugeordnet sein. Der Namenshinweis
bestätigt weder die Dateizuordnung noch die Unversehrtheit des Inhalts.
Die Suche im Reiter „Dateien & Ordner“ findet den Hinweis. Die Signatursuche
erkennt unterstützte Dateistrukturen und erhält daraus keine Originalnamen.
Reiner Text wie die Zeichenfolge HELLO hat keine eindeutige Dateisignatur.

Ein erfolgreicher Lesetest bestätigt die Lesbarkeit der gelesenen Daten.
Für die Inhaltsprüfung gelten weiterhin formatabhängige Grenzen. Die
beim Export berechnete SHA256 vergleicht den kopierten Datenstrom mit der
Zieldatei und ist kein Vergleich mit einer bekannten Originaldatei.

## Pakete und Freigabestand

- `Tenshi_Setup_3.0.16_Win64.exe`
- `Tenshi_Portable_3.0.16_Win64.zip`
- `tenshi-recovery_3.0.16-1_all.deb`

Der gemeinsame Workflow baut die Pakete mit stabiler Kennung aus demselben
sauberen Commit. Paketgrößen, SHA256 und Build-Herkunft werden geprüft.
Die Funktionsabnahmen unter Windows und Mint sind bestätigt. Paketversionen,
Starts, GitHub-Veröffentlichung, APT-Signierung und Website-Aktualisierung
werden anschließend getrennt abgeschlossen.

[Benutzerhilfe](HILFE_3.0.16.md) ·
[Änderungsnotizen in sechs Sprachen](RELEASE_NOTES_3.0.16.json)

Fragen und Verbesserungsvorschläge an **kontakt@freewarefuchs.de**.
