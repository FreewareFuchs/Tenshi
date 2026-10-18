# Tenshi 3.0.1 – Wartungsupdate

## Behoben

Windows-Testlogs konnten während des Tests `test_tmp_remains_hidden_across_pages_and_search` die Tk-Meldung `invalid command name ...<lambda> (after script)` enthalten, obwohl alle Tests erfolgreich waren. Ursache waren nach Fenster-Zerstörung verbleibende Tcl-`after`-Aufträge. Hauptfenster und betroffene Dialoge melden ausstehende Timer nun vor der Zerstörung ab.

## Unverändert

- Die beiden Hauptregister, die Partitions-Doppelklick-Navigation, der breite Ordnerbaum.
- Tenshi-Logo, sechs Sprachen, Hell-/Dunkelmodus, integrierte F1-Hilfe.
- Imaging, Analysesitzungen und grüne Stapel-Export-Schaltfläche.
- Quelldatenträger werden nur gelesen; keine Änderung am Wiederherstellungsformat.

## Tests und Grenzen

Die GUI-Regressionstests verwenden synthetische Datenträgerabbilder und virtuelle Linux-Anzeige. Die Windows-EXE muss mit `build_windows.bat` auf Windows erstellt werden; unter Windows `run_tests.bat` ausführen. Tests auf tatsächlichen beschädigten Datenträgern sind noch ausstehend.
