# Darstellung

Tenshi verwendet Sun Valley ttk 2.6.1 mit den bisherigen Tenshi-Schriften.
Unter **Darstellung** stehen **System**, **Hell** und **Dunkel** zur Wahl.
Neue Einstellungen verwenden System; vorhandene explizite Hell-/Dunkel-Wahlen
bleiben erhalten. Der Exportbutton ist mit einer blauen Akzentfarbe hervorgehoben.

System liest unter Windows die App-Farbeinstellung, unter Linux bevorzugt das
Settings-Portal. Ohne Portal-Präferenz werden außerhalb von Flatpak die GTK-
Einstellungen von Cinnamon, Xfce bzw. GNOME gelesen. Bei nicht verfügbarer oder
unbekannter Einstellung verwendet Tenshi Hell. Innerhalb von Flatpak wird nur
das Portal verwendet; zusätzliche Geräte-, Dateisystem- oder Busrechte werden
nicht angefordert. Die Erkennung läuft im Hintergrund mit begrenzten Wartezeiten
und prüft nach jedem Durchlauf nach fünf Sekunden erneut. Manuelle Auswahl hat
Vorrang. Die System-Akzentfarbe und native Fenstertitelleiste werden nicht geändert.

Die Theme-Dateien einschließlich MIT-Lizenz werden fest mitgeliefert, ohne pip
oder Downloads beim Programmstart. Herkunft: `recoverydesk/assets/sun_valley/UPSTREAM.md`.
Tenshi lädt die beiden unveränderten Theme-Dateien direkt; der globale
Schriftwechsel des upstream `sv.tcl` wird nicht verwendet. Klassische Tk-Widgets
und die Offline-Hilfe erhalten passende Farben über die Tenshi-Palette.

Die Layout-Prüfung umfasst beide Farbvarianten, alle sechs Sprachen, kleine
Fenster und größere Schrift-Skalierung. Tatsächliche Desktop-/Portal-Erkennung
unter Linux Mint und die visuelle Abnahme bleiben zusätzlich am Zielsystem zu
prüfen. Die bereits abgenommenen 3.0.5-Archive werden nicht neu geschrieben.
