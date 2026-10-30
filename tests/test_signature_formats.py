"""Conservative category and extent checks for added signature formats."""
from io import BytesIO
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
import wave
import zipfile

from PIL import Image

from recoverydesk.signature_search import scan_signatures


def bmp():
    pixels = b'\x00\x00\xff\x00'
    dib = struct.pack('<IiiHHIIiiII', 40, 1, 1, 1, 24, 0, len(pixels), 0, 0, 0, 0)
    return struct.pack('<2sIHHI', b'BM', 54 + len(pixels), 0, 0, 54) + dib + pixels


def image_bytes(kind):
    out = BytesIO()
    Image.new('RGB', (3, 2), 'red').save(out, kind)
    return out.getvalue()


def ogg_opus_page():
    from recoverydesk.signature_formats import _ogg_crc
    body = b'OpusHead' + bytes((1, 2)) + b'\0' * 9
    header = bytearray(b'OggS' + bytes((0, 6)) + b'\0' * 8 + struct.pack('<II', 7, 0) + b'\0' * 4 + bytes((1, len(body))))
    page = header + body
    page[22:26] = struct.pack('<I', _ogg_crc(page))
    return bytes(page)


def tagged_mp3():
    frame = b'\xff\xfb\x90\x64' + b'\0' * (417 - 4)
    return b'ID3\x04\0\0\0\0\0\0' + frame * 3


def zip_bytes(files):
    out = BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return out.getvalue()


def tar_bytes():
    out = BytesIO()
    with tarfile.open(fileobj=out, mode='w') as archive:
        info = tarfile.TarInfo('notes.txt')
        info.size = 3
        archive.addfile(info, BytesIO(b'abc'))
    return out.getvalue()


def wav_bytes():
    out = BytesIO()
    with wave.open(out, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
        audio.writeframes(b'\0\0' * 5)
    return out.getvalue()


def mp4_bytes():
    def box(kind, body=b''):
        return struct.pack('>I4s', len(body) + 8, kind) + body
    return box(b'ftyp', b'isom\0\0\0\0') + box(b'moov') + box(b'mdat', b'video')


def avi_bytes():
    def list_chunk(kind):
        body = kind + b'\0' * 4
        return b'LIST' + struct.pack('<I', len(body)) + body
    body = b'AVI ' + list_chunk(b'hdrl') + list_chunk(b'movi')
    return b'RIFF' + struct.pack('<I', len(body)) + body


class SignatureFormatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'raw.img'

    def scan(self, payload, category):
        self.source.write_bytes(b'X' * 512 + payload + b'Y' * 512)
        return scan_signatures(str(self.source), category=category)

    def test_images_have_exact_extents_and_category_filtering(self):
        for data, extension in ((bmp(), '.bmp'), (image_bytes('GIF'), '.gif'),
                                (image_bytes('TIFF'), '.tiff')):
            index = self.scan(data, 'images')
            self.assertEqual(len(index.entries), 1)
            self.assertTrue(index.entries[0].name.endswith(extension))
            self.assertEqual(index.entries[0].size, len(data))

    def test_webp_is_in_image_category(self):
        try:
            data = image_bytes('WEBP')
        except (OSError, ValueError):
            self.skipTest('Pillow WebP encoder unavailable')
        index = self.scan(data, 'images')
        self.assertEqual([entry.name.rsplit('.', 1)[-1] for entry in index.entries], ['webp'])
        self.assertEqual(index.entries[0].size, len(data))

    def test_ooxml_packages_and_ordinary_zip_are_separated(self):
        office_packages = (
            ('word/document.xml', b'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml', '.docx'),
            ('word/document.xml', b'application/vnd.ms-word.document.macroEnabled.main+xml', '.docm'),
            ('xl/workbook.xml', b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml', '.xlsx'),
            ('ppt/presentation.xml', b'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml', '.pptx'),
        )
        for path, content_type, extension in office_packages:
            types = b'<Types><Override PartName="/' + path.encode() + b'" ContentType="' + content_type + b'"/></Types>'
            office = zip_bytes({'[Content_Types].xml': types, path: b'<root/>'})
            self.assertTrue(self.scan(office, 'office').entries[0].name.endswith(extension))
        archive = zip_bytes({'readme.txt': b'hello'})
        self.assertTrue(self.scan(archive, 'archives').entries[0].name.endswith('.zip'))
        self.assertFalse(self.scan(archive, 'office').entries)

    def test_odt_package_is_recognized_from_its_mimetype(self):
        out = BytesIO()
        with zipfile.ZipFile(out, 'w') as package:
            package.writestr('mimetype', 'application/vnd.oasis.opendocument.text', compress_type=zipfile.ZIP_STORED)
            package.writestr('content.xml', '<document/>')
        self.assertTrue(self.scan(out.getvalue(), 'office').entries[0].name.endswith('.odt'))

    def test_tar_is_returned_as_a_complete_archive(self):
        data = tar_bytes()
        index = self.scan(data, 'archives')
        self.assertEqual(len(index.entries), 1)
        self.assertTrue(index.entries[0].name.endswith('.tar'))
        self.assertLessEqual(index.entries[0].size, len(data))
        with tarfile.open(fileobj=BytesIO(self.source.read_bytes()[512:512 + index.entries[0].size])) as archive:
            self.assertEqual(archive.extractfile('notes.txt').read(), b'abc')

    def test_wav_avi_and_mp4_are_category_specific(self):
        for category, data, extension in (
            ('audio', wav_bytes(), '.wav'),
            ('video', avi_bytes(), '.avi'),
            ('video', mp4_bytes(), '.mp4'),
            ('audio', ogg_opus_page(), '.opus'),
            ('audio', tagged_mp3(), '.mp3'),
        ):
            index = self.scan(data, category)
            self.assertEqual(len(index.entries), 1)
            self.assertTrue(index.entries[0].name.endswith(extension))
            self.assertEqual(index.entries[0].size, len(data))

    def test_video_with_format_declared_extent_over_32_mib_is_supported(self):
        body = b'AVI ' + b'LIST' + struct.pack('<I', 8) + b'hdrl\0' * 2
        body += b'LIST' + struct.pack('<I', 8) + b'movi\0' * 2
        target_size = 33 * 1024**2
        data = b'RIFF' + struct.pack('<I', target_size - 8) + body
        data += b'\0' * (target_size - len(data))
        index = self.scan(data, 'video')
        self.assertEqual(len(index.entries), 1)
        self.assertEqual(index.entries[0].size, target_size)

    def test_invalid_archive_and_wrong_category_are_rejected(self):
        invalid = bytearray(zip_bytes({'a.txt': b'a'}))
        invalid[-8] ^= 0x40
        self.assertFalse(self.scan(bytes(invalid), 'archives').entries)
        self.assertFalse(self.scan(wav_bytes(), 'video').entries)


if __name__ == '__main__':
    unittest.main()
