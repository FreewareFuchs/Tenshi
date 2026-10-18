# Prüfnachweise zu Tenshi 3.0.2 (Stand 18.10.2026)

## Automatisierte Tests

- **441 Tests** bestanden unter Linux mit virtuellem X-Display, gemeldet im bestehenden Projektbericht `TESTERGEBNIS.txt`. Keine automatischen Fehler gemeldet.
- Version 3.0.1: Windows-Testprotokoll mit 429 ausgeführten Tests, davon 424 erfolgreich und 5 plattformabhängig übersprungen. Das ist ein früherer Stand.

## Vom Anwender unter Windows gemeldete Praxistests

- 3.0.1: GPT/MBR mit NTFS, FAT32, exFAT, ext4; Export von neun Referenzdateien mit **9 übereinstimmenden SHA-256-Werten** und 0 Fehlern.
- 3.0.1: Imaging `MBR_FAT32.raw` -> `Kopie_FAT32.img`, 4.194.304 Byte, SHA-256 auf beiden Seiten `202140683030325d05815c8bf303a7489b943fbd25c68223039931a49692aa5b`.
- 3.0.1: Imaging-Unterbrechung und Fortsetzung laut Nutzer funktionsfähig; Installer, Deinstallation sowie physische Datenträger und USB laut Nutzer geprüft.
- 3.0.2: Der Nutzer meldete die vorgeschlagene Windows-Checkliste insgesamt erfolgreich (Quellenwahl/automatischer Schnellscan, Quellenwechsel, Doppelklick, Exportordner, Stapel-Export, Sitzung und automatisierte Tests). Die einzelnen neuen Windows-Protokolle liegen nicht vollständig als eigenständige Nachweise bei.

## Was diese Ergebnisse NICHT beweisen

- Sichere Wiederherstellung von allen beschädigten, verschlüsselten, fragmentierten oder bereits überschriebenen Daten.
- Allseitige USB-/Controller-/4Kn-Kompatibilität oder Belastbarkeit bei fortschreitenden physischen Defekten.
- Vollständige Barrierefreiheit, Sicherheit aller denkbaren Dateisystemeingaben oder Ausschluss falscher Antiviren-Alarme.
- Integrität der später **neu gebauten** offiziellen Downloadpakete: Nach jedem Release-Build SHA-256 neu bilden und erneut testen.

**Keine Angabe einer Erfolgsquote oder pauschaler Veröffentlichungsgarantie.**
