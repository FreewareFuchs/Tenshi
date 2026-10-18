# Tenshi 3.0.2 Beta – MIT / GitHub-Vorbereitung

Dieses Paket ist eine **Vorbereitung** für die MIT-Veröffentlichung, noch keine öffentliche Freigabe.

## Unbedingt vor der Veröffentlichung

1. In `LICENSE` steht jetzt `Copyright (c) 2026 FreewareFuchs` als vom Herausgeber gewähltes Entwickler-Pseudonym. **Vor der Veröffentlichung sicherstellen**, dass dieser Name tatsächlich als Pseudonym der berechtigten Person verwendet wird und alle urheberrechtlich relevanten Rechte vorliegen; die Identität intern nachvollziehbar dokumentieren.
2. Rechte an `recoverydesk/assets` (Logo und Icons) und an möglicherweise fremden Code-/Textbestandteilen sowie die Lizenzpflichten tatsächlich mitgelieferter Drittkomponenten prüfen (`THIRD_PARTY_NOTICES.md`).
3. Den alten Freeware-Lizenzentwurf aus dem Releaseprozess entfernen. Nur die **MIT-Lizenz** als Open-Source-Lizenz des eigenen Codes verwenden; verbindliche Rechte Dritter bleiben unberührt.
4. Windows-EXE und Installer/Portable-Paket nach der Änderung erneut erzeugen und prüfen. **Nur** die aus dieser Projektkopie erstellten Pakete veröffentlichen; ältere 3.0.2-Pakete enthalten möglicherweise keinen MIT-Hinweis.
5. `python open_source_preflight.py` ausführen. Das Skript prüft technische Platzhalter und Lizenzmitgabe, **nicht** den tatsächlichen Rechtsbesitz.
6. Betreiberangaben, Datenschutz, Spenden/Steuern und den Hinweis auf unsignierte Windows-Pakete prüfen.

## GitHub – einfachster Weg unter Windows

1. https://github.com registrieren und https://desktop.github.com/ installieren.
2. Das Verzeichnis `Tenshi` aus diesem ZIP auf eine lokale Festplatte entpacken.
3. GitHub Desktop öffnen: **File > Add Local Repository** und den Tenshi-Ordner wählen. Falls es noch kein Git-Repository ist, dort **Create a Repository** nutzen.
4. Vor dem ersten Commit `git status` prüfen: keine persönlichen Exporte, Datenträger-Images, `.tenshi-session` oder Protokolle mit hochladen.
5. Änderungen committen, **Publish repository**, zunächst **Keep this code private** aktivieren.
6. Lizenz und Rechte/Buildergebnisse prüfen; danach Repo auf **Public** stellen.
7. Auf GitHub unter **Releases > Draft a new release** den Tag `v3.0.2-beta` verwenden und das portable ZIP, den Installer sowie `SHA256SUMS.txt` aus `VEROEFFENTLICHUNG/UPLOAD` anhängen. **Set as pre-release** wählen.
8. GitHub-Release von deiner Webseite **FreewareFuchs** verlinken.

## Für Windows-Binärdateien

`RELEASE_WINDOWS_ERSTELLEN.bat` prüft die MIT-Lizenz und stoppt, falls ein Lizenz-Platzhalter enthalten ist. Es folgen Tests, Build, Portabilitätsprüfung und Packaging. Beachte `VEROEFFENTLICHUNG/01_START_HIER.md`.

## Grenzen der Lizenz

Die MIT-Lizenz erlaubt auch kommerzielle Nutzung und geschlossene Weiterentwicklungen. Wer Tenshi weitergibt, muss die entsprechenden Lizenz- und Copyright-Hinweise beibehalten. Freiwillige Spenden sind unabhängig von der Lizenz möglich, steuerlich aber gesondert zu beurteilen.
