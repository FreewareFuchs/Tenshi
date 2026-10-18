"""Real byte-recovery tests for *hypothetically* recoverable deleted ext files."""
import struct
import tempfile
import unittest
from pathlib import Path

from recoverydesk.filesystems import scan_tree, export_file, FileSystemError
from test_deleted_non_ntfs import make_ext_image

BS = 1024
PAYLOAD = b'old ext data'


def ext_deleted_image(*, extents=False, inode_occupied=False,
                      data_occupied=False, corrupt_pointer=False,
                      partition_offset=0):
    old = bytearray(make_ext_image())
    desc = 2 * BS
    # Group 0 descriptor: block bitmap at 3, inode bitmap at 4,
    # inode table at 5 (as provided by the base fixture).
    struct.pack_into('<I', old, desc, 3)
    struct.pack_into('<I', old, desc + 4, 4)
    # Mark root-directory block 12 as allocated; old data block 15 must be free.
    old[3*BS + 12//8] |= (1 << (12 % 8))
    # Inode 2 allocated; old inode 11 is free.
    old[4*BS] |= (1 << 1)
    if inode_occupied:
        old[4*BS + 10//8] |= (1 << (10 % 8))
    if data_occupied:
        old[3*BS + 15//8] |= (1 << (15 % 8))
    pos = 5 * BS + (11-1)*128
    struct.pack_into('<I', old, pos+4, len(PAYLOAD))
    if extents:
        struct.pack_into('<I', old, BS+96, 0x40)
        struct.pack_into('<I', old, pos+32, 0x80000)
        old[pos+40:pos+100] = bytes(60)
        struct.pack_into('<HHHHI', old, pos+40, 0xF30A, 1, 4, 0, 0)
        struct.pack_into('<IHHI', old, pos+52, 0, 1, 0, 15)
    if corrupt_pointer:
        struct.pack_into('<I', old, pos+40, 0)
    old[15*BS:15*BS+len(PAYLOAD)] = PAYLOAD
    return bytes(partition_offset) + bytes(old)


class DeletedExtRecoveryTests(unittest.TestCase):
    def _candidate(self, data, offset=0):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        src = Path(tmp.name)/'volume.raw'
        src.write_bytes(data)
        index = scan_tree(str(src), offset=offset)
        entries = [e for e in index.list_dir(5) if e.is_deleted and e.name == 'old.txt']
        self.assertEqual(len(entries), 1)
        return src, index, entries[0], Path(tmp.name)/'out.txt'

    def test_ext2_direct_deleted_inode_recovery(self):
        image = ext_deleted_image()
        src, index, item, dest = self._candidate(image)
        self.assertTrue(item.recoverable, item.unsupported_reason)
        self.assertTrue(item.is_deleted)
        self.assertEqual(item.size, len(PAYLOAD))
        self.assertEqual(export_file(str(src), index, item, str(dest)), len(PAYLOAD))
        self.assertEqual(dest.read_bytes(), PAYLOAD)
        self.assertEqual(src.read_bytes(), image)

    def test_ext4_inline_extent_recovery_with_partition_offset(self):
        offset = 4096
        raw = ext_deleted_image(extents=True, partition_offset=offset)
        src, index, item, dest = self._candidate(raw, offset=offset)
        self.assertEqual(index.filesystem, 'ext4')
        self.assertTrue(item.recoverable, item.unsupported_reason)
        export_file(str(src), index, item, str(dest))
        self.assertEqual(dest.read_bytes(), PAYLOAD)

    def test_deleted_inode_reallocated_is_not_exported(self):
        src, index, item, dest = self._candidate(ext_deleted_image(inode_occupied=True))
        self.assertFalse(item.recoverable)
        self.assertIn('wieder belegt', item.unsupported_reason)
        with self.assertRaises(FileSystemError):
            export_file(str(src), index, item, str(dest))
        self.assertFalse(dest.exists())

    def test_deleted_data_block_reallocated_is_not_exported(self):
        src, index, item, dest = self._candidate(ext_deleted_image(data_occupied=True))
        self.assertFalse(item.recoverable)
        self.assertIn('wieder belegt', item.unsupported_reason)

    def test_zeroed_or_missing_old_pointer_remains_metadata_only(self):
        src, index, item, dest = self._candidate(ext_deleted_image(corrupt_pointer=True))
        self.assertFalse(item.recoverable)
        self.assertIn('Löcher', item.unsupported_reason)

    def test_changed_block_bitmap_between_scan_and_export_is_blocked(self):
        src, index, item, dest = self._candidate(ext_deleted_image())
        self.assertTrue(item.recoverable)
        with src.open('r+b') as f:
            f.seek(3*BS + 15//8)
            b = f.read(1)[0]
            f.seek(3*BS + 15//8)
            f.write(bytes([b | (1 << (15 % 8))]))
        with self.assertRaises(FileSystemError):
            export_file(str(src), index, item, str(dest))
        self.assertFalse(dest.exists())

    def test_inode_reused_after_scan_is_blocked(self):
        src, index, item, dest = self._candidate(ext_deleted_image())
        self.assertTrue(item.recoverable)
        with src.open('r+b') as f:
            f.seek(4*BS + 10//8)
            b = f.read(1)[0]
            f.seek(4*BS + 10//8)
            f.write(bytes([b | (1 << (10 % 8))]))
        with self.assertRaises(FileSystemError):
            export_file(str(src), index, item, str(dest))
        self.assertFalse(dest.exists())

    def test_unavailable_bitmaps_are_not_assumed_free(self):
        src, index, item, dest = self._candidate(make_ext_image())
        self.assertFalse(item.recoverable)
        self.assertIn('bitmap', item.unsupported_reason.lower())

    def test_bigalloc_rejected_for_deleted_inode(self):
        img = bytearray(ext_deleted_image(extents=True))
        struct.pack_into('<I',img,BS+100,0x200)
        src,index,item,dest=self._candidate(bytes(img))
        self.assertFalse(item.recoverable)
        self.assertIn('Bigalloc', item.unsupported_reason)

    def test_ext3_direct_deleted_inode_recovery(self):
        image = bytearray(ext_deleted_image())
        struct.pack_into('<I', image, BS + 92, 4)  # has_journal
        src, index, entry, dest = self._candidate(bytes(image))
        self.assertEqual(index.filesystem, 'ext3')
        self.assertTrue(entry.recoverable, entry.unsupported_reason)
        export_file(str(src), index, entry, str(dest))
        self.assertEqual(dest.read_bytes(), PAYLOAD)

    def test_uninitialized_inode_bitmap_is_not_used(self):
        image = bytearray(ext_deleted_image())
        struct.pack_into('<H', image, 2*BS+18, 1)  # EXT4_BG_INODE_UNINIT
        _, _, entry, _ = self._candidate(bytes(image))
        self.assertFalse(entry.recoverable)
        self.assertIn('nicht initialisiert', entry.unsupported_reason)

    def test_uninitialized_block_bitmap_is_not_used(self):
        image = bytearray(ext_deleted_image())
        struct.pack_into('<H', image, 2*BS+18, 2)  # EXT4_BG_BLOCK_UNINIT
        _, _, entry, _ = self._candidate(bytes(image))
        self.assertFalse(entry.recoverable)
        self.assertIn('nicht initialisiert', entry.unsupported_reason)

    def test_ext4_fragmented_old_extent_data(self):
        image = bytearray(ext_deleted_image(extents=True))
        inode_pos = 5*BS+(11-1)*128
        # Two logical blocks, physical blocks 15 and 18.
        payload_a = b'A' * BS
        payload_b = b'B' * 17
        struct.pack_into('<I', image, inode_pos+4, BS + len(payload_b))
        struct.pack_into('<H', image, inode_pos+42, 2)
        struct.pack_into('<IHHI', image, inode_pos+64, 1, 1, 0, 18)
        image[15*BS:16*BS] = payload_a
        image[18*BS:18*BS+len(payload_b)] = payload_b
        src,index,entry,dest=self._candidate(bytes(image))
        self.assertTrue(entry.recoverable, entry.unsupported_reason)
        export_file(str(src),index,entry,str(dest))
        self.assertEqual(dest.read_bytes(),payload_a+payload_b)

    def test_ext4_fragmented_old_extent_block_reallocated(self):
        image = bytearray(ext_deleted_image(extents=True))
        inode_pos = 5*BS+(11-1)*128
        struct.pack_into('<I', image, inode_pos+4, BS+8)
        struct.pack_into('<H', image, inode_pos+42, 2)
        struct.pack_into('<IHHI', image, inode_pos+64, 1, 1, 0, 18)
        image[3*BS + 18//8] |= (1 << (18 % 8))
        _,_,entry,_ = self._candidate(bytes(image))
        self.assertFalse(entry.recoverable)
        self.assertIn('wieder belegt',entry.unsupported_reason)

    def test_normal_existing_files_unaffected(self):
        from test_filesystems import ext4_img
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'ext4.raw';src.write_bytes(ext4_img())
            idx=scan_tree(str(src))
            files=[e for e in idx.list_dir(5) if not e.is_directory]
            self.assertEqual([e.name for e in files],['report.any'])
            out=Path(d)/'exported.dat'
            export_file(str(src),idx,files[0],str(out))
            self.assertEqual(out.read_bytes(),b'HELLOext4')


if __name__=='__main__':
    unittest.main()
