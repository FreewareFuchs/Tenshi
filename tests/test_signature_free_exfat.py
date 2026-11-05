"""exFAT bitmap carving: validated metadata, bounded chains and saved scope."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.filesystems import ExFAT, ScanCancelled
from recoverydesk.exfat_usage import free_exfat_ranges, AllocationUnavailable
from recoverydesk.signature_search import scan_signatures
from recoverydesk.signature_checkpoint import read_checkpoint, checkpoint_digest, EXFAT_FREE_SCHEMA
from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import read_saved_export, prepare_saved_export
from test_signature_search import picture


def boot_region(boot,sector_size=512):
    region=bytearray(12*sector_size);region[:512]=boot
    for sector in range(1,9):region[(sector+1)*sector_size-4:(sector+1)*sector_size]=b'\0\0\x55\xaa'
    checksum=0
    for offset in range(11*sector_size):
        if offset not in (106,107,112):
            checksum=((checksum>>1)|((checksum&1)<<31))+region[offset]
            checksum &= 0xffffffff
    region[11*sector_size:]=struct.pack('<I',checksum)*(sector_size//4)
    return region


def make_exfat(path,*,offset=0,clusters=256,fragmented_bitmap=False):
    b=bytearray(512);b[:3]=b'\xeb\x76\x90';b[3:11]=b'EXFAT   ';b[510:]=b'\x55\xaa'
    fat_sectors=(clusters+129)//128;heap=max(32,24+fat_sectors)
    struct.pack_into('<Q',b,72,heap+clusters)
    struct.pack_into('<IIIII',b,80,24,fat_sectors,heap,clusters,2)
    struct.pack_into('<H',b,104,0x100);b[108]=9;b[110]=1;b[112]=255
    size=(clusters+7)//8;count=(size+511)//512
    bitmap_clusters=[3+2*n if fragmented_bitmap else 3+n for n in range(count)]
    bitmap=bytearray(size)
    for cluster in (2,*bitmap_clusters,80):bitmap[(cluster-2)//8] |= 1<<((cluster-2)%8)
    root=bytearray(512);root[0]=0x81;struct.pack_into('<IQ',root,20,bitmap_clusters[0],size)
    with Path(path).open('xb') as stream:
        stream.truncate(offset+(heap+clusters)*512)
        stream.seek(offset);stream.write(boot_region(b));stream.write(boot_region(b))
        stream.seek(offset+24*512);stream.write(struct.pack('<III',0xfffffff8,0xffffffff,0xffffffff))
        for i,cluster in enumerate(bitmap_clusters):
            stream.seek(offset+24*512+cluster*4)
            stream.write(struct.pack('<I',bitmap_clusters[i+1] if i+1<count else 0xffffffff))
            stream.seek(offset+(heap+cluster-2)*512);stream.write(bitmap[i*512:(i+1)*512])
        stream.seek(offset+(heap+80-2)*512);stream.write(picture('PNG'))
        stream.seek(offset+(heap+140-2)*512);stream.write(picture('PNG'))
        stream.seek(offset+heap*512);stream.write(root)
    with Path(path).open('rb') as stream:return ExFAT(stream,offset)


class FreeExFATTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'exfat.img';self.checkpoint=self.root/'search.json'

    def scan(self,**options):
        return scan_signatures(str(self.source),search_area='exfat-free',**options)

    def write(self,at,data):
        with self.source.open('r+b') as stream:stream.seek(at);stream.write(data)

    def test_only_free_png_and_progress_exclude_allocated_clusters(self):
        volume=make_exfat(self.source,offset=4096);before=self.source.read_bytes();progress=[]
        self.assertEqual(len(scan_signatures(str(self.source)).entries),2)
        result=self.scan(partition_offset=4096,progress=lambda d,t:progress.append((d,t)))
        self.assertEqual([e.locator[1] for e in result.entries],[volume.cluster_offset(140)])
        self.assertEqual(progress[-1],((volume.cluster_count-3)*512,)*2)
        self.assertEqual(before,self.source.read_bytes())

    def test_allocated_user_data_is_not_read_as_scan_payload(self):
        volume=make_exfat(self.source);allocated=volume.cluster_offset(80)
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
        with patch.object(signature_search,'open_source',return_value=Guard()):self.assertEqual(len(self.scan().entries),1)

    def test_free_fat_chain_remnants_do_not_count_as_allocated(self):
        volume=make_exfat(self.source)
        self.write(volume.fat_offset+140*4,struct.pack('<I',141))
        self.write(volume.fat_offset+141*4,struct.pack('<I',0xffffffff))
        self.assertEqual(len(self.scan().entries),1)

    def test_candidates_cannot_cross_allocated_boundary(self):
        volume=make_exfat(self.source)
        with self.source.open('r+b') as stream:
            at=volume.cluster_offset(3)+(141-2)//8;stream.seek(at);value=stream.read(1)[0]
            stream.seek(at);stream.write(bytes([value | 1<<((141-2)%8)]))
            stream.seek(volume.cluster_offset(140));stream.write(bytes(512))
            stream.seek(volume.cluster_offset(141)-20);stream.write(picture('PNG'))
        self.assertEqual(self.scan().entries,[])

    def test_fragmented_bitmap_chain_and_padding_bits_are_supported(self):
        volume=make_exfat(self.source,clusters=5001,fragmented_bitmap=True)
        # Last byte: one meaningful free bit, seven padding bits set.
        self.write(volume.cluster_offset(5)+113,b'\xfe')
        result=self.scan()
        self.assertEqual(len(result.entries),1)
        self.assertEqual(result.signature_source_bytes,(5001-4)*512)

    def test_boot_checksum_backup_mismatch_and_dirty_flags_refuse_scan(self):
        volume=make_exfat(self.source);original=self.source.read_bytes()
        for at,data in ((11*512,b'bad!'),(12*512+11*512,b'bad!'),(106,b'\x02\0'),(106,b'\x04\0')):
            self.write(at,data)
            with self.assertRaisesRegex(ValueError,'nicht sicher bestimmbar'):self.scan()
            self.source.write_bytes(original)
        b=bytearray(original[12*512:13*512]);b[100]^=1
        self.write(12*512,boot_region(b))
        with self.assertRaisesRegex(ValueError,'Bootkopien'):self.scan()
        self.source.write_bytes(original)
        # Backup VolumeFlags/PercentInUse may legitimately be stale.
        self.write(12*512+106,b'\x02\0');self.write(12*512+112,b'\x64')
        self.assertEqual(len(self.scan().entries),1)

    def test_texfat_multiple_or_misidentified_bitmaps_refuse_scan(self):
        volume=make_exfat(self.source);original=self.source.read_bytes()
        self.write(110,b'\x02')
        with self.assertRaisesRegex(ValueError,'TexFAT'):self.scan()
        self.source.write_bytes(original);root=volume.cluster_offset(2)
        self.write(root+1,b'\x01')
        with self.assertRaisesRegex(ValueError,'Bitmapkennung'):self.scan()
        self.source.write_bytes(original);self.write(root+32,original[root:root+32])
        with self.assertRaisesRegex(ValueError,'eindeutige'):self.scan()

    def test_missing_short_oversized_and_unallocated_metadata_refuse_scan(self):
        volume=make_exfat(self.source);original=self.source.read_bytes();root=volume.cluster_offset(2)
        for at,data in ((root,b'\0'),(root+24,struct.pack('<Q',1)),(root+24,struct.pack('<Q',129*1024**2)),
                        (volume.cluster_offset(3),b'\0')):
            self.write(at,data)
            with self.assertRaisesRegex(ValueError,'nicht sicher bestimmbar'):self.scan()
            self.source.write_bytes(original)

    def test_cyclic_overlapping_and_out_of_bounds_metadata_chains_refuse_scan(self):
        volume=make_exfat(self.source);original=self.source.read_bytes();root=volume.cluster_offset(2)
        for at,data in ((volume.fat_offset+8,struct.pack('<I',2)),(volume.fat_offset+12,struct.pack('<I',3)),
                        (volume.fat_offset+12,struct.pack('<I',999)),(root+20,struct.pack('<I',2))):
            self.write(at,data)
            with self.assertRaisesRegex(ValueError,'nicht sicher bestimmbar'):self.scan()
            self.source.write_bytes(original)

    def test_wrong_offset_truncation_and_metadata_limits_refuse_scan(self):
        make_exfat(self.source)
        with self.assertRaises(ValueError):self.scan(partition_offset=512)
        with self.source.open('rb') as stream:
            with self.assertRaises(AllocationUnavailable):free_exfat_ranges(stream,0,self.source.stat().st_size,max_bitmap_bytes=1)
            with self.assertRaises(AllocationUnavailable):free_exfat_ranges(stream,0,self.source.stat().st_size,max_root_bytes=0)
            with patch('recoverydesk.exfat_usage.MAX_METADATA_BYTES',1024):
                with self.assertRaises(AllocationUnavailable):free_exfat_ranges(stream,0,self.source.stat().st_size)
        with self.source.open('r+b') as stream:stream.truncate(self.source.stat().st_size-512)
        with self.assertRaisesRegex(ValueError,'Image-Ende'):self.scan()

    def test_cancellation_during_metadata_validation_is_honored(self):
        make_exfat(self.source);calls=[]
        def cancel():calls.append(1);return len(calls)>6
        with self.assertRaises(ScanCancelled):self.scan(cancel=cancel)

    def test_no_free_clusters_is_complete_and_can_reopen(self):
        volume=make_exfat(self.source)
        self.write(volume.cluster_offset(3),b'\xff'*32)
        result=self.scan(checkpoint_path=self.checkpoint)
        self.assertEqual(result.signature_source_bytes,0);self.assertEqual(result.entries,[])
        self.assertTrue(result.signature_complete)
        self.assertEqual(scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True).entries,[])

    def test_pause_resume_keeps_scope_and_revalidates_metadata_digest(self):
        make_exfat(self.source,clusters=5000);progress=[]
        with self.assertRaises(ScanCancelled):
            self.scan(checkpoint_path=self.checkpoint,progress=lambda d,t:progress.append(d),cancel=lambda:bool(progress))
        state=read_checkpoint(self.checkpoint)
        self.assertEqual(state['schema'],EXFAT_FREE_SCHEMA);self.assertEqual(state['search_area'],'exfat-free')
        self.assertEqual(len(scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True).entries),1)
        with self.assertRaisesRegex(ValueError,'Sucheinstellungen'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True,search_area='fat32-free')
        state=read_checkpoint(self.checkpoint);state['bitmap_sha256']='0'*64;state['checksum']=checkpoint_digest(state)
        self.checkpoint.write_text(json.dumps(state),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Belegungsdaten'):
            scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)

    def test_saved_export_rebuild_keeps_scope_offset_and_exact_content(self):
        make_exfat(self.source,offset=4096);index=self.scan(partition_offset=4096)
        target=self.root/'export';target.mkdir();report=export_batch(str(self.source),index,index.entries,str(target))
        saved=read_saved_export(report.manifest)
        self.assertEqual(saved.signature_search_area,'exfat-free');self.assertEqual(saved.signature_partition_offset,4096)
        self.assertEqual(prepare_saved_export(saved)['index'].signature_search_area,'exfat-free')
        self.assertEqual(next((Path(report.root)/'files').glob('*.png')).read_bytes(),picture('PNG'))


if __name__=='__main__':unittest.main()
