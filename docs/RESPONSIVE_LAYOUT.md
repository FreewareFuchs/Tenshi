# Fortschrittsanzeige und Fenstergrößen

Die Statuszeile wird am unteren Fensterrand reserviert, bevor der ausfüllende
Hauptbereich seinen Platz erhält. Der Einlesezähler bleibt so auch bei
1024 × 650 sichtbar, einschließlich aufgeklappter Exportwarteschlange.
Kleine Fenster reduzieren dekorative Abstände und blenden den langen,
wiederholten allgemeinen Sicherheitstext in der Fußzeile aus. Quellauswahl,
Dateiansicht, Hilfe und Bestätigungen behalten ihre Hinweise und Funktionen.

Kopftext-Umbrüche und das Belegungsdiagramm bündeln Resize-Ereignisse in
40-ms-Abständen. Unveränderte Umbruchbreiten und Diagrammzustände lösen keine
erneute Konfiguration aus. Der Diagrammtext wird nur bei einer tatsächlichen
Änderung gesetzt. Scanstatus-Meldungen werden auf höchstens zehn Zwischenstände
pro Sekunde begrenzt; Abschlussmeldungen und Ergebnis-/Fehlercallbacks bleiben
in ihrer bisherigen Reihenfolge. Es werden weder Lesearbeit noch Abbruch- oder
Sicherheitsprüfungen des Scanners reduziert.

Referenzsuche: Die vorhandene lokale XERJ-Suche im Index `tenshi-*` fand die
frühere Lösung in `recoverydesk/gui.py`, `_build_export_queue` (Indexfund ab
Zeile 2693): Fortschritt vor dem expandierenden Browser einpacken. Der Index
enthält einen älteren Tenshi-Stand; das Muster wurde am aktuellen Code geprüft
und auf die allgemeine Statuszeile übertragen. Keine Indexaktualisierung oder
externe Rückmeldung wurde ausgelöst.

Tests: laufender synthetischer Scan mit 10.001 Fortschrittsmeldungen, sichtbarer
Status bei Größenwechseln und ausgeklappter Warteschlange, gebündelte Resize-
Arbeit und unveränderte Diagrammdaten. Die Linux-Matrix prüft beide Farbvarianten,
sechs Sprachen sowie kleine und große Fenster mit unterschiedlicher Skalierung.
Die installierte Tk-9-Flatpak-Oberfläche prüft die Statuszeile auch bei 1024 × 650.
