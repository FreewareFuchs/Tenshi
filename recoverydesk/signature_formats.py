"""Conservative, bounded validators for common carved file formats.

Parsers return only a contiguous extent with enough structural evidence for a
candidate. They do not establish original filenames, integrity or recoverability.
"""
import math
import struct
import zlib
from io import BytesIO
import zipfile

MAX_FILE = 32 * 1024**2
MAX_FORMAT_FILE = 4 * 1024**4
MAX_ZIP_ENTRIES = 10_000
MAX_TAR_ENTRIES = 100_000


class Invalid(ValueError):
    pass


class Limit(Invalid):
    pass


def _read(stream, start, size, total, budget):
    if size < 0 or start < 0 or start + size > total or size > MAX_FILE:
        raise Invalid()
    if size > 512 * 1024**2 - budget[0]:
        raise Limit()
    stream.seek(start)
    data = stream.read(size)
    if len(data) != size:
        raise Invalid()
    budget[0] += size
    return data


def _bmp(stream, start, total, budget):
    head = _read(stream, start, 54, total, budget)
    size, offset, dib = struct.unpack_from('<IxxxxI', head, 2)[0], struct.unpack_from('<I', head, 10)[0], struct.unpack_from('<I', head, 14)[0]
    if head[:2] != b'BM' or dib not in (40, 52, 56, 64, 108, 124):
        raise Invalid()
    if size < offset or size > MAX_FORMAT_FILE or offset < 14 + dib or start + size > total:
        raise Invalid()
    width, height = struct.unpack_from('<ii', head, 18)
    planes, bits_per_pixel = struct.unpack_from('<HH', head, 26)
    compression = struct.unpack_from('<I', head, 30)[0]
    if (width <= 0 or height == 0 or planes != 1 or
            bits_per_pixel not in (1, 4, 8, 16, 24, 32) or
            compression not in (0, 1, 2, 3, 4, 5, 6, 11, 12, 13)):
        raise Invalid()
    return size, 'BMP', 'images'


def _gif(stream, start, total, budget):
    head = _read(stream, start, 13, total, budget)
    if head[:6] not in (b'GIF87a', b'GIF89a') or not any(head[6:8]) or not any(head[8:10]):
        raise Invalid()
    packed = head[10]
    pos = 13 + (3 * (2 ** ((packed & 7) + 1)) if packed & 0x80 else 0)
    if pos > MAX_FILE:
        raise Invalid()
    for _ in range(100_000):
        code = _read(stream, start + pos, 1, total, budget)[0]
        pos += 1
        if code == 0x3b:
            return pos, 'GIF', 'images'
        if code == 0x21:
            _read(stream, start + pos, 1, total, budget)
            pos += 1
        elif code == 0x2c:
            desc = _read(stream, start + pos, 9, total, budget)
            pos += 9
            flags = desc[8]
            if flags & 0x80:
                pos += 3 * (2 ** ((flags & 7) + 1))
            _read(stream, start + pos, 1, total, budget)  # LZW code size
            pos += 1
        else:
            raise Invalid()
        if code in (0x21, 0x2c):
            for _ in range(100_000):
                length = _read(stream, start + pos, 1, total, budget)[0]
                pos += 1
                if length == 0:
                    break
                pos += length
                _read(stream, start + pos - length, length, total, budget)
                if pos > MAX_FILE:
                    raise Invalid()
            else:
                raise Invalid()
    raise Invalid()


def _webp(stream, start, total, budget):
    head = _read(stream, start, 12, total, budget)
    if head[:4] != b'RIFF' or head[8:] != b'WEBP':
        raise Invalid()
    size = struct.unpack_from('<I', head, 4)[0] + 8
    if size < 20 or size > MAX_FORMAT_FILE or start + size > total:
        raise Invalid()
    chunk = _read(stream, start + 12, 8, total, budget)
    if chunk[:4] not in (b'VP8 ', b'VP8L', b'VP8X'):
        raise Invalid()
    first_size = struct.unpack_from('<I', chunk, 4)[0]
    if first_size < 1 or 20 + first_size > size:
        raise Invalid()
    return size, 'WebP', 'images'


