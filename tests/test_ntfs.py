"""Tests use a self-contained synthetic NTFS volume, never real user data."""
import os
import struct
import tempfile
import unittest
from pathlib import Path

from recoverydesk.ntfs import (
    NTFSError, DataRun, parse_runlist, apply_update_sequence, parse_boot_sector,
    scan_deleted_files, recover_ntfs_file,
)

SIZE = 1024
CLUSTER = 512
TOTAL_CLUSTERS = 512
MFT_LCN = 4


def align8(n):
    return (n + 7) & ~7


def resident_attr(typ, payload, flags=0):
    size = align8(24 + len(payload))
    out = bytearray(size)
    struct.pack_into('<II', out, 0, typ, size)
    struct.pack_into('<H', out, 12, flags)
    struct.pack_into('<I', out, 16, len(payload))
    struct.pack_into('<H', out, 20, 24)
    out[24:24+len(payload)] = payload
    return bytes(out)


def nonresident_attr(typ, runlist, real_size, last_vcn, flags=0):
    size = align8(64 + len(runlist))
    out = bytearray(size)
    struct.pack_into('<II', out, 0, typ, size)
    out[8] = 1
    struct.pack_into('<H', out, 12, flags)
    struct.pack_into('<QQ', out, 16, 0, last_vcn)
    struct.pack_into('<H', out, 32, 64)
    struct.pack_into('<QQQ', out, 40, (last_vcn+1)*CLUSTER, real_size, real_size)
    out[64:64+len(runlist)] = runlist
    return bytes(out)


def filename_attr(name):
    encoded = name.encode('utf-16le')
    payload = bytearray(66 + len(encoded))
    struct.pack_into('<Q', payload, 0, 5)
    payload[64] = len(encoded) // 2
    payload[65] = 1
    payload[66:] = encoded
    return resident_attr(0x30, payload)


def file_record(attrs, in_use=False):
    out = bytearray(SIZE)
    out[:4] = b'FILE'
    struct.pack_into('<HH', out, 4, 0x30, 3)
    struct.pack_into('<H', out, 20, 0x38)
    struct.pack_into('<H', out, 22, 1 if in_use else 0)
    p = 0x38
    for attr in attrs:
        out[p:p+len(attr)] = attr
        p += len(attr)
    struct.pack_into('<I', out, p, 0xffffffff)
    # Update Sequence Array: matching USN at last 2 bytes of each sector.
    out[0x30:0x32] = b'\xad\xde'
    for i in range(1, 3):
        end = i * CLUSTER - 2
        original = bytes(out[end:end+2])
        out[0x30+i*2:0x32+i*2] = original
        out[end:end+2] = b'\xad\xde'
    return bytes(out)


def make_image(base=0):
    raw = bytearray(base + TOTAL_CLUSTERS * CLUSTER)
    boot = bytearray(512)
    boot[3:11] = b'NTFS    '
    struct.pack_into('<H', boot, 11, CLUSTER)
    boot[13] = 1
    struct.pack_into('<Q', boot, 40, TOTAL_CLUSTERS)
    struct.pack_into('<Q', boot, 48, MFT_LCN)
    struct.pack_into('<b', boot, 64, -10)  # 1024-byte MFT records
    boot[510:512] = b'\x55\xaa'
    raw[base:base+512] = boot
    # MFT stream: 16 contiguous clusters beginning at LCN 4.
    mft_attr = nonresident_attr(0x80, b'\x11\x10\x04\x00', 16*CLUSTER, 15)
    records = [
        file_record([mft_attr], in_use=True),
        file_record([filename_attr('gelöscht.txt'), resident_attr(0x80, b'Hallo RecoveryDesk!')]),
        file_record([filename_attr('fragmentiert.bin'),
            nonresident_attr(0x80, b'\x11\x01\x28\x11\x01\x14\x00', 700, 1)]),
        file_record([filename_attr('verschlüsselt.bin'), resident_attr(0x80, b'SECRET', flags=0x4000)]),
        file_record([filename_attr('aktiv.txt'), resident_attr(0x80, b'ACTIVE')], in_use=True),
    ]
    for i, record in enumerate(records):
        off = base + MFT_LCN*CLUSTER + i*SIZE
        raw[off:off+SIZE] = record
    raw[base+40*CLUSTER:base+41*CLUSTER] = b'A'*CLUSTER
    raw[base+60*CLUSTER:base+60*CLUSTER+188] = b'B'*188
    return bytes(raw)


class NTFSTests(unittest.TestCase):
    def test_runlist_fragmented_and_sparse(self):
        self.assertEqual(parse_runlist(b'\x11\x01\x28\x11\x01\x14\x00', TOTAL_CLUSTERS),
                         [DataRun(40, 1), DataRun(60, 1)])
        self.assertEqual(parse_runlist(b'\x01\x02\x00', TOTAL_CLUSTERS), [DataRun(None, 2)])
        with self.assertRaises(NTFSError):
            parse_runlist(b'\x11\x01\x00', TOTAL_CLUSTERS)

    def test_mft_deleted_recovery_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, 'image.img')
            Path(source).write_bytes(make_image())
            info, deleted = scan_deleted_files(source)
            self.assertEqual(info.record_size, 1024)
            self.assertEqual(len(deleted), 3)
            self.assertEqual({x.name for x in deleted},
                             {'gelöscht.txt', 'fragmentiert.bin', 'verschlüsselt.bin'})
            resident = next(x for x in deleted if x.name == 'gelöscht.txt')
            target = os.path.join(tmp, 'restored.txt')
            self.assertEqual(recover_ntfs_file(source, resident, target), len(b'Hallo RecoveryDesk!'))
            self.assertEqual(Path(target).read_bytes(), b'Hallo RecoveryDesk!')
            with self.assertRaises(FileExistsError):
                recover_ntfs_file(source, resident, target)
            fragmented = next(x for x in deleted if x.name == 'fragmentiert.bin')
            other = os.path.join(tmp, 'recovered.bin')
            self.assertEqual(recover_ntfs_file(source, fragmented, other), 700)
            self.assertEqual(Path(other).read_bytes(), b'A'*512 + b'B'*188)
            unsupported = next(x for x in deleted if x.name == 'verschlüsselt.bin')
            self.assertFalse(unsupported.recoverable)
            with self.assertRaises(NTFSError):
                recover_ntfs_file(source, unsupported, os.path.join(tmp, 'no.bin'))
            with self.assertRaises(ValueError):
                recover_ntfs_file(source, resident, source)

    def test_partition_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = os.path.join(tmp, 'disk.img')
            offset = 128*512
            Path(image).write_bytes(make_image(offset))
            info, entries = scan_deleted_files(image, partition_offset=offset)
            self.assertEqual(info.partition_offset, offset)
            target = os.path.join(tmp, 'out.txt')
            selected = next(e for e in entries if e.name == 'gelöscht.txt')
            recover_ntfs_file(image, selected, target, partition_offset=offset)
            self.assertEqual(Path(target).read_bytes(), b'Hallo RecoveryDesk!')
            with self.assertRaises(NTFSError):
                scan_deleted_files(image, partition_offset=0)

    def test_corrupt_fixups_refused(self):
        raw = bytearray(file_record([filename_attr('bad.txt'), resident_attr(0x80, b'broken')]))
        raw[510] = 0
        with self.assertRaises(NTFSError):
            apply_update_sequence(bytes(raw), CLUSTER)

if __name__ == '__main__':
    unittest.main()
