"""Synthetic NTFS large directory indexes / orphan graph; never access real disks."""
from __future__ import annotations
import struct
import tempfile
import unittest
from pathlib import Path
from test_browser import filename, image_with_folders, record
from test_ntfs import MFT_LCN, CLUSTER, SIZE, align8, nonresident_attr, resident_attr
from test_ntfs_reconstruction import _index_root
from recoverydesk.ntfs_browser import (ORPHANS, ROOT_RECORD, scan_ntfs_tree,
                                       export_selection)
from recoverydesk.ntfs_reconstruct import (_fixed_index_buffer,
                                           directory_allocation_hints)
from recoverydesk.ntfs import NTFSError


def _resident_named(kind: int, name: str, value: bytes) -> bytes:
    encoded = name.encode('utf-16le')
    voff = align8(24+len(encoded))
    size = align8(voff+len(value))
    raw = bytearray(size)
    struct.pack_into('<II', raw, 0, kind, size)
    raw[9] = len(encoded)//2
    struct.pack_into('<H', raw, 10, 24)
    struct.pack_into('<I', raw, 16, len(value))
    struct.pack_into('<H', raw, 20, voff)
    raw[24:24+len(encoded)] = encoded
    raw[voff:voff+len(value)] = value
    return bytes(raw)


def _index_allocation_attr() -> bytes:
    name = '$I30'.encode('utf-16le')
    run_off = align8(64+len(name))
    blob = bytes([0x11, 4, 100, 0])
    size = align8(run_off+len(blob))
    raw = bytearray(size)
    struct.pack_into('<II', raw, 0, 0xA0, size)
    raw[8] = 1
    raw[9] = len(name)//2
    struct.pack_into('<H', raw, 10, 64)
    struct.pack_into('<QQ', raw, 16, 0, 3)
    struct.pack_into('<H', raw, 32, run_off)
    struct.pack_into('<QQQ', raw, 40, 2048, 2048, 2048)
    raw[64:64+len(name)] = name
    raw[run_off:run_off+len(blob)] = blob
    return bytes(raw)


def _index_buffer(child: int, filename_text: str, *, corrupt_fixup=False) -> bytes:
    key_attr = filename(filename_text, 5, parent_sequence=1)
    # $FILE_NAME resident attribute's value begins at +24.
    key = key_attr[24:24+struct.unpack_from('<I', key_attr, 16)[0]]
    entry_len = align8(16+len(key))
    out = bytearray(SIZE)
    out[:4] = b'INDX'
    struct.pack_into('<HH', out, 4, 0x30, 3)
    struct.pack_into('<Q', out, 16, 0)
    # INDEX_HEADER at offset 24; entries begin at 72, past update array.
    struct.pack_into('<III', out, 24, 48, 48+entry_len+16, SIZE-24)
    pos = 72
    struct.pack_into('<Q', out, pos, (1 << 48) | child)
    struct.pack_into('<HH', out, pos+8, entry_len, len(key))
    out[pos+16:pos+16+len(key)] = key
    end = pos+entry_len
    struct.pack_into('<H', out, end+8, 16)
    struct.pack_into('<H', out, end+12, 2)
    out[0x30:0x32] = b'\x9a\xcd'
    for sector in (1, 2):
        tail = sector*CLUSTER-2
        out[0x30+sector*2:0x32+sector*2] = out[tail:tail+2]
        out[tail:tail+2] = b'\x9a\xcd'
    if corrupt_fixup:
        out[510:512] = b'\x00\x00'
    return bytes(out)


def large_index_image(*, bitmap=3, corrupt=False):
    raw = bytearray(image_with_folders())
    raw[MFT_LCN*CLUSTER:MFT_LCN*CLUSTER+SIZE] = record([
        nonresident_attr(0x80, b'\x11\x20\x04\x00', 32*CLUSTER, 31)], flags=1)
    root_attr = bytearray(_index_root(6, 1, name='Dokumente'))
    start = 24+len('$I30'.encode('utf-16le'))
    struct.pack_into('<I', root_attr, start+8, SIZE)  # INDEX_ROOT index block size
    root_attr[start+12] = 1  # has child nodes
    root = record([filename('Wurzel', 5), bytes(root_attr),
                   _index_allocation_attr(),
                   _resident_named(0xB0, '$I30', bytes([bitmap]))], flags=3)
    raw[MFT_LCN*CLUSTER+5*SIZE:MFT_LCN*CLUSTER+6*SIZE] = root
    raw[100*CLUSTER:102*CLUSTER] = _index_buffer(12, 'VerschollenerOrdner', corrupt_fixup=corrupt)
    raw[102*CLUSTER:104*CLUSTER] = _index_buffer(13, 'WeitereDatei.xyz')
    return bytes(raw)


