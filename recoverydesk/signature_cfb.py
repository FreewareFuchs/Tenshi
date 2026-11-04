"""Bounded CFB structure candidates for Word/Excel/PowerPoint binary files.

Own implementation from MS-CFB/MS-DOC/MS-XLS/MS-PPT. No COM, Office automation,
macro execution, decompression or claim of original-content integrity.
"""
from array import array
import struct
import sys

from .signature_formats import Invalid, _read, _file_limit

MAGIC=b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
FREE=0xffffffff
END=0xfffffffe
FAT=0xfffffffd
DIF=0xfffffffc
MAX_ENTRIES=8192


def _words(data):
    values=array('I');values.frombytes(data)
    if sys.byteorder!='little':values.byteswap()
    return values


class _Compound:
    def __init__(self,stream,start,total,budget):
        self.stream=stream;self.start=start;self.budget=budget
        self.limit=min(_file_limit(budget),total-start)
        h=self.read(0,512)
        self.version=struct.unpack_from('<H',h,26)[0]
        shift=struct.unpack_from('<H',h,30)[0]
        if (h[:8]!=MAGIC or any(h[8:24]) or self.version not in (3,4) or
                struct.unpack_from('<H',h,28)[0]!=0xfffe or
                shift!={3:9,4:12}[self.version] or h[32:34]!=b'\x06\0' or any(h[34:40])):
            raise Invalid()
        self.sector_size=1<<shift
        self.available=self.limit//self.sector_size-1
        if self.available<2:raise Invalid()
        if self.version==4 and any(self.read(512,self.sector_size-512)):raise Invalid()
        dirs,nfat,first_dir=struct.unpack_from('<III',h,40)
        cutoff,first_mini,nmini,first_dif,ndif=struct.unpack_from('<IIIII',h,56)
        per_sector=self.sector_size//4
        if (cutoff!=4096 or not 1<=nfat<=(self.available+per_sector-1)//per_sector or
                nmini>self.available or ndif!=(max(0,nfat-109)+per_sector-2)//(per_sector-1)):
            raise Invalid()
        if self.version==3 and dirs:raise Invalid()
        fat_ids=[];dif_ids=[]
        def add_fat(values):
            for value in values:
                if value!=FREE:
                    if value>=self.available or value in fat_seen:raise Invalid()
                    fat_seen.add(value);fat_ids.append(value)
                    if len(fat_ids)>nfat:raise Invalid()
        fat_seen=set();add_fat(_words(h[76:512]))
        current=first_dif
        for _ in range(ndif):
            self.check()
            if current>=self.available or current in dif_ids or current in fat_seen:raise Invalid()
            dif_ids.append(current)
            values=_words(self.sector(current));add_fat(values[:-1]);current=values[-1]
        if current!=END or len(fat_ids)!=nfat or set(dif_ids)&fat_seen:raise Invalid()
        self.fat=array('I')
        for sector in fat_ids:self.fat.extend(_words(self.sector(sector)))
        self.owners=bytearray(len(self.fat))
        last=-1
        for number,value in enumerate(self.fat):
            if number%4096==0:self.check()
            if value==FREE:continue
            if number>=self.available or (value not in (END,FAT,DIF) and value>=min(self.available,len(self.fat))):
                raise Invalid()
            last=number
        self.extent=(last+2)*self.sector_size
        if self.extent>self.limit:raise Invalid()
        for number in fat_ids:
            if number>=len(self.fat) or self.fat[number]!=FAT:raise Invalid()
            self.claim(number)
        for number in dif_ids:
            if number>=len(self.fat) or self.fat[number]!=DIF:raise Invalid()
            self.claim(number)
        directory=self.chain(first_dir,maximum=MAX_ENTRIES//(self.sector_size//128))
        if self.version==4 and len(directory)!=dirs:raise Invalid()
        entries=[]
        for number in directory:
            data=self.sector(number)
            entries.extend(self.entry(data[n:n+128]) for n in range(0,len(data),128))
        if not entries or entries[0] is None or entries[0]['kind']!=5:raise Invalid()
        root=entries[0]
        if root['left']!=FREE or root['right']!=FREE:raise Invalid()
        # Iterative hierarchy traversal rejects cycles, shared children and
        # stream-name tricks inside embedded storages when classifying roots.
        visited={0};names={};stack=[(root['child'],0)]
        while stack:
            self.check()
            number,parent=stack.pop()
            if number==FREE:continue
            if not 0<number<len(entries) or number in visited or entries[number] is None:raise Invalid()
            visited.add(number);entry=entries[number]
            if entry['kind'] not in (1,2):raise Invalid()
            identity=(parent,entry['name'].casefold())
            if identity in names:raise Invalid()
            names[identity]=number
            stack.extend(((entry['left'],parent),(entry['right'],parent)))
            if entry['kind']==1:stack.append((entry['child'],number))
            elif entry['child']!=FREE:raise Invalid()
        if {i for i,e in enumerate(entries) if e is not None}!=visited:raise Invalid()
        self.entries=entries
        # Do not allocate a MiniFAT based on an attacker-controlled header
        # count unrelated to the bounded root mini stream it describes.
        if nmini>(root['size']+64*per_sector-1)//(64*per_sector):raise Invalid()
        mini_sectors=self.chain(first_mini,maximum=nmini) if nmini else []
        if len(mini_sectors)!=nmini or (not nmini and first_mini!=END):raise Invalid()
        self.mini=array('I')
        for number in mini_sectors:self.mini.extend(_words(self.sector(number)))
        self.mini_owners=bytearray(len(self.mini))
        self.root_chain=self.data_chain(root,root=True)
        self.chains={}
        for number in sorted(visited-{0}):
            entry=entries[number]
            if entry['kind']==2:self.chains[number]=self.data_chain(entry)
        if any(value!=FREE and not self.owners[i] for i,value in enumerate(self.fat)):raise Invalid()
        if any(value!=FREE and not self.mini_owners[i] for i,value in enumerate(self.mini)):raise Invalid()
        self.roots={name:number for (parent,name),number in names.items() if parent==0 and entries[number]['kind']==2}

    def check(self):
        if hasattr(self.budget,'check'):self.budget.check()

    def read(self,offset,size):
        if offset<0 or size<0 or offset+size>self.limit:raise Invalid()
        return _read(self.stream,self.start+offset,size,self.start+self.limit,self.budget)

    def sector(self,number):
        if not 0<=number<self.available:raise Invalid()
        return self.read((number+1)*self.sector_size,self.sector_size)

    def claim(self,number,*,mini=False):
        owners=self.mini_owners if mini else self.owners
        table=self.mini if mini else self.fat
        if not 0<=number<len(owners) or owners[number] or table[number]==FREE:raise Invalid()
        owners[number]=1

    def chain(self,first,*,maximum=None,mini=False):
        result=array('I');table=self.mini if mini else self.fat
        bound=len(table) if maximum is None else maximum
        current=first
        while current!=END:
            if len(result)%256==0:self.check()
            if len(result)>=bound:raise Invalid()
            self.claim(current,mini=mini);result.append(current);current=table[current]
        return result

    def entry(self,raw):
        kind=raw[66]
        if kind==0:return None
        length=struct.unpack_from('<H',raw,64)[0]
        if kind not in (1,2,5) or raw[67]>1 or not 2<=length<=64 or length%2 or raw[length-2:length]!=b'\0\0':raise Invalid()
        try:name=raw[:length-2].decode('utf-16le')
        except UnicodeError as exc:raise Invalid() from exc
        if not name or any(c in name for c in '\0/\\:!'):raise Invalid()
        left,right,child=struct.unpack_from('<III',raw,68)
        first,size=struct.unpack_from('<IQ',raw,116)
        # Historical v3 writers sometimes left the upper size word uninitialized.
        if self.version==3:size &= 0xffffffff
        if size>self.limit or (kind==1 and (first or size)):raise Invalid()
        return dict(kind=kind,name=name,left=left,right=right,child=child,first=first,size=size)

    def data_chain(self,entry,*,root=False):
        size=entry['size']
        if not size:
            if entry['first']!=END:raise Invalid()
            return array('I')
        small=not root and size<4096
        unit=64 if small else self.sector_size
        chain=self.chain(entry['first'],mini=small)
        if len(chain)<(size+unit-1)//unit:raise Invalid()
        if small and any((i+1)*64>self.entries[0]['size'] for i in chain):raise Invalid()
        return chain

    def stream_read(self,number,offset,size):
        entry=self.entries[number]
        if offset<0 or size<0 or offset+size>entry['size']:raise Invalid()
        small=entry['size']<4096;unit=64 if small else self.sector_size
        chain=self.chains[number];result=bytearray()
        while size:
            sector=chain[offset//unit];part=offset%unit;count=min(size,unit-part)
            if small:
                at=sector*64+part
                physical=self.root_chain[at//self.sector_size]
                absolute=(physical+1)*self.sector_size+at%self.sector_size
            else:absolute=(sector+1)*self.sector_size+part
            result.extend(self.read(absolute,count));offset+=count;size-=count
        return bytes(result)

    def classify(self):
        roots=self.roots;families=[]
        if 'worddocument' in roots:
            number=roots['worddocument'];head=self.stream_read(number,0,68)
            ident,version=struct.unpack_from('<HH',head)
            table='1table' if struct.unpack_from('<H',head,10)[0]&0x200 else '0table'
            if (ident==0xa5ec and version in (0xc1,0xd9,0x101,0x10c,0x112) and table in roots and
                    struct.unpack_from('<H',head,32)[0]==14 and struct.unpack_from('<H',head,62)[0]==22):
                count=struct.unpack('<H',self.stream_read(number,152,2))[0]
                if 93<=count<=183 and 156+8*count<=self.entries[number]['size']:families.append('DOC')
        for name in ('workbook','book'):
            if name not in roots:continue
            number=roots[name];head=self.stream_read(number,0,20)
            record,length,version,kind=struct.unpack_from('<HHHH',head)
            if record==0x809 and length==16 and version==0x600 and kind==5:
                position=20
                for _ in range(100000):
                    if position+4>self.entries[number]['size']:break
                    record,length=struct.unpack('<HH',self.stream_read(number,position,4))
                    position+=4
                    if position+length>self.entries[number]['size']:raise Invalid()
                    if record==0x0a:
                        if length:raise Invalid()
                        families.append('XLS');break
                    position+=length
        if 'powerpoint document' in roots and 'current user' in roots:
            user=self.stream_read(roots['current user'],0,28)
            flags,kind,length,size,token,edit=struct.unpack_from('<HHIIII',user)
            stream_size=self.entries[roots['current user']]['size']
            username=struct.unpack_from('<H',user,20)[0]
            if (flags==0 and kind==0xff6 and length+8<=stream_size and username<=255 and
                    stream_size in (32+username,32+3*username) and
                    length in (24+username,24+3*username) and size==20 and
                    token in (0xe391c05f,0xf3d1c4df) and struct.unpack_from('<H',user,22)[0]==0x3f4 and user[24:26]==b'\x03\0'):
                release=struct.unpack('<I',self.stream_read(roots['current user'],28+username,4))[0]
                if release not in (8,9):raise Invalid()
                head=self.stream_read(roots['powerpoint document'],edit,8)
                flags,kind,length=struct.unpack('<HHI',head)
                if flags==0 and kind==0xff5 and length in (28,32) and edit+8+length<=self.entries[roots['powerpoint document']]['size']:
                    families.append('PPT')
        if len(families)!=1:raise Invalid()
        return families[0]


def cfb(stream,start,total,budget):
    compound=_Compound(stream,start,total,budget)
    return compound.extent,compound.classify(),'office'
