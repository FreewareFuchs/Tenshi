"""Bounded RAR 4/5 header walkers. No extraction or decryption."""
import struct
import zlib

from .signature_formats import Invalid, _read, MAX_FORMAT_FILE

RAR4 = b'Rar!\x1a\x07\x00'
RAR5 = b'Rar!\x1a\x07\x01\x00'


def _vint(data, position, end):
    value = 0
    for shift in range(0,70,7):
        if position >= end:
            raise Invalid()
        byte = data[position]; position += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            if value >= 1 << 64:
                raise Invalid()
            return value, position
    raise Invalid()


def rar4(stream, start, total, budget):
    if _read(stream,start,7,total,budget) != RAR4:
        raise Invalid()
    position = 7
    files = 0
    main = False
    for _ in range(100_000):
        base = _read(stream,start+position,7,total,budget)
        crc,kind,flags,size = struct.unpack('<HBHH',base)
        if size < 7 or position + size > MAX_FORMAT_FILE:
            raise Invalid()
        header = _read(stream,start+position,size,total,budget)
        if zlib.crc32(header[2:]) & 0xffff != crc:
            raise Invalid()
        packed = 0
        if not main:
            if kind != 0x73 or size < 13 or flags & (0x0001|0x0002|0x0080|0x8000):
                raise Invalid()  # volumes, legacy embedded comments, encrypted headers
            main = True
        elif kind == 0x73:
            raise Invalid()
        elif kind in (0x74,0x7a):
            if size < 32 or not flags & 0x8000 or flags & 3:
                raise Invalid()
            packed = struct.unpack_from('<I',header,7)[0]
            name_size = struct.unpack_from('<H',header,26)[0]
            name_start = 32
            if flags & 0x100:
                if size < 40:raise Invalid()
                packed += struct.unpack_from('<I',header,32)[0] << 32
                name_start = 40
            if not name_size or name_start + name_size > size:
                raise Invalid()
            if kind == 0x74:files += 1
        elif kind == 0x7b:
            if not files or flags & (1|0x8000):raise Invalid()
            return position + size, 'RAR', 'archives'
        elif kind in (0x75,0x76,0x77,0x78,0x79):
            if flags & 0x8000:
                if size < 11:raise Invalid()
                packed = struct.unpack_from('<I',header,7)[0]
        else:
            raise Invalid()
        position += size + packed
        if position > MAX_FORMAT_FILE or start + position > total:
            raise Invalid()
    raise Invalid()


def rar5(stream, start, total, budget):
    if _read(stream,start,8,total,budget) != RAR5:
        raise Invalid()
    position = 8
    main = False
    files = 0
    for _ in range(100_000):
        prefix = _read(stream,start+position, min(7,total-start-position),total,budget)
        if len(prefix) < 5:raise Invalid()
        size, at = _vint(prefix,4,len(prefix))
        if at > 7 or size < 2 or size > 2*1024**2 or position+at+size > MAX_FORMAT_FILE:
            raise Invalid()
        header = _read(stream,start+position+at,size,total,budget)
        if zlib.crc32(prefix[4:at]+header) & 0xffffffff != struct.unpack_from('<I',prefix)[0]:
            raise Invalid()
        kind, cur = _vint(header,0,size)
        flags, cur = _vint(header,cur,size)
        if flags & 0x18:raise Invalid()  # split volumes
        extra = packed = 0
        if flags & 1:extra,cur = _vint(header,cur,size)
        if flags & 2:packed,cur = _vint(header,cur,size)
        end = size-extra
        if end < cur:raise Invalid()
        if not main:
            if kind != 1 or packed:raise Invalid()
            archive_flags,cur = _vint(header,cur,end)
            if archive_flags & 3:raise Invalid()
            main = True
        elif kind == 1 or kind == 4:
            raise Invalid()  # duplicate main or header encryption
        elif kind in (2,3):
            file_flags,cur = _vint(header,cur,end)
            _,cur = _vint(header,cur,end)  # unpacked size
            _,cur = _vint(header,cur,end)  # attributes
            cur += (4 if file_flags & 2 else 0) + (4 if file_flags & 4 else 0)
            _,cur = _vint(header,cur,end)  # compression information
            host,cur = _vint(header,cur,end)
            length,cur = _vint(header,cur,end)
            if host not in (0,1) or not length or cur+length > end:
                raise Invalid()
            if kind == 2:files += 1
        elif kind == 5:
            final_flags,cur = _vint(header,cur,end)
            if not files or final_flags & 1 or packed:raise Invalid()
            return position+at+size, 'RAR', 'archives'
        elif not flags & 4:
            raise Invalid()
        position += at+size+packed
        if position > MAX_FORMAT_FILE or start+position > total:raise Invalid()
    raise Invalid()
