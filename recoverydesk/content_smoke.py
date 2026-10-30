"""Small in-memory packaging probes; no devices, source paths or GUI."""
import io
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
