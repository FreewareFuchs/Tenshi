# Veröffentlichung in FreewareFuchs – praktische Reihenfolge

1. Projekt direkt aus diesem ZIP nach Windows entpacken. Falls Tenshi 3.0.2 bereits auf dem Rechner liegt, eine **neue** Arbeitskopie verwenden. Keine alten Exportordner, Datenträger-Images oder persönlichen Sitzungen mit hochladen.
2. Für den ersten Build `check_windows.bat` und `run_tests.bat` ausführen oder das kombinierte `RELEASE_WINDOWS_ERSTELLEN.bat` starten (nach Ausfüllen des Copyright-Felds in `LICENSE`). Der kombinierte Ablauf stoppt bei Fehlern.
3. `build_windows.bat` erzeugt `dist\Tenshi.exe`; `build_portable.bat` erzeugt `portable_output\Tenshi_Portable_3.0.2_Win64.zip`; `build_installer.bat` erzeugt `installer_output\Tenshi_Setup_3.0.2.exe`.
4. Das Skript `release_finalize.py` prüft beide PE-Dateien, das Portable-Archiv und die zugrunde liegende EXE-Prüfsumme. Es kopiert in `VEROEFFENTLICHUNG\UPLOAD` und erzeugt `SHA256SUMS.txt` + `release_manifest.json`. Ein Gleichheitsvergleich ersetzt keine digitale Signatur oder Virenprüfung.
5. Installations- und Deinstallationstest der **neu gebauten Version**, portable Startprüfung, Quellwechsel/Auto-Schnellscan, NTFS/FAT32/exFAT/ext4 und Export im Test-Image wiederholen.
6. Seite `04_FREEWAREFUCHS_TEXTE.md` übernehmen. Downloads auf die tatsächlich hochgeladenen Artefakte verlinken. Die darin beschriebenen Grenzen und fehlende Signatur offen nennen.
7. MIT-Lizenz im Projektstamm `LICENSE` mit dem tatsächlichen Rechteinhaber ausfüllen. `python open_source_preflight.py` ausführen. Rechte an Assets und Drittkomponenten, Impressum und Datenschutz manuell prüfen. **Erst dann** öffentlich freigeben.

**Wichtig:** Die internen Namen `recoverydesk/` und `recoverydesk_status.json` sind aus Kompatibilitätsgründen unverändert. Neue Exportaufträge verwenden `Tenshi_Export_*`, bestehende `RecoveryDesk_Export_*` bleiben fortsetzbar. Im Ordner `files` liegen die exportierten Dateien.
