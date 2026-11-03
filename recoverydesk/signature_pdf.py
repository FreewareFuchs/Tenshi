"""Bounded structural PDF carving; never render streams or run document actions."""
import re

from .signature_formats import Invalid, Limit, _read, _file_limit

_EOF = re.compile(rb'(?:^|[\r\n])[ \t]{0,16}startxref[\x00\t\n\f\r ]{1,64}([0-9]{1,12})[\x00\t\n\f\r ]{1,64}%%EOF(?:\r\n|\r|\n)?')
_WS = re.compile(rb'[\x00\t\n\f\r ]*')
_SECTION = re.compile(rb'([0-9]{1,10})[ \t]+([0-9]{1,10})[ \t]*(?:\r\n|\r|\n)')
_ROW = re.compile(rb'([0-9]{10})[ \t]([0-9]{5})[ \t]([nf])[ \t]*(?:\r\n|\r|\n)')


def _xref(stream,start,offset,end,budget):
    if not 0 < offset < end:raise Invalid()
    data = _read(stream,start+offset,min(1024**2,end-offset),start+end,budget)
    classic = data.startswith(b'xref')
    if classic:
        trailer = re.search(rb'\btrailer\s*<<',data)
        if trailer is None:raise Invalid()
        dictionary = data[trailer.end()-2:]
    else:
        obj = re.match(rb'[0-9]{1,10}\s+[0-9]{1,5}\s+obj\s*<<',data)
        if obj is None:raise Invalid()
        dictionary = data[obj.end()-2:]
    match = re.match(rb'<<(.*?)>>',dictionary,re.S)
    if match is None or match.end() > 65536:raise Invalid()
    fields = re.sub(rb'%[^\r\n]*',b'',match[1])
    size = re.search(rb'/Size\s+([0-9]{1,10})\b',fields)
    root = re.search(rb'/Root\s+([0-9]{1,10})\s+([0-9]{1,5})\s+R\b',fields)
    prev = re.search(rb'/Prev\s+([0-9]{1,12})\b',fields)
    previous = int(prev[1]) if prev else None
    if size is None or not 0 < int(size[1]) <= 10_000_000:raise Invalid()
    if root and not 0 < int(root[1]) < int(size[1]):raise Invalid()
    root_found = False
    if classic:
        position = _WS.match(data,4).end()
        rows = 0
        while position < trailer.start():
            section = _SECTION.match(data,position)
            if section is None:raise Invalid()
            first,count = int(section[1]),int(section[2])
            rows += count
            if rows > 50_000 or first+count > int(size[1]):raise Invalid()
            position = section.end()
            for number in range(first,first+count):
                row = _ROW.match(data,position)
                if row is None:raise Invalid()
                object_offset,generation = int(row[1]),int(row[2])
                if row[3] == b'n' and not 0 < object_offset < end:raise Invalid()
                if root and number == int(root[1]) and generation == int(root[2]) and row[3] == b'n':
                    head = _read(stream,start+object_offset,min(256,end-object_offset),start+end,budget)
                    expected = str(number).encode()+rb'\s+'+str(generation).encode()+rb'\s+obj\b'
                    if not re.match(expected,head):raise Invalid()
                    root_found = True
                position = row.end()
            position = _WS.match(data,position).end()
        if position != trailer.start():raise Invalid()
    else:
        if not re.search(rb'/Type\s*/XRef\b',fields):raise Invalid()
        widths = re.search(rb'/W\s*\[\s*([0-9]{1,2})\s+([0-9]{1,2})\s+([0-9]{1,2})\s*\]',fields)
        length = re.search(rb'/Length\s+([0-9]{1,12})\s*(?=/|$)',fields)
        if widths is None or length is None:raise Invalid()
        widths = [int(widths[i]) for i in (1,2,3)]
        if max(widths) > 8 or not sum(widths):raise Invalid()
        prefix_length = len(data)-len(dictionary)+match.end()
        stream_marker = re.match(rb'\s*stream(?:\r\n|\r|\n)',data[prefix_length:])
        if stream_marker is None:raise Invalid()
        stream_end = offset+prefix_length+stream_marker.end()+int(length[1])
        if stream_end >= end:raise Invalid()
        ending = _read(stream,start+stream_end,min(64,end-stream_end),start+end,budget)
        if not re.match(rb'\s*endstream\s+endobj\b',ending):raise Invalid()
        root_found = root is not None
    if previous is None and not root_found:raise Invalid()
    return previous, root_found


def _continues(stream,start,end,limit,total,budget):
    """Distinguish an appended PDF update from unrelated bytes after EOF."""
    if end >= total-start:return False
    data = _read(stream,start+end,min(65536,total-start-end),total,budget)
    position = 0
    while position < len(data):
        position = _WS.match(data,position).end()
        if data[position:position+5] == b'%PDF-':return False
        if data[position:position+1] != b'%':break
        newline = re.search(rb'[\r\n]',data[position:])
        if newline is None:return start+end+len(data) < total
        position += newline.end()
    if position == len(data):return end+len(data) < total-start
    return bool(re.match(rb'(?:[0-9]{1,10}\s+[0-9]{1,5}\s+obj\b|xref\b)',data[position:]))


def pdf(stream,start,total,budget):
    limit = min(_file_limit(budget),total-start)
    header = _read(stream,start,min(16,limit),total,budget)
    if not re.match(rb'%PDF-(?:1\.[0-7]|2\.0)[ \t]*(?:\r\n|\r|\n)',header):raise Invalid()
    position = 0;tail = b'';last = None;last_xref = None;forward = None;seen = set()
    for _ in range((limit+65535)//65536):
        block = _read(stream,start+position,min(65536,limit-position),total,budget)
        data = tail+block;base = position-len(tail)
        for match in _EOF.finditer(data):
            end = base+match.end()
            if end in seen or (match.end()==len(data) and position+len(block)<limit):continue
            seen.add(end)
            if len(seen) > 128:raise Invalid()
            offset = int(match[1])
            try:previous,root = _xref(stream,start,offset,base+match.start(),budget)
            except Limit:raise
            except Invalid:continue
            if last is None:
                if not root or (previous is not None and previous < end):continue
            elif previous != last_xref and offset != forward:
                continue
            last = end;last_xref = offset
            forward = previous if previous is not None and previous > end else None
            if forward is None and not _continues(stream,start,end,limit,total,budget):
                return end,'PDF','office'
        position += len(block);tail = data[-512:]
    # An incomplete appended update must not be exported as an older revision.
    if last is not None and forward is None and not _continues(stream,start,last,limit,total,budget):
        return last,'PDF','office'
    raise Invalid()
