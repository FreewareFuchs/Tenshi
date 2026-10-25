# Tenshi 3.0.2 – stabile Version in Vorbereitung

Die stabile Ausgabe übernimmt den unter Windows und Linux geprüften Funktionsstand von Beta.6. Diese Datei dokumentiert die Vorbereitung; die Veröffentlichung erfolgt erst nach Prüfung der neu gebauten Pakete.

## Bereitstellung

- Windows 10/11, 64 Bit: `Tenshi_Setup_3.0.2_Win64.exe` und `Tenshi_Portable_3.0.2_Win64.zip`.
- Linux Mint 22.x / Python ab 3.11: `tenshi_3.0.2-1_all.deb`, Debian-Version `3.0.2-1`.
- Gemeinsame `SHA256SUMS.txt`; vorgesehener Git-Tag `v3.0.2`.
- Nur saubere, bekannte Git-Commits erhalten eine explizite Release-Kennung. Unveröffentlichte Entwicklungsstände tragen weiterhin `+dev`.

## Enthaltene Verbesserungen

- Exportordner heißen `Tenshi_Export_<Signatur>`; ältere `RecoveryDesk_Export_*`-Aufträge bleiben sicher fortsetzbar.
- Nach neuer Quellenauswahl startet automatisch die nur lesende Schnellanalyse im Register „Partitionen“. Die ersten 64 MiB und gültige Partitionstabellen ersetzen keinen vollständigen Tiefenscan.

- Read-only-Quellenprüfung mit Erkennung entfernter oder geänderter Geräte und ungültiger älterer Scan-Ergebnisse.
- FAT32-Auswahl der aktiven FAT und exFAT-Berücksichtigung der gültigen Dateidatenlänge.
- Stapel-Export mit Fortsetzen, Prüfung vorhandener Exporte und Schutz vor dem Überschreiben veränderter Zieldateien.
- Deutliche Warnmeldung und Fehleranzeige bei fehlgeschlagenen Exporten; korrigierte Abbruchanzeige.
- Optionale ZIP-Struktur-/CRC-Prüfung mit Fortschritt und Abbruch. Grenzen: je 512 MiB Archiv/entpackte Daten und 10.000 Einträge.
- Geringerer Speicherbedarf großer Dateibäume, genauere NTFS-Diagnose und verständlichere Angaben zur Partitionserkennung.
- Sechs Oberflächensprachen, unabhängige Dateisystem-Referenztests und festgelegte Windows-Buildwerkzeuge.

## Bestätigter Teststand vor der stabilen Paketierung

Beta.6 wurde auf Windows und Linux manuell geprüft: Paketstart/Versionsanzeige, Export-Abbruch und erneuter Export, SHA-256-Vergleich mit dem Original, Erkennung vorhandener und nachträglich veränderter Zieldateien sowie sichtbare Export-Warnungen. Die veröffentlichten Beta.6-Pakete wurden vom Anwender ebenfalls positiv geprüft.

Die stabilen Pakete werden neu gebaut und benötigen anschließend noch die kurze Paketabnahme.

## Grenzen bleiben bestehen

Eine stabile Programmversion garantiert keine erfolgreiche Datenrettung oder unbeschädigte Dateiinhalte. Gelöschte Dateien und eingeschränkte Dateisystemfunktionen bleiben entsprechend gekennzeichnet. ZIP-CRC-Prüfung ersetzt keinen Originalvergleich. Gerettete Daten und Images auf einem anderen physischen Datenträger speichern. Linux Mint 21.x mit Python 3.10 ist kein unterstütztes DEB-Ziel.
