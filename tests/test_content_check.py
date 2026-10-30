"""Real isolated decoding, malformed data, bounded reads and cancellation."""
import base64
import io
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
import zlib

from PIL import Image
from recoverydesk.content_check import analyze,check_file,check_path,read_file,ContentCancelled
from recoverydesk.content_worker import inspect,MAX_INPUT,MAX_PIXELS
from recoverydesk.content_smoke import pdf_fixture,office_fixture
from recoverydesk.filesystems import scan_tree
from test_filesystems import fat_img,fat_short


def picture(kind='JPEG'):
    stream=io.BytesIO();Image.new('RGB',(32,24),'orange').save(stream,kind)
    return stream.getvalue()


def file_image(data,name='PHOTO   JPG'):
    raw=bytearray(fat_img());root=48*512
    raw[root:root+512]=bytes(512)
    raw[root:root+32]=fat_short(name,0x20,3,len(data))
    count=(len(data)+511)//512
    for cluster in range(3,3+count):
        struct.pack_into('<I',raw,32*512+cluster*4,cluster+1 if cluster<2+count else 0x0fffffff)
    raw[root+512:root+512+len(data)]=data
    return bytes(raw)


def replace_member(data,name,payload):
    stream=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as before,zipfile.ZipFile(stream,'w') as after:
        for item in before.infolist():after.writestr(item.filename,payload if item.filename==name else before.read(item))
    return stream.getvalue()


