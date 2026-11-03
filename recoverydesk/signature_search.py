"""Bounded carving of contiguous JPEG/PNG structures in regular images only.

This is not a free-space scan, undelete proof, decoder or fragment reassembler.
Format structure establishes a candidate extent, never original integrity.
"""
import os
import stat
import struct
import zlib

from .filesystems import GenericEntry,GenericIndex,ROOT,ScanCancelled,read_exact
from .sources import open_source,is_device_source,validate_source
from .signature_formats import (Invalid as FormatInvalid, Limit as FormatLimit,
                                parse as parse_format)

FILESYSTEM='File signatures v2'
LEGACY_FILESYSTEM='JPEG/PNG signatures v1'
PNG=b'\x89PNG\r\n\x1a\n'
JPEG=b'\xff\xd8\xff'
MAX_FILE=32*1024**2
SCAN_BLOCK=1024**2
MAX_CANDIDATES=5000
MAX_HITS=1000
MAX_INSPECTION=512*1024**2
MAX_CONFIGURABLE_FILE=256*1024**2
SCOPE='Signaturfunde: erkannte zusammenhängende Dateistrukturen ohne Originalnamen oder Ordner. Belegte und freie Bereiche werden durchsucht; ein Fund beweist weder Löschung noch unversehrte Originalinhalte. Fragmente werden nicht zusammengesetzt.'


class _Invalid(ValueError):pass
class _Limit(ValueError):pass


class _Budget(list):
    def __init__(self, file_limit, cancel):
        super().__init__([0])
        self.file_limit = file_limit
        self.cancel = cancel

    def check(self):
        _stop(self.cancel)


def _stop(cancel):
    if cancel and cancel():raise ScanCancelled('Scan abgebrochen.')


class _Reader:
    def __init__(self,stream,start,total,budget,cancel):
        self.stream=stream;self.start=start;self.limit=min(getattr(budget,'file_limit',MAX_FILE),total-start)
        self.pos=0;self.buffer=b'';self.budget=budget;self.cancel=cancel
    def read(self,n):
        _stop(self.cancel)
        if n<0 or n>self.limit-self.pos:raise _Invalid()
        while len(self.buffer)<n:
            at=self.pos+len(self.buffer)
            size=min(64*1024,self.limit-at)
            if not size:raise _Invalid()
            if size>MAX_INSPECTION-self.budget[0]:raise _Limit()
            self.stream.seek(self.start+at);block=self.stream.read(size)
            if len(block)!=size:raise OSError('Image lieferte unvollständige Daten.')
            self.budget[0]+=size;self.buffer+=block
        data=self.buffer[:n];self.buffer=self.buffer[n:];self.pos+=n
        return data
    def entropy_marker(self):
        while True:
            _stop(self.cancel)
            if not self.buffer:
                first=self.read(1)
                self.buffer=first+self.buffer;self.pos-=1
            at=self.buffer.find(b'\xff')
            if at<0:self.pos+=len(self.buffer);self.buffer=b'';continue
            self.read(at+1)
            marker=self.read(1)[0]
            while marker==255:marker=self.read(1)[0]
            if marker==0 or 0xd0<=marker<=0xd7:continue
            return marker


def _png(reader):
    if reader.read(8)!=PNG:raise _Invalid()
    ihdr=False;idat=False;ended_idat=False;palette=False;indexed=False
    for _ in range(4096):
        size,kind=struct.unpack('>I4s',reader.read(8))
        if size+4>reader.limit-reader.pos:raise _Invalid()
        if any(not (65<=x<=90 or 97<=x<=122) for x in kind) or kind[2]&32:raise _Invalid()
        if not ihdr and (kind!=b'IHDR' or size!=13):raise _Invalid()
        if kind==b'IHDR' and ihdr:raise _Invalid()
        if kind==b'IHDR' and size!=13:raise _Invalid()
        if kind[0]&32==0 and kind not in (b'IHDR',b'PLTE',b'IDAT',b'IEND'):raise _Invalid()
        crc=zlib.crc32(kind);remaining=size;header=b''
        while remaining:
            block=reader.read(min(64*1024,remaining));crc=zlib.crc32(block,crc)
            if kind==b'IHDR':header+=block
            remaining-=len(block)
        if struct.unpack('>I',reader.read(4))[0]!=crc&0xffffffff:raise _Invalid()
        if kind==b'IHDR':
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',header)
            depths={0:(1,2,4,8,16),2:(8,16),3:(1,2,4,8),4:(8,16),6:(8,16)}
            if not 0<width<2**31 or not 0<height<2**31 or depth not in depths.get(color,()) or compression or filtering or interlace not in (0,1):raise _Invalid()
            indexed=color==3;ihdr=True
        elif kind==b'PLTE':
            if palette or idat or not size or size%3 or size>768:raise _Invalid()
            palette=True
        elif kind==b'IDAT':
            if ended_idat or (indexed and not palette):raise _Invalid()
            idat=True
        elif kind==b'IEND':
            if size or not idat:raise _Invalid()
            return reader.pos
        elif idat:ended_idat=True
    raise _Invalid()


