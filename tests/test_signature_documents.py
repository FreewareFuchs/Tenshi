"""PDF/RAR extents and rejection of incomplete or inconsistent structures."""
from io import BytesIO
from pathlib import Path
import json
import re
import struct
import tempfile
import unittest
import zipfile
import zlib

from recoverydesk.content_smoke import pdf_fixture
from recoverydesk.signature_search import scan_signatures
from recoverydesk.signature_checkpoint import read_checkpoint, checkpoint_digest
from recoverydesk.filesystems import ScanCancelled
from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import read_saved_export, prepare_saved_export


def _v(number):
    result = bytearray()
    while number > 127:
        result.append((number & 127)|128); number >>= 7
    result.append(number)
    return bytes(result)


def rar_fixture(version=5, volume=False, encrypted=False):
    name = b'test.txt'; data = b'hello RAR test\n'
    if version == 4:
        def block(kind,flags,body=b''):
            header=struct.pack('<BHH',kind,flags,7+len(body))+body
            return struct.pack('<H',zlib.crc32(header)&0xffff)+header
        main=block(0x73,(1 if volume else 0)|(0x80 if encrypted else 0),b'\0'*6)
        body=struct.pack('<IIBIIBBHI',len(data),len(data),3,zlib.crc32(data),0,20,0x30,len(name),0x20)+name
        return b'Rar!\x1a\x07\0'+main+block(0x74,0x8000,body)+data+block(0x7b,0)
    def block(kind,flags,body=b'',packed=b''):
        header=_v(kind)+_v(flags)+(_v(len(packed)) if flags & 2 else b'')+body
        encoded=_v(len(header))+header
        return struct.pack('<I',zlib.crc32(encoded))+encoded+packed
    file=_v(4)+_v(len(data))+_v(0)+struct.pack('<I',zlib.crc32(data))+_v(0)+_v(1)+_v(len(name))+name
    return (b'Rar!\x1a\x07\1\0'+(block(4,0,b'\0'*32) if encrypted else b'')+
            block(1,0,_v(1 if volume else 0))+block(2,2,file,data)+block(5,0,_v(0)))


def incremental_pdf():
    base=pdf_fixture()
    previous=int(re.search(rb'startxref\s+(\d+)',base)[1])
    body=base+b'5 0 obj\n<< /Producer (Tenshi test) >>\nendobj\n'
    xref=len(body)
    return body+(f'xref\n5 1\n{len(base):010d} 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R /Info 5 0 R /Prev {previous} >>\nstartxref\n{xref}\n%%EOF\n'.encode())