class ContentTests(unittest.TestCase):
    def test_images_decode_in_disposable_process_and_return_bounded_png(self):
        for kind in ('JPEG','PNG','BMP','GIF'):
            with self.subTest(kind=kind):
                answer=analyze(picture(kind),'file.'+kind.lower(),preview=True)
                self.assertEqual(answer['status'],'checked');self.assertEqual(answer['format'],kind)
                data=base64.b64decode(answer['image'],validate=True)
                with Image.open(io.BytesIO(data)) as image:
                    self.assertLessEqual(image.width,720);self.assertLessEqual(image.height,360)

    def test_truncated_jpeg_and_corrupted_png_do_not_pass(self):
        self.assertEqual(analyze(picture()[:-30],'broken.jpg')['status'],'unreadable')
        data=bytearray(picture('PNG'));data[-5]^=1
        self.assertEqual(analyze(bytes(data),'broken.png')['status'],'unreadable')

    def test_header_pixel_bomb_is_limit_not_corruption(self):
        data=bytearray(picture('PNG'));struct.pack_into('>II',data,16,MAX_PIXELS,2)
        struct.pack_into('>I',data,29,zlib.crc32(data[12:29]))
        self.assertEqual(analyze(bytes(data),'huge.png')['status'],'limited')

    def test_animation_only_claims_first_frame(self):
        stream=io.BytesIO();a=Image.new('RGB',(16,16),'red');b=Image.new('RGB',(16,16),'blue')
        a.save(stream,'GIF',save_all=True,append_images=[b],duration=100,loop=0)
        self.assertEqual(analyze(stream.getvalue(),'animated.gif')['code'],'image_first_frame')

    def test_pdf_preview_is_explicitly_partial(self):
        answer=analyze(pdf_fixture(),'document.pdf',preview=True)
        self.assertEqual((answer['status'],answer['code']),('partial','pdf_first_page'))
        self.assertEqual(answer['values']['pages'],1);self.assertTrue(answer['image'])
        self.assertEqual(analyze(b'%PDF-1.4\nmissing objects','bad.pdf')['status'],'unreadable')

    def test_password_protected_pdf_is_not_called_corrupt(self):
        data=base64.b64decode(Path(__file__).with_name('fixtures').joinpath('content-password-pdf.b64').read_bytes())
        self.assertEqual(analyze(data,'protected.pdf',preview=True)['status'],'encrypted')

    def test_ole_wrapped_office_is_not_called_corrupt(self):
        data=b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'+bytes(100)
        self.assertEqual(analyze(data,'protected.docx')['code'],'office_ole')

    @unittest.skipUnless(shutil.which('pdfinfo') and shutil.which('pdftoppm'),'Native Debian PDF backend required')
    def test_native_poppler_backend_renders_first_page(self):
        from recoverydesk.content_worker import _poppler
        answer=_poppler(pdf_fixture(),True)
        self.assertEqual(answer['code'],'pdf_first_page');self.assertTrue(answer['image'])

    def test_docx_xlsx_pptx_container_checks_and_no_automatic_macro_execution(self):
        for kind in ('docx','xlsx','pptx'):
            with self.subTest(kind=kind):
                answer=analyze(office_fixture(kind),'document.'+kind,preview=True)
                self.assertEqual(answer['code'],'office_container');self.assertEqual(answer['format'],kind.upper())

    def test_office_missing_main_relationship_and_bad_xml_are_rejected(self):
        good=office_fixture()
        for name,payload in [('_rels/.rels',b'<Relationships/>'),('word/document.xml',b'<broken>')]:
            with self.subTest(name=name):
                self.assertEqual(analyze(replace_member(good,name,payload),'bad.docx')['status'],'unreadable')

    def test_xml_entities_external_links_and_dtd_are_never_resolved(self):
        dangerous=b'<!DOCTYPE document [<!ENTITY leak SYSTEM "file:///should-not-open">]><document>&leak;</document>'
        data=replace_member(office_fixture(),'word/document.xml',dangerous)
        answer=analyze(data,'hostile.docx',preview=True)
        self.assertEqual(answer['status'],'unreadable');self.assertEqual(answer['text'],'')
        self.assertNotIn('should-not-open',str(answer))

    def test_xml_expansion_limit_is_distinct_from_parse_failure(self):
        large=b'<document>'+b'A'*(2*1024*1024)+b'</document>'
        answer=analyze(replace_member(office_fixture(),'word/document.xml',large),'large.docx')
        self.assertEqual(answer['status'],'limited')

    def test_office_zip_crc_failure_is_not_confirmed(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(office_fixture())) as original,zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as archive:
            for name in original.namelist():archive.writestr(name,original.read(name))
        data=bytearray(stream.getvalue());offset=data.index(b'<w:document');data[offset+1]^=1
        self.assertEqual(analyze(bytes(data),'broken.docx')['status'],'unreadable')

    def test_duplicate_archive_names_and_paths_are_not_accepted(self):
        for name in ('../foreign.xml','word/document.xml'):
            with self.subTest(name=name):
                stream=io.BytesIO(office_fixture())
                with zipfile.ZipFile(stream,'a') as archive:archive.writestr(name,b'<x/>')
                self.assertEqual(analyze(stream.getvalue(),'ambiguous.docx')['status'],'unreadable')

    def test_unknown_legacy_and_generic_zip_are_not_called_corrupt(self):
        for data,name in [(b'plain text','notes.txt'),(b'\xd0\xcf\x11\xe0binary','old.doc')]:
            self.assertEqual(analyze(data,name)['status'],'unsupported')
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr('readme.txt','text')
        self.assertEqual(analyze(stream.getvalue(),'archive.zip')['code'],'zip_scope')

    def test_input_limit_and_early_cancel_do_not_start_decoder(self):
        with patch('recoverydesk.content_check.subprocess.Popen') as popen:
            self.assertEqual(analyze(bytes(MAX_INPUT+1),'large.pdf')['status'],'limited')
            with self.assertRaises(ContentCancelled):analyze(b'bytes','file',cancel=lambda:True)
        popen.assert_not_called()

    def test_timeout_and_cancel_reap_worker(self):
        real_popen=subprocess.Popen
        for cancelling in (False,True):
            processes=[];cancel=threading.Event()
            def launch(*args,**kwargs):
                process=real_popen([sys.executable,'-c','import time; time.sleep(30)'],**kwargs)
                processes.append(process)
                if cancelling:cancel.set()
                return process
            with patch('recoverydesk.content_check.subprocess.Popen',side_effect=launch):
                if cancelling:
                    with self.assertRaises(ContentCancelled):analyze(b'text',cancel=cancel.is_set)
                else:self.assertEqual(analyze(b'text',timeout=.2)['status'],'limited')
            self.assertEqual(len(processes),1);self.assertIsNotNone(processes[0].poll())

    def test_real_fat_file_is_checked_without_source_changes_or_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.raw';original=file_image(picture());source.write_bytes(original)
            index=scan_tree(str(source));entry=next(e for e in index.entries if e.name=='PHOTO.JPG')
            answer=check_file(str(source),index,entry,'FAT32')
            self.assertEqual(answer['code'],'image_decoded');self.assertEqual(source.read_bytes(),original)
            self.assertEqual([p.name for p in Path(folder).iterdir()],['source.raw'])
            self.assertEqual(read_file(str(source),index,entry,'FAT32',limit=20),picture()[:20])

    def test_exported_regular_file_is_checked_without_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'photo.jpg';data=picture();path.write_bytes(data)
            before=path.stat()
            self.assertEqual(check_path(path)['code'],'image_decoded')
            self.assertEqual(path.read_bytes(),data);self.assertEqual(path.stat().st_mtime_ns,before.st_mtime_ns)
            with self.assertRaises(ValueError):check_path(folder)

    def test_nonresident_ntfs_uninitialized_tail_is_zero_filled(self):
        from types import SimpleNamespace
        entry=SimpleNamespace(is_directory=False,recoverable=True,size=8,data_kind='nonresident',initialized_size=3,data_runs=[])
        index=SimpleNamespace(info=None)
        with patch('recoverydesk.content_check.open_source',return_value=io.BytesIO(b'')),patch('recoverydesk.content_check.iter_stream',return_value=[b'ABC']):
            self.assertEqual(read_file('source',index,entry,'NTFS'),b'ABC'+bytes(5))

    def test_short_stream_and_oversized_file_are_rejected_before_parsing(self):
        from types import SimpleNamespace
        entry=SimpleNamespace(is_directory=False,recoverable=True,size=5)
        index=SimpleNamespace(volumes=SimpleNamespace(iter_file=lambda *args,**kwargs:[b'AB']))
        with patch('recoverydesk.content_check.open_source',return_value=io.BytesIO(b'')):
            with self.assertRaisesRegex(ValueError,'unvollständig'):read_file('source',index,entry,'FAT32')
        entry.size=MAX_INPUT+1
        with patch('recoverydesk.content_check.read_file') as read:
            self.assertEqual(check_file('source',index,entry,'FAT32')['status'],'limited')
        read.assert_not_called()


if __name__=='__main__':unittest.main()
