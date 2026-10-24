# Gerätewechsel bei gleicher Quellenadresse

Die Dateisystemanalyse in der Oberfläche erfasst vor dem Lesen eine Gerätekennung und vergleicht sie nach dem Scan erneut. Der veröffentlichte Index behält diese Kennung nur im Arbeitsspeicher. Die Vorschau prüft sie vor und nach dem Lesen. Der Stapel-Export vergleicht die Kennung des Index mit der aktuellen Quelle, bevor er einen Exportordner anlegt.

Bei Geräten besteht die Kennung aus Größe, logischer Sektorgröße und dem gewählten Partitionsoffset sowie verfügbaren Zusatzmerkmalen:

- Windows: SHA-256 der vom Gerät gemeldeten Seriennummer aus `IOCTL_STORAGE_QUERY_PROPERTY`. Fehlende oder nicht unterstützte Seriennummern bleiben ausdrücklich ohne Kennung.
- Linux: Gerätenummer und verfügbare sysfs-Werte `diskseq`, `device/serial` und `wwid`. Die Zusatzwerte werden gehasht. Für Partitionen werden die Merkmale des übergeordneten Datenträgers verwendet.
- Stabile Volume-IDs aus erkannten NTFS-, FAT32- und exFAT-Bootsektoren am Quellenanfang und am Partitionsoffset. Veränderliche Belegungszähler werden nicht verglichen.

Alle Gerätezugriffe sind lesend; es gibt keine Sperrung, Aushängung oder Reparatur. Seriennummern werden nicht im Klartext in den Exportstatus geschrieben.

Während des Stapel-Exports wird die Kennung an Datei- und Schreibfortschrittsgrenzen höchstens zweimal pro Sekunde erneut abgefragt. Zusätzlich erfolgt bei jedem letzten Dateiblock eine Prüfung, bevor die Datei als erfolgreich abgeschlossen wird. Eine erkannte Änderung während des Schreibens entfernt die aktuelle Ausgabedatei, vermerkt einen Fehler und beendet den Auftrag. Bereits abgeschlossene Dateien bleiben erhalten. Ein erneuter Scan ist erforderlich, wenn die Kennung nicht mehr zum Index passt.

Die Gerätekennung gehört zur Identität des gespeicherten Stapelauftrags. Ältere Geräteaufträge ohne diese Kennung werden nicht unter ihrer bisherigen Signatur fortgesetzt. Image-Aufträge behalten ihr bisheriges Identitätsformat.

## Grenzen

Dies ist eine zusätzliche Konsistenzprüfung, kein Beweis der Datenträgeridentität oder intakter Dateien. Seriennummern können fehlen oder mehrfach vergeben sein; geklonte Datenträger können dieselben Volume-IDs besitzen. Auf Windows ohne nutzbare Seriennummer und ohne erkannte Volume-ID bleiben nur Geometrie und Offset. Die Linux-`diskseq` kann einen erneuten Anschluss erkennen, auch wenn dieselbe Seriennummer gemeldet wird.

Änderungen zwischen den Prüfzeitpunkten oder auf dem bereits geöffneten Gerätehandle sind nicht atomar ausgeschlossen. Die Prüfung ersetzt keine konsistente Offline-Quelle und keine Inhaltsprüfung nach dem Export. Frühere erfolgreich abgeschlossene Exporte werden nicht rückwirkend verworfen.

Die Bindung an den Analysezeitpunkt gilt für die Dateisystemanalyse der Oberfläche. Direkte API-Aufrufe ohne gebundene Indexkennung erhalten erst beim Start von `export_batch` eine Vergleichsbasis. Direkte Einzeldatei-Exporter und Imaging-Aufträge sind durch diese Änderung nicht zusätzlich abgesichert.

Die automatisierten Tests simulieren Austausch und Verbindungsverlust. Eine Hardwareabnahme unter Windows oder Linux ist damit nicht behauptet.
