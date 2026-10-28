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

## Langsame Größenänderungen durch Bildkacheln

Das Bündeln der Configure-Callbacks allein beseitigte die gemeldete Trägheit
nicht. Ein lokaler Windows-Vergleich mit derselben leeren Dateiansicht und
40 Größenänderungen benötigte mit unveränderten Sun-Valley-Flächen ca. 33,5 s,
mit clam ca. 5,1 s. Selbst ohne Tenshis Layout-, Umbruch- und Übersetzungs-
Callbacks brauchte Sun Valley noch ca. 24,9 s. Diese Messung umfasst synchrone
Fenster- und Zeichenarbeit; sie ist keine Aussage zur Bildrate auf jedem System.

Die Anpassung in `appearance._native_surfaces` kopiert einmal je Farbvariante
die portablen clam-Elemente für Notebook, Tabellenflächen und -köpfe, Rahmen,
Eingabefelder, Comboboxen, Trennlinien und Bildlaufleisten. Sie erhalten die
Sun-Valley-Farben einschließlich Fokus, deaktiviertem Zustand und Auswahl.
Schaltflächen und Auswahlhäkchen behalten die Sun-Valley-Grafiken. Schrift,
Quellenleser und Scanablauf bleiben unverändert. Die Originaldateien des Themes
werden nicht bearbeitet. Die clam-Layouts werden beim Start einmal gelesen und
zwischengespeichert; dabei erfolgt kein Zeichnen oder Verarbeiten von Ereignissen.
Spätere Farbwechsel benötigen keinen Wechsel zu clam.

Upstream-Hinweis zur Kachelgröße:
https://github.com/rdbende/Sun-Valley-ttk-theme/issues/106

Die endgültige Beurteilung der Reaktion beim Ziehen mit der Maus erfordert
weiterhin den Test auf der Mint-VM; der Windows-Vergleich ersetzt diesen nicht.
