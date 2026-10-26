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

## Stabile Version 3.0.2

Die [veröffentlichte 3.0.2](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.2) wurde mit `stable` vom Commit `abfd4c973a253c2a8571d238e15a0fb77b013dec` erstellt ([Workflow](https://github.com/FreewareFuchs/Tenshi/actions/runs/40242121217)). Sie enthält `Tenshi_Setup_3.0.2_Win64.exe`, `Tenshi_Portable_3.0.2_Win64.zip`, `tenshi-recovery_3.0.2-2_all.deb` und `SHA256SUMS.txt`. Die Debian-Metadaten enthalten Version `3.0.2-1`, der Git-Tag ist `v3.0.2`. Der Workflow selbst erstellt weiterhin weder Tags noch Veröffentlichungen.
