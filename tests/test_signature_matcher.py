"""Shared matcher preserves the legacy per-marker candidate enumeration."""
import itertools
import random
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from recoverydesk import signature_search as search
from recoverydesk.filesystems import ScanCancelled

SPECS=(
    (search.PNG,'PNG',('images',),1),(search.JPEG,'JPEG',('images',),1),
    (b'BM','OTHER',('images',),1),(b'GIF87a','OTHER',('images',),1),
    (b'GIF89a','OTHER',('images',),1),(b'II*\0','OTHER',('images',),1),
    (b'MM\0*','OTHER',('images',),1),(b'RIFF','OTHER',('images','audio','video'),1),
    (b'PK\x03\x04','OTHER',('office','archives'),1),
    (b'%PDF-','OTHER',('office',),2),
    (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1','OTHER',('office',),3),
    (b'Rar!\x1a\x07','OTHER',('archives',),2),
    (b'7z\xbc\xaf\x27\x1c','OTHER',('archives',),1),
    (b'OggS','OTHER',('audio',),1),(b'ID3','OTHER',('audio',),1))

def reference(data,base,last,specs,limit):
    found=[]
    for marker,kind in specs.items():
        at=data.find(marker);count=0
        while at>=0 and count<=limit:
            if base+at>last:found.append((base+at,kind))
            count+=1;at=data.find(marker,at+1)
    return sorted(found)

class SignatureMatcherTests(unittest.TestCase):
    def test_complete_scans_and_checkpoint_match_byte_search_at_block_boundary(self):
        def chunk(kind,raw):
            return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
        png=search.PNG+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0RGB'))+chunk(b'IEND',b'')
        categories=('images','office','archives','audio','video')
        data=b'X'*508+png+b'X'*900+b'BMM\0*'+png*5+b'X'*800
        matcher=search._candidate_matcher(frozenset(categories),3)
        self.assertIsNotNone(matcher[0])
        with tempfile.TemporaryDirectory() as temporary,patch.object(search,'SCAN_BLOCK',512):
            source=Path(temporary)/'new.img';source.write_bytes(data)
            def summary(index):
                return ([(e.locator,e.name) for e in index.entries],index.signature_candidates,
                        index.signature_complete,index.signature_scanned_bytes,index.scan_warnings)
            for limit in (3,5000):
                with patch.object(search,'MAX_CANDIDATES',limit):
                    actual=search.scan_signatures(str(source),categories=categories)
                    with patch.object(search,'_candidate_matcher',return_value=(None,matcher[1])):
                        legacy=search.scan_signatures(str(source),categories=categories)
                    self.assertEqual(summary(actual),summary(legacy))
            checkpoint=Path(temporary)/'checkpoint.json';progress=[]
            with self.assertRaises(ScanCancelled):
                search.scan_signatures(str(source),categories=categories,checkpoint_path=str(checkpoint),
                                       progress=lambda done,total:progress.append(done),cancel=lambda:bool(progress))
            resumed=search.scan_signatures(str(source),checkpoint_path=str(checkpoint),resume=True)
            self.assertEqual(summary(resumed),summary(legacy))
            self.assertEqual(source.read_bytes(),data)

    def test_all_category_subsets_revisions_overlaps_and_dense_limits(self):
        categories=('images','office','archives','audio','video')
        rng=random.Random(1729)
        pieces=[x[0] for x in SPECS]+[b'BMM\0*',b'X']
        data=b'BMM\0*'+b''.join(rng.choice(pieces) for _ in range(1000))
        for revision in (1,2,3):
            for mask in range(1,32):
                selected=frozenset(c for i,c in enumerate(categories) if mask&(1<<i))
                expected={s:k for s,k,cs,v in SPECS if revision>=v and selected.intersection(cs)}
                matcher=search._candidate_matcher(selected,revision)
                self.assertEqual(matcher[1],expected)
                # Alternation assumes no marker is a prefix of another.
                self.assertFalse(any(b.startswith(a) for a,b in itertools.permutations(expected,2)))
                for limit in (2,5000):
                    for base,last in ((0,-1),(4096,4300)):
                        with self.subTest(revision=revision,mask=mask,limit=limit,base=base),patch.object(search,'MAX_CANDIDATES',limit):
                            actual=search._block_candidates(data,base,last,matcher)
                            self.assertEqual(sorted(actual),reference(data,base,last,expected,limit))

    def test_each_marker_at_every_boundary_split(self):
        selected=frozenset(('images','office','archives','audio','video'))
        matcher=search._candidate_matcher(selected,3)
        for marker,kind in matcher[1].items():
            for cut in range(1,len(marker)):
                # Scanner retains 264 bytes from the previous block.
                data=b'X'*(264-cut)+marker+b'X'*20
                self.assertIn((1000+264-cut,kind),search._block_candidates(data,1000,-1,matcher))

    def test_dense_enumeration_can_be_cancelled(self):
        matcher=search._candidate_matcher(frozenset(('images',)),3)
        with self.assertRaises(ScanCancelled):
            search._block_candidates(b'BM'*10000,0,-1,matcher,cancel=lambda:True)