def _tiff(stream, start, total, budget):
    header = _read(stream, start, 8, total, budget)
    if header[:4] == b'II*\0':
        endian = '<'
    elif header[:4] == b'MM\0*':
        endian = '>'
    else:
        raise Invalid()
    first_ifd = struct.unpack_from(endian + 'I', header, 4)[0]
    type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1,
                  8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
    extent = 8
    ifd_offset = first_ifd
    seen = set()
    pages = 0
    while ifd_offset:
        if ifd_offset in seen or pages >= 64 or ifd_offset + 2 > MAX_FILE:
            raise Invalid()
        seen.add(ifd_offset)
        count = struct.unpack(endian + 'H', _read(stream, start + ifd_offset, 2, total, budget))[0]
        if count > 4096:
            raise Invalid()
        table_size = 2 + count * 12 + 4
        table = _read(stream, start + ifd_offset, table_size, total, budget)
        extent = max(extent, ifd_offset + table_size)
        tags = {}
        for pos in range(2, 2 + count * 12, 12):
            tag, typ, n = struct.unpack_from(endian + 'HHI', table, pos)
            unit = type_sizes.get(typ)
            if unit is None or n > MAX_FILE // unit:
                raise Invalid()
            byte_length = unit * n
            if byte_length <= 4:
                raw = table[pos + 8:pos + 8 + byte_length]
            else:
                value_offset = struct.unpack_from(endian + 'I', table, pos + 8)[0]
                raw = _read(stream, start + value_offset, byte_length, total, budget)
                extent = max(extent, value_offset + byte_length)
            if tag in (256, 257, 273, 279, 324, 325):
                if typ not in (3, 4) or n > 1_000_000:
                    raise Invalid()
                if tag in tags:
                    raise Invalid()
                code = 'H' if typ == 3 else 'I'
                tags[tag] = list(struct.unpack(endian + code * n, raw))
        width = tags.get(256, [0])[0]
        height = tags.get(257, [0])[0]
        if not width or not height:
            raise Invalid()
        offsets = tags.get(273, tags.get(324, []))
        counts = tags.get(279, tags.get(325, []))
        if not offsets or len(offsets) != len(counts):
            raise Invalid()
        for offset, length in zip(offsets, counts):
            if not length or offset + length > MAX_FILE or start + offset + length > total:
                raise Invalid()
            extent = max(extent, offset + length)
        next_offset = struct.unpack_from(endian + 'I', table, 2 + count * 12)[0]
        if next_offset >= MAX_FILE:
            raise Invalid()
        if next_offset:
            extent = max(extent, next_offset + 2)
        ifd_offset = next_offset
        pages += 1
    if not pages or extent > MAX_FORMAT_FILE:
        raise Invalid()
    return extent, 'TIFF', 'images'


