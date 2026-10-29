"""Real files: per-file durability, resume and consolidation failure handling."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.batch_export import export_batch,MANIFEST
from recoverydesk.export_checksums import ExportChecksums,INDIVIDUAL,SUMMARY,checksum_line
import test_batch_export


class ExportChecksumTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.source,self.index,self.parent,self.target=test_batch_export.BatchExportTests().fixture(self.root)
        self.original=self.source.read_bytes()

    def export(self,**kwargs):
        result=export_batch(str(self.source),self.index,[self.parent],str(self.target),**kwargs)
        self.assertEqual(self.source.read_bytes(),self.original)
        return result

    def singles(self,result):return sorted((Path(result.root)/INDIVIDUAL).glob('*.sha256'))

    def interrupt(self):
        stop=False;export_root=None
        def event(item):
            nonlocal stop,export_root
            if item['type']=='plan':export_root=Path(item['root'])
            if item['type']=='done' and item['status']=='Erfolgreich':
                # The checksum must already be readable at file completion.
                files=list((export_root/INDIVIDUAL).glob('*.sha256'))
                self.assertEqual(len(files),1)
                digest,relative=files[0].read_text(encoding='utf-8').strip().split('  ',1)
                self.assertEqual(hashlib.sha256((export_root/relative).read_bytes()).hexdigest(),digest)
                stop=True
        result=self.export(event=event,cancel=lambda:stop)
        self.assertTrue(result.cancelled);self.assertEqual(result.exported,1)
        return result

    def test_immediate_individual_then_resume_consolidates_without_recopy(self):
        first=self.interrupt();self.assertFalse((Path(first.root)/SUMMARY).exists())
        second=self.export()
        self.assertTrue(second.resumed);self.assertEqual(second.verified_existing,1)
        self.assertEqual(second.exported,2);self.assertFalse(second.checksum_errors)
        self.assertEqual(self.singles(second),[])
        summary=Path(second.checksums)
        lines=summary.read_text(encoding='utf-8').splitlines();self.assertEqual(len(lines),3)
        for line in lines:
            digest,relative=line.split('  ',1)
            self.assertEqual(hashlib.sha256((summary.parent/relative).read_bytes()).hexdigest(),digest)
        again=self.export();self.assertEqual(again.exported,0)
        self.assertFalse(again.checksum_errors);self.assertEqual(again.checksums,second.checksums)

    def test_summary_save_failure_preserves_every_individual_and_reports_error(self):
        original=ExportChecksums._write
        def fail_summary(store,relative,payload):
            if relative==SUMMARY:raise OSError('disk full while saving summary')
            return original(store,relative,payload)
        with patch.object(ExportChecksums,'_write',fail_summary):result=self.export()
        self.assertEqual(result.exported,3);self.assertEqual(len(self.singles(result)),3)
        self.assertFalse((Path(result.root)/SUMMARY).exists());self.assertFalse(result.checksums)
        self.assertIn('disk full',result.checksum_errors[0])
        self.assertIn('disk full',Path(result.log).read_text(encoding='utf-8'))
        retry=self.export();self.assertEqual(retry.exported,0)
        self.assertEqual(retry.verified_existing,3);self.assertFalse(retry.checksum_errors)
        self.assertTrue(Path(retry.checksums).is_file());self.assertEqual(self.singles(retry),[])

    def test_cleanup_failure_keeps_saved_summary_and_remaining_individuals(self):
        with patch('recoverydesk.export_checksums.remove_owned_output',side_effect=PermissionError('locked checksum')):
            result=self.export()
        self.assertTrue(Path(result.checksums).is_file())
        self.assertEqual(len(self.singles(result)),3);self.assertTrue(result.checksum_errors)
        retry=self.export();self.assertFalse(retry.checksum_errors);self.assertEqual(self.singles(retry),[])

    def test_individual_changed_after_summary_save_is_not_deleted(self):
        original=ExportChecksums._write
        changed=[]
        def change_after_summary(store,relative,payload):
            result=original(store,relative,payload)
            if relative==SUMMARY:
                path=next((store.root/INDIVIDUAL).glob('*.sha256'))
                path.write_bytes(b'changed during cleanup');changed.append(path)
            return result
        with patch.object(ExportChecksums,'_write',change_after_summary):result=self.export()
        self.assertTrue(result.checksum_errors);self.assertTrue(Path(result.checksums).is_file())
        self.assertEqual(changed[0].read_bytes(),b'changed during cleanup')

    def test_cancel_during_cleanup_keeps_remaining_checksums(self):
        from recoverydesk.export_checksums import remove_owned_output
        stop=False
        def remove(*args):
            nonlocal stop
            remove_owned_output(*args);stop=True
        with patch('recoverydesk.export_checksums.remove_owned_output',side_effect=remove):
            result=self.export(cancel=lambda:stop)
        self.assertTrue(result.cancelled);self.assertFalse(result.checksum_errors)
        self.assertTrue(Path(result.checksums).is_file());self.assertEqual(len(self.singles(result)),2)
        retry=self.export();self.assertFalse(retry.checksum_errors);self.assertEqual(self.singles(retry),[])

    def test_changed_individual_is_not_rewritten_or_deleted(self):
        first=self.interrupt();sidecar=self.singles(first)[0];sidecar.write_bytes(b'keep my changes')
        retry=self.export()
        self.assertEqual(sidecar.read_bytes(),b'keep my changes')
        self.assertTrue(retry.checksum_errors);self.assertFalse(retry.checksums)
        self.assertFalse((Path(first.root)/SUMMARY).exists())

    def test_replaced_individual_with_same_bytes_is_not_deleted(self):
        first=self.interrupt();sidecar=self.singles(first)[0];payload=sidecar.read_bytes()
        sidecar.rename(sidecar.with_suffix('.saved'))
        sidecar.write_bytes(payload)
        retry=self.export()
        self.assertEqual(sidecar.read_bytes(),payload)
        self.assertTrue(retry.checksum_errors);self.assertFalse(retry.checksums)

    def test_foreign_summary_and_untracked_individuals_are_preserved(self):
        first=self.interrupt();summary=Path(first.root)/SUMMARY
        summary.write_bytes(b'foreign summary')
        untracked=Path(first.root)/INDIVIDUAL/'foreign.sha256';untracked.write_bytes(b'foreign checksum')
        retry=self.export()
        self.assertEqual(summary.read_bytes(),b'foreign summary')
        self.assertEqual(untracked.read_bytes(),b'foreign checksum')
        self.assertTrue(retry.checksum_errors);self.assertFalse(retry.checksums)
        self.assertEqual(len(self.singles(retry)),4)

    def test_cancelled_hash_has_no_unconfirmed_checksum_file(self):
        from recoverydesk.export_io import ExportCancelled
        with patch('recoverydesk.batch_export._hash_file',side_effect=ExportCancelled('stop')):
            result=self.export()
        self.assertTrue(result.cancelled);self.assertEqual(result.exported,0)
        self.assertFalse(self.singles(result));self.assertFalse(result.checksums)

    def test_legacy_checkpoint_can_add_checksum_files_without_recopied_data(self):
        first=self.interrupt()
        for path in self.singles(first):path.unlink()
        manifest=Path(first.root)/MANIFEST
        state=json.loads(manifest.read_text(encoding='utf-8'));state.pop('checksum_outputs')
        manifest.write_text(json.dumps(state),encoding='utf-8')
        retry=self.export()
        self.assertEqual(retry.verified_existing,1);self.assertEqual(retry.exported,2)
        self.assertFalse(retry.checksum_errors);self.assertTrue(Path(retry.checksums).is_file())

    def test_interrupted_owned_metadata_write_can_be_repaired(self):
        state={};store=ExportChecksums(self.root,str(self.source),state,lambda:None)
        payload=checksum_line('日本語/file with spaces.txt','a'*64)
        with patch('recoverydesk.export_checksums.os.fsync',side_effect=OSError('flush failed')):
            with self.assertRaises(OSError):store._write('individual.sha256',payload)
        self.assertFalse(state['checksum_outputs']['individual.sha256']['complete'])
        store._write('individual.sha256',payload)
        self.assertEqual((self.root/'individual.sha256').read_bytes(),payload)
        self.assertTrue(state['checksum_outputs']['individual.sha256']['complete'])

    def test_corrupted_summary_is_not_reported_as_verified(self):
        first=self.export();summary=Path(first.checksums);summary.write_bytes(b'changed')
        retry=self.export()
        self.assertTrue(retry.checksum_errors);self.assertFalse(retry.checksums)
        self.assertEqual(summary.read_bytes(),b'changed');self.assertEqual(len(self.singles(retry)),3)

    def test_source_named_like_checksum_file_remains_export_data(self):
        chosen=next(e for e in self.index.list_dir(self.parent.record_number) if not e.is_directory)
        chosen.name=SUMMARY
        result=self.export()
        self.assertFalse(result.checksum_errors)
        self.assertTrue((Path(result.root)/'files/Dokumente'/SUMMARY).is_file())
        self.assertEqual(len(Path(result.checksums).read_text(encoding='utf-8').splitlines()),3)
