# Versions- und Build-Anzeige

Fenstertitel, Offline-Hilfe unter „Über Tenshi“ und `--version` zeigen dieselbe Kennung. Die Programmversion ist `3.0.2`.

- Stabiles Release: `3.0.2 (abfd4c973a)`.
- Vorabversion, beispielsweise: `3.0.2 Beta.6 (0123456789)`.
- Ungetaggter Entwicklungsstand: `3.0.2 +dev (0123456789)`.
- Lokale Änderungen werden zusätzlich mit `+dirty` am Commit markiert.
- Ohne Git oder eingebettete Kennung steht beim Commit `?`; der Stand wird nicht als bestätigter Release ausgegeben.

Der Wert in Klammern sind die ersten zehn Zeichen des Git-Commits. Er identifiziert den genauen Quellstand und ist kein weiterer Versions- oder Beta-Zusatz. Die veröffentlichte 3.0.2 stammt aus `abfd4c973a253c2a8571d238e15a0fb77b013dec`.

Beim Quellcodestart wird ausschließlich die Git-Verwaltung des Anwendungsverzeichnisses gelesen. Die Dateien werden nicht verändert. Die Kennung bleibt während eines laufenden Prozesses stabil; nach einem Quellenupdate Tenshi neu starten.

Beim Windows-Bau erzeugt `write_build_info.py` die Datei `build/identity/recoverydesk/_build_info.json`; PyInstaller bettet sie ein. Das DEB erhält dieselbe Metadatenstruktur im temporären Paketverzeichnis. Installierte Anwendungen benötigen Git nicht und verwenden keine zufällige übergeordnete Git-Verwaltung als eigenen Build.

Explizite Kennungen sind `stable` und `beta.N` (positive ganze Zahl). Sie erfordern einen bekannten Commit und einen sauberen Arbeitsbaum:

```bash
python3 write_build_info.py --release stable
python3 build_deb.py --package-version 3.0.2-1 --release stable
```

Für eine Beta passen beispielsweise `--package-version 3.0.2~beta.6-1 --release beta.6` zusammen. Exakt passende Git-Tags `v3.0.2` beziehungsweise `v3.0.2-beta.N` werden ebenfalls erkannt. Der Debian-Dateiname allein macht einen Build nicht zum veröffentlichten Release.

Unter Windows vor dem Build in einer Eingabeaufforderung:

```bat
set TENSHI_RELEASE=stable
build_windows.bat
```

Die Variable wird nur beim Erzeugen der Metadaten berücksichtigt, nicht beim späteren Start. Ohne ausdrückliche Kennung oder passenden Tag bleiben ungetaggte Builds als Entwicklung erkennbar.

Build-Metadaten enthalten nur Programmversion, Release-Kennung, Commit und Statusflags. Lokale Pfade, Benutzernamen und Repository-Adressen werden nicht eingebettet.