def _zip(stream, start, total, budget):
    data = _read(stream, start, min(MAX_FILE, total - start), total, budget)
    eocd = data.rfind(b'PK\x05\x06')
    if eocd < 0 or eocd + 22 > len(data):
        raise Invalid()
    disk, cd_disk, disk_entries, entries, cd_size, cd_offset, comment_len = struct.unpack_from('<4H2IH', data, eocd + 4)
    end = eocd + 22 + comment_len
    if disk or cd_disk or disk_entries != entries or entries > MAX_ZIP_ENTRIES or end > len(data):
        raise Invalid()
    if cd_offset + cd_size > eocd or cd_offset + cd_size < cd_offset:
        raise Invalid()
    names = set()
    records = {}
    pos = cd_offset
    for _ in range(entries):
        if pos + 46 > cd_offset + cd_size or data[pos:pos + 4] != b'PK\x01\x02':
            raise Invalid()
        name_len, extra_len, note_len = struct.unpack_from('<3H', data, pos + 28)
        rec_end = pos + 46 + name_len + extra_len + note_len
        if rec_end > cd_offset + cd_size:
            raise Invalid()
        name_bytes = data[pos + 46:pos + 46 + name_len]
        name = name_bytes.decode('ascii', 'ignore').lower()
        local_offset = struct.unpack_from('<I', data, pos + 42)[0]
        compressed_size = struct.unpack_from('<I', data, pos + 20)[0]
        if local_offset + 30 > cd_offset or data[local_offset:local_offset + 4] != b'PK\x03\x04':
            raise Invalid()
        flags = struct.unpack_from('<H', data, pos + 8)[0]
        method = struct.unpack_from('<H', data, pos + 10)[0]
        local_name_len, local_extra_len = struct.unpack_from('<2H', data, local_offset + 26)
        local_end = local_offset + 30 + local_name_len + local_extra_len + compressed_size
        local_flags, local_method = struct.unpack_from('<HH', data, local_offset + 6)
        if (local_name_len != name_len or data[local_offset + 30:local_offset + 30 + local_name_len] != name_bytes or
                local_end > cd_offset or local_flags != flags or local_method != method):
            raise Invalid()
        uncompressed_size = struct.unpack_from('<I', data, pos + 24)[0]
        if flags & 1 or name in records:
            raise Invalid()
        names.add(name)
        records[name] = (local_offset + 30 + local_name_len + local_extra_len,
                         compressed_size, uncompressed_size, method)
        pos = rec_end
    if pos != cd_offset + cd_size or not entries:
        raise Invalid()
    kind = 'ZIP'
    if '[content_types].xml' in names:
        offset, compressed, uncompressed, method = records['[content_types].xml']
        if uncompressed <= 1024 * 1024 and compressed <= 1024 * 1024 and method in (0, 8):
            try:
                with zipfile.ZipFile(BytesIO(data[:end])) as archive:
                    types = archive.read('[Content_Types].xml')
                lowered = types.lower()
            except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, zlib.error):
                raise Invalid()
            if records['[content_types].xml'][2] != len(types):
                raise Invalid()
            if any(name.startswith('word/') for name in names):
                if 'word/document.xml' in names:
                    if b'ms-word.document.macroenabled.main+xml' in lowered:
                        kind = 'DOCM'
                    elif b'wordprocessingml.document.main+xml' in lowered:
                        kind = 'DOCX'
                    elif b'ms-word.template.macroenabledtemplate.main+xml' in lowered:
                        kind = 'DOTM'
                    elif b'wordprocessingml.template.main+xml' in lowered:
                        kind = 'DOTX'
            elif any(name.startswith('xl/') for name in names):
                if 'xl/workbook.xml' in names:
                    if b'excel.sheet.macroenabled.main+xml' in lowered:
                        kind = 'XLSM'
                    elif b'spreadsheetml.sheet.main+xml' in lowered:
                        kind = 'XLSX'
                    elif b'excel.template.macroenabled.main+xml' in lowered:
                        kind = 'XLTM'
                    elif b'spreadsheetml.template.main+xml' in lowered:
                        kind = 'XLTX'
            elif any(name.startswith('ppt/') for name in names):
                if 'ppt/presentation.xml' in names:
                    if b'powerpoint.presentation.macroenabled.main+xml' in lowered:
                        kind = 'PPTM'
                    elif b'presentationml.presentation.main+xml' in lowered:
                        kind = 'PPTX'
                    elif b'powerpoint.template.macroenabled.main+xml' in lowered:
                        kind = 'POTM'
                    elif b'presentationml.template.main+xml' in lowered:
                        kind = 'POTX'
    elif 'mimetype' in names:
        offset, compressed, uncompressed, method = records['mimetype']
        if method == 0 and 1 <= uncompressed <= 128 and compressed == uncompressed:
            mime = data[offset:offset + compressed].lower()
            kind = {
                b'application/vnd.oasis.opendocument.text':'ODT',
                b'application/vnd.oasis.opendocument.spreadsheet':'ODS',
                b'application/vnd.oasis.opendocument.presentation':'ODP',
                b'application/vnd.oasis.opendocument.graphics':'ODG',
            }.get(mime, 'ZIP')
    office_kinds = ('DOCX','DOCM','DOTX','DOTM','XLSX','XLSM','XLTX','XLTM','PPTX','PPTM','POTX','POTM','ODT','ODS','ODP','ODG')
    return end, kind, 'office' if kind in office_kinds else 'archives'


