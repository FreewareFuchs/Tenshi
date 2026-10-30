# Erweiterte Dateivorschau und Inhaltsprüfung

Für 3.0.11 vorgesehen. Der vollständige Funktionsstand ist manuell bestätigt; endgültige Pakete und Veröffentlichung werden vorbereitet.

## Bedienung

Eine oder mehrere Dateien auswählen und **Vorschau** öffnen.
**Zurück / Weiter** blättert nur durch die beim Öffnen erfasste Dateiauswahl.
Die Anzeige **Datei … von …** nennt die Position. Am Anfang beziehungsweise Ende
ist die jeweilige Richtung gesperrt; es gibt keinen automatischen Dateiwechsel.
Ordner werden ausgelassen. Nicht darstellbare Dateien zeigen ihren Hinweis,
bleiben aber Teil der Auswahl. Eine spätere Änderung der Hauptansicht verändert
weder Auswahl noch Quelle des geöffneten Vorschaufensters.

Ein Fenster verarbeitet jeweils nur eine Datei. Beim Wechsel wird der bisherige
Vorgang abgebrochen. Schon überholte, wartende Aufträge werden vor dem Quellzugriff
übersprungen; verspätete Ergebnisse können keine andere Datei überschreiben.
Es werden keine weiteren Dateien vorgeladen oder auf Platte zwischengespeichert.

JPEG, PNG, BMP und GIF erscheinen
verkleinert; bei PDF wird die erste Seite gezeigt. Der Bildbereich ist scrollbar,
damit bei kleinen Fenstern keine Bereiche unerreichbar bleiben. Text bleibt auf
128 KiB begrenzt. Für DOCX ist ein begrenzter Textauszug möglich; eine vollständige
Office-Darstellung ist nicht enthalten. XLSX/PPTX werden als Container geprüft;
aus ihrer Hauptstruktur entsteht keine Tabellen- oder Folienvorschau.

Unter **Datei prüfen → Inhalt prüfen** wird derselbe Prüfkern ohne Bildausgabe
verwendet. Die bisherige **vollständige Leseprüfung** und ihre SHA256 bleiben
separate Aktionen. Zwei Prüfungen desselben Dialogs laufen nicht gleichzeitig.
**Prüfung abbrechen** und Schließen des Fensters stoppen die Verarbeitung.

Im **Ergebnisbericht → Exportierte Datei prüfen …** lässt sich dieselbe Prüfung
auf eine Datei im Exportziel anwenden. Die Auswahl beginnt im Unterordner `files`.
Dabei werden weder ursprüngliche Quelle noch Exportbericht oder SHA-Dateien
verändert. Dieser Weg vermeidet zusätzliche Lesezugriffe auf das Quellmedium.

## Was das Ergebnis bedeutet

- **Struktur lesbar**: Bilddaten konnten dekodiert werden oder die ZIP-Prüfsummen
  und XML-Strukturen des Office-Pakets sind lesbar. Das bestätigt keine intakten
  Originalinhalte, vollständige Dokumentsemantik oder korrekte Darstellung.
- **Teilprüfung**: Bei PDF wurde nur die erste Seite gerendert. Weitere Seiten,
  Anhänge und aktive Inhalte bleiben ungeprüft. Bei Animationen gilt das Ergebnis
  nur für das erste Bild.
- **Nicht als unterstütztes Format lesbar**: Eine Beschädigung oder ein anderer
  tatsächlicher Dateityp ist möglich. Dateiendungen allein sind kein Formatbeweis.
- **Prüfgrenze erreicht / Nicht geprüft**: Aus dieser Anzeige darf kein
  Dateischaden abgeleitet werden. Legacy-Office/OLE, nicht unterstützte Formate
  und geschützte Container werden nicht als bestätigter Schaden ausgegeben.
- **Verschlüsselt / geschützt**: Es erfolgt keine Entschlüsselung und keine
  Passwortabfrage. Bei ZIP wird auf die vorhandene Prüfung im Exportbericht
  verwiesen.

Ein erfolgreich dekodiertes Bild kann trotzdem fremde, ersetzte oder inhaltlich
beschädigte Pixel enthalten. Die Prüfung vergleicht nicht mit einer bekannten
Originaldatei. Sie erweitert weder die Löschrettung noch die Dateisuche.

## Grenzen und Verarbeitung

Die Quelle wird nur lesend geöffnet. NTFS-Inhalte hinter InitializedSize werden
wie beim Export als logische Nullen behandelt. Lesefehler und unvollständige
Datenströme werden gemeldet. Es gibt keine Indexkopie und keinen Vorschau-Cache
auf einem Quell- oder Zieldatenträger.

- Erweiterte Vorschau/Inhaltsprüfung: höchstens 32 MiB Eingabe pro Datei.
- Bilder: höchstens 20 Millionen Pixel, Ausgabe höchstens 720 × 360 Pixel.
- Office: DOCX/XLSX/PPTX, höchstens 2000 ZIP-Einträge, zusammen 32 MiB entpackt,
  XML-Teil höchstens 2 MiB. Hauptbeziehungen und Inhaltstyp werden geprüft;
  DTDs, externe Entitäten, mehrdeutige Namen und ungewöhnliche Paketpfade werden
  nicht akzeptiert. Dateien werden nicht aus dem ZIP auf die Platte entpackt.
- Verarbeitung in einem beendbaren separaten Prozess: 15 Sekunden Gesamtfrist,
  768 MiB Speichergrenze; unter Linux zusätzlich CPU-Grenze. Unter Windows
  begrenzt ein Job Object auch die Lebensdauer des Prozessbaums. Unter Linux
  beendet Abbrechen die eigene Prozessgruppe einschließlich PDF-Werkzeugen.
- Links, Makros und Dokumentaktionen werden nicht ausgeführt. Die Prozessgrenzen
  sind keine vollständige Sicherheitsisolierung gegen Bibliotheksschwachstellen.

Vorschau und Inhaltsprüfung verursachen zusätzliche Lesezugriffe. Bei physisch
instabilen Medien möglichst zunächst ein geeignetes Image erstellen.

## Paketierung und Prüfung

Windows und Flatpak verwenden hashgebundene Pillow-/PDFium-/defusedxml-Pakete.
Das native DEB bleibt architekturunabhängiger Python-Code; Pillow, defusedxml
und Poppler werden als Distributionsabhängigkeiten installiert. Es enthält
keine eingebettete PDFium-Binärbibliothek. Lizenzen und Herkunft stehen unter
`recoverydesk/assets/content_licenses/` und in den Drittkomponentenhinweisen.
Portable-ZIPs enthalten die vollständigen Texte zusätzlich als
`THIRD_PARTY_NOTICES.txt`; Installer legen sie unter `licenses/content` ab.

Die Paket-Startprüfung dekodiert kleine JPEG-, PNG-, BMP-, GIF-, PDF- und
Office-Referenzen tatsächlich im separaten Prozess, auch in der Windows-EXE
ohne Konsolenfenster. Automatische Tests prüfen beschädigte und begrenzte
Eingaben, Passwortschutz, unveränderte Quellen, Abbruch, Prozessende,
sechs Sprachen und kleine Fenster. Das ersetzt keine Hardwareabnahme.
