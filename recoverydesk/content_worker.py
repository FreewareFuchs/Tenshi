"""Bounded decoders, invoked only inside the disposable content-check process.

Input is copied bytes, never a source device/path. No document actions, macros,
links or external applications are opened. PDF rendering covers page one only.
"""
from __future__ import annotations
import base64
import io
import json
import math
import os
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import sys
import warnings
import zipfile

MAX_INPUT = 32 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_MEMBERS = 2000
MAX_EXPANDED = 32 * 1024 * 1024
MAX_XML = 2 * 1024 * 1024
THUMBNAIL = (720, 360)
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
OFFICE_EXTENSIONS = {'.docx', '.xlsx', '.pptx'}


class CheckLimit(Exception):
    pass


def result(status, kind, code, **values):
    return dict(status=status, format=kind, code=code, values=values,
                image='', text='')


def content_kind(data, extension=''):
    if data.startswith((b'\xff\xd8', b'\x89PNG', b'GIF8', b'BM')):
        return 'image'
    if data.startswith(b'%PDF-'):
        return 'pdf'
    if data.startswith(b'PK') or extension in OFFICE_EXTENSIONS:
        return 'office'
    if extension in IMAGE_EXTENSIONS:
        return 'image'
    if extension == '.pdf':
        return 'pdf'
    return ''


def _png(image):
    from PIL import Image
    if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_PIXELS:
        raise CheckLimit()
    image.thumbnail(THUMBNAIL, Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    if stream.tell() > 2 * 1024 * 1024:
        raise CheckLimit()
    return base64.b64encode(stream.getvalue()).decode('ascii')


def _image(data, preview):
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        formats = ['JPEG', 'PNG', 'BMP', 'GIF']
        with Image.open(io.BytesIO(data), formats=formats) as image:
            kind = image.format
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise CheckLimit()
            image.verify()
        # verify() alone does not decode all JPEG/BMP pixel data.
        with Image.open(io.BytesIO(data), formats=formats) as image:
            animated = bool(getattr(image, 'is_animated', False))
            image.load()
            answer = result('partial' if animated else 'checked', kind,
                            'image_first_frame' if animated else 'image_decoded',
                            width=width, height=height)
            if preview:
                thumbnail = ImageOps.exif_transpose(image).convert('RGBA')
                answer['image'] = _png(thumbnail)
            return answer


def _pdfium(data, preview):
    import pypdfium2 as pdfium
    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        if getattr(exc, 'err_code', None) == 4:
            return result('encrypted', 'PDF', 'pdf_encrypted')
        raise
    try:
        pages = len(document)
        if not 1 <= pages <= 100_000:
            raise CheckLimit()
        page = document[0]
        try:
            width, height = page.get_size()
            if not all(math.isfinite(value) and 0 < value <= 100_000 for value in (width, height)):
                raise CheckLimit()
            scale = min(THUMBNAIL[0] / width, THUMBNAIL[1] / height)
            bitmap = page.render(scale=scale, draw_annots=False, limit_image_cache=True)
            try:
                image = bitmap.to_pil()
                answer = result('partial', 'PDF', 'pdf_first_page', pages=pages)
                if preview:
                    answer['image'] = _png(image.copy())
                return answer
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()


def _poppler(data, preview):
    # Native Debian packages use the maintained distribution PDF renderer.
    # Fixed argv, stdin only, no shell, no temporary documents and no actions.
    from PIL import Image
    env = {**os.environ, 'LC_ALL': 'C', 'LANG': 'C'}
    info = subprocess.run(['pdfinfo', '-f', '1', '-l', '1', '-'], input=data,
                          capture_output=True, timeout=8, env=env)
    if info.returncode:
        if b'password' in info.stderr.lower() or b'encrypted' in info.stderr.lower():
            return result('encrypted', 'PDF', 'pdf_encrypted')
        raise ValueError('PDF metadata unavailable')
    match = re.search(rb'^Pages:\s*(\d+)\s*$', info.stdout, re.M)
    if not match:
        raise ValueError('PDF page count unavailable')
    pages = int(match[1])
    if not 1 <= pages <= 100_000:
        raise CheckLimit()
    rendered = subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-singlefile',
                               '-scale-to', '720', '-png', '-'], input=data,
                              capture_output=True, timeout=8, env=env)
    # Poppler may render a damaged file with nonfatal syntax errors. Such a
    # result remains partial and never becomes a full-file integrity claim.
    if rendered.returncode or len(rendered.stdout) > 4 * 1024 * 1024:
        raise ValueError('PDF page unavailable')
    with Image.open(io.BytesIO(rendered.stdout), formats=['PNG']) as image:
        if image.width * image.height > MAX_PIXELS:
            raise CheckLimit()
        image.load()
        answer = result('partial', 'PDF', 'pdf_first_page', pages=pages)
        if preview:
            answer['image'] = _png(image)
        return answer


def pdf_backend():
    try:
        import pypdfium2  # noqa: F401
        return 'pdfium'
    except ImportError:
        return 'poppler' if shutil.which('pdfinfo') and shutil.which('pdftoppm') else ''


