"""Independent Office fixtures plus hostile CFB allocation and resume metadata."""
from array import array
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from recoverydesk.signature_cfb import cfb, MAGIC, FREE, END, FAT, DIF, _Compound
from recoverydesk.signature_formats import Invalid, Limit
from recoverydesk.signature_search import scan_signatures, _Budget
from recoverydesk.signature_checkpoint import read_checkpoint
from recoverydesk.filesystems import ScanCancelled
from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import read_saved_export, prepare_saved_export
from test_ntfs_bitmap_usage import make_volume, SECTOR

FIXTURES=Path(__file__).parent/'fixtures/office_cfb'


def directory_entry(name,kind,first=END,size=0,child=FREE):
    raw=bytearray(128);encoded=(name+'\0').encode('utf-16le')
    raw[:len(encoded)]=encoded
    struct.pack_into('<HBBIII',raw,64,len(encoded),kind,1,FREE,FREE,child)
    struct.pack_into('<IQ',raw,116,first,size)
    return raw


def container(*,version=3,data_sectors=8):
    """A minimal independent CFB writer; Workbook data is a structural stub."""
    sector=512 if version==3 else 4096;per=sector//4
    nfat=1
    while True:
        ndif=(max(0,nfat-109)+per-2)//(per-1)
        total=nfat+ndif+1+data_sectors
        needed=(total+per-1)//per
        if needed==nfat:break
        nfat=needed
    raw=bytearray((total+1)*sector);raw[:8]=MAGIC
    struct.pack_into('<HHHHH',raw,24,0x3e,version,0xfffe,9 if version==3 else 12,6)
    directory=nfat+ndif;first_data=directory+1
    struct.pack_into('<IIIIIIIII',raw,40,0 if version==3 else 1,nfat,directory,0,4096,END,0,nfat if ndif else END,ndif)
    struct.pack_into('<109I',raw,76,*list(range(min(109,nfat))),*([FREE]*max(0,109-nfat)))
    fat=[FREE]*(nfat*per)
    for number in range(nfat):fat[number]=FAT
    for number in range(nfat,nfat+ndif):fat[number]=DIF
    fat[directory]=END
    for number in range(first_data,total):fat[number]=number+1 if number+1<total else END
    for number in range(nfat):
        struct.pack_into('<'+'I'*per,raw,(number+1)*sector,*fat[number*per:(number+1)*per])
    remaining=list(range(109,nfat))
    for number in range(ndif):
        items=remaining[number*(per-1):(number+1)*(per-1)]
        values=items+[FREE]*(per-1-len(items))+[nfat+number+1 if number+1<ndif else END]
        struct.pack_into('<'+'I'*per,raw,(nfat+number+1)*sector,*values)
    offset=(directory+1)*sector
    raw[offset:offset+128]=directory_entry('Root Entry',5,child=1)
    raw[offset+128:offset+256]=directory_entry('Workbook',2,first_data,data_sectors*sector)
    struct.pack_into('<HHHH',raw,(first_data+1)*sector,0x809,16,0x600,5)
    struct.pack_into('<HH',raw,(first_data+1)*sector+20,0x0a,0)
    return raw


class CompoundSignatureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'test.img'

    def parse(self,data,*,limit=32*1024**2,budget=None):
        return cfb(BytesIO(data),0,len(data),budget or _Budget(limit,None))

    def test_independent_office_fixtures_and_provenance(self):
        for row in json.loads((FIXTURES/'SOURCES.json').read_text()):
            data=(FIXTURES/row['file']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
            self.assertEqual(self.parse(data),(len(data),row['kind'],'office'))

    def test_cfb_version_four_and_large_difat_are_bounded_and_supported(self):
        for options in ({'version':4,'data_sectors':1},{'data_sectors':13900}):
            with self.subTest(options=options):
                data=container(**options)
                self.assertEqual(self.parse(data),(len(data),'XLS','office'))

    def test_corrupt_header_fat_cycle_crosslinks_and_directory_cycle_rejected(self):
        original=container()
        mutations=[(30,'<H',12),(56,'<I',2048),(44,'<I',0),
                   (512+2*4,'<I',2),(512+2*4,'<I',1),(512+2*4,'<I',0xfffffffb),
                   (1024+128+72,'<I',1),(60,'<I',0),(68,'<I',0),(72,'<I',100000)]
        for offset,fmt,value in mutations:
            with self.subTest(offset=offset,value=value):
                data=bytearray(original);struct.pack_into(fmt,data,offset,value)
                with self.assertRaises(Invalid):self.parse(data)

    def test_truncation_candidate_size_and_global_budget_do_not_guess_extent(self):
        data=(FIXTURES/'simple.doc').read_bytes()
        for truncated in (data[:512],data[:-1],data[:4096]):
            with self.assertRaises(Invalid):self.parse(truncated)
        with self.assertRaises(Invalid):self.parse(data,limit=4096)
        budget=_Budget(32*1024**2,None);budget[0]=512*1024**2-511
        with self.assertRaises(Limit):self.parse(data,budget=budget)

    def test_v4_nonzero_header_padding_and_oversized_minifat_rejected(self):
        data=container(version=4,data_sectors=1);data[600]=1
        with self.assertRaises(Invalid):self.parse(data)
        data=container();struct.pack_into('<II',data,60,2,8)
        with self.assertRaises(Invalid):self.parse(data)

    def test_nested_workbook_is_not_misidentified_as_top_level_excel(self):
        data=container();directory=1024
        data[directory+128:directory+256]=directory_entry('Embedded',1,0,0,child=2)
        data[directory+256:directory+384]=directory_entry('Workbook',2,2,4096)
        with self.assertRaises(Invalid):self.parse(data)

    def test_stream_name_without_type_header_is_not_a_format_match(self):
        data=container();data[1536:1556]=b'\0'*20
        with self.assertRaises(Invalid):self.parse(data)
        self.assertEqual(self.parse(container()+b'\0'*1024)[0],len(container()))

    def test_minifat_overlap_and_office_header_corruption_rejected(self):
        original=(FIXTURES/'basic_test_ppt_file.ppt').read_bytes()
        compound=_Compound(BytesIO(original),0,len(original),_Budget(32*1024**2,None))
        directory_sid=struct.unpack_from('<I',original,48)[0]
        minis=[i for i,e in enumerate(compound.entries) if e and e['kind']==2 and 0<e['size']<4096]
        self.assertGreaterEqual(len(minis),2)
        data=bytearray(original)
        # This independently generated fixture has one directory sector.
        struct.pack_into('<I',data,(directory_sid+1)*512+minis[1]*128+116,compound.entries[minis[0]]['first'])
        with self.assertRaises(Invalid):self.parse(data)

    def test_cancellation_is_checked_while_parsing(self):
        def cancel():raise ScanCancelled()
        budget=_Budget(32*1024**2,None);budget.check=cancel
        with self.assertRaises(ScanCancelled):self.parse(container(),budget=budget)

    def combined_image(self):
        data=bytearray(b'X'*(1024**2-3));expected=[]
        for name in ('simple.doc','Simple.xls','basic_test_ppt_file.ppt'):
            payload=(FIXTURES/name).read_bytes();expected.append((len(data),payload))
            data.extend(payload);data.extend(b'X'*512)
        self.source.write_bytes(data)
        return expected

    def test_search_block_boundary_export_and_saved_job_are_byte_exact(self):
        expected=self.combined_image();before=self.source.read_bytes()
        index=scan_signatures(str(self.source),category='office')
        self.assertEqual([e.name.split('_')[0] for e in index.entries],['DOC','XLS','PPT'])
        self.assertEqual([e.locator[1] for e in index.entries],[p for p,_ in expected])
        target=self.root/'out';target.mkdir()
        result=export_batch(str(self.source),index,index.entries,str(target))
        self.assertEqual(result.exported,3);self.assertFalse(result.checksum_errors)
        for entry,(_,payload) in zip(index.entries,expected):
            self.assertEqual((Path(result.root)/'files'/entry.name).read_bytes(),payload)
        saved=read_saved_export(result.manifest)
        self.assertEqual(saved.signature_parser_revision,3)
        self.assertEqual(len(prepare_saved_export(saved)['selection']),3)
        self.assertEqual(self.source.read_bytes(),before)

    def test_old_scope_remains_old_and_new_checkpoint_resumes(self):
        self.combined_image()
        old=scan_signatures(str(self.source),category='office',parser_revision=2)
        self.assertEqual(old.entries,[])
        checkpoint=self.root/'old.tenshi-search.json'
        scan_signatures(str(self.source),category='office',parser_revision=2,checkpoint_path=checkpoint)
        self.assertEqual(scan_signatures(str(self.source),checkpoint_path=checkpoint,resume=True).entries,[])
        fresh=self.root/'new.tenshi-search.json';stopped=[]
        with self.assertRaises(ScanCancelled):
            scan_signatures(str(self.source),category='office',checkpoint_path=fresh,
                progress=lambda d,t:stopped.append(d),cancel=lambda:bool(stopped))
        self.assertEqual(read_checkpoint(fresh)['parser_revision'],3)
        self.assertEqual(len(scan_signatures(str(self.source),checkpoint_path=fresh,resume=True).entries),3)

    def test_ntfs_free_scan_never_crosses_an_allocated_cfb_boundary(self):
        data=bytearray(make_volume(cluster_count=4096,used_clusters=120))
        payload=(FIXTURES/'simple.doc').read_bytes();start=140*SECTOR
        data[start:start+len(payload)]=payload;self.source.write_bytes(data)
        options=dict(category='office',search_area='ntfs-free')
        self.assertEqual(len(scan_signatures(str(self.source),**options).entries),1)
        data[100*SECTOR+160//8] |= 1<<(160%8);self.source.write_bytes(data)
        self.assertEqual(scan_signatures(str(self.source),**options).entries,[])