def stream_pdf():
    result=bytearray(b'%PDF-1.5\n'); offsets=[0]
    for number,body in enumerate((b'<< /Type /Catalog /Pages 2 0 R >>',
                                 b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                                 b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] >>'),1):
        offsets.append(len(result));result.extend(str(number).encode()+b' 0 obj\n'+body+b'\nendobj\n')
    xref=len(result);offsets.append(xref)
    entries=b'\0'+struct.pack('>IH',0,65535)+b''.join(b'\1'+struct.pack('>IH',offset,0) for offset in offsets[1:])
    result.extend(f'4 0 obj\n<< /Type /XRef /Size 5 /Root 1 0 R /W [1 4 2] /Length {len(entries)} >>\nstream\n'.encode())
    result.extend(entries+b'\nendstream\nendobj\n')
    result.extend(f'startxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)


class SignatureDocumentTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.source=self.root/'test.img'

    def scan(self,payload,category):
        self.source.write_bytes(b'X'*512+payload+b'Y'*512)
        return scan_signatures(str(self.source),category=category)

    def test_classic_incremental_and_stream_pdf_extents(self):
        for data in (pdf_fixture(),pdf_fixture().rstrip(b'\n'),incremental_pdf(),stream_pdf()):
            with self.subTest(length=len(data)):
                index=self.scan(data,'office')
                self.assertEqual(len(index.entries),1)
                self.assertTrue(index.entries[0].name.endswith('.pdf'))
                self.assertEqual(index.entries[0].size,len(data))

    def test_two_pdfs_and_unfinished_update_are_not_conflated(self):
        data=pdf_fixture()
        index=self.scan(data+data,'office')
        self.assertEqual([e.size for e in index.entries],[len(data),len(data)])
        self.assertFalse(self.scan(incremental_pdf().rsplit(b'startxref',1)[0],'office').entries)

    def test_pdf_end_marker_across_reader_block_boundary(self):
        data=pdf_fixture();old=int(re.search(rb'startxref\s+(\d+)',data)[1])
        length=65539-len(data)-2
        padding=b'%'+b'p'*(length-2)+b'\n'
        data=data[:old]+padding+data[old:].replace(f'startxref\n{old}\n'.encode(),f'startxref\n{old+length}\n'.encode())
        self.assertEqual(len(data),65539)
        self.assertEqual([e.size for e in self.scan(data,'office').entries],[len(data)])

    def test_pdf_rejects_false_end_wrong_xref_and_size_limit(self):
        data=pdf_fixture()
        for bad in (b'%PDF-1.7\nstartxref\n0\n%%EOF\n',data.replace(b'startxref\n',b'startxref\n9',1),data[:-6]):
            self.assertFalse(self.scan(bad,'office').entries)
        self.source.write_bytes(b'X'*512+data+b'Y'*512)
        self.assertFalse(scan_signatures(str(self.source),category='office',max_file_bytes=len(data)-3).entries)

    def test_rar4_and_rar5_extents_and_categories(self):
        for version in (4,5):
            data=rar_fixture(version)
            index=self.scan(data,'archives')
            self.assertEqual(len(index.entries),1)
            self.assertEqual(index.entries[0].size,len(data))
            self.assertTrue(index.entries[0].name.endswith('.rar'))
            self.assertFalse(self.scan(data,'office').entries)

    def test_large_pdf_update_never_returns_an_older_revision_at_size_limit(self):
        base=pdf_fixture();previous=int(re.search(rb'startxref\s+(\d+)',base)[1])
        with self.source.open('wb') as stream:
            stream.write(b'X'*512+base)
            stream.write(f'5 0 obj\n<< /Length {33*1024**2} >>\nstream\n'.encode())
            for _ in range(33):stream.write(b'x'*1024**2)
            stream.write(b'\nendstream\nendobj\n')
            xref=stream.tell()-512
            stream.write(f'xref\n5 1\n{len(base):010d} 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R /Prev {previous} >>\nstartxref\n{xref}\n%%EOF\n'.encode())
            expected=stream.tell()-512
            stream.write(b'Y'*512)
        self.assertFalse(scan_signatures(str(self.source),category='office').entries)
        index=scan_signatures(str(self.source),category='office',max_file_bytes=64*1024**2)
        self.assertEqual([e.size for e in index.entries],[expected])

    def test_rar_bad_crc_truncation_volumes_and_encrypted_headers(self):
        for version in (4,5):
            data=bytearray(rar_fixture(version));data[10]^=0x40
            for bad in (bytes(data),rar_fixture(version)[:-3],rar_fixture(version,volume=True),rar_fixture(version,encrypted=True)):
                self.assertFalse(self.scan(bad,'archives').entries)

    def test_pdf_rar_export_job_keeps_new_parser_scope(self):
        self.source.write_bytes(b'X'*512+pdf_fixture()+b'Y'*512+rar_fixture()+b'Z'*512)
        index=scan_signatures(str(self.source),categories=('office','archives'))
        target=self.root/'export';target.mkdir()
        result=export_batch(str(self.source),index,index.entries,str(target))
        self.assertEqual(result.exported,2)
        job=read_saved_export(result.manifest)
        self.assertEqual(job.signature_parser_revision,2)
        prepared=prepare_saved_export(job)
        self.assertEqual([e.name for e in prepared['selection']],[e.name for e in index.entries])

    def test_checkpoint_revalidates_pdf_and_rar_and_preserves_legacy_scope(self):
        archive=BytesIO()
        with zipfile.ZipFile(archive,'w') as z:z.writestr('old.txt','old format')
        payload=bytearray(b'X'*(2*1024**2))
        payload[512:512+len(archive.getvalue())]=archive.getvalue()
        new=pdf_fixture()+b'Z'*512+rar_fixture()
        payload[1024**2+100:1024**2+100+len(new)]=new
        self.source.write_bytes(payload)
        checkpoint=self.root/'legacy.tenshi-search.json';stopped=[]
        with self.assertRaises(ScanCancelled):
            scan_signatures(str(self.source),categories=('office','archives'),parser_revision=1,
                checkpoint_path=str(checkpoint),progress=lambda done,total:stopped.append(done),cancel=lambda:bool(stopped))
        state=read_checkpoint(checkpoint);state.pop('parser_revision')
        state['checksum']=checkpoint_digest(state)
        checkpoint.write_text(json.dumps(state),encoding='utf-8')
        restored=scan_signatures(str(self.source),checkpoint_path=str(checkpoint),resume=True)
        self.assertEqual([e.name.rsplit('.',1)[-1] for e in restored.entries],['zip'])
        fresh=scan_signatures(str(self.source),categories=('office','archives'),checkpoint_path=str(self.root/'new.tenshi-search.json'))
        self.assertEqual(len(fresh.entries),3)
        again=scan_signatures(str(self.source),checkpoint_path=str(self.root/'new.tenshi-search.json'),resume=True)
        self.assertEqual([e.name for e in again.entries],[e.name for e in fresh.entries])


if __name__ == '__main__':unittest.main()
