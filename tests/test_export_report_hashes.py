from pathlib import Path
import tempfile
import unittest
from recoverydesk.batch_export import _write_log, BatchResult


class ExportReportHashTests(unittest.TestCase):
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