def _tar(stream, start, total, budget):
    pos = 0
    entries = 0
    zero_blocks = 0
    while pos + 512 <= min(MAX_FORMAT_FILE, total - start):
        head = _read(stream, start + pos, 512, total, budget)
        if not any(head):
            zero_blocks += 1
            pos += 512
            if zero_blocks == 2 and entries:
                return pos, 'TAR', 'archives'
            continue
        if zero_blocks or head[257:262] != b'ustar':
            raise Invalid()
        try:
            stored = int(head[148:156].strip(b' \0') or b'0', 8)
            size = int(head[124:136].strip(b' \0') or b'0', 8)
        except ValueError:
            raise Invalid()
        actual = sum(head[:148]) + 8 * 32 + sum(head[156:])
        if stored != actual or size > MAX_FORMAT_FILE - 512:
            raise Invalid()
        entries += 1
        if entries > MAX_TAR_ENTRIES:
            raise Invalid()
        pos += 512 + math.ceil(size / 512) * 512
        if pos > MAX_FORMAT_FILE or start + pos > total:
            raise Invalid()
    raise Invalid()


def _seven_zip(stream, start, total, budget):
    head = _read(stream, start, 32, total, budget)
    if head[:6] != b'7z\xbc\xaf\x27\x1c' or zlib.crc32(head[12:32]) & 0xffffffff != struct.unpack_from('<I', head, 8)[0]:
        raise Invalid()
    next_offset, next_size, next_crc = struct.unpack_from('<QQI', head, 12)
    extent = 32 + next_offset + next_size
    if next_size < 1 or extent > MAX_FORMAT_FILE or start + extent > total:
        raise Invalid()
    next_header = _read(stream, start + 32 + next_offset, next_size, total, budget)
    if zlib.crc32(next_header) & 0xffffffff != next_crc:
        raise Invalid()
    return extent, '7Z', 'archives'


def _riff(stream, start, total, budget, subtype):
    head = _read(stream, start, 12, total, budget)
    if head[:4] != b'RIFF' or head[8:12] != subtype.encode('ascii'):
        raise Invalid()
    extent = struct.unpack_from('<I', head, 4)[0] + 8
    if extent < 12 or extent > MAX_FORMAT_FILE or start + extent > total:
        raise Invalid()
    sample = _read(stream, start, min(extent, 1024 * 1024), total, budget)
    if subtype == 'WAVE':
        if b'fmt ' not in sample or b'data' not in sample:
            raise Invalid()
        return extent, 'WAV', 'audio'
    if subtype == 'AVI ':
        if b'hdrl' not in sample or b'movi' not in sample:
            raise Invalid()
        return extent, 'AVI', 'video'
    raise Invalid()


