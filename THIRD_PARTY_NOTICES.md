# Drittkomponenten und Rechteprüfung

Diese Bestandsaufnahme ist **keine vollständige Rechtsprüfung**.

- **Python**: Der Quellcode nutzt die Python-Standardbibliothek und die unten genannten Inhaltsprüfungsbibliotheken. Wird Python mit der Windows-EXE gebündelt, gelten hierfür zusätzlich die einschlägigen Python-Lizenzbedingungen. https://docs.python.org/3/license.html
- **Sun Valley ttk theme 2.6.1**: Copyright (c) rdbende <rdbende@proton.me>, MIT. Unveränderte Theme-Dateien unter `recoverydesk/assets/sun_valley/theme`; vollständige Lizenz und Herkunft unter `recoverydesk/assets/sun_valley/LICENSE` und `UPSTREAM.md`. Diese Dateien werden auch in Windows-EXE, DEB und Flatpak mitgeliefert. https://github.com/rdbende/Sun-Valley-ttk-theme/tree/v2.6.1
- **PyInstaller**: Build-Werkzeug für `Tenshi.exe`; eigene Lizenzbedingungen einschließlich Bootloader-Ausnahme. https://pyinstaller.org/en/stable/license.html
- **Inno Setup**: Werkzeug für den Installer, mit eigenen Lizenzbedingungen. https://jrsoftware.org/isinfo.php
- **Tenshi-Logos und Icons**: In `recoverydesk/assets` enthalten. Rechte und mögliche Drittquellen vor der öffentlichen MIT-Veröffentlichung bestätigen. Eine MIT-Lizenzierung darf nur erfolgen, soweit die erforderlichen Nutzungsrechte bestehen.
- **Weitere Komponenten**: Die tatsächlichen Inhalte der erzeugten EXE und des Installers sind vor Upload zu untersuchen. Soweit weitere Lizenzen vorgeschrieben sind, deren Notices beilegen.

Die MIT-Lizenz des Tenshi-Projekts ersetzt keine Lizenzen oder Rechte Dritter.

## Erweiterte Vorschau und Inhaltsprüfung

- **Pillow 13.0.0**: Bilddekodierung (JPEG/PNG/BMP/GIF), HPND und enthaltene Drittbedingungen. https://python-pillow.org/
- **pypdfium2 5.14.0 / PDFium**: Windows- und Flatpak-PDF-Vorschau. BSD-3-Clause, Apache-2.0 und die enthaltenen Abhängigkeitsbedingungen; vollständige upstream Notices werden mitgeführt. https://pypdfium2.readthedocs.io/
- **defusedxml 0.7.1**: eingeschränkte XML-Verarbeitung für Office-Container, PSF-Lizenz. https://pypi.org/project/defusedxml/
- **Native Debian-Ausgabe**: `python3-pil`, `python3-defusedxml` und `poppler-utils` werden als Distributionsabhängigkeiten installiert. Deren Lizenz- und Sicherheitspflege übernimmt die Distribution. Die PDF-Werkzeuge werden als separate Programme mit festen Argumenten aufgerufen.

Übernommene Lizenztexte und Herkunft: `recoverydesk/assets/content_licenses/`.
Windows- und Flatpak-Bibliotheken sind mit Versions- und Hashbindung festgelegt.
Die MIT-Lizenz von Tenshi ersetzt diese Bedingungen nicht.
