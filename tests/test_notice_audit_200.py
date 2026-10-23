"""Regression tests for historically misleading in-app safety notices."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from recoverydesk import __version__
from recoverydesk.i18n import LANGUAGES, TRANSLATIONS, translate
from recoverydesk.gui import RecoveryDeskApp

BROWSER_NOTICE = (
    'Dateiansicht: NTFS, FAT32, exFAT, ext2/3/4 sowie eingeschränkt Btrfs und XFS. '
    'Gelöschte Dateien: NTFS, FAT32, exFAT und ext2/3/4 teilweise rettbar; '
    'Btrfs/XFS nur nicht exportierbare Metadatenhinweise. '
    'Ein Export garantiert keine intakten Inhalte.'
)
FOOTER_NOTICE = (
    'Bei Hardwaredefekt weitere Lesezugriffe minimieren und möglichst ein schonendes Image erstellen. '
    'Gerettete Daten nur auf einem anderen physischen Datenträger speichern.'
)
IMAGING_DEST_NOTICE = (
    'Schreibzugriffe erfolgen nur auf die Image-Zieldatei (neu oder fortgesetzt) und ihre Statusdateien, '
    'nicht auf das Quellmedium. Für mechanisch defekte Laufwerke spezialisierte, '
    'schonende Imaging-Verfahren verwenden.'
)
IMAGING_ZERO_NOTICE = (
    'Unlesbare Bereiche werden mit Nullen ersetzt und als Fehlstellen protokolliert; '
    'das Image kann dadurch Datenlücken enthalten.'
)
PHYSICAL_NOTICE = (
    'Achtung: Schon das Lesen kann eine physisch defekte Festplatte zusätzlich belasten. '
    'Weitere Zugriffe möglichst vermeiden und zuerst ein schonendes Image mit geeigneten Werkzeugen erstellen.'
)

class NoticeLogicTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(__version__, '3.0.2')

    def test_all_five_notices_have_all_six_languages(self):
        for notice in (BROWSER_NOTICE, FOOTER_NOTICE, IMAGING_DEST_NOTICE,
                       IMAGING_ZERO_NOTICE, PHYSICAL_NOTICE):
            self.assertIn(notice, TRANSLATIONS)
            for lang in LANGUAGES:
                value = translate(notice, lang)
                self.assertTrue(value)
                if lang != 'de':
                    self.assertNotEqual(value, notice)

    def test_outdated_ntfs_only_notice_absent(self):
        root = Path(__file__).resolve().parents[1] / 'recoverydesk'
        for file in ('gui.py', 'i18n.py'):
            source = (root / file).read_text(encoding='utf-8')
            self.assertNotIn('Gelöschte Dateien werden derzeit nur aus NTFS-MFT-Metadaten erkannt.', source)
            self.assertNotIn('Nur eine neue Zieldatei wird beschrieben.', source)

    def test_notice_not_used_as_filename_translator(self):
        for lang in LANGUAGES:
            self.assertEqual(translate(r'C:\Personal\Bilder.raw', lang), r'C:\Personal\Bilder.raw')

    def test_untested_hardware_not_claimed_in_release_notes(self):
        readme = (Path(__file__).resolve().parents[1] / 'README.md').read_text(encoding='utf-8')
        self.assertIn('Windows-Hardwaretest steht aus', readme)
        self.assertIn('keine fehlerfreien Daten', readme)

    def test_installer_contains_only_application_exe(self):
        script = (Path(__file__).resolve().parents[1] / 'installer' / 'Tenshi.iss').read_text(encoding='utf-8')
        self.assertIn('Source: "..\\dist\\Tenshi.exe"', script)
        self.assertNotIn('DestDir: "{app}\\Images"', script)
        self.assertIn('PrivilegesRequired=lowest', script)

@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'Graphical display required')
class NoticeGuiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path_patch = mock.patch.dict(os.environ, {
            'TENSHI_SETTINGS_FILE': str(Path(temporary.name) / 'settings.json')})
        self.path_patch.start()
        self.app=RecoveryDeskApp()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.path_patch.stop()

    def _find_labels(self):
        labels=[]
        def walk(parent):
            for child in parent.winfo_children():
                if 'text' in child.keys():
                    labels.append(child.cget('text'))
                walk(child)
        walk(self.app)
        return labels

    def test_corrected_notices_visible_and_tabs_still_available(self):
        labels=self._find_labels()
        self.assertIn(BROWSER_NOTICE, labels)
        self.assertIn(FOOTER_NOTICE, labels)
        self.assertEqual(len(self.app.tabs.tabs()),2)
        self.assertEqual(self.app.export_button.cget('bg'),'#16803c')
        self.assertEqual(self.app.tmp_toggle.cget('text'),'TMP anzeigen (nur Ansicht)')

    def test_corrected_notices_translate_and_preserve_source(self):
        self.app.source_path.set('/test/path.raw')
        self.app.change_language('en')
        self.app.update()
        labels=self._find_labels()
        self.assertIn(translate(BROWSER_NOTICE,'en'),labels)
        self.assertIn(translate(FOOTER_NOTICE,'en'),labels)
        self.assertEqual(self.app.source_path.get(), '/test/path.raw')
        self.assertEqual(self.app.tmp_toggle.cget('text'),translate('TMP anzeigen (nur Ansicht)','en'))
        self.app.change_language('de')
        self.app.update()
        self.assertIn(BROWSER_NOTICE,self._find_labels())

if __name__ == '__main__':
    unittest.main()
