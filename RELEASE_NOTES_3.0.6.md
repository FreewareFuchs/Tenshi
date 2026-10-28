# Tenshi 3.0.6 – Oberfläche und Windows-Laufwerke

Release-Vorbereitung; noch nicht veröffentlicht. Die öffentliche Ausgabe bleibt
3.0.5. Die zugrunde liegende Oberfläche und das Öffnen von C: wurden im Testpaket
vom Anwender bestätigt. Die endgültigen 3.0.6-Pakete benötigen eine eigene Abnahme.

## Darstellung und Bedienung

- Sun-Valley-Farben mit den Einstellungen System, Hell und Dunkel. Bestehende
  manuelle Einstellungen und die bisherige Schrift bleiben erhalten. Der
  Exportknopf ist über die Akzentfarbe hervorgehoben.
- Unter Windows wird die Systemdarstellung gelesen; unter Linux wird bevorzugt
  die Desktop-Schnittstelle verwendet. Eine manuelle Auswahl hat Vorrang.
- Datenträger und Laufwerke erscheinen in einer gemeinsamen Auswahl. Eindeutig
  zugeordnete Laufwerke stehen unter ihrem Datenträger. Die Übersicht fragt
  Metadaten ab; ein Lesezugriff erfolgt erst nach der bestätigten Quellenauswahl.
- Der Scanfortschritt bleibt auch in kleinen Fenstern und bei ausgeklappter
  Exportwarteschlange sichtbar. Große Flächen werden ohne gekachelte
  Theme-Bilder gezeichnet, damit Größenänderungen schneller reagieren.

## Windows-Volume-Lesen und Prüfsummen

Windows-Volumes lassen sich über den Dateisystembereich hinaus bis zum
ermittelten Partitionsende lesen. Damit wird unter anderem der bisherige Fehler
beim Öffnen von C: behoben. Die Einstellung gilt nur für den vorhandenen
schreibgeschützten Handle. Unerwartet kurze Leseantworten bleiben Fehler;
Schreibrechte, Sperren oder Aushängen werden nicht angefordert.

Neue Release-Pakete und Portable-Archive verwenden `SHA256SUMS.sha256`.
Bereits veröffentlichte Pakete mit `SHA256SUMS.txt` bleiben unverändert prüfbar.
Es werden keine zusätzlichen Prüfsummendateien für Bilder oder Dokumente erzeugt.

## Pakete und Abnahme

- `Tenshi_Setup_3.0.6_Win64.exe`
- `Tenshi_Portable_3.0.6_Win64.zip`
- `tenshi-recovery_3.0.6-1_all.deb`

Alle drei Pakete stammen aus einem gemeinsamen sauberen Commit mit Kennung
`stable`. Das Release-Manifest legt Dateinamen, Größen, SHA256 und Quellcommit fest.
Vor Veröffentlichung Installer und Portable unter Windows sowie das DEB unter
Mint starten, Version, Farbwahl, Quellenauswahl, Fenstergrößen und einen bekannten
Image-/Exportablauf prüfen. Unter Windows das Öffnen von C: erneut prüfen.
Flatpak bleibt experimentell und gehört nicht zu diesen drei Release-Paketen.

Die Dateisystemunterstützung und Schreibschutzregeln werden nicht erweitert.
Quelldatenträger werden ausschließlich lesend geöffnet; Images und Exporte
gehören auf ein anderes physisches Medium. Die Windows-Pakete bleiben unsigniert.
