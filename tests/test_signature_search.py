"""Unformatted images, true extent boundaries and rejected false signatures."""
from dataclasses import replace
from io import BytesIO
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import zlib

from PIL import Image
from recoverydesk import signature_search as search
from recoverydesk.batch_export import export_batch
from recoverydesk.export_resume import read_saved_export,prepare_saved_export
from recoverydesk.filesystems import ScanCancelled
from recoverydesk.file_verification import verify_file
from recoverydesk.recovery_quality import assess
from recoverydesk.scan_report import format_scan_report
from recoverydesk.session_store import save_session,SessionError


def picture(kind,*,progressive=False):
    out=BytesIO();Image.new('RGB',(24,16),'blue').save(out,kind,progressive=progressive)
    return out.getvalue()


def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)


class SignatureSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.source=self.base/'source.img'
    def image(self,data):
        self.source.write_bytes(data+b'\x00'*max(512-len(data),0));return str(self.source)
    def scan(self,data,**kwargs):return search.scan_signatures(self.image(data),**kwargs)

    def test_unformatted_image_exact_extents_and_readonly_verification(self):
        jpeg=picture('JPEG');png=picture('PNG');data=b'X'*513+jpeg+b'X'*137+png+b'X'*1024
        events=[];index=self.scan(data,progress=lambda a,b:events.append((a,b)))
        self.assertEqual(len(index.entries),2);self.assertTrue(index.signature_complete)
        self.assertEqual(events[-1],(len(data),len(data)))
        for entry,content in zip(index.entries,(jpeg,png)):
            with self.source.open('rb') as stream:self.assertEqual(b''.join(index.volumes.iter_file(stream,entry)),content)
            self.assertEqual(verify_file(str(self.source),index,entry,filesystem=search.FILESYSTEM).read_bytes,len(content))
            self.assertEqual(assess(entry).grade,'uncertain');self.assertIn('Signatur',entry.status)
        self.assertEqual(self.source.read_bytes(),data)
        self.assertIn('ohne Originalnamen',format_scan_report(str(self.source),index))

    def test_png_and_jpeg_headers_cross_scan_block_boundary(self):
        for kind in ('PNG','JPEG'):
            for cut in range(1,len(search.PNG if kind=='PNG' else search.JPEG)):
                data=picture(kind)
                with patch.object(search,'SCAN_BLOCK',512):index=self.scan(b'X'*(512-cut)+data+b'X'*512)
                self.assertEqual([e.locator[1] for e in index.entries],[512-cut])
                self.assertEqual(index.entries[0].size,len(data))

    def test_progressive_jpeg_multiple_scans(self):
        data=picture('JPEG',progressive=True);index=self.scan(data)
        self.assertEqual([e.size for e in index.entries],[len(data)])

    def test_jpeg_eoi_inside_metadata_is_not_file_end(self):
        image=picture('JPEG');metadata=b'Exif\0\0false-end\xff\xd9rest'
        data=image[:2]+b'\xff\xe1'+struct.pack('>H',len(metadata)+2)+metadata+image[2:]
        index=self.scan(data);self.assertEqual([e.size for e in index.entries],[len(data)])

    def test_jpeg_entropy_crosses_reader_boundary(self):
        original=picture('JPEG');position=original.index(b'\xff\xda')
        start=position+2+int.from_bytes(original[position+2:position+4],'big')
        data=original[:start]+b'A'*65535+b'\xff\x00B\xff\xd0C'+original[start:]
        index=self.scan(data);self.assertEqual([e.size for e in index.entries],[len(data)])

    def test_png_iend_inside_ancillary_data_is_not_file_end(self):
        image=picture('PNG');end=image.index(b'IEND')-4
        data=image[:end]+chunk(b'tEXt',b'note\0false IEND\xaeB`\x82')+image[end:]
        index=self.scan(data);self.assertEqual([e.size for e in index.entries],[len(data)])

    def test_damaged_crc_and_truncated_images_are_not_exportable(self):
        png=bytearray(picture('PNG'));png[-1]^=1
        for data in (bytes(png),picture('PNG')[:-12],picture('JPEG')[:-2],search.JPEG+b'garbage',search.PNG+b'\xff'*30):
            index=self.scan(data);self.assertFalse(index.entries)

    def test_png_rejects_duplicate_header_and_unknown_critical_chunk(self):
        image=picture('PNG')
        for extra in (image[8:33],chunk(b'ABCD',b'')):
            self.assertFalse(self.scan(image[:33]+extra+image[33:]).entries)

    def test_file_limit_does_not_publish_truncated_candidate(self):
        with patch.object(search,'MAX_FILE',64):self.assertFalse(self.scan(picture('JPEG')).entries)

    def test_candidate_and_result_limits_are_reported(self):
        with patch.object(search,'MAX_CANDIDATES',2):index=self.scan((search.JPEG+b'X')*50)
        self.assertFalse(index.signature_complete);self.assertEqual(index.signature_candidates,2)
        with patch.object(search,'MAX_HITS',1):index=self.scan(picture('PNG')+b'X'*16+picture('PNG'))
        self.assertFalse(index.signature_complete);self.assertEqual(len(index.entries),1)

    def test_inspection_budget_is_reported(self):
        with patch.object(search,'MAX_INSPECTION',1):index=self.scan(picture('PNG'))
        self.assertFalse(index.signature_complete);self.assertFalse(index.entries)

    def test_cancellation_and_changed_source_do_not_return_results(self):
        self.image(picture('PNG'))
        with self.assertRaises(ScanCancelled):search.scan_signatures(str(self.source),cancel=lambda:True)
        def progress(*_):
            with self.source.open('ab') as stream:stream.write(b'changed')
        with self.assertRaisesRegex(ValueError,'geändert'):search.scan_signatures(str(self.source),progress=progress)

    def test_changed_source_or_forged_extent_cannot_be_read(self):
        index=self.scan(picture('PNG'));entry=index.entries[0]
        with self.source.open('rb') as stream:
            with self.assertRaises(ValueError):list(index.volumes.iter_file(stream,replace(entry,locator=('signature-v1',1,entry.size))))
        self.source.write_bytes(self.source.read_bytes()+b'changed')
        with self.source.open('rb') as stream:
            with self.assertRaisesRegex(ValueError,'geändert'):list(index.volumes.iter_file(stream,entry))

    def test_physical_sources_rejected_before_open(self):
        with patch.object(search,'validate_source'),patch.object(search,'is_device_source',return_value=True),patch.object(search,'open_source') as opened:
            with self.assertRaises(ValueError):search.scan_signatures('/dev/fake')
            opened.assert_not_called()

    def test_export_and_saved_job_rescan_reuse_confirmed_files(self):
        data=b'X'*700+picture('JPEG')+b'X'*200+picture('PNG');index=self.scan(data)
        target=self.base/'output';target.mkdir()
        first=export_batch(str(self.source),index,index.entries,str(target))
        self.assertFalse(first.cancelled);self.assertEqual(first.exported,2)
        job=prepare_saved_export(read_saved_export(first.manifest))
        second=export_batch(job['source'],job['index'],job['selection'],job['target'])
        self.assertEqual(second.exported,0);self.assertEqual(self.source.read_bytes(),data)

    def test_archive_export_job_resumes_across_all_categories(self):
        archive=BytesIO()
        with zipfile.ZipFile(archive,'w') as package:package.writestr('readme.txt','restored')
        data=b'X'*512+archive.getvalue()+b'Y'*512
        self.source.write_bytes(data)
        index=search.scan_signatures(str(self.source),category='archives')
        target=self.base/'archive-output';target.mkdir()
        first=export_batch(str(self.source),index,index.entries,str(target))
        saved=read_saved_export(first.manifest)
        prepared=prepare_saved_export(saved)
        self.assertEqual([entry.name for entry in prepared['selection']],[index.entries[0].name])
        self.assertEqual(prepared['index'].filesystem,search.FILESYSTEM)

    def test_legacy_image_signature_job_remains_resumable(self):
        self.source.write_bytes(picture('PNG')+b'Y'*512)
        index=search.scan_signatures(str(self.source))
        index.filesystem=search.LEGACY_FILESYSTEM
        index.volumes.label=search.LEGACY_FILESYSTEM
        target=self.base/'legacy-output';target.mkdir()
        first=export_batch(str(self.source),index,index.entries,str(target))
        prepared=prepare_saved_export(read_saved_export(first.manifest))
        self.assertEqual(prepared['index'].filesystem,search.LEGACY_FILESYSTEM)

    def test_session_save_rejects_signature_cache_before_creating_file(self):
        index=self.scan(picture('PNG'));destination=self.base/'saved.tenshi-session'
        with self.assertRaises(SessionError):save_session(str(destination),str(self.source),index=index)
        self.assertFalse(destination.exists())
