"""Free FAT32 carving: authoritative allocation, boundaries and saved scope."""
from pathlib import Path
import json
import os
import struct
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.fat32_usage import free_fat32_ranges, AllocationUnavailable
from recoverydesk.filesystems import FAT32, ScanCancelled
from recoverydesk.signature_search import scan_signatures
from recoverydesk.signature_checkpoint import read_checkpoint, checkpoint_digest, FAT32_FREE_SCHEMA
from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import read_saved_export, prepare_saved_export
from test_signature_search import picture


def make_fat32(path, *, offset=0, copies=2, flags=0, clusters=65525):
    """Minimal FAT32 volume with a genuine FAT32 cluster count, exclusively local."""
    sectors=(clusters+2+127)//128
    total=32+copies*sectors+clusters
    boot=bytearray(512);boot[:3]=b'\xeb\x58\x90'
    boot[82:90]=b'FAT32   ';boot[510:512]=b'\x55\xaa'
    struct.pack_into('<H',boot,11,512);boot[13]=1
    struct.pack_into('<H',boot,14,32);boot[16]=copies;boot[21]=0xf8
    struct.pack_into('<IIHHI',boot,32,total,sectors,flags,0,2)
    with Path(path).open('xb') as stream:
        stream.truncate(offset+total*512)
        stream.seek(offset);stream.write(boot)
        for copy in range(copies):
            stream.seek(offset+(32+copy*sectors)*512)
            stream.write(struct.pack('<III',0x0ffffff8,0x0fffffff,0x0fffffff))
    with Path(path).open('rb') as stream:
        return FAT32(stream,offset)