def _mp4(stream, start, total, budget):
    head = _read(stream, start, 16, total, budget)
    if head[4:8] != b'ftyp':
        raise Invalid()
    first_size = struct.unpack_from('>I', head)[0]
    if first_size < 16 or first_size > MAX_FILE:
        raise Invalid()
    pos = first_size
    seen = {b'ftyp'}
    known = {b'free', b'skip', b'mdat', b'moov', b'wide', b'uuid', b'sidx',
             b'moof', b'mfra', b'pnot', b'prft', b'emsg', b'pdin'}
    for _ in range(100_000):
        if pos >= MAX_FORMAT_FILE or start + pos + 8 > total:
            break
        box = _read(stream, start + pos, 8, total, budget)
        size, kind = struct.unpack('>I4s', box)
        header_size = 8
        if size == 1:
            size = struct.unpack('>Q', _read(stream, start + pos + 8, 8, total, budget))[0]
            header_size = 16
        elif size == 0:
            size = total - start - pos
        if kind not in known or size < header_size or pos + size > MAX_FORMAT_FILE or start + pos + size > total:
            break
        seen.add(kind)
        pos += size
    else:
        raise Invalid()
    if b'moov' not in seen or b'mdat' not in seen or pos <= first_size:
        raise Invalid()
    return pos, 'MP4', 'video'


def _ogg_crc(data):
    crc = 0
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xffffffff
    return crc


def _ogg(stream, start, total, budget):
    pos = 0
    serial = None
    expected_sequence = 0
    codec = None
    for _ in range(100_000):
        header = _read(stream, start + pos, 27, total, budget)
        if header[:4] != b'OggS' or header[4] != 0 or header[5] & ~7:
            raise Invalid()
        page_serial = struct.unpack_from('<I', header, 14)[0]
        page_sequence = struct.unpack_from('<I', header, 18)[0]
        stored_crc = struct.unpack_from('<I', header, 22)[0]
        count = header[26]
        lacing = _read(stream, start + pos + 27, count, total, budget)
        body_size = sum(lacing)
        body = _read(stream, start + pos + 27 + count, body_size, total, budget)
        page = bytearray(header + lacing + body)
        page[22:26] = b'\0\0\0\0'
        if _ogg_crc(page) != stored_crc:
            raise Invalid()
        if serial is None:
            serial = page_serial
            if not header[5] & 2 or page_sequence != 0:
                raise Invalid()
            packet_end = next((i + 1 for i, length in enumerate(lacing) if length < 255), None)
            if packet_end is None:
                raise Invalid()
            packet = body[:sum(lacing[:packet_end])]
            if packet.startswith(b'\x01vorbis') and len(packet) >= 30:
                version = struct.unpack_from('<I', packet, 7)[0]
                if version != 0 or packet[11] == 0 or packet[29] != 1:
                    raise Invalid()
                codec = 'OGG-Vorbis'
            elif packet.startswith(b'OpusHead') and len(packet) >= 19:
                if packet[8] > 15 or packet[9] == 0:
                    raise Invalid()
                codec = 'OGG-Opus'
            else:
                raise Invalid()
        elif page_serial != serial or page_sequence != expected_sequence:
            raise Invalid()
        expected_sequence = page_sequence + 1
        pos += 27 + count + body_size
        if pos > MAX_FORMAT_FILE:
            raise Invalid()
        if header[5] & 4:
            return pos, codec, 'audio'
    raise Invalid()


