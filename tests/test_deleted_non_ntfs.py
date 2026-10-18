"""Synthetic deleted-entry tests. No original media modified."""
import os
import struct
import tempfile
import unittest
from pathlib import Path
from recoverydesk.filesystems import scan_tree, export_file, FileSystemError


def make_fat_image(reuse=False, partition_offset=0):
    bps=512
    total=512
    reserved=32
    fat_sectors=4
    root=2
    image=bytearray(partition_offset+total*bps)
    boot=bytearray(512)
    boot[82:90]=b'FAT32   '
    struct.pack_into('<H',boot,11,bps)
    boot[13]=1
    struct.pack_into('<H',boot,14,reserved)
    boot[16]=1
    struct.pack_into('<I',boot,32,total)
    struct.pack_into('<I',boot,36,fat_sectors)
    struct.pack_into('<I',boot,44,root)
    boot[510:512]=b'\x55\xaa'
    image[partition_offset:partition_offset+512]=boot
    fat_offset=partition_offset+reserved*bps
    for c,v in [(0,0x0FFFFFF8),(1,0x0FFFFFFF),(2,0x0FFFFFFF)]:
        struct.pack_into('<I',image,fat_offset+c*4,v)
    if reuse:struct.pack_into('<I',image,fat_offset+5*4,0x0FFFFFFF)
    data_sector=reserved+fat_sectors
    root_off=partition_offset+data_sector*bps
    row=bytearray(32)
    row[:11]=bytes([0xE5])+b'ECRET  TXT'
    row[11]=0x20
    struct.pack_into('<H',row,26,5)
    struct.pack_into('<I',row,28,11)
    image[root_off:root_off+32]=row
    image[root_off+32]=0
    data_off=partition_offset+(data_sector+3)*bps
    image[data_off:data_off+11]=b'HELLO WORLD'
    return bytes(image)


def make_exfat_image(reuse=False, partition_offset=0):
    image=bytearray(partition_offset+512*256)
    boot=bytearray(512)
    boot[3:11]=b'EXFAT   '
    boot[108]=9;boot[109]=0;boot[110]=1
    struct.pack_into('<Q',boot,72,256)
    struct.pack_into('<I',boot,80,24) # FAT offset
    struct.pack_into('<I',boot,84,2)
    struct.pack_into('<I',boot,88,32) # cluster heap
    struct.pack_into('<I',boot,92,120)
    struct.pack_into('<I',boot,96,2)
    boot[510:512]=b'\x55\xaa'
    image[partition_offset:partition_offset+512]=boot
    def cl(n): return partition_offset+(32+n-2)*512
    fat=partition_offset+24*512
    struct.pack_into('<I',image,fat+2*4,0xFFFFFFFF)
    struct.pack_into('<I',image,fat+3*4,0xFFFFFFFF)
    # Root bitmap entry
    bitmap=bytearray(32)
    bitmap[0]=0x81
    struct.pack_into('<I',bitmap,20,3)
    struct.pack_into('<Q',bitmap,24,15)
    image[cl(2):cl(2)+32]=bitmap
    # deleted file entry group
    primary=bytearray(32);primary[0]=0x05;primary[1]=2
    stream=bytearray(32);stream[0]=0x40;stream[1]=0x02;stream[3]=7
    struct.pack_into('<I',stream,20,5)
    struct.pack_into('<Q',stream,8,11)
    struct.pack_into('<Q',stream,24,11)
    name=bytearray(32);name[0]=0x41;name[2:16]='old.txt'.encode('utf-16le')
    image[cl(2)+32:cl(2)+64]=primary
    image[cl(2)+64:cl(2)+96]=stream
    image[cl(2)+96:cl(2)+128]=name
    image[cl(2)+128]=0
    # bit 0 root, bit 1 bitmap. optionally bit 3 reused file cluster.
    image[cl(3)]=0b00001011 if reuse else 0b00000011
    image[cl(5):cl(5)+11]=b'HELLO WORLD'
    return bytes(image)


