"""Verification copy must describe the performed check, not imply original integrity."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.batch_export import export_batch
from recoverydesk.filesystems import scan_tree
from recoverydesk.i18n import LANGUAGES, translate
from recoverydesk.verification_labels import (METADATA_SCOPE, READ_SCOPE, EXPORT_SCOPE,
    RESUME_SCOPE, WRITTEN_LABEL, RESUME_LABEL, METADATA_LABEL, export_status_label)
from test_filesystems import fat_img


class VerificationLabelTests(unittest.TestCase):
    def test_all_check_scopes_and_labels_have_six_languages(self):
        for text in (METADATA_SCOPE, READ_SCOPE, EXPORT_SCOPE, RESUME_SCOPE,
                     WRITTEN_LABEL, RESUME_LABEL, METADATA_LABEL):
            for language in LANGUAGES:
                with self.subTest(text=text, language=language):
                    translated = translate(text, language)
                    self.assertTrue(translated)
                    if language != 'de':
                        self.assertNotEqual(translated, text)

    def test_export_report_explains_saved_hash_without_changing_resume_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.img'
            raw = fat_img()
            source.write_bytes(raw)
            index = scan_tree(str(source))
            item = next(e for e in index.list_dir(5) if e.name == 'README.TXT')
            destination = root / 'out'
            destination.mkdir()
            first = export_batch(str(source), index, [item], str(destination))
            self.assertEqual(first.exported, 1)
            report = Path(first.log).read_text(encoding='utf-8')
            self.assertIn(EXPORT_SCOPE, report)
            self.assertIn(RESUME_SCOPE, report)
            self.assertIn(WRITTEN_LABEL, report)
            state = json.loads(Path(first.manifest).read_text(encoding='utf-8'))
            self.assertEqual(state['results']['README.TXT']['status'], 'Erfolgreich')
            checksum=state['results']['README.TXT']['sha256']
            self.assertIn('SHA256 (Zieldatei bestätigt): '+checksum,report)
            second = export_batch(str(source), index, [item], str(destination))
            self.assertEqual((second.exported, second.verified_existing, second.failed), (0, 1, 0))
            self.assertIn('SHA256 (Zieldatei bestätigt): '+checksum,Path(second.log).read_text(encoding='utf-8'))
            self.assertIn('Export-Prüfsumme bestätigt: 1', Path(second.log).read_text(encoding='utf-8'))
            self.assertEqual(source.read_bytes(), raw)

    def test_only_successful_export_states_receive_check_labels(self):
        self.assertEqual(export_status_label('Erfolgreich'), WRITTEN_LABEL)
        self.assertEqual(export_status_label('Bereits verifiziert'), RESUME_LABEL)
        for state in ('Fehler', 'Abgebrochen', 'Übersprungen', 'Wartend'):
            self.assertEqual(export_status_label(state), state)


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Display required')
class VerificationLabelGuiTests(unittest.TestCase):
    def test_displayed_export_checks_survive_all_language_switches(self):
        from recoverydesk.gui import RecoveryDeskApp
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'TENSHI_SETTINGS_FILE': str(Path(tmp) / 'settings.json'),
                'TENSHI_LOG_DIR': str(Path(tmp) / 'logs')}):
            app = RecoveryDeskApp()
            try:
                app._handle_export_event({'type': 'plan', 'total': 2, 'total_bytes': 10,
                    'items': [{'path': 'new.txt', 'size': 5}, {'path': 'old.txt', 'size': 5}]})
                for path, status in (('new.txt', 'Erfolgreich'), ('old.txt', 'Bereits verifiziert')):
                    app._handle_export_event({'type': 'done', 'path': path, 'size': 5, 'status': status})
                for language in (*LANGUAGES, 'de'):
                    app.change_language(language)
                    app.update()
                    with patch('recoverydesk.gui.messagebox.showinfo') as show:
                        app._show_export_scope()
                    self.assertEqual(show.call_args.args[1],
                                     translate(EXPORT_SCOPE,language)+'\n\n'+translate(RESUME_SCOPE,language))
                    self.assertNotIn('export_queue_tree',app.__dict__)
                self.assertEqual(app.export_progress.visible_items['new.txt']['status'], 'Erfolgreich')
                self.assertEqual(app.export_progress.visible_items['old.txt']['status'], 'Bereits verifiziert')
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main()
