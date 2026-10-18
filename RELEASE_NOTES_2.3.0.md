# Tenshi 2.3.0 – Versionshinweise

Die neue Export-Vorabprüfung wertet die bereits eingelesenen Metadaten der ausgewählten Dateien und Ordner aus und erstellt eine nachvollziehbare Aufstellung. Sie greift **nicht schreibend** auf die Quelle zu. Bei NTFS können eindeutig widersprüchliche Streamlängen oder Clusterzuordnungen vor dem Export erkannt und für den Stapel-Export gesperrt werden. Der echte Inhalt wird bei der Vorabprüfung nicht erneut gelesen; für Einzeldateien steht die separate Leseprüfung zur Verfügung.

**Neue Bedienung:** Unter „Dateien & Ordner“ Dateien/Ordner markieren → im Bereich „Wiederherstellungswarteschlange“ „Export prüfen“ anklicken. Prüfbericht kann als neue Textdatei gespeichert werden. Erst danach „Stapel-Export / fortsetzen“ starten.

**Grenzen:** Die Prüfung kann keine überschriebene Datei erkennen, wenn ihre Metadaten plausibel erscheinen. Verwaiste Ordnerpfade sind teils nur als Warnhinweis feststellbar. Es gibt keine Schreib-Reparatur von Partitionen oder Dateisystemen.

**Tests:** 316 automatisierte Tests unter Linux mit synthetischen Abbildern. Die Windows-EXE wird nicht mitgeliefert; Build und Tests unter Windows erfolgen separat über die enthaltenen Batchskripte. Praxistest auf Windows-Hardware steht aus.