def _jpeg(reader):
    if reader.read(2)!=b'\xff\xd8':raise _Invalid()
    sof=False;scan=False;pending=None
    for _ in range(65536):
        if pending is None:
            if reader.read(1)!=b'\xff':raise _Invalid()
            marker=reader.read(1)[0]
            while marker==255:marker=reader.read(1)[0]
        else:marker=pending;pending=None
        if marker==0xd9:
            if not sof or not scan:raise _Invalid()
            return reader.pos
        if marker in (0,0xd8) or 0xd0<=marker<=0xd7:raise _Invalid()
        if marker==1:continue
        size=int.from_bytes(reader.read(2),'big')
        if size<2:raise _Invalid()
        data=reader.read(size-2)
        if marker in (0xc0,0xc1,0xc2):
            if sof or len(data)<6:raise _Invalid()
            precision,height,width,components=struct.unpack('>BHHB',data[:6])
            if precision not in (8,12) or not width or not height or not 1<=components<=4 or len(data)!=6+3*components:raise _Invalid()
            sof=True
        elif marker==0xda:
            if not sof or len(data)<4 or not 1<=data[0]<=4 or len(data)!=4+2*data[0]:raise _Invalid()
            scan=True;pending=reader.entropy_marker()
        elif 0xc0<=marker<=0xcf and marker not in (0xc4,0xc8,0xcc):raise _Invalid()
    raise _Invalid()


class SignatureVolume:
    label=FILESYSTEM
    offset=0
    def __init__(self,total,entries,snapshot):
        self.total=total
        self.snapshot=snapshot
        self.allowed={entry.key:(entry.size,entry.locator) for entry in entries}
    def iter_file(self,stream,entry,max_bytes=None):
        if _snapshot(os.fstat(stream.fileno()))!=self.snapshot:raise ValueError('Quell-Image wurde geändert.')
        if self.allowed.get(entry.key)!=(entry.size,entry.locator):raise ValueError('Ungültiger Signaturfund.')
        tag,start,size=entry.locator
        if tag!='signature-v1' or not 0<=start<=self.total-size:raise ValueError('Ungültiger Signaturbereich.')
        remaining=size if max_bytes is None else min(size,max_bytes)
        if remaining<0:raise ValueError('Ungültige Lesegrenze.')
        at=start
        while remaining:
            block=read_exact(stream,at,min(64*1024,remaining))
            yield block;at+=len(block);remaining-=len(block)
        if _snapshot(os.fstat(stream.fileno()))!=self.snapshot:raise ValueError('Quell-Image wurde geändert.')


def _snapshot(value):
    return value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns


def scan_signatures(source,*,category='images',categories=None,max_file_bytes=None,cancel=None,progress=None,
                    checkpoint_path=None,resume=False,parser_revision=2):
    """Optionally persist completed scan blocks and resume an explicitly selected image."""
    if checkpoint_path is None:
        if resume:
            raise ValueError('Bitte einen gespeicherten Suchstand auswählen.')
        return _scan_signatures(source,category=category,categories=categories,
                                max_file_bytes=max_file_bytes,cancel=cancel,progress=progress,
                                _parser_revision=parser_revision)
    from .signature_checkpoint import read_checkpoint, CheckpointWriter
    from .session_store import fingerprint_image, check_fingerprint
    if max_file_bytes is not None and max_file_bytes not in tuple(m*1024**2 for m in (32,64,128,256)):
        raise ValueError('Ungültige Größenbegrenzung für die Signatursuche.')
    state = read_checkpoint(checkpoint_path) if resume else None
    if state is not None:
        if ((categories is not None and frozenset(categories) != frozenset(state['categories'])) or
                (max_file_bytes is not None and max_file_bytes != state['file_limit'])):
            raise ValueError('Suchstand oder Sucheinstellungen wurden geändert. Bitte erneut öffnen.')
        if state['limited']:
            raise ValueError('Suchstand hat eine Prüfgrenze erreicht. Bitte eine neue Suche starten.')
        fingerprint = check_fingerprint(source,state['fingerprint'],original=state['source'])
        categories = tuple(state['categories'])
        max_file_bytes = state['file_limit']
        parser_revision = state.get('parser_revision',1)
    else:
        fingerprint = fingerprint_image(source,[1])
    source_snapshot = _snapshot(os.stat(source))
    if fingerprint['size'] != source_snapshot[2] or fingerprint['mtime_ns'] != source_snapshot[3]:
        raise ValueError('Quell-Image wurde geändert.')
    writer = CheckpointWriter(checkpoint_path,source,fingerprint,source_snapshot)
    try:
        return _scan_signatures(source,category=category,categories=categories,max_file_bytes=max_file_bytes,
                                cancel=cancel,progress=progress,_resume=state,_checkpoint=writer.update,
                                _parser_revision=parser_revision)
    finally:
        writer.flush()


