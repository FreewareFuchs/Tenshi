"""Real restart/rescan exports and rejection of untrusted saved requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.batch_export import export_batch,MANIFEST
from recoverydesk.export_resume import (read_saved_export,prepare_saved_export,
                                       ExportResumeError,SavedExport)
from recoverydesk.export_target import TargetReviewDeclined
import test_batch_export
import test_filesystems
from recoverydesk.filesystems import scan_tree
from recoverydesk.ntfs_browser import scan_ntfs_tree


class SavedExportTests(unittest.TestCase):
    def fixture(self, *, cancel=True):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        source,index,parent,target=test_batch_export.BatchExportTests().fixture(Path(temp.name))
        stopped=False
        def event(data):
            nonlocal stopped
            if cancel and data['type']=='done' and data['status']=='Erfolgreich':stopped=True
        result=export_batch(str(source),index,[parent],str(target),cancel=lambda:stopped,event=event)
        return source,index,parent,target,result,Path(result.manifest)

    def write(self,path,data):path.write_text(json.dumps(data),encoding='utf-8')

    def snapshot(self,root):
        return {p.relative_to(root):p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}

    def test_fresh_process_rescans_original_selection_and_hashes_completed_files(self):
        source,index,parent,target,first,path=self.fixture()
        self.assertTrue(first.cancelled);self.assertEqual(first.exported,1)
        before=source.read_bytes()
        script='''
import json,sys
from recoverydesk.export_resume import read_saved_export,prepare_saved_export
from recoverydesk.batch_export import export_batch
job=prepare_saved_export(read_saved_export(sys.argv[1]))
r=export_batch(job['source'],job['index'],job['selection'],job['target'],expected_root=job['root'])
print(json.dumps(dict(verified=r.verified_existing,exported=r.exported,failed=r.failed,root=r.root)))
'''
        result=subprocess.run([sys.executable,'-c',script,str(path)],cwd=Path(__file__).parent.parent,
                              capture_output=True,text=True,timeout=30,check=True)
        report=json.loads(result.stdout)
        self.assertEqual((report['verified'],report['exported'],report['failed']),(1,2,0))
        self.assertEqual(report['root'],first.root);self.assertEqual(source.read_bytes(),before)
        self.assertEqual(len(list(target.glob('Tenshi_Export_*'))),1)

    def test_request_only_contains_root_ids_and_scan_options(self):
        source,index,parent,target,result,path=self.fixture()
        data=json.loads(path.read_text(encoding='utf-8'));request=data['resume_request']
        self.assertEqual(request,dict(schema=1,selected=[parent.key],scan=dict(max_records=0,tolerant=False)))
        self.assertNotIn('resident_data',json.dumps(request));self.assertNotIn('FIRST',json.dumps(request))
        with patch('recoverydesk.export_resume._identity',side_effect=AssertionError('Source opened before consent')):
            saved=read_saved_export(path)
        self.assertEqual(saved.source,os.path.normcase(str(source)));self.assertEqual(saved.keys,(parent.key,))

    def test_fat_exfat_and_ext_jobs_rescan_without_copying_finished_file(self):
        for make in (test_filesystems.fat_img,test_filesystems.exfat_img,test_filesystems.ext4_img):
            with self.subTest(filesystem=make.__name__):
                temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
                root=Path(temp.name);source=root/'image.raw';source.write_bytes(make())
                index=scan_tree(str(source));entry=next(e for e in index.entries if e.recoverable)
                target=root/'target';target.mkdir()
                first=export_batch(str(source),index,[entry],str(target))
                self.assertEqual(first.failed,0)
                job=prepare_saved_export(read_saved_export(first.manifest))
                result=export_batch(job['source'],job['index'],job['selection'],job['target'],expected_root=job['root'])
                self.assertEqual((result.verified_existing,result.exported,result.failed),(1,0,0))

    def test_original_ntfs_record_limit_is_reused(self):
        source,index,parent,target,result,path=self.fixture()
        limited=scan_ntfs_tree(str(source),max_records=8)
        entry=next(e for e in limited.entries if e.recoverable)
        first=export_batch(str(source),limited,[entry],str(target))
        saved=read_saved_export(first.manifest);self.assertEqual(saved.limit,8)
        job=prepare_saved_export(saved)
        self.assertEqual(job['index'].scanned_records,8)

    def test_original_partition_offset_is_reused(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);source=root/'disk.img';source.write_bytes(test_filesystems.fat_img(offset=4096))
        index=scan_tree(str(source),offset=4096)
        entry=next(e for e in index.entries if e.recoverable)
        target=root/'target';target.mkdir()
        first=export_batch(str(source),index,[entry],str(target))
        job=prepare_saved_export(read_saved_export(first.manifest))
        self.assertEqual(job['index'].offset,4096)
        resumed=export_batch(job['source'],job['index'],job['selection'],job['target'],expected_root=job['root'])
        self.assertEqual(resumed.verified_existing,1);self.assertEqual(resumed.failed,0)

    def test_changed_source_rejected_before_rescan_without_target_changes(self):
        source,index,parent,target,result,path=self.fixture();saved=read_saved_export(path)
        before=self.snapshot(result.root);stamp=source.stat()
        os.utime(source,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+1000000000))
        with patch('recoverydesk.export_resume.scan_ntfs_tree') as scan:
            with self.assertRaisesRegex(ExportResumeError,'Quelle wurde geändert'):prepare_saved_export(saved)
        scan.assert_not_called();self.assertEqual(self.snapshot(result.root),before)

    def test_source_changed_during_scan_is_rejected(self):
        source,index,parent,target,result,path=self.fixture();before=self.snapshot(result.root)
        def changed(*args,**kwargs):
            stamp=source.stat();os.utime(source,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+1000000000))
            return index
        with patch('recoverydesk.export_resume.scan_ntfs_tree',side_effect=changed):
            with self.assertRaises(ExportResumeError):prepare_saved_export(read_saved_export(path))
        self.assertEqual(self.snapshot(result.root),before)

    def test_altered_selection_and_missing_entry_do_not_write(self):
        for key in ('11:0','999999:0'):
            source,index,parent,target,result,path=self.fixture();data=json.loads(path.read_text(encoding='utf-8'))
            # Use another real entry for the first case, absent ID for the second.
            if key=='11:0':key=next(e.key for e in index.entries if e.recoverable)
            data['resume_request']['selected']=[key];self.write(path,data)
            before=self.snapshot(result.root)
            with self.assertRaises(ExportResumeError):prepare_saved_export(read_saved_export(path))
            self.assertEqual(self.snapshot(result.root),before)

    def test_checkpoint_is_reread_by_engine_after_preparation(self):
        source,index,parent,target,result,path=self.fixture()
        job=prepare_saved_export(read_saved_export(path))
        data=json.loads(path.read_text(encoding='utf-8'));data['signature']='0'*64;self.write(path,data)
        before=self.snapshot(result.root)
        with self.assertRaises(ValueError):
            export_batch(job['source'],job['index'],job['selection'],job['target'],expected_root=job['root'])
        self.assertEqual(self.snapshot(result.root),before)

    def test_cancellation_prevents_source_access(self):
        source,index,parent,target,result,path=self.fixture()
        with patch('recoverydesk.export_resume._identity') as identity:
            with self.assertRaises(TargetReviewDeclined):prepare_saved_export(read_saved_export(path),cancel=lambda:True)
        identity.assert_not_called()

    def test_changed_device_identity_is_rejected_before_scan(self):
        source,index,parent,target,result,path=self.fixture();saved=read_saved_export(path)
        device=r'\\.\PhysicalDrive0' if os.name=='nt' else '/dev/sdz'
        identity=dict(saved.identity,source=device,device_snapshot={'serial':'old'})
        request=SavedExport(saved.root,identity,saved.signature,saved.keys,0,False)
        with patch('recoverydesk.export_resume._identity',return_value=dict(identity,device_snapshot={'serial':'new'})), \
             patch('recoverydesk.export_resume.scan_ntfs_tree') as scan:
            with self.assertRaises(ExportResumeError):prepare_saved_export(request)
        scan.assert_not_called()

    def test_legacy_job_retains_manual_resume_and_is_upgraded(self):
        source,index,parent,target,result,path=self.fixture()
        data=json.loads(path.read_text(encoding='utf-8'));data.pop('resume_request');self.write(path,data)
        with self.assertRaisesRegex(ExportResumeError,'noch keine gespeicherte Auswahl'):read_saved_export(path)
        resumed=export_batch(str(source),index,[parent],str(target),expected_root=result.root)
        self.assertEqual(resumed.verified_existing,1);self.assertEqual(resumed.failed,0)
        self.assertEqual(read_saved_export(path).keys,(parent.key,))

    def test_legacy_metadata_is_upgraded_even_if_copy_is_immediately_cancelled(self):
        source,index,parent,target,result,path=self.fixture()
        data=json.loads(path.read_text(encoding='utf-8'));data.pop('resume_request');self.write(path,data)
        resumed=export_batch(str(source),index,[parent],str(target),expected_root=result.root,cancel=lambda:True)
        self.assertTrue(resumed.cancelled)
        self.assertEqual(read_saved_export(path).keys,(parent.key,))

    def test_invalid_schema_limit_and_duplicate_keys_are_rejected(self):
        source,index,parent,target,result,path=self.fixture();original=json.loads(path.read_text(encoding='utf-8'))
        mutations=(lambda d:d.update(schema=True),
                   lambda d:d['resume_request'].update(selected=[]),
                   lambda d:d['resume_request'].update(selected=[parent.key,parent.key]),
                   lambda d:d['resume_request']['scan'].update(max_records=30000001),
                   lambda d:d['resume_request']['scan'].update(tolerant='yes'),
                   lambda d:d['identity'].update(offset=1))
        for change in mutations:
            data=json.loads(json.dumps(original));change(data);self.write(path,data)
            with self.assertRaises(ExportResumeError):read_saved_export(path)
        path.write_text('{"schema":1,"schema":1}',encoding='utf-8')
        with self.assertRaises(ExportResumeError):read_saved_export(path)

    def test_validation_cannot_be_disabled_by_python_optimization(self):
        source,index,parent,target,result,path=self.fixture();data=json.loads(path.read_text(encoding='utf-8'))
        data['schema']=True;self.write(path,data)
        script='''
import sys
from recoverydesk.export_resume import read_saved_export,ExportResumeError
try:read_saved_export(sys.argv[1])
except ExportResumeError:sys.exit(0)
sys.exit(2)
'''
        r=subprocess.run([sys.executable,'-O','-c',script,str(path)],cwd=Path(__file__).parent.parent,timeout=30)
        self.assertEqual(r.returncode,0)

    def test_status_size_bound_and_wrong_folder(self):
        source,index,parent,target,result,path=self.fixture()
        with patch('recoverydesk.export_resume.MAX_STATUS_BYTES',10):
            with self.assertRaisesRegex(ExportResumeError,'zu groß'):read_saved_export(path)
        with self.assertRaisesRegex(ExportResumeError,'kein gespeicherter'):read_saved_export(target/MANIFEST)

    @unittest.skipUnless(os.name!='nt','POSIX special files')
    def test_fifo_and_symlink_status_are_rejected_without_reading(self):
        source,index,parent,target,result,path=self.fixture();data=path.read_bytes()
        path.unlink();os.mkfifo(path)
        with self.assertRaises(ExportResumeError):read_saved_export(path)
        path.unlink();real=path.with_name('original.json');real.write_bytes(data);path.symlink_to(real)
        with self.assertRaises(ExportResumeError):read_saved_export(path)