class IndexAllocationTests(unittest.TestCase):
    def test_reads_large_nonresident_directory_index(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td)/'large.raw'; src.write_bytes(large_index_image())
            index = scan_ntfs_tree(str(src))
            names = {e.name for e in index.list_dir(ROOT_RECORD)}
            self.assertIn('VerschollenerOrdner', names)
            self.assertIn('WeitereDatei.xyz', names)
            self.assertEqual(index.allocation_index_hints, 2)
            self.assertEqual(index.reconstructed_index_hints, 2)
            self.assertTrue(all(e.metadata_only for e in index.list_dir(5) if e.name in ('VerschollenerOrdner','WeitereDatei.xyz')))
            out = Path(td)/'export'; out.mkdir()
            hint = next(e for e in index.list_dir(5) if e.name == 'VerschollenerOrdner')
            report = export_selection(str(src), index, [hint], str(out))
            self.assertEqual(report.exported, 0)
            self.assertGreater(report.skipped, 0)

    def test_bitmap_skips_unallocated_index_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'bitmap.raw'; src.write_bytes(large_index_image(bitmap=1))
            index=scan_ntfs_tree(str(src))
            self.assertEqual(index.allocation_index_hints, 1)
            self.assertNotIn('WeitereDatei.xyz', [e.name for e in index.list_dir(5)])

    def test_torn_index_buffer_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'corrupt.raw'; src.write_bytes(large_index_image(corrupt=True))
            index=scan_ntfs_tree(str(src))
            self.assertEqual(index.allocation_index_hints, 1)
            self.assertFalse(any(e.name == 'VerschollenerOrdner' for e in index.list_dir(5)))
            self.assertIn('WeitereDatei.xyz', [e.name for e in index.list_dir(5)])
            self.assertTrue(any('INDEX' in w.upper() or 'Verzeichnisindex' in w for w in index.scan_warnings))

    def test_cycle_is_broken_and_all_children_remain_visible(self):
        raw=bytearray(image_with_folders())
        # 6 -> 9 -> 6 used to form an inaccessible subtree.
        raw[MFT_LCN*CLUSTER+6*SIZE:MFT_LCN*CLUSTER+7*SIZE] = record([filename('A', 9)], flags=3)
        raw[MFT_LCN*CLUSTER+9*SIZE:MFT_LCN*CLUSTER+10*SIZE] = record([filename('B', 6)], flags=3)
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'cycle.raw'; src.write_bytes(raw)
            index=scan_ntfs_tree(str(src))
            self.assertEqual(index.orphan_cycles, 1)
            self.assertIn('A', [e.name for e in index.list_dir(ORPHANS)])
            self.assertIn('B', [e.name for e in index.list_dir(6)])
            self.assertIn('bericht.txt', [e.name for e in index.list_dir(6)])
            self.assertIn('bild.irgendwas', [e.name for e in index.list_dir(9)])
            self.assertGreaterEqual(index.orphan_count, 4)

    def test_mft_directory_with_missing_parent_keeps_child_hierarchy(self):
        raw=bytearray(image_with_folders())
        raw[MFT_LCN*CLUSTER+6*SIZE:MFT_LCN*CLUSTER+7*SIZE] = record([filename('Dokumente', 40000)], flags=3)
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'broken_parent.raw'; src.write_bytes(raw)
            index=scan_ntfs_tree(str(src))
            self.assertIn('Dokumente', [e.name for e in index.list_dir(ORPHANS)])
            self.assertIn('bericht.txt', [e.name for e in index.list_dir(6)])
            self.assertGreaterEqual(index.orphan_count, 4)


if __name__ == '__main__':
    unittest.main()
