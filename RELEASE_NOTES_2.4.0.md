# Tenshi 2.4.0 – Versionshinweise

## Enthaltene Verbesserungen

1. Neue Schaltfläche **◐ Darstellung** mit den Optionen **Hell** und **Dunkel**; Wechsel zur Laufzeit.
2. Speicherung von Fenstergröße und -position, Ordnerbaum-Verhältnis und individuellen Tabellenbreiten.
3. Partitionsübersicht mit Plausibilitätszusammenfassung und horizontaler Scrollleiste.
4. Beibehaltung des Tenshi-Logos, der sechs Sprachen und der grünen Stapel-Export-Schaltfläche.
5. Bestehender schreibgeschützter Zugriff auf Quelldatenträger bleibt unverändert.

## Technische Umsetzung

- Neues Modul `recoverydesk/ui_preferences.py` für eingeschränkte/validierte UI-Einstellungen.
- Speichert zusammen mit Sprache in der bisherigen Tenshi-`settings.json`, ohne diese gegenseitig zu löschen.
- Für gespeicherte Geometrien, Tabellenbreiten und Sash-Anteile werden Grenzen geprüft.
- Der Datenrettungsindex und Quelldatenträgerpfade werden nicht in UI-Einstellungen gespeichert.
- Hell-/Dunkelmodus betrifft Tenshi-eigene Tk-/ttk-Elemente; native Windows-Dialoge können abweichen.

## Tests & Grenzen

322 von 322 automatisierten Tests bestanden unter Linux mit virtuellem Display. Windows-EXE und reale Laufwerkszugriffe sind nicht in dieser Umgebung geprüft. Partitions-Plausibilität garantiert keine Rettbarkeit und keine Datenintegrität.
