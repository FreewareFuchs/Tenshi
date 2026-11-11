from pathlib import Path
import tempfile
import unittest
from recoverydesk.batch_export import _write_log, BatchResult


class ExportReportHashTests(unittest.TestCase):
    def test_name_hint_is_reported_when_an_existing_export_is_resumed(self):
        from recoverydesk.batch_export import export_batch
        from recoverydesk.filesystems import scan_tree
        from test_fat32_name_case import deleted_name_image

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.img'
            image = deleted_name_image('Grüner Bericht 2026.txt')
            source.write_bytes(image)
            index = scan_tree(str(source))
            entry, = index.list_dir(index.root)
            hint = entry.possible_original_name
            entry.possible_original_name = None
            target = root / 'export'
            target.mkdir()
            first = export_batch(str(source), index, [entry], str(target))
            self.assertEqual(first.errors, [])
            self.assertNotIn('Möglicher Originalname', Path(first.log).read_text(encoding='utf-8'))

            entry.possible_original_name = hint
            resumed = export_batch(str(source), index, [entry], str(target))
            self.assertEqual(resumed.errors, [])
            self.assertEqual(resumed.root, first.root)
            self.assertEqual(resumed.verified_existing, 1)
            self.assertEqual(resumed.exported, 0)
            text = Path(resumed.log).read_text(encoding='utf-8')
            self.assertIn('Möglicher Originalname (Namenshinweis): '+hint, text)
            self.assertIn('SHA256 (Zieldatei bestätigt):', text)
            files = list((Path(resumed.root) / 'files').iterdir())
            self.assertEqual([path.name for path in files], ['_EPORT~1.TXT'])
            self.assertEqual(files[0].read_bytes(), b'HELLO')
            self.assertEqual(source.read_bytes(), image)

    def test_unverified_hashes_never_receive_a_confirmation_label(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/'source.img';source.write_bytes(b'untouched')
            confirmed='a'*64;pending='b'*64;failed='c'*64
            state={'identity':{'source':str(source),'filesystem':'test'},'results':{
                'ok':{'status':'Erfolgreich','sha256':confirmed},
                'cancelled':{'status':'Abgebrochen','copied_sha256':pending,'verification_pending':True},
                'error':{'status':'Fehler','sha256':failed,'copied_sha256':failed},
                'folder':{'status':'Ordner erstellt'},
            }}
            report=root/'report.txt'
            _write_log(report,state,BatchResult(root=str(root),cancelled=True))
            text=report.read_text(encoding='utf-8')
            self.assertIn('SHA256 (Zieldatei bestätigt): '+confirmed,text)
            for digest in (pending,failed):
                self.assertIn('SHA256 (kopierter Datenstrom; Zielprüfung nicht bestätigt): '+digest,text)
                self.assertNotIn('SHA256 (Zieldatei bestätigt): '+digest,text)
            self.assertIn('SHA256: nicht verfügbar',text)
            self.assertEqual(source.read_bytes(),b'untouched')