def make_ext_image():
    image=bytearray(128*1024)
    sb=1024
    struct.pack_into('<I',image,sb+0,64) # inodes
    struct.pack_into('<I',image,sb+4,128) # blocks
    struct.pack_into('<I',image,sb+24,0) # block 1024
    struct.pack_into('<I',image,sb+32,128)
    struct.pack_into('<I',image,sb+40,64)
    struct.pack_into('<H',image,sb+56,0xEF53)
    struct.pack_into('<H',image,sb+88,128)
    # group descriptor at 2*1024, inode table starts block 5
    struct.pack_into('<I',image,2*1024+8,5)
    def inode(n,mode,size,link,dtime,block):
        p=5*1024+(n-1)*128
        struct.pack_into('<H',image,p,mode)
        struct.pack_into('<I',image,p+4,size)
        struct.pack_into('<I',image,p+20,dtime)
        struct.pack_into('<H',image,p+26,link)
        struct.pack_into('<I',image,p+40,block)
    inode(2,0x41ed,1024,2,0,12)
    inode(11,0x81a4,12,0,123456,15)
    # root dir block: live . and .. and a record whose rec_len spans stale dirent
    dir_off=12*1024
    struct.pack_into('<IHBB',image,dir_off,2,12,1,2)
    image[dir_off+8:dir_off+9]=b'.'
    struct.pack_into('<IHBB',image,dir_off+12,2,12,2,2)
    image[dir_off+20:dir_off+22]=b'..'
    # active entry covers rest of block; stale deleted entry in slack
    struct.pack_into('<IHBB',image,dir_off+24,2,1000,4,2)
    image[dir_off+32:dir_off+36]=b'live'
    stale=dir_off+36
    struct.pack_into('<IHBB',image,stale,11,20,7,1)
    image[stale+8:stale+15]=b'old.txt'
    return bytes(image)

class DeletedNonNTFSTests(unittest.TestCase):
    def test_fat32_deleted_contiguous_candidate_and_export(self):
        for offset in (0,4096):
            with tempfile.TemporaryDirectory() as d:
                src=Path(d)/'fat.img';src.write_bytes(make_fat_image(partition_offset=offset))
                index=scan_tree(str(src),offset)
                found=index.list_dir(5)
                self.assertEqual(len(found),1)
                e=found[0]
                self.assertTrue(e.is_deleted)
                self.assertIn('ECRET',e.name)
                self.assertTrue(e.recoverable)
                self.assertEqual(index.list_dir(5,False),[])
                target=Path(d)/'recovered.bin'
                self.assertEqual(export_file(str(src),index,e,str(target)),11)
                self.assertEqual(target.read_bytes(),b'HELLO WORLD')
                self.assertEqual(src.read_bytes(),make_fat_image(partition_offset=offset))

    def test_fat32_prevent_export_if_clusters_reused(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'fat.img';src.write_bytes(make_fat_image(reuse=True))
            index=scan_tree(str(src))
            e=index.list_dir(5)[0]
            self.assertTrue(e.is_deleted)
            self.assertFalse(e.recoverable)
            with self.assertRaises(FileSystemError):
                export_file(str(src),index,e,str(Path(d)/'no.bin'))

    def test_exfat_deleted_candidate_and_export(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'exfat.img';src.write_bytes(make_exfat_image())
            index=scan_tree(str(src))
            e=index.list_dir(5)[0]
            self.assertEqual(e.name,'old.txt')
            self.assertTrue(e.is_deleted)
            self.assertTrue(e.recoverable,e.unsupported_reason)
            dest=Path(d)/'recovered.txt'
            export_file(str(src),index,e,str(dest))
            self.assertEqual(dest.read_bytes(),b'HELLO WORLD')

    def test_exfat_prevent_export_if_bitmap_reused(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'exfat.img';src.write_bytes(make_exfat_image(reuse=True))
            index=scan_tree(str(src))
            e=index.list_dir(5)[0]
            self.assertTrue(e.is_deleted)
            self.assertFalse(e.recoverable)
            self.assertIn('Bitmap',e.unsupported_reason)

    def test_fat32_rechecks_cluster_allocation_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'fat.img';src.write_bytes(make_fat_image())
            index=scan_tree(str(src))
            candidate=index.list_dir(5)[0]
            self.assertTrue(candidate.recoverable)
            with src.open('r+b') as f:
                f.seek(32*512+5*4)
                f.write(struct.pack('<I',0x0FFFFFFF))
            with self.assertRaises(FileSystemError):
                export_file(str(src),index,candidate,str(Path(d)/'no.bin'))
            self.assertFalse((Path(d)/'no.bin').exists())

    def test_exfat_rechecks_bitmap_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'exfat.img';src.write_bytes(make_exfat_image())
            index=scan_tree(str(src))
            candidate=index.list_dir(5)[0]
            self.assertTrue(candidate.recoverable)
            with src.open('r+b') as f:
                f.seek((32 + 3 - 2)*512)
                f.write(bytes([0b00001011]))
            with self.assertRaises(FileSystemError):
                export_file(str(src),index,candidate,str(Path(d)/'no.bin'))
            self.assertFalse((Path(d)/'no.bin').exists())

    def test_ext_slack_is_metadata_only(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'ext.img';src.write_bytes(make_ext_image())
            index=scan_tree(str(src))
            matches=[e for e in index.list_dir(5) if e.is_deleted]
            self.assertEqual(len(matches),1)
            self.assertEqual(matches[0].name,'old.txt')
            self.assertFalse(matches[0].recoverable)
            self.assertFalse(any(e.is_deleted for e in index.list_dir(5,False)))

if __name__ == '__main__':unittest.main()