def _signature_entry(start,size,kind):
    extension={'PNG':'png','JPEG':'jpg','BMP':'bmp','GIF':'gif','WebP':'webp','TIFF':'tiff',
               'DOCX':'docx','DOCM':'docm','DOTX':'dotx','DOTM':'dotm',
               'XLSX':'xlsx','XLSM':'xlsm','XLTX':'xltx','XLTM':'xltm',
               'PPTX':'pptx','PPTM':'pptm','POTX':'potx','POTM':'potm',
               'ODT':'odt','ODS':'ods','ODP':'odp','ODG':'odg','ZIP':'zip',
               'TAR':'tar','7Z':'7z','RAR':'rar','PDF':'pdf','WAV':'wav','AVI':'avi','MP4':'mp4',
               'OGG-Vorbis':'ogg','OGG-Opus':'opus','MP3':'mp3'}.get(kind)
    if extension is None:
        raise ValueError('Ungültiger gespeicherter Suchstand.')
    return GenericEntry(start+100,f'{kind}_{start:016X}.{extension}',ROOT,False,size,('signature-v1',start,size))


def _scan_signatures(source,*,category='images',categories=None,max_file_bytes=None,cancel=None,progress=None,
                     _resume=None,_checkpoint=None,_parser_revision=2):
    """Search selected categories in a single sequential pass over a regular image."""
    available = ('images','office','archives','audio','video')
    if type(_parser_revision) is not int or _parser_revision not in (1,2):
        raise ValueError('Ungültige Suchversion.')
    selected = frozenset(categories) if categories is not None else frozenset(available if category == 'all' else (category,))
    if not selected or not selected.issubset(available):
        raise ValueError('Unbekannte Signaturkategorie.')
    file_limit = MAX_FILE if max_file_bytes is None else max_file_bytes
    if type(file_limit) is not int or not 0 < file_limit <= MAX_CONFIGURABLE_FILE:
        raise ValueError('Ungültige Größenbegrenzung für die Signatursuche.')
    category = next(iter(selected)) if len(selected) == 1 else 'all'
    validate_source(source)
    if is_device_source(source):raise ValueError('Signatursuche erfordert ein reguläres Image.')
    before=os.stat(source)
    if not stat.S_ISREG(before.st_mode) or before.st_size<512:raise ValueError('Signatursuche erfordert ein reguläres Image.')
    entries=[];candidates=0;budget=_Budget(file_limit,cancel);position=0;tail=b'';last=-1;limited=False
    with open_source(source) as stream:
        opened=os.fstat(stream.fileno())
        if _snapshot(opened)!=_snapshot(before):raise ValueError('Quell-Image wurde geändert.')
        total=opened.st_size
        if _resume is not None:
            # Reparse every cached candidate instead of trusting stored extents.
            validation = _Budget(file_limit,cancel)
            for start, expected_size, expected_kind in _resume['hits']:
                _stop(cancel)
                if _parser_revision == 1 and expected_kind in ('PDF','RAR'):
                    raise ValueError('Ungültiger gespeicherter Suchstand.')
                try:
                    if expected_kind in ('PNG','JPEG'):
                        if 'images' not in selected:raise _Invalid()
                        reader = _Reader(stream,start,total,validation,cancel)
                        size = (_png if expected_kind == 'PNG' else _jpeg)(reader)
                        kind = expected_kind
                    else:
                        size,kind,found_category = parse_format(stream,start,total,validation,category)
                        if found_category not in selected or (kind in ('GIF','TIFF') and size > file_limit):raise _Invalid()
                    if size != expected_size or kind != expected_kind:raise _Invalid()
                    entries.append(_signature_entry(start,size,kind))
                except (FormatInvalid,_Invalid,_Limit) as exc:
                    raise ValueError('Gespeicherte Signaturfunde konnten nicht bestätigt werden.') from exc
            position = _resume['position'];last = _resume['last']
            candidates = _resume['candidates'];budget[0] = _resume['inspection']
            stream.seek(max(0,position-264));tail=stream.read(min(264,position))
        def save_block():
            if _checkpoint is not None:
                _checkpoint(dict(position=position,last=last,candidates=candidates,inspection=budget[0],
                                 categories=[key for key in available if key in selected],file_limit=file_limit,
                                 parser_revision=_parser_revision,
                                 limited=limited,hits=[[e.locator[1],e.size,e.name.split('_',1)[0]] for e in entries]))
        save_block()
        if _resume is not None and progress:progress(position,total)
        while position<total:
            _stop(cancel)
            stream.seek(position);block=stream.read(min(SCAN_BLOCK,total-position))
            if len(block)!=min(SCAN_BLOCK,total-position):raise OSError('Image lieferte unvollständige Daten.')
            data=tail+block;base=position-len(tail);found=[]
            if 'images' in selected:
                signatures=[(PNG,'PNG'),(JPEG,'JPEG'),(b'BM','OTHER'),
                            (b'GIF87a','OTHER'),(b'GIF89a','OTHER'),(b'RIFF','OTHER'),
                            (b'II*\0','OTHER'),(b'MM\0*','OTHER')]
            else:signatures=[]
            if selected.intersection(('office','archives')):
                signatures.append((b'PK\x03\x04','OTHER'))
            if _parser_revision >= 2 and 'office' in selected:
                signatures.append((b'%PDF-','OTHER'))
            if _parser_revision >= 2 and 'archives' in selected:
                signatures.append((b'Rar!\x1a\x07','OTHER'))
            if 'archives' in selected:
                signatures.append((b'7z\xbc\xaf\x27\x1c','OTHER'))
            if selected.intersection(('audio','video')):
                signatures.append((b'RIFF','OTHER'))
            if 'audio' in selected:
                signatures.extend(((b'OggS','OTHER'),(b'ID3','OTHER')))
            if 'video' in selected:
                for marker in (b'ftyp',):
                    at=data.find(marker)
                    while at>=4:
                        if base+at-4>last:found.append((base+at-4,'OTHER'))
                        at=data.find(marker,at+1)
            if 'archives' in selected:
                at=data.find(b'ustar')
                while at>=0:
                    start=base+at-257
                    if start>=0 and start>last:found.append((start,'OTHER'))
                    at=data.find(b'ustar',at+1)
            for signature,kind in dict.fromkeys(signatures):
                at=data.find(signature);count=0
                while at>=0 and count<=MAX_CANDIDATES:
                    if base+at>last:found.append((base+at,kind))
                    count+=1
                    at=data.find(signature,at+1)
            for start,kind in sorted(set(found)):
                _stop(cancel)
                if candidates>=MAX_CANDIDATES or len(entries)>=MAX_HITS:limited=True;break
                candidates+=1;last=start
                try:
                    if kind=='PNG' or kind=='JPEG':
                        reader=_Reader(stream,start,total,budget,cancel)
                        size=(_png if kind=='PNG' else _jpeg)(reader)
                    else:
                        size,kind,found_category=parse_format(stream,start,total,budget,category)
                        if _parser_revision == 1 and kind in ('PDF','RAR'):continue
                        if found_category not in selected:continue
                        if kind in ('GIF','TIFF') and size > file_limit:continue
                except (FormatLimit, _Limit):limited=True;break
                except (FormatInvalid, _Invalid):continue
                entries.append(_signature_entry(start,size,kind))
            position+=len(block);tail=data[-264:]
            save_block()
            if progress:progress(position,total)
            if limited:break
        after=os.fstat(stream.fileno());_stop(cancel)
        if _snapshot(opened)!=_snapshot(after) or _snapshot(opened)!=_snapshot(os.stat(source)):raise ValueError('Quell-Image wurde geändert.')
    index=GenericIndex(FILESYSTEM,0,entries,SignatureVolume(total,entries,_snapshot(opened)),children={ROOT:entries})
    index.scan_warnings=[SCOPE]
    if limited:index.scan_warnings.append('Signatursuche: Prüfgrenze erreicht; Ergebnis unvollständig.')
    index.signature_scanned_bytes=position;index.signature_source_bytes=total
    index.signature_candidates=candidates;index.signature_complete=not limited
    index.signature_category=category
    index.signature_categories=tuple(key for key in available if key in selected)
    index.signature_file_limit=file_limit
    index.signature_parser_revision=_parser_revision
    if _parser_revision == 1:
        index.scan_warnings.append('Älterer Suchstand: PDF/RAR erfordern eine neue Suche.')
    return index
