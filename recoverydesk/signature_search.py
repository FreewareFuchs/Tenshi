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

FILESYSTEM='JPEG/PNG signatures v1'
PNG=b'\x89PNG\r\n\x1a\n'
JPEG=b'\xff\xd8\xff'
MAX_FILE=32*1024**2
SCAN_BLOCK=1024**2
MAX_CANDIDATES=5000
MAX_HITS=1000
MAX_INSPECTION=512*1024**2
SCOPE='Signaturfunde: zusammenhängende JPEG/PNG-Strukturen, keine Originalnamen oder Ordner. Belegte und freie Bereiche werden durchsucht; ein Fund beweist weder Löschung noch unversehrte Originalinhalte. Fragmentierte Dateien werden nicht zusammengesetzt.'


class _Invalid(ValueError):pass
class _Limit(ValueError):pass


def _stop(cancel):
    if cancel and cancel():raise ScanCancelled('Scan abgebrochen.')


class _Reader:
    def __init__(self,stream,start,total,budget,cancel):
        self.stream=stream;self.start=start;self.limit=min(MAX_FILE,total-start)
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
        if size>MAX_FILE or size+4>reader.limit-reader.pos:raise _Invalid()
        if any(not (65<=x<=90 or 97<=x<=122) for x in kind) or kind[2]&32:raise _Invalid()
        if not ihdr and (kind!=b'IHDR' or size!=13):raise _Invalid()
        if kind==b'IHDR' and ihdr:raise _Invalid()
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


def scan_signatures(source,*,cancel=None,progress=None):
    """Search the complete regular image; no output files or decoder processes."""
    validate_source(source)
    if is_device_source(source):raise ValueError('Signatursuche erfordert ein reguläres Image.')
    before=os.stat(source)
    if not stat.S_ISREG(before.st_mode) or before.st_size<512:raise ValueError('Signatursuche erfordert ein reguläres Image.')
    entries=[];candidates=0;budget=[0];position=0;tail=b'';last=-1;limited=False
    with open_source(source) as stream:
        opened=os.fstat(stream.fileno())
        if _snapshot(opened)!=_snapshot(before):raise ValueError('Quell-Image wurde geändert.')
        total=opened.st_size
        while position<total:
            _stop(cancel)
            stream.seek(position);block=stream.read(min(SCAN_BLOCK,total-position))
            if len(block)!=min(SCAN_BLOCK,total-position):raise OSError('Image lieferte unvollständige Daten.')
            data=tail+block;base=position-len(tail);found=[]
            for signature,kind in ((PNG,'PNG'),(JPEG,'JPEG')):
                at=data.find(signature);count=0
                while at>=0 and count<=MAX_CANDIDATES:
                    if base+at>last:found.append((base+at,kind))
                    count+=1
                    at=data.find(signature,at+1)
            for start,kind in sorted(found):
                _stop(cancel)
                if candidates>=MAX_CANDIDATES or len(entries)>=MAX_HITS:limited=True;break
                candidates+=1;last=start
                reader=_Reader(stream,start,total,budget,cancel)
                try:size=(_png if kind=='PNG' else _jpeg)(reader)
                except _Invalid:continue
                except _Limit:limited=True;break
                extension='png' if kind=='PNG' else 'jpg'
                entries.append(GenericEntry(start+100,f'{kind}_{start:016X}.{extension}',ROOT,False,size,('signature-v1',start,size)))
            position+=len(block);tail=data[-7:]
            if progress:progress(position,total)
            if limited:break
        after=os.fstat(stream.fileno());_stop(cancel)
        if _snapshot(opened)!=_snapshot(after) or _snapshot(opened)!=_snapshot(os.stat(source)):raise ValueError('Quell-Image wurde geändert.')
    index=GenericIndex(FILESYSTEM,0,entries,SignatureVolume(total,entries,_snapshot(opened)),children={ROOT:entries})
    index.scan_warnings=[SCOPE]
    if limited:index.scan_warnings.append('Signatursuche: Prüfgrenze erreicht; Ergebnis unvollständig.')
    index.signature_scanned_bytes=position;index.signature_source_bytes=total
    index.signature_candidates=candidates;index.signature_complete=not limited
    return index