def _office(data, preview, extension):
    from defusedxml.ElementTree import fromstring
    components = {
        'word/document.xml': ('DOCX', 'document', 'wordprocessingml.document.main+xml'),
        'xl/workbook.xml': ('XLSX', 'workbook', 'spreadsheetml.sheet.main+xml'),
        'ppt/presentation.xml': ('PPTX', 'presentation', 'presentationml.presentation.main+xml'),
    }
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS or sum(item.file_size for item in members) > MAX_EXPANDED:
            raise CheckLimit()
        names = [item.filename for item in members]
        if len(names) != len(set(names)):
            raise ValueError('Ambiguous archive')
        for name in names:
            if (len(name) > 512 or '\\' in name or '\0' in name or name.startswith('/') or
                    '..' in PurePosixPath(name).parts):
                raise ValueError('Invalid package member')
        present = [name for name in components if name in names]
        if not present and extension not in OFFICE_EXTENSIONS:
            return result('unsupported', 'ZIP', 'zip_scope')
        if len(present) != 1 or '[Content_Types].xml' not in names or '_rels/.rels' not in names:
            raise ValueError('Missing Office components')
        component = present[0]
        kind, root_name, mime_suffix = components[component]
        trees = {}
        expanded = 0
        for item in members:
            if item.flag_bits & 1:
                return result('encrypted', kind, 'office_encrypted')
            is_xml = item.filename.endswith(('.xml', '.rels'))
            payload = bytearray()
            count = 0
            with archive.open(item) as stream:
                while True:
                    block = stream.read(64 * 1024)
                    if not block:
                        break
                    expanded += len(block);count += len(block)
                    if expanded > MAX_EXPANDED or (is_xml and count > MAX_XML):
                        raise CheckLimit()
                    if is_xml:
                        payload.extend(block)
            if count != item.file_size:
                raise ValueError('Incomplete archive member')
            if is_xml:
                tree = fromstring(bytes(payload), forbid_dtd=True,
                                  forbid_entities=True, forbid_external=True)
                # Bound XML depth/node count after the input/expansion limits.
                stack = [(tree, 0)];nodes = 0
                while stack:
                    node, depth = stack.pop();nodes += 1
                    if depth > 64 or nodes > 100_000:
                        raise CheckLimit()
                    stack.extend((child, depth + 1) for child in node)
                if item.filename in (component, '[Content_Types].xml', '_rels/.rels'):
                    trees[item.filename] = tree
        if trees[component].tag.rsplit('}', 1)[-1] != root_name:
            raise ValueError('Invalid Office root')
        types = trees['[Content_Types].xml']
        if types.tag != '{http://schemas.openxmlformats.org/package/2006/content-types}Types':
            raise ValueError('Invalid content types')
        if not any(node.attrib.get('PartName') == '/' + component and
                   node.attrib.get('ContentType', '').endswith(mime_suffix) for node in types):
            raise ValueError('Missing main content type')
        relationships = trees['_rels/.rels']
        if relationships.tag != '{http://schemas.openxmlformats.org/package/2006/relationships}Relationships':
            raise ValueError('Invalid relationships')
        if not any(node.attrib.get('Type', '').endswith('/officeDocument') and
                   node.attrib.get('Target', '').lstrip('/') == component and
                   node.attrib.get('TargetMode', 'Internal') == 'Internal' for node in relationships):
            raise ValueError('Missing main relationship')
        answer = result('checked', kind, 'office_container', members=len(members))
        if preview:
            snippet = ' '.join(text.strip() for text in trees[component].itertext() if text.strip())
            answer['text'] = snippet[:32768]
        return answer


def inspect(data, extension='', preview=False):
    kind = content_kind(data, extension)
    if len(data) > MAX_INPUT:
        return result('limited', '', 'input_limit')
    try:
        if kind == 'image':
            return _image(data, preview)
        if kind == 'pdf':
            backend = pdf_backend()
            if not backend:
                return result('unsupported', 'PDF', 'dependency_missing')
            return _pdfium(data, preview) if backend == 'pdfium' else _poppler(data, preview)
        if kind == 'office':
            if data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                return result('unsupported', 'Office', 'office_ole')
            return _office(data, preview, extension)
        return result('unsupported', '', 'unsupported')
    except (CheckLimit, MemoryError, subprocess.TimeoutExpired):
        return result('limited', kind, 'processing_limit')
    except ImportError:
        return result('unsupported', kind, 'dependency_missing')
    except Exception as exc:
        from PIL import Image
        if isinstance(exc, (Image.DecompressionBombError, Image.DecompressionBombWarning)):
            return result('limited', kind, 'processing_limit')
        # Parser errors can contain document text/metadata. Do not leak them
        # into logs or treat every unsupported/limited case as corruption.
        return result('unreadable', kind, 'parse_failed')


def main(mode, extension):
    if mode not in ('preview', 'check') or len(extension) > 16:
        return 2
    if sys.platform != 'win32':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    def binary_stream(stream, handle, flags, mode):
        if stream is not None:
            return stream.buffer
        # PyInstaller --windowed deliberately sets sys.stdin/stdout to None.
        # Popen supplied inherited anonymous pipe handles for this worker.
        import ctypes
        from ctypes import wintypes
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel.GetStdHandle.restype = wintypes.HANDLE
        native = kernel.GetStdHandle(handle & 0xffffffff)
        if not native or native == ctypes.c_void_p(-1).value:
            raise OSError('Content worker pipe unavailable')
        return os.fdopen(msvcrt.open_osfhandle(int(native), flags | os.O_BINARY), mode)
    incoming=binary_stream(sys.stdin,-10,os.O_RDONLY,'rb')
    outgoing=binary_stream(sys.stdout,-11,os.O_WRONLY,'wb')
    data = incoming.read(MAX_INPUT + 1)
    answer = inspect(data, extension.lower(), mode == 'preview')
    encoded = json.dumps(answer, ensure_ascii=True).encode('ascii')
    if len(encoded) > 4 * 1024 * 1024:
        encoded = json.dumps(result('limited', '', 'processing_limit')).encode('ascii')
    outgoing.write(encoded)
    outgoing.flush()
    return 0
