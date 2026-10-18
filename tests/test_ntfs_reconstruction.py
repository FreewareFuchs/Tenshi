"""Focused synthetic tests; never touch actual disks."""
from __future__ import annotations
import struct
import tempfile
import unittest
from pathlib import Path

from test_browser import filename, image_with_folders, record
from test_ntfs import (SIZE, CLUSTER, MFT_LCN, file_record, resident_attr,
                       nonresident_attr, align8)
from recoverydesk.ntfs_browser import (scan_ntfs_tree, export_file,
                                       export_selection, ORPHANS)
from recoverydesk.ntfs_reconstruct import read_attribute_list, directory_index_hints
from recoverydesk.ntfs import apply_update_sequence, NTFSError


def _attrlist_item(vcn, recno, sequence, instance, kind=0x80):
    b = bytearray(32)
    struct.pack_into('<I', b, 0, kind)
    struct.pack_into('<H', b, 4, len(b))
    struct.pack_into('<Q', b, 8, vcn)
    struct.pack_into('<Q', b, 16, (sequence << 48) | recno)
    struct.pack_into('<H', b, 24, instance)
    return bytes(b)


def _attr_id(a, n):
    b = bytearray(a)
    struct.pack_into('<H', b, 14, n)
    return bytes(b)


def _split_data(vcn, last_vcn, lcn, real_size=700):
    a = bytearray(nonresident_attr(0x80, bytes([0x11, 0x01, lcn, 0]),
                                   real_size, last_vcn))
    struct.pack_into('<Q', a, 16, vcn)
    return bytes(a)


def build_split_attribute_image(*, bad_ref=False, bad_sequence=False,
                                broken_second=False, compressed=False):
    raw = bytearray(image_with_folders())
    # Increase $MFT stream to 32 clusters (=16 records, including #12).
    raw[MFT_LCN*CLUSTER:MFT_LCN*CLUSTER+SIZE] = file_record([
        nonresident_attr(0x80, b'\x11\x20\x04\x00', 32*CLUSTER, 31)], in_use=True)
    base_no, extension_no = 7, (14 if bad_ref else 12)
    al = _attrlist_item(0, base_no, 1, 5) + _attrlist_item(1, extension_no,
                                                        999 if bad_sequence else 1, 9)
    first = _attr_id(_split_data(0, 0, 40), 5)
    raw[MFT_LCN*CLUSTER+base_no*SIZE:MFT_LCN*CLUSTER+(base_no+1)*SIZE] = record([
        filename('umfangreich.bin', 6), resident_attr(0x20, al), first], flags=1)
    if not broken_second:
        second = _attr_id(_split_data(1, 1, 60), 9)
        if compressed:
            second = bytearray(second)
            struct.pack_into('<H', second, 12, 0x0001)
            second = bytes(second)
        extension = bytearray(record([second], flags=1))
        struct.pack_into('<Q', extension, 32, (1 << 48) | base_no)
        # Reapply valid fixups (base_ref field not at fixup point).
        raw[MFT_LCN*CLUSTER+12*SIZE:MFT_LCN*CLUSTER+13*SIZE] = extension
    raw[40*CLUSTER:41*CLUSTER] = b'A' * CLUSTER
    raw[60*CLUSTER:60*CLUSTER+188] = b'B' * 188
    return bytes(raw)


def _index_root(child_no, child_seq, parent=5, name='GeretteterOrdner', is_dir=True):
    enc = name.encode('utf-16le')
    key = bytearray(66+len(enc))
    struct.pack_into('<Q', key, 0, (1 << 48) | parent)
    if is_dir:
        struct.pack_into('<I', key, 56, 0x10000000)
    key[64], key[65] = len(enc)//2, 1
    key[66:] = enc
    length = align8(16+len(key))
    root = bytearray(32+length+16)
    struct.pack_into('<I', root, 0, 0x30)  # indexed $FILE_NAME
    struct.pack_into('<I', root, 16, 16)  # entries start at root+32
    struct.pack_into('<I', root, 20, 16+length+16)  # INDEX_HEADER used bytes
    struct.pack_into('<I', root, 24, 16+length+16)
    struct.pack_into('<Q', root, 32, (child_seq << 48) | child_no)
    struct.pack_into('<HH', root, 40, length, len(key))
    root[48:48+len(key)] = key
    end = 32+length
    struct.pack_into('<H', root, end+8, 16)
    struct.pack_into('<H', root, end+12, 2)  # LAST ENTRY
    name16 = '$I30'.encode('utf-16le')
    attr_len = align8(24 + len(name16) + len(root))
    attr = bytearray(attr_len)
    struct.pack_into('<II', attr, 0, 0x90, attr_len)
    attr[9] = len(name16)//2
    struct.pack_into('<H', attr, 10, 24)
    struct.pack_into('<I', attr, 16, len(root))
    struct.pack_into('<H', attr, 20, 24+len(name16))
    attr[24:24+len(name16)] = name16
    attr[24+len(name16):24+len(name16)+len(root)] = root
    return bytes(attr)


