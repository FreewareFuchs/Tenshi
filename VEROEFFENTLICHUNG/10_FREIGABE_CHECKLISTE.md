# Checkliste – vor dem ersten öffentlichen Download

## Technische Freigabe

- [ ] Neue 3.0.2-Windows-EXE auf Windows 10/11 64 Bit erfolgreich gebaut, Smoke-Test bestanden.
- [ ] Windows-Tests erneut erfolgreich und Abweichungen dokumentiert.
- [ ] Portable-Archiv durch `release_tools.py verify` bestätigt.
- [ ] Installer aus aktuellem Build installiert, gestartet und deinstalliert.
- [ ] Unkritisches MBR/GPT-Testimage automatisch eingelesen, Dateiexport und `Tenshi_Export_*/files/` kontrolliert.
- [ ] SHA-256 der herunterladbaren **fertigen Pakete** aus `VEROEFFENTLICHUNG/UPLOAD/SHA256SUMS.txt` auf Downloadseite veröffentlicht.
- [ ] Download und Prüfsummen von separatem Rechner/Browser nachvollzogen.
- [ ] Sicherheitssoftware-Ergebnis und fehlende digitale Signatur berücksichtigt.
- [ ] Upload enthält keine privaten Bilddateien, Sitzungen, Logs, Nutzerpfade oder Testdaten.

## Rechtliche Freigabe

- [ ] MIT als Lizenz gewählt: Copyright-Rechteinhaber in `LICENSE` korrekt eingesetzt; `python open_source_preflight.py` erfolgreich; keine widersprüchlichen Freeware-Beschränkungen.
- [ ] MIT-Lizenz in GitHub-Projekt, Portable-ZIP und Installer enthalten; Lizenzinformationen der tatsächlich ausgelieferten Drittkomponenten geprüft.
- [ ] Recht zur Verwendung des Logos und aller Assets geklärt.
- [ ] Tatsächliche Betreiber- und Kontaktdaten für ggf. nötiges Impressum eingesetzt.
- [ ] Datenschutzangaben passend zum Hoster, Logs und Spendenanbieter erstellt.
- [ ] Rechtliche/steuerliche Bewertung freiwilliger Zahlungen durchgeführt; keine Steuerfreiheit behauptet.

## Öffentlich sichtbare Angaben

- [ ] Name/Version `Tenshi 3.0.2 Beta`; Windows 10/11 x64.
- [ ] Downloadlinks nur zu real hochgeladenen Dateien.
- [ ] Experimentelle Grenzen, Datenrettungsrisiken, kein garantiertes Ergebnis.
- [ ] Download kostenlos; Unterstützungslink nur freiwillig.
- [ ] Anleitung DE/EN, Versionstext und Kontaktmöglichkeit.
