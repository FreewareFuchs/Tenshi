"""Small in-memory packaging probes; no devices, source paths or GUI."""
import io
import struct
import zipfile


def pdf_fixture():
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
             b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Contents 4 0 R >>',
             b'<< /Length 0 >>\nstream\n\nendstream']
    data=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(data));data.extend(str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    start=len(data);data.extend(b'xref\n0 5\n0000000000 65535 f \n')
    for offset in offsets[1:]:data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Root 1 0 R /Size 5 >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(data)


def office_fixture(kind='docx'):
    components={
        'docx':('word/document.xml','wordprocessingml.document.main+xml',
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Tenshi</w:t></w:r></w:p></w:body></w:document>'),
        'xlsx':('xl/workbook.xml','spreadsheetml.sheet.main+xml',
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets/></workbook>'),
        'pptx':('ppt/presentation.xml','presentationml.presentation.main+xml',
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'),
    }
    name,mime,xml=components[kind];stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml',f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/{name}" ContentType="application/vnd.openxmlformats-officedocument.{mime}"/></Types>')
        archive.writestr('_rels/.rels',f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="{name}"/></Relationships>')
        archive.writestr(name,xml)
    return stream.getvalue()


def binary_office_fixture():
    """Tiny CFB/BIFF8 structural probe, not a complete spreadsheet document."""
    free, end, fat = 0xffffffff, 0xfffffffe, 0xfffffffd
    raw = bytearray(5632)
    raw[:8] = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    struct.pack_into('<HHHHH', raw, 24, 0x3e, 3, 0xfffe, 9, 6)
    struct.pack_into('<IIIIIIIII', raw, 40, 0, 1, 1, 0, 4096, end, 0, end, 0)
    struct.pack_into('<109I', raw, 76, 0, *([free] * 108))
    allocation = [fat, end] + list(range(3, 10)) + [end] + [free] * 118
    struct.pack_into('<128I', raw, 512, *allocation)
    for at, name, kind, first, size, child in (
            (1024, 'Root Entry', 5, end, 0, 1),
            (1152, 'Workbook', 2, 2, 4096, free)):
        encoded = (name + '\0').encode('utf-16le')
        raw[at:at+len(encoded)] = encoded
        struct.pack_into('<HBBIII', raw, at+64, len(encoded), kind, 1, free, free, child)
        struct.pack_into('<IQ', raw, at+116, first, size)
    struct.pack_into('<HHHH', raw, 1536, 0x809, 16, 0x600, 5)
    struct.pack_into('<HH', raw, 1556, 0x0a, 0)
    return bytes(raw)


def run():
    from PIL import Image
    from .content_check import analyze
    for kind in ('JPEG','BMP','PNG','GIF'):
        stream=io.BytesIO();Image.new('RGB',(12,8),'blue').save(stream,kind)
        answer=analyze(stream.getvalue(),'picture.'+kind.lower(),preview=True)
        if answer['status']!='checked' or not answer['image']:
            raise RuntimeError('Packaged image decoder failed: '+kind)
    answer=analyze(pdf_fixture(),'sample.pdf',preview=True)
    if answer['code']!='pdf_first_page' or not answer['image']:
        raise RuntimeError('Packaged PDF decoder failed')
    answer=analyze(office_fixture(),'sample.docx')
    if answer['code']!='office_container':
        raise RuntimeError('Packaged Office decoder failed')
    answer=analyze(binary_office_fixture(),'sample.xls',preview=True)
    if (answer['status'],answer['format'],answer['code'])!=('partial','XLS','office_binary_structure') or answer['image'] or answer['text']:
        raise RuntimeError('Packaged binary Office structure check failed')