class ReconstructionTests(unittest.TestCase):
    def test_multiextent_attribute_list_can_export(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp)/'volume.raw'
            src.write_bytes(build_split_attribute_image())
            index = scan_ntfs_tree(str(src))
            entry = next(e for e in index.entries if e.name == 'umfangreich.bin')
            self.assertTrue(entry.recoverable, entry.unsupported_reason)
            self.assertEqual(index.resolved_attribute_lists, 1)
            self.assertEqual(entry.size, 700)
            dest = Path(temp)/'recovered.bin'
            self.assertEqual(export_file(str(src), index.info, entry, str(dest)), 700)
            self.assertEqual(dest.read_bytes(), b'A'*512+b'B'*188)

    def test_reject_missing_or_incorrect_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            for variant in ({'bad_ref':True}, {'bad_sequence':True},
                            {'broken_second':True}, {'compressed':True}):
                src = Path(tmp)/'source.raw'
                src.write_bytes(build_split_attribute_image(**variant))
                index = scan_ntfs_tree(str(src))
                entry = next(e for e in index.entries if e.name == 'umfangreich.bin')
                self.assertFalse(entry.recoverable, variant)
                self.assertEqual(index.unresolved_attribute_lists, 1)
                with self.assertRaises((ValueError, NTFSError)):
                    export_file(str(src), index.info, entry, str(Path(tmp)/'out.bin'))

    def test_missing_folder_metadata_can_relink_children_but_never_export(self):
        raw = bytearray(image_with_folders())
        # Existing children of #6: `bericht.txt`, `unterordner`, etc.
        # Corrupt actual record 6, while a parent $I30 name still survives.
        root = record([filename('Wurzel', 5), _index_root(6, 1, 5, 'Dokumente')], flags=3)
        raw[MFT_LCN*CLUSTER+5*SIZE:MFT_LCN*CLUSTER+6*SIZE] = root
        raw[MFT_LCN*CLUSTER+6*SIZE:MFT_LCN*CLUSTER+7*SIZE] = bytes(SIZE)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'corrupt.raw'
            path.write_bytes(raw)
            index = scan_ntfs_tree(str(path))
            restored = next(e for e in index.list_dir(5) if e.name == 'Dokumente')
            self.assertTrue(restored.metadata_only)
            self.assertTrue(restored.is_directory)
            self.assertEqual(index.reconstructed_index_hints, 1)
            self.assertIn('bericht.txt', [e.name for e in index.list_dir(6)])
            self.assertNotIn('bericht.txt', [e.name for e in index.list_dir(ORPHANS)])
            dest = Path(td)/'dest'; dest.mkdir()
            report = export_selection(str(path), index, [restored], str(dest))
            self.assertEqual(report.directories, 0)
            self.assertEqual(report.exported, 0)
            self.assertGreater(report.skipped, 0)

    def test_index_hints_do_not_claim_unscanned_records_are_damaged(self):
        raw = bytearray(image_with_folders())
        root = record([filename('Wurzel', 5), _index_root(6, 1, 5, 'Dokumente')], flags=3)
        raw[MFT_LCN*CLUSTER+5*SIZE:MFT_LCN*CLUSTER+6*SIZE] = root
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'shortscan.raw'; path.write_bytes(raw)
            index = scan_ntfs_tree(str(path), max_records=6)
            self.assertEqual(index.reconstructed_index_hints, 0)
            self.assertFalse(any(e.metadata_only for e in index.entries))

    def test_index_key_parent_mismatch_ignored(self):
        raw = bytearray(image_with_folders())
        root = record([filename('Wurzel', 5), _index_root(6, 1, 42, 'FalscheReferenz')], flags=3)
        raw[MFT_LCN*CLUSTER+5*SIZE:MFT_LCN*CLUSTER+6*SIZE] = root
        raw[MFT_LCN*CLUSTER+6*SIZE:MFT_LCN*CLUSTER+7*SIZE] = bytes(SIZE)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'bad.raw'; path.write_bytes(raw)
            index = scan_ntfs_tree(str(path))
            self.assertEqual(index.reconstructed_index_hints, 0)
            self.assertIn('bericht.txt', [e.name for e in index.list_dir(ORPHANS)])

if __name__ == '__main__':
    unittest.main()
