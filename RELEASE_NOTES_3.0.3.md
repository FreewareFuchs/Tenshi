# Tenshi 3.0.3 – stabil veröffentlicht (26.10.2026)

[GitHub-Release v3.0.3](https://github.com/FreewareFuchs/Tenshi/releases/tag/v3.0.3)

- Die SHA256-Berechnung beim Stapel-Export und bei der Prüfung vorhandener Exporte lässt sich abbrechen. Vollständig geschriebene Dateien bleiben erhalten; unvollständige Prüfungen erhalten keinen Erfolgsstatus. Unbestätigte vorhandene Dateien werden weiterhin nicht überschrieben.
- Windows-Installer und Portable-ZIP verwenden Version 3.0.3. Linux verwendet Paketname und Startbefehl `tenshi-recovery`, Paketversion `3.0.3-1`. Diese sortiert nach `3.0.2-2`.
- Die signierte FreewareFuchs-APT-Quelle bietet das geprüfte Paket an; die [Einrichtung](docs/APT_REPOSITORY.md) bleibt unverändert.

## Build und manuelle Prüfung

[Finaler Build](https://github.com/FreewareFuchs/Tenshi/actions/runs/40363573058) aus Commit `18d973dd88346157da8e3bbf9856bc44ebe71f25` mit Kennung `stable`.
Linux-/Windows-CI und gemeinsame Paket-/Prüfsummenprüfung erfolgreich.

Der Nutzer bestätigte die finalen Pakete unter Linux sowie Windows-Installer und Portable-Version: Start, Versionsanzeige, Image einlesen, Export und Original-/Export-SHA256-Vergleich. Der Abbruch während der SHA256-Prüfung wurde zuvor mit dem Funktionsstand aus PR #47 unter beiden Systemen bestätigt.

Die SHA256-Werte aller drei Pakete wurden bestätigt. Das Linux-Paket wurde lokal installiert und anschließend erneut aus der öffentlichen APT-Quelle installiert. Öffentlicher Schlüssel, InRelease-Signatur, Index-Hash, DEB-Größe und DEB-Hash wurden geprüft. Der Versionsvergleich ist bestätigt; ein tatsächliches Upgrade von einer noch installierten 3.0.2-2 über die öffentliche Quelle ist damit nicht gesondert belegt.

## Linux-Paket

Datei: `tenshi-recovery_3.0.3-1_all.deb` (740270 Bytes)

SHA256:
```text
153ec71e9597f614f7d1adf610db3486cc91b7d20745a1573af1d8e072aa1a34
```

Die Downloadseiten und Anleitungen in sechs Sprachen sowie der Softwarekatalog wurden auf 3.0.3 aktualisiert und nach dem Upload geprüft.

Quellen weiterhin ausschließlich lesend verwenden; Exporte und Images auf einem anderen physischen Datenträger speichern. Eine Prüfsumme garantiert keine erfolgreiche Wiederherstellung. Allgemeine Tests beschädigter Hardware werden durch die Pakettests nicht ersetzt. Windows-Installer und EXE sind nicht digital signiert.

Die veröffentlichten Pakete bleiben unverändert. Die nachträgliche Dokumentation der Freigabe ändert ihren Quellstand nicht.
