"""Free-space carving must not parse across allocated clusters or forget scope."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_ntfs_bitmap_usage import make_volume, SECTOR
from test_signature_search import picture
from recoverydesk.signature_search import scan_signatures
from recoverydesk.signature_checkpoint import read_checkpoint, checkpoint_digest
from recoverydesk.filesystems import ScanCancelled
from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import read_saved_export, prepare_saved_export, ExportResumeError


class FreeNTFSSignatureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'ntfs.img'
        self.checkpoint=self.root/'search.tenshi-search.json'

    def volume(self, *, offset=0, clusters=512):
        data=bytearray(make_volume(cluster_count=clusters,used_clusters=120))
        payload=picture('PNG')
        for cluster in (80,140):data[cluster*SECTOR:cluster*SECTOR+len(payload)]=payload
        self.source.write_bytes(b'P'*offset+data)
        return data

    def scan(self, **options):
        return scan_signatures(str(self.source),search_area='ntfs-free',**options)

    def test_used_files_excluded_and_progress_counts_only_free_bytes(self):
        self.volume();before=self.source.read_bytes();progress=[]
        full=scan_signatures(str(self.source))
        free=self.scan(progress=lambda done,total:progress.append((done,total)))
        self.assertEqual(len(full.entries),2)
        self.assertEqual([e.locator[1] for e in free.entries],[140*SECTOR])
        self.assertEqual(progress[-1],((512-120)*SECTOR,)*2)
        self.assertEqual(free.signature_search_area,'ntfs-free')
        self.assertEqual(before,self.source.read_bytes())

    def test_allocated_data_is_not_read_as_scan_payload(self):
        self.volume()
        from recoverydesk import signature_search as module
        original=module.open_source
        class Guard:
            def __enter__(guard):
                guard.context=original(str(self.source))
                guard.stream=guard.context.__enter__()
                return guard
            def __exit__(guard,*args):return guard.context.__exit__(*args)
            def __getattr__(guard,key):return getattr(guard.stream,key)
            def read(guard,n=-1):
                at=guard.stream.tell()
                if n < 0 or (at < 81*SECTOR and at+n > 80*SECTOR):
                    raise AssertionError('Allocated file contents read')
                return guard.stream.read(n)
        with patch.object(module,'open_source',return_value=Guard()):
            self.assertEqual(len(self.scan().entries),1)

    def test_candidate_cannot_cross_allocated_boundary(self):
        data=self.volume()
        data[140*SECTOR:141*SECTOR]=b'\0'*SECTOR
        payload=picture('PNG');start=141*SECTOR-20
        data[start:start+len(payload)]=payload
        data[100*SECTOR+141//8] |= 1 << (141%8)
        self.source.write_bytes(data)
        self.assertEqual(len(scan_signatures(str(self.source)).entries),2)
        self.assertEqual(self.scan().entries,[])

    def test_nonzero_partition_offset_is_absolute_in_results(self):
        self.volume(offset=4096)
        index=self.scan(partition_offset=4096)
        self.assertEqual(index.entries[0].locator[1],4096+140*SECTOR)
        self.assertEqual(index.signature_partition_offset,4096)

    def test_empty_free_space_and_separate_extents(self):
        data=self.volume()
        data[100*SECTOR:100*SECTOR+64]=b'\xff'*64
        self.source.write_bytes(data)
        index=self.scan(checkpoint_path=self.checkpoint)
        self.assertTrue(index.signature_complete)
        self.assertEqual(index.entries,[])
        self.assertEqual(index.signature_source_bytes,0)
        self.assertEqual(scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True).entries,[])
        # Separate free extents retain their own tails, never joining a signature across a gap.
        data=self.volume()
        data[100*SECTOR+140//8] |= 1 << (140%8)
        payload=picture('PNG')
        data[200*SECTOR:200*SECTOR+len(payload)]=payload
        self.source.write_bytes(data)
        self.assertEqual([e.locator[1] for e in self.scan().entries],[200*SECTOR])

    def test_unreadable_bitmap_wrong_offset_and_truncated_volume_refuse_scan(self):
        for options in ({'missing_bitmap':True},{'broken_record':True},{'wrong_name':True},{'corrupt_run':True}):
            with self.subTest(options=options):
                self.source.write_bytes(make_volume(**options))
                with self.assertRaisesRegex(ValueError,'nicht sicher bestimmbar'):self.scan()
        self.volume()
        with self.assertRaises(ValueError):self.scan(partition_offset=512)
        self.source.write_bytes(self.source.read_bytes()[:-512])
        with self.assertRaises(ValueError):self.scan()

    def test_pause_restart_revalidates_scope_and_skips_completed_free_bytes(self):
        data=self.volume(clusters=4096)
        payload=picture('PNG');boundary=120*SECTOR+1024**2-3
        data[boundary:boundary+len(payload)]=payload
        self.source.write_bytes(data)
        stopped=[]
        with self.assertRaises(ScanCancelled):
            self.scan(checkpoint_path=self.checkpoint,progress=lambda d,t:stopped.append(d),cancel=lambda:bool(stopped))
        state=read_checkpoint(self.checkpoint)
        self.assertEqual(state['search_area'],'ntfs-free')
        self.assertNotEqual(state['position']%1024**2,0)
        progress=[]
        resumed=scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True,progress=lambda d,t:progress.append(d))
        self.assertEqual(progress[0],1024**2)
        self.assertEqual([e.name for e in resumed.entries],[e.name for e in self.scan().entries])
        self.assertEqual(len(resumed.entries),2)
        with self.assertRaisesRegex(ValueError,'Sucheinstellungen'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True,search_area='all')
        state=read_checkpoint(self.checkpoint);state['bitmap_sha256']='0'*64
        state['checksum']=checkpoint_digest(state)
        self.checkpoint.write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Belegungsbitmap'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)

    def test_forged_saved_hit_in_allocated_area_is_rejected(self):
        self.volume();self.scan(checkpoint_path=self.checkpoint)
        state=read_checkpoint(self.checkpoint)
        state['hits'][0][0]=80*SECTOR
        state['checksum']=checkpoint_digest(state)
        self.checkpoint.write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Suchbereich'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)

    def test_saved_export_keeps_free_scope_and_partition_offset(self):
        self.volume(offset=4096)
        index=self.scan(partition_offset=4096)
        target=self.root/'export';target.mkdir()
        result=export_batch(str(self.source),index,index.entries,str(target))
        saved=read_saved_export(result.manifest)
        self.assertEqual(saved.signature_search_area,'ntfs-free')
        self.assertEqual(saved.signature_partition_offset,4096)
        rebuilt=prepare_saved_export(saved)
        self.assertEqual(rebuilt['index'].signature_search_area,'ntfs-free')
        self.assertEqual(len(rebuilt['index'].entries),1)
        path=Path(result.manifest);data=json.loads(path.read_text(encoding='utf-8'))
        for area,offset in (('unknown',0),('all',512),('ntfs-free',True),('ntfs-free',-512)):
            data['resume_request']['scan'].update(signature_search_area=area,signature_partition_offset=offset)
            path.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ExportResumeError):read_saved_export(path)


if __name__=='__main__':unittest.main()