class FreeFAT32Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'fat32.img'
        self.checkpoint=self.root/'search.tenshi-search.json'

    def entry(self,volume,cluster,value,*,copies=None):
        with self.source.open('r+b') as stream:
            for copy in range(volume.fats) if copies is None else copies:
                stream.seek(volume.fat_offset+copy*volume.fat_bytes+cluster*4)
                stream.write(struct.pack('<I',value))

    def volume(self,**options):
        volume=make_fat32(self.source,**options)
        self.entry(volume,80,0x0fffffff)
        payload=picture('PNG')
        with self.source.open('r+b') as stream:
            for cluster in (80,140):
                stream.seek(volume.cluster_offset(cluster));stream.write(payload)
        return volume

    def scan(self,**options):
        return scan_signatures(str(self.source),search_area='fat32-free',**options)

    def test_only_free_payload_and_progress_use_data_cluster_geometry(self):
        volume=self.volume(offset=4096);before=self.source.read_bytes();progress=[]
        self.assertEqual(len(scan_signatures(str(self.source)).entries),2)
        result=self.scan(partition_offset=4096,progress=lambda d,t:progress.append((d,t)))
        self.assertEqual([e.locator[1] for e in result.entries],[volume.cluster_offset(140)])
        self.assertEqual(progress[-1],((volume.cluster_count-2)*512,)*2)
        self.assertEqual(result.signature_partition_offset,4096)
        self.assertEqual(before,self.source.read_bytes())

    def test_allocated_file_payload_is_not_read_and_candidates_cannot_cross_it(self):
        volume=self.volume();allocated=volume.cluster_offset(80)
        from recoverydesk import signature_search
        original=signature_search.open_source
        class Guard:
            def __enter__(guard):
                guard.context=original(str(self.source));guard.stream=guard.context.__enter__();return guard
            def __exit__(guard,*args):return guard.context.__exit__(*args)
            def __getattr__(guard,key):return getattr(guard.stream,key)
            def read(guard,n=-1):
                at=guard.stream.tell()
                if n<0 or at<allocated+512 and at+n>allocated:raise AssertionError('Allocated payload read')
                return guard.stream.read(n)
        with patch.object(signature_search,'open_source',return_value=Guard()):
            self.assertEqual(len(self.scan().entries),1)
        self.entry(volume,141,0x0ffffff7)
        with self.source.open('r+b') as stream:
            stream.seek(volume.cluster_offset(140));stream.write(bytes(512))
            stream.seek(volume.cluster_offset(141)-20);stream.write(picture('PNG'))
        self.assertEqual(self.scan().entries,[])

    def test_mirrors_must_agree_but_reserved_upper_bits_are_ignored(self):
        volume=self.volume();self.entry(volume,140,0xf0000000,copies=(1,))
        self.assertEqual(len(self.scan().entries),1)
        self.entry(volume,140,0x0fffffff,copies=(1,))
        with self.assertRaisesRegex(ValueError,'widersprechen'):self.scan()

    def test_disabled_mirroring_uses_only_selected_active_fat(self):
        volume=self.volume(flags=0x81)
        self.entry(volume,140,0x0fffffff,copies=(0,))
        self.entry(volume,0,0,copies=(0,))
        self.assertEqual(len(self.scan().entries),1)

    def test_single_fat_fsinfo_hints_and_unused_padding_do_not_define_free_space(self):
        volume=self.volume(copies=1)
        with self.source.open('r+b') as stream:
            stream.seek(512+488);stream.write(struct.pack('<I',0))
            stream.seek(volume.fat_offset+(volume.cluster_count+2)*4);stream.write(b'\xff'*12)
        self.assertEqual(len(self.scan().entries),1)

    def test_bad_reserved_and_allocated_clusters_are_excluded(self):
        volume=self.volume()
        for cluster,value in ((140,0x0ffffff7),(141,0x0ffffff0),(142,0x0fffffff)):
            self.entry(volume,cluster,value)
            with self.source.open('r+b') as stream:
                stream.seek(volume.cluster_offset(cluster));stream.write(picture('PNG'))
        self.assertEqual(self.scan().entries,[])

    def test_dirty_table_unallocated_root_and_invalid_links_refuse_scan(self):
        volume=self.volume()
        for cluster,value in ((1,0x07ffffff),(1,0x0bffffff),(0,0),(2,0),(140,1),(140,volume.cluster_count+10)):
            with self.subTest(cluster=cluster,value=value):
                self.entry(volume,cluster,value)
                with self.assertRaisesRegex(ValueError,'nicht sicher bestimmbar'):self.scan()
                self.entry(volume,cluster,{0:0x0ffffff8,1:0x0fffffff,2:0x0fffffff}.get(cluster,0))

    def test_truncated_wrong_geometry_and_metadata_limits_refuse_scan(self):
        volume=self.volume()
        with self.source.open('rb') as stream:
            with self.assertRaises(AllocationUnavailable):free_fat32_ranges(stream,0,self.source.stat().st_size,max_table_bytes=512)
        with self.assertRaises(ValueError):self.scan(partition_offset=512)
        with self.source.open('r+b') as stream:stream.truncate(self.source.stat().st_size-512)
        with self.assertRaisesRegex(ValueError,'Image-Ende'):self.scan()

    def test_non_fat32_cluster_count_and_unknown_version_refuse_scan(self):
        make_fat32(self.source,clusters=400)
        with self.assertRaisesRegex(ValueError,'Geometrie'):self.scan()
        self.source.unlink();self.volume()
        with self.source.open('r+b') as stream:stream.seek(42);stream.write(b'\x01\0')
        with self.assertRaisesRegex(ValueError,'Versionsangaben'):self.scan()

    def test_cancellation_is_honored_during_metadata_reads(self):
        self.volume();checks=[]
        def cancel():checks.append(1);return len(checks)>3
        with self.assertRaises(ScanCancelled):self.scan(cancel=cancel)

    def test_no_free_clusters_is_a_complete_empty_search_and_can_reopen(self):
        volume=self.volume()
        with self.source.open('r+b') as stream:
            for copy in range(volume.fats):
                stream.seek(volume.fat_offset+copy*volume.fat_bytes+8)
                stream.write(b'\xff'*(volume.cluster_count*4))
        result=self.scan(checkpoint_path=self.checkpoint)
        self.assertTrue(result.signature_complete)
        self.assertEqual(result.signature_source_bytes,0)
        self.assertEqual(result.entries,[])
        self.assertEqual(scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True).entries,[])

    def test_real_allocation_change_outside_fingerprint_samples_invalidates_resume(self):
        volume=self.volume();self.scan(checkpoint_path=self.checkpoint)
        before=self.source.stat()
        self.entry(volume,50000,0x0fffffff)
        os.utime(self.source,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'Belegungstabelle'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)

    def test_pause_resume_revalidates_digest_scope_and_schema(self):
        volume=self.volume();progress=[]
        with self.assertRaises(ScanCancelled):
            self.scan(checkpoint_path=self.checkpoint,progress=lambda d,t:progress.append(d),cancel=lambda:bool(progress))
        state=read_checkpoint(self.checkpoint)
        self.assertEqual(state['schema'],FAT32_FREE_SCHEMA)
        self.assertEqual(state['search_area'],'fat32-free')
        result=scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)
        self.assertEqual(len(result.entries),1)
        with self.assertRaisesRegex(ValueError,'Sucheinstellungen'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True,search_area='ntfs-free')
        state=read_checkpoint(self.checkpoint);state['bitmap_sha256']='0'*64;state['checksum']=checkpoint_digest(state)
        self.checkpoint.write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Belegungstabelle'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)

    def test_forged_allocated_hit_or_downgraded_schema_is_rejected(self):
        volume=self.volume();self.scan(checkpoint_path=self.checkpoint)
        state=read_checkpoint(self.checkpoint);state['hits'][0][0]=volume.cluster_offset(80)
        state['checksum']=checkpoint_digest(state);self.checkpoint.write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Suchbereich'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)
        state['schema']='tenshi-signature-search-v1';state['checksum']=checkpoint_digest(state)
        self.checkpoint.write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaises(ValueError):read_checkpoint(self.checkpoint)

    def test_saved_export_rebuild_keeps_scope_and_byte_exact_content(self):
        self.volume(offset=4096);index=self.scan(partition_offset=4096)
        target=self.root/'export';target.mkdir()
        report=export_batch(str(self.source),index,index.entries,str(target))
        saved=read_saved_export(report.manifest)
        self.assertEqual(saved.signature_search_area,'fat32-free')
        self.assertEqual(saved.signature_partition_offset,4096)
        rebuilt=prepare_saved_export(saved)
        self.assertEqual(rebuilt['index'].signature_search_area,'fat32-free')
        self.assertEqual(len(rebuilt['index'].entries),1)
        self.assertEqual(next((Path(report.root)/'files').glob('*.png')).read_bytes(),picture('PNG'))


if __name__=='__main__':unittest.main()
