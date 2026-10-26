"""Checksum progress is a separate phase and never counts as copied bytes."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from recoverydesk.batch_export import _hash_file, export_batch
from recoverydesk.export_io import ExportCancelled
from recoverydesk.export_queue import QueueProgress
from recoverydesk.i18n import LANGUAGES, translate


class VerificationProgressTests(unittest.TestCase):
    def test_hash_counts_bytes_and_can_cancel_mid_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'large.dat'
            data = b'x' * (3 * 1024 * 1024 + 7)
            path.write_bytes(data)
            counts = []
            digest = _hash_file(path, progress=counts.append)
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())
            self.assertEqual(counts, [0, 1024*1024, 2*1024*1024, 3*1024*1024, len(data)])
            counts.clear()
            with self.assertRaises(ExportCancelled):
                _hash_file(path, progress=counts.append,
                           cancel=lambda: bool(counts and counts[-1] >= 1024*1024))
            self.assertEqual(counts, [0, 1024*1024])

    def test_phase_reset_rate_and_fraction_do_not_double_count(self):
        q = QueueProgress()
        q.handle({'type':'plan','total':1,'total_bytes':100,
                  'items':[{'path':'file','size':100}]}, now=0)
        q.handle({'type':'start','path':'file','size':100}, now=0)
        q.handle({'type':'bytes','path':'file','delta':100}, now=1)
        q.handle({'type':'verify','path':'file','size':100,'read':25}, now=2)
        self.assertTrue(q.verifying)
        self.assertEqual(q.verification_fraction, .25)
        self.assertEqual(q.written_bytes, 100)
        self.assertEqual(q.done_count, 0)
        self.assertIsNone(q.eta(now=2))
        q.handle({'type':'verify','path':'file','size':100,'read':100})
        self.assertLess(q.verification_fraction, 1)
        q.handle({'type':'done','path':'file','size':100,'status':'Erfolgreich'})
        self.assertFalse(q.verifying)
        self.assertEqual(q.overall_fraction, 1)
        q.handle({'type':'complete','cancelled':True})
        self.assertEqual(q.overall_fraction, 0)
        q.handle({'type':'plan','total':0,'total_bytes':0})
        self.assertFalse(q.verifying)
        self.assertEqual(q.verified_bytes, 0)

    def test_resume_hash_does_not_report_transfer_bytes(self):
        from recoverydesk.ntfs_browser import scan_ntfs_tree
        from test_browser import image_with_folders
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'source.raw'; source.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(source))
            parent = next(e for e in index.list_dir(5) if e.name == 'Dokumente')
            target = root/'out'; target.mkdir()
            events=[]
            first = export_batch(str(source), index, [parent], str(target), event=events.append)
            self.assertEqual(first.exported, 3)
            self.assertTrue(any(e['type']=='verify' and e['read']==0 for e in events))
            events.clear()
            second = export_batch(str(source), index, [parent], str(target), event=events.append)
            self.assertEqual(second.verified_existing, 3)
            self.assertFalse(any(e['type']=='bytes' for e in events))
            q=QueueProgress()
            for e in events:
                q.handle(e)
            self.assertEqual(q.written_bytes, 0)
            self.assertEqual(q.overall_fraction, 1)
            self.assertEqual(sum(e['read'] == e['size'] for e in events if e['type']=='verify'), 3)

    def test_empty_file_and_nonvisible_item_have_bounded_progress(self):
        q=QueueProgress()
        q.handle({'type':'plan','total':2,'total_bytes':100,'items':[]})
        q.handle({'type':'start','path':'not-in-preview','size':100})
        q.handle({'type':'bytes','path':'not-in-preview','delta':50})
        self.assertEqual(q.overall_fraction,.5)
        q.handle({'type':'verify','path':'not-in-preview','size':0,'read':0})
        self.assertEqual(q.verification_fraction,0)
        q.handle({'type':'complete','cancelled':True})
        self.assertFalse(q.verifying)
        self.assertEqual(q.overall_fraction,0)

    def test_ui_phase_label_is_translated_and_clears_on_cancel(self):
        from recoverydesk.gui import RecoveryDeskApp
        class Value:
            def set(self, value): self.value=value
            def configure(self, **kwargs): self.value=kwargs['value']
        q=QueueProgress()
        q.handle({'type':'plan','total':1,'total_bytes':100,'items':[]})
        q.handle({'type':'start','path':'file','size':100})
        q.handle({'type':'verify','path':'file','size':100,'read':50})
        for language in LANGUAGES:
            app=SimpleNamespace(export_progress=q,language=language,
                                export_queue_bar=Value(),export_queue_percent=Value())
            RecoveryDeskApp._paint_export_progress(app)
            self.assertEqual(app.export_queue_bar.value,50)
            self.assertEqual(app.export_queue_percent.value,
                             translate('SHA256 prüfen',language)+': 50.0 %')
            if language!='de':
                self.assertNotEqual(translate('SHA256 prüfen',language),'SHA256 prüfen')
                self.assertNotEqual(translate('Datei kopieren',language),'Datei kopieren')
        q.failed=q.ended=True
        RecoveryDeskApp._paint_export_progress(app)
        self.assertEqual(app.export_queue_percent.value,translate('Fehler',app.language))
        q.failed=q.ended=False
        q.handle({'type':'complete','cancelled':True})
        RecoveryDeskApp._paint_export_progress(app)
        self.assertEqual(app.export_queue_bar.value,0)
        self.assertEqual(app.export_queue_percent.value,'0.0 %')


if __name__=='__main__':
    unittest.main()
