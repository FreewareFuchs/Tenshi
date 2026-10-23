# Versions- und Build-Anzeige

Fenstertitel, Offline-Hilfe unter „Über Tenshi“ und `--version` zeigen dieselbe Kennung. Die technische Programmversion bleibt `3.0.2`, damit bestehende Dateiformate und Paketprüfungen kompatibel bleiben.

- Beispiel eines veröffentlichten, sauber getaggten Builds: `3.0.2 Beta.5 (0123456789)`.
- Ein Entwicklungsstand nach der zuletzt deklarierten Beta: `3.0.2 Beta.4+dev (0123456789)`.
- Lokale Änderungen werden zusätzlich mit `+dirty` am Commit markiert.
- Ohne Git oder eingebettete Kennung steht anstelle des Commits `?`; der Stand wird nicht als bestätigter Release ausgegeben.

`Beta.4+dev` bezeichnet die Entwicklungsbasis nach Beta.4 und keine Veröffentlichung von Beta.5. Beim nächsten Release muss die Basis `__release__` in `recoverydesk/__init__.py` zusammen mit der Paketversion fortgeschrieben werden.

Beim Quellcodestart wird ausschließlich die Git-Verwaltung des Anwendungsverzeichnisses gelesen. Die Dateien werden nicht verändert. Die Kennung bleibt während eines laufenden Prozesses stabil; nach einem Quellenupdate Tenshi neu starten.

Beim Windows-Bau erzeugt `write_build_info.py` die Datei `build/identity/recoverydesk/_build_info.json`; PyInstaller bettet sie ein. Das DEB erhält dieselbe Metadatenstruktur direkt im temporären Paketverzeichnis. Installierte Anwendungen benötigen Git nicht und versuchen nicht, eine zufällige übergeordnete Git-Verwaltung als eigenen Build auszugeben.

Für einen ausdrücklich bezeichneten Release-Build kann `write_build_info.py --release beta.5` verwendet werden; das erfordert einen bekannten Commit und einen unveränderten Arbeitsbaum. Das DEB unterstützt entsprechend `build_deb.py --package-version 3.0.2~beta.5-1 --release beta.5`; Paketversion und explizite Release-Kennung müssen zusammenpassen. Ein exakt passender Git-Tag wird ebenfalls erkannt. Ungetaggte CI-Builds bleiben ausdrücklich Entwicklungsstände; der Debian-Paketname allein macht einen Build nicht zum veröffentlichten Release.

Bei einem Windows-Release kann vor `build_windows.bat` die Build-Variable `TENSHI_RELEASE=beta.5` gesetzt werden. Sie wird ausschließlich beim Erzeugen der Metadaten berücksichtigt, nicht beim späteren Start der Anwendung. Ohne ausdrückliche Angabe bleibt ein ungetaggter Build als Entwicklung gekennzeichnet.

Build-Metadaten enthalten nur Programmversion, Beta-Kennung, Commit und Statusflags. Lokale Pfade, Benutzernamen und Repository-Adressen werden nicht eingebettet.
