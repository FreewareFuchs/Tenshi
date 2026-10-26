# Release-Paket automatisch vorbereiten

Unter GitHub Actions **Prepare release bundle (no publishing)** manuell starten,
den gewünschten Branch und `stable` für eine stabile Ausgabe oder `beta.N` für
eine Vorabversion auswählen. Die Basisversion stammt aus `recoverydesk/__init__.py`. Es wird kein Tag oder Release angelegt.

Der Workflow führt die bestehenden vollständigen Linux- und Windows-Prüfungen
für denselben Commit aus. Beide Builds erhalten dieselbe explizite Release-Kennung;
das DEB erhält die dazu passende Debian-Version. Erst wenn beide Jobs erfolgreich
sind, entsteht das Actions-Artefakt `Tenshi-prepared-release` mit:

- Windows-Installer und Portable-ZIP; bei `stable` ohne Beta-Suffix, bei `beta.N` mit entsprechendem Suffix
- Linux-DEB
- SHA256SUMS.txt und release_manifest.json mit vollständigem Commit
- RELEASE_NOTES.md mit beschrifteten Download-Links als Entwurf

Die Zusammenstellung prüft die Windows-Build-Metadaten, den Portable-Inhalt und
dessen Übereinstimmung mit der separat gebauten EXE sowie Paketname, Architektur,
Version und eingebettete Build-Metadaten des DEB. Fehlende, doppelte oder abweichende
Pakete brechen den Vorgang ab. Windows-Metadaten stammen als Begleitdatei aus dem
Buildjob; die Zusammenstellung liest sie nicht erneut aus der PyInstaller-EXE.
Der Windows-Job testet die gebaute EXE separat per Smoke-Test.

Lokal auf Linux mit installiertem `dpkg-deb` lassen sich heruntergeladene,
entpackte Build-Artefakte ebenfalls prüfen:

```sh
python3 prepare_release.py --artifacts artifacts --output release_bundle \
  --release stable --commit VOLLSTAENDIGER_COMMIT_HASH
```

Das Ausgabeziel darf noch nicht existieren. Die bisherigen Windows-Skripte
bleiben verwendbar. Die Vorbereitung ersetzt keine manuellen Gerätetests.
Vor dem späteren Veröffentlichen die Änderungen in den Release-Notizen ergänzen,
die Pakete auf Windows/Linux testen und die Prüfsummen kontrollieren. Die beschrifteten Download-Links verweisen auf die vorgesehenen späteren
Release-Assets und funktionieren erst nach deren Veröffentlichung. Actions-Artefakte innerhalb ihrer Aufbewahrungsfrist
herunterladen. Der Workflow besitzt ausschließlich lesende Repository-Rechte.

## Versionsangaben zentral abgleichen

Die Programmversion wird ausschließlich in `recoverydesk/__init__.py` geändert.
Danach die abgeleiteten Windows-/Installer-/CI-Angaben erzeugen:

```bash
python3 sync_release_version.py --write
python3 sync_release_version.py --check
```

Die Änderungen prüfen und gemeinsam committen, bevor ein Release-Build mit
sauberem Git-Stand gestartet wird. Der Abgleich ändert keine Tags, Releases,
Quellgeräte oder bereits veröffentlichten Pakete. Historische Release-Notizen
und Abhängigkeiten werden nicht umnummeriert. Die Debian-Paketrevision bleibt
als separate Paketierungsangabe in `build_deb.py` bestehen.

Der Windows-Build und die drei CI-Workflows prüfen den Abgleich vor dem Bau.
Veraltete oder fehlende Versionsfelder stoppen den Vorgang. Die Tests für
Build-Kennung und Paketinhalt verwenden die Programmversion statt einer
separaten festen Release-Nummer. Zusätzliche Tests simulieren eine künftige
Version und prüfen die daraus entstehenden Windows-Ressourcen, Dateinamen
und Actions-Artefakte sowie den Abbruch ohne Teiländerungen bei ungültigen
Eingaben. Die bekannten Build-Einstiegspunkte bleiben verwendbar.

## Stabile Version 3.0.2

Die [veröffentlichte 3.0.2](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.2) wurde mit `stable` vom Commit `abfd4c973a253c2a8571d238e15a0fb77b013dec` erstellt ([Workflow](https://github.com/FreewareFuchs/Tenshi/actions/runs/40242121217)). Sie enthält `Tenshi_Setup_3.0.2_Win64.exe`, `Tenshi_Portable_3.0.2_Win64.zip`, `tenshi_3.0.2-1_all.deb` und `SHA256SUMS.txt`. Die Debian-Metadaten enthalten Version `3.0.2-1`, der Git-Tag ist `v3.0.2`. Der Workflow selbst erstellt weiterhin weder Tags noch Veröffentlichungen.


## Stabile Version 3.0.3

[Finaler Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40363573058) aus Commit `18d973dd88346157da8e3bbf9856bc44ebe71f25` mit Kennung `stable`.
Veröffentlicht als [v3.0.3](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.3).
Das Release enthält `Tenshi_Setup_3.0.3_Win64.exe`, `Tenshi_Portable_3.0.3_Win64.zip`, `tenshi-recovery_3.0.3-1_all.deb` und `SHA256SUMS.txt`. [Pakettests und Grenzen](../RELEASE_NOTES_3.0.3.md).

Die finalen Pakete wurden manuell bestätigt. Die APT-Quelle ist veröffentlicht und die erneute Installation daraus geprüft. Ein gesonderter Upgrade-Test von installierter 3.0.2-2 über die öffentliche Quelle bleibt offen. Bestehende Dateien älterer Releases wurden nicht ersetzt.
