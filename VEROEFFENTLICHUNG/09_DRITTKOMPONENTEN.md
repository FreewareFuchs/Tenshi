# Hinweise zu Laufzeit- und Paketierkomponenten

- Der Anwendungsquellcode von Tenshi 3.0.2 benennt die **Python-Standardbibliothek** als einzige Laufzeitabhängigkeit. Die spätere ausführbare Datei kann Python-Komponenten enthalten; Lizenzen aller tatsächlich mitgelieferten Dateien sind vor dem Versand zu prüfen.
- **PyInstaller** erzeugt die Windows-EXE. PyInstaller steht überwiegend unter GPL-2.0-or-later mit Bootloader-Ausnahme. Die Ausnahme erlaubt die Verteilung damit erstellter Programme unter anderen Lizenzen, sofern übrige Abhängigkeiten korrekt lizenziert sind. Für Modifikationen an PyInstaller gelten eigene Regeln. Aktuelle Angaben: https://pyinstaller.org/en/stable/license.html und https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt
- **Inno Setup** wird zum Bau des Installers verwendet. Die Lizenz der installierten konkreten Inno-Setup-Version und gegebenenfalls gebündelter Installer-Bestandteile überprüfen: https://jrsoftware.org/isinfo.php
- **Tenshi-Logo, Icons und sonstige Designressourcen:** Rechte für die öffentliche Weitergabe vorab feststellen. Im Projekt vorhandene Assets sind kein eigenständiger Nachweis einer erlaubten Weitergabe.
- **Freeware** bezeichnet kostenlose Nutzung, legt aber *nicht* von selbst fest, ob der Quellcode bearbeitet/weitergegeben werden darf. Eine passende Lizenz ausdrücklich auswählen, bevor Quellcode öffentlich gestellt wird.

Diese Hinweise sind eine Bestandsaufnahme und ersetzen keine vollständige Software-Lizenzprüfung des tatsächlich auf Windows gebauten Binärpakets.
