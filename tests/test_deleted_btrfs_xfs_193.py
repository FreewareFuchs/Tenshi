"""Synthetic forensic fixtures: Btrfs orphan metadata and XFS AGI unlinked heads.

These are deliberately only metadata hints; they must never be exportable.
"""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from recoverydesk.filesystems import scan_tree, export_file, FileSystemError
from tests.test_linux_advanced import btrfs_img, xfs_img


def btrfs_orphan_image(*, linked=False, partition_offset=0):
    image = bytearray(btrfs_img(offset=partition_offset))
    base = partition_offset + 393216
    n = 4096
    node = image[base:base+n]
    count = struct.unpack_from('<I', node, 96)[0]
    items = []
    for i in range(count):
        position = 101 + i*25
        objectid, kind, keyoff, itemoff, length = struct.unpack_from('<QBQII', node, position)
        items.append(((objectid,kind,keyoff), bytes(node[101+itemoff:101+itemoff+length])))
    inode_item = struct.pack('<QQQ',1,1,23)+bytes(28)+struct.pack('<I',0x81a4)+bytes(104)
    items.append(((260,1,0), inode_item))
    items.append((((1<<64)-5,48,260), b''))
    if linked:
        def diridx(target,name,kind):
            name=name.encode()
            return struct.pack('<QBQ',target,1,0)+struct.pack('<QHHB',1,0,len(name),kind)+name
        items.append(((256,96,9),diridx(260,'existing.txt',1)))
    node = bytearray(n)
    struct.pack_into('<Q',node,48,393216)
    struct.pack_into('<I',node,96,len(items))
    node[100] = 0
    cursor = n
    for i,(key,data) in enumerate(sorted(items)):
        cursor -= len(data)
        node[cursor:cursor+len(data)] = data
        struct.pack_into('<QBQII',node,101+i*25,*key,cursor-101,len(data))
    assert cursor > 101+25*len(items)
    image[base:base+n] = node
    return bytes(image)


def xfs_unlinked_image(*, valid=True, linked=False, partition_offset=0):
    image=bytearray(xfs_img(offset=partition_offset))
    agi = bytearray(512)
    agi[:4] = b'XAGI' if valid else b'BADA'
    struct.pack_into('>IIII',agi,4,1,0,1024,10)
    for i in range(64):
        struct.pack_into('>I',agi,40+i*4,0xffffffff)
    struct.pack_into('>I',agi,40,168)  # known regular file inode
    image[partition_offset+1024:partition_offset+1536] = agi
    inode_offset = partition_offset + (168//8)*4096 +(168%8)*512
    struct.pack_into('>I',image,inode_offset+16,1 if linked else 0)
    return bytes(image)


class LinuxDeletedMetadataTests(unittest.TestCase):
    def _scan(self, image, offset=0):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source=Path(temp.name)/'source.raw'
        source.write_bytes(image)
        digest=hashlib.sha256(source.read_bytes()).digest()
        index=scan_tree(str(source),offset)
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),digest)
        return source,index

    def test_btrfs_orphan_is_visible_only_as_non_exportable_hint(self):
        source,index=self._scan(btrfs_orphan_image())
        matches=[e for e in index.list_dir(index.root) if e.name.startswith('Btrfs-Orphan-Inode')]
        self.assertEqual(len(matches),1)
        item=matches[0]
        self.assertTrue(item.is_deleted)
        self.assertFalse(item.recoverable)
        self.assertEqual(item.size,23)
        self.assertNotIn(item,index.list_dir(index.root,False))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileSystemError):
                export_file(str(source),index,item,str(Path(d)/'output.bin'))
        self.assertTrue(any('Orphan' in x for x in index.scan_warnings))

    def test_btrfs_orphan_with_live_name_does_not_fabricate_deletion(self):
        _,idx=self._scan(btrfs_orphan_image(linked=True))
        self.assertFalse(any(e.name.startswith('Btrfs-Orphan') for e in idx.entries))
        self.assertTrue(any(e.name=='existing.txt' for e in idx.entries))

    def test_xfs_unlinked_bucket_non_exportable(self):
        source,index=self._scan(xfs_unlinked_image())
        matches=[e for e in index.entries if e.name.startswith('XFS-Unlinked-Inode')]
        self.assertEqual(len(matches),1)
        self.assertIn('168',matches[0].name)
        self.assertTrue(matches[0].is_deleted)
        self.assertFalse(matches[0].recoverable)
        self.assertNotIn(matches[0],index.list_dir(index.root,False))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileSystemError):
                export_file(str(source),index,matches[0],str(Path(d)/'target'))

    def test_xfs_ignores_invalid_agi(self):
        _,index=self._scan(xfs_unlinked_image(valid=False))
        self.assertFalse(any(e.name.startswith('XFS-Unlinked-Inode') for e in index.entries))

    def test_xfs_nlink_must_be_zero(self):
        _,index=self._scan(xfs_unlinked_image(linked=True))
        self.assertFalse(any(e.name.startswith('XFS-Unlinked-Inode') for e in index.entries))

    def test_xfs_with_partition_offset(self):
        offset=1048576
        _,index=self._scan(xfs_unlinked_image(partition_offset=offset),offset)
        self.assertTrue(any(e.name.startswith('XFS-Unlinked-Inode') for e in index.entries))

if __name__=='__main__':unittest.main()
