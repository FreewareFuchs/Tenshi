# Tenshi 3.0.2 – Prüfung der eingebauten Hinweise

- **Quellenauswahl:** Neue Bilddatei, physischer Datenträger oder Windows-Laufwerk führt automatisch zum Register „Partitionen“ und startet die nur lesende 64-MiB-Schnellanalyse. Die Anweisung zum manuellen Start im Startbereich wurde aktualisiert.
- **Export:** Neue Aufgaben legen `Tenshi_Export_*` an; laufende ältere Aufgaben nutzen weiterhin `RecoveryDesk_Export_*`. Der Ordner `files` mit den geretteten Dateien bleibt erhalten.
- **Analysesitzungen:** Das Wiederherstellen einer geprüften Sitzung ist von der automatischen Neuanalyse ausgenommen, um die gespeicherten Ergebnisse nicht zu überschreiben.

## Seit Tenshi 3.0.0 – Prüfung der eingebauten Hilfe

- **Partionsanalyse:** Bootsektorfunde ohne Partitionstabelle bleiben Kandidaten; Plausibilität ist keine Inhaltsprüfung.
- **Dateibrowser:** Unterschiede zwischen NTFS, FAT32, exFAT, ext2/3/4 und eingeschränktem Btrfs/XFS erklärt. Keine Garantie für gelöschte Dateiinhalte.
- **Imaging:** Fortgesetzte Images beschreiben bestehende Zieldateien; 0–3 Zusatzversuche, Nullfüllung = Datenlücke, sicherer Stopp und harte Verbindungsfehler erläutert.
- **Stapel-Export:** Vorabprüfung ist eine Metadatenprüfung; Ausgabe nur auf getrennten Datenträger; wiederaufgenommene Dateien per SHA-256 geprüft. TMP-Anzeigefilter verändert rekursiven Export nicht zwingend.
- **Sitzungen:** Stichproben-Hashes ersetzen keinen vollständigen Prüfsummenvergleich; Sitzungsarchiv enthält möglicherweise private Dateinamen.
- **Fehlersuche:** EXE, portable Ausgabe und Installer müssen unter Windows gebaut werden; Fehlerlogs auf private Pfade prüfen.
- **Erststart:** Keine automatischen Scans durch die Hilfe, kein neues Hauptregister, Logo/Sprachen/Exportfarbe erhalten.

Die Angaben beruhen auf den vorhandenen Implementierungen, nicht auf einer neu durchgeführten Hardwareabnahme. Für Version 3.0.1 hat der Anwender erfolgreich die Windows-Tests von Installer, USB/physischem Datenträger, 9 Dateien und Imaging gemeldet. Die Änderungen in 3.0.2 benötigen noch eine Windows-Prüfung.

## Zusatzprüfung Tenshi 2.8.0 – Export-Vorabprüfung

- „Gesperrt“ bei gelöschten NTFS-Einträgen mit nachgewiesener Überlappung zu aktuell vorhandenen NTFS-Dateien; die Prüfung basiert ausschließlich auf dem zuletzt eingelesenen Index.
- „Gesperrt“ bei widersprüchlich mehrfach belegten Datenläufen innerhalb desselben NTFS-Datenstroms.
- „Warnung“ bei anderen gelöschten Dateien bleibt bestehen. Keine bestätigte Überlappung bedeutet ausdrücklich **keine** nachgewiesene Wiederherstellbarkeit.
- Vorabprüfung liest keine Dateiinhalte; eine SHA-256-Prüfsumme des Exportergebnisses beweist nicht dessen ursprüngliche Richtigkeit.
- Der Batch-Export setzt dieselbe Sperrprüfung um und schreibt nicht auf die Quelldatenquelle.

## Zusatzprüfung Tenshi 2.7.0 – Imaging

- Im Dialog wird die Standardstrategie „Nullen + protokollieren“ mit ausdrücklicher Warnung vor Datenlücken angezeigt.
- Die alternative Strategie „Sicher anhalten“ wird auch im Bestätigungsdialog korrekt beschrieben; kein Versprechen von Nullfüllung bei ausgewähltem Stopp.
- 0 Zusatzversuche bedeuten: keine erneuten Leseversuche am defekten Sektor. Die Erstlesung findet immer statt.
- Im Abschlussdialog wird die Nullfüllung nur erwähnt, wenn tatsächlich Fehlerbereiche registriert wurden.
- Das Quellenmedium bleibt schreibgeschützt; bei Zugriff- oder Geräteverbindungsfehlern darf keine scheinbare Wiederherstellung behauptet werden.
- Der Fehlerstellen-Bericht ist eine Auflistung von Bytebereichen, **keine** Garantie intakter Daten.

# Tenshi 2.0.0 – Audit der sichtbaren Hinweise

| Ort | Vorher | Korrektur | Validierungsgrund |
|---|---|---|---|
| Dateibrowser | Nur NTFS-MFT-Löschsuche | NTFS, FAT32, exFAT und ext2/3/4 eingeschränkt; Btrfs/XFS nur Löschspuren | Implementierte Dateisystemparser und Löschhinweise in 1.9.3 |
| Hauptfenster-Fußzeile | Beschädigte Datenträger einfach zuerst abbilden | Zugriffe minimieren und schonende Imaging-Verfahren; getrenntes physisches Ziel | Lesevorgänge können defekte Hardware belasten |
| Physischer Datenträger | Erst Image erstellen (ohne Vorsichtshinweis) | Schon Lesen kann Zustand verschlechtern | Praxisorientierte Risikokommunikation |
| Imaging-Dialog | Nur eine **neue** Datei wird beschrieben | Neue **oder fortgesetzte** Image-Datei plus Prüfpunkte werden beschrieben | Resume aktualisiert vorhandenes Image |
| Imaging-Dialog | Nullfüllung als reine Tätigkeit | Explizit als *Datenlücken* ausgewiesen | Nullen sind keine Rekonstruktion |
| Datei-/Ordnerliste | TMP standardmäßig unsichtbar, Exportverhalten nicht erklärt | TMP auch bei vollständigem Ordnerexport möglich | Ansicht und rekursiver Export haben andere Semantik |
| Rettbarkeit | Hinweise, keine Garantie | Bestehender Warntext bleibt | Metadatenbeurteilung ≠ Inhaltsintegrität |
| Partitionsprüfung | Nur Metadatenprüfung, keine Reparatur | Bleibt unverändert | Inhalt trifft weiterhin zu |
| Fehlertolerante Suche | Nur Images | Bleibt unverändert | In GUI wird physische Quelle abgewiesen |

## Nicht vollständig durch Tests abgedeckt

- Unter Windows: physische Lesefehler, 4Kn-/USB-Bridges, UAC, Virenscanner und Berechtigungen.
- Echtes Btrfs/XFS mit beschädigten Bäumen, RAID und Snapshot-Sonderfällen.
- Komprimierte, verschlüsselte und spezialisierte Dateisystemfeatures.
- Die sechs Sprachen umfassen technische Meldungen nicht vollständig; unbekannte Fehler bleiben bewusst im Original.