def _mp3_frame(stream, start, total, budget):
    header = _read(stream, start, 4, total, budget)
    if header[0] != 0xff or header[1] & 0xe0 != 0xe0:
        raise Invalid()
    version = (header[1] >> 3) & 3
    layer = (header[1] >> 1) & 3
    bitrate_index = header[2] >> 4
    sample_index = (header[2] >> 2) & 3
    padding = (header[2] >> 1) & 1
    if version == 1 or layer == 0 or bitrate_index in (0, 15) or sample_index == 3:
        raise Invalid()
    rates = {
        (3, 3): (32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
        (3, 2): (32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
        (3, 1): (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
        (0, 1): (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
        (0, 2): (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
        (0, 3): (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
        (2, 1): (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
        (2, 2): (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
        (2, 3): (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    }
    version_key = 3 if version == 3 else version
    bitrate = rates[(version_key, layer)][bitrate_index - 1] * 1000
    sample_rate = (44100, 48000, 32000)[sample_index]
    if version == 2:
        sample_rate //= 2
    elif version == 0:
        sample_rate //= 4
    if layer == 3:
        frame_size = (12 * bitrate // sample_rate + padding) * 4
    else:
        coefficient = 72 if layer == 1 and version != 3 else 144
        frame_size = coefficient * bitrate // sample_rate + padding
    if frame_size < 24 or start + frame_size > total:
        raise Invalid()
    return frame_size, (version, layer, sample_rate)


def _mp3(stream, start, total, budget):
    offset = 0
    head = _read(stream, start, min(10, total - start), total, budget)
    if head.startswith(b'ID3'):
        if len(head) != 10 or head[3] not in (2, 3, 4) or head[4] == 0xff or any(x & 0x80 for x in head[6:10]):
            raise Invalid()
        tag_size = ((head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9])
        offset = 10 + tag_size + (10 if head[3] == 4 and head[5] & 0x10 else 0)
        if offset >= MAX_FORMAT_FILE or start + offset + 4 > total:
            raise Invalid()
    expected = None
    frames = 0
    pos = offset
    for _ in range(1_000_000):
        try:
            frame_size, identity = _mp3_frame(stream, start + pos, total, budget)
        except Invalid:
            if frames < 3:
                raise
            break
        if expected is None:
            expected = identity
        elif identity != expected:
            if frames < 3:
                raise Invalid()
            break
        pos += frame_size
        frames += 1
        if pos > MAX_FORMAT_FILE:
            raise Invalid()
    else:
        raise Invalid()
    if frames < 3:
        raise Invalid()
    return pos, 'MP3', 'audio'


def parse(stream, start, total, budget, category):
    """Return (size, display type, category) for a recognized candidate."""
    head = _read(stream, start, min(12, total - start), total, budget)
    parsers = []
    if category in ('images', 'all'):
        if head.startswith((b'II*\0', b'MM\0*')):
            parsers.append(_tiff)
        if head.startswith(b'BM'):
            parsers.append(_bmp)
        if head.startswith((b'GIF87a', b'GIF89a')):
            parsers.append(_gif)
        if head.startswith(b'RIFF') and len(head) >= 12 and head[8:] == b'WEBP':
            parsers.append(_webp)
    if category in ('office', 'archives', 'all') and head.startswith(b'PK\x03\x04'):
        parsers.append(_zip)
    if category in ('archives', 'all') and head.startswith(b'7z\xbc\xaf\x27\x1c'):
        parsers.append(_seven_zip)
    if category in ('archives', 'all') and start + 262 <= total:
        try:
            if _read(stream, start + 257, 5, total, budget) == b'ustar':
                parsers.append(_tar)
        except Limit:
            raise
        except Invalid:
            pass
    if category in ('video', 'all') and len(head) >= 8 and head[4:8] == b'ftyp':
        parsers.append(_mp4)
    if category in ('audio', 'video', 'all') and head.startswith(b'RIFF'):
        subtype = head[8:12].decode('ascii', 'ignore')
        if subtype == 'WAVE' and category in ('audio', 'all'):
            parsers.append(lambda *args: _riff(*args, 'WAVE'))
        if subtype == 'AVI ' and category in ('video', 'all'):
            parsers.append(lambda *args: _riff(*args, 'AVI '))
    if category in ('audio', 'all') and head.startswith(b'OggS'):
        parsers.append(_ogg)
    if category in ('audio', 'all') and head.startswith(b'ID3'):
        parsers.append(_mp3)
    if category in ('audio', 'all') and len(head) >= 2 and head[0] == 0xff and head[1] & 0xe0 == 0xe0:
        parsers.append(_mp3)
    for parser in parsers:
        try:
            return parser(stream, start, total, budget)
        except Limit:
            raise
        except Invalid:
            continue
    raise Invalid()
