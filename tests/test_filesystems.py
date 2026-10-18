"""Synthetic volume images prove real directory traversal, not extension guessing."""
from __future__ import annotations
import os
import struct
import tempfile
import unittest
from pathlib import Path

from recoverydesk.filesystems import scan_tree, export_selection, FileSystemError, FAT32
from recoverydesk.partition_scan import analyze_image

SECTOR=512

def fat_short(name, attr, cluster, size=0):
    result=bytearray(32)
    result[:11]=name.encode('ascii')
    result[11]=attr
    struct.pack_into('<H',result,20,cluster>>16)
    struct.pack_into('<H',result,26,cluster&65535)
    struct.pack_into('<I',result,28,size)
    return bytes(result)

def fat_img(offset=0):
    raw=bytearray(offset+512*512)
    b=bytearray(512);b[:3]=b'\xeb\x58\x90';b[82:90]=b'FAT32   ';b[510:]=b'\x55\xaa'
    struct.pack_into('<H',b,11,512);b[13]=1;struct.pack_into('<H',b,14,32);b[16]=1
    struct.pack_into('<I',b,32,512);struct.pack_into('<I',b,36,16);struct.pack_into('<I',b,44,2)
    raw[offset:offset+512]=b
    fat=offset+32*512
    for cl,val in ((0,0x0FFFFFF8),(1,0xFFFFFFFF),(2,0x0FFFFFFF),(3,0x0FFFFFFF),(4,0x0FFFFFFF),(5,0x0FFFFFFF)):
        struct.pack_into('<I',raw,fat+cl*4,val)
    data=offset+48*512
    raw[data:data+64]=fat_short('DOCS       ',0x10,4)+fat_short('README  TXT',0x20,3,5)
    raw[data+512:data+517]=b'HELLO'
    raw[data+2*512:data+2*512+32]=fat_short('DATA    BIN',0x20,5,6)
    raw[data+3*512:data+3*512+6]=b'ABCDEF'
    return bytes(raw)


def exfat_img(offset=0):
    raw=bytearray(offset+256*512)
    b=bytearray(512)
    b[:3]=b'\xeb\x76\x90';b[3:11]=b'EXFAT   ';b[510:]=b'\x55\xaa'
    struct.pack_into('<Q',b,72,256)
    struct.pack_into('<IIIII',b,80,24,1,32,128,2)
    b[108]=9;b[109]=0;b[110]=1
    raw[offset:offset+512]=b
    fat=offset+24*512
    for cl,val in ((2,0xFFFFFFFF),(3,0xFFFFFFFF),(5,0xFFFFFFFF)):
        struct.pack_into('<I',raw,fat+cl*4,val)
    data=offset+32*512
    def file_set(name,cluster,size,attrib=0x20,contiguous=False):
        n=name.encode('utf-16le')
        parent=bytearray(32);parent[0]=0x85;parent[1]=2;struct.pack_into('<H',parent,4,attrib)
        stream=bytearray(32);stream[0]=0xC0;stream[1]=2 if contiguous else 0
        stream[3]=len(n)//2;struct.pack_into('<Q',stream,8,size)
        struct.pack_into('<I',stream,20,cluster);struct.pack_into('<Q',stream,24,size)
        filename=bytearray(32);filename[0]=0xC1;filename[2:2+len(n)]=n
        return bytes(parent+stream+filename)
    root=data
    raw[root:root+96]=file_set('notes.log',3,7)
    raw[root+96:root+192]=file_set('folder',5,512,attrib=0x10)
    raw[data+512:data+519]=b'EXFAT!!'
    raw[data+3*512:data+3*512+96]=file_set('nested.bin',4,4,contiguous=True)
    raw[data+2*512:data+2*512+4]=b'FOUR'
    return bytes(raw)


def ext4_img(offset=0):
    block=1024
    raw=bytearray(offset+256*block)
    superblock=offset+1024
    struct.pack_into('<I',raw,superblock+0,32)    # inodes
    struct.pack_into('<I',raw,superblock+4,256)   # blocks
    struct.pack_into('<I',raw,superblock+24,0)    # 1024 blocksize
    struct.pack_into('<I',raw,superblock+20,1)    # first data block
    struct.pack_into('<I',raw,superblock+32,256)  # blocks/group
    struct.pack_into('<I',raw,superblock+40,32)   # inodes/group
    struct.pack_into('<H',raw,superblock+56,0xEF53)
    struct.pack_into('<H',raw,superblock+88,128)
    struct.pack_into('<I',raw,superblock+96,0x40) # extents enabled => ext4
    struct.pack_into('<I',raw,offset+2*block+8,5) # group inode table block

    def inode(no,mode,size,physical):
        o=offset+5*block+(no-1)*128
        struct.pack_into('<H',raw,o,mode)
        struct.pack_into('<I',raw,o+4,size)
        struct.pack_into('<I',raw,o+32,0x80000) # extent
        struct.pack_into('<HHHHI',raw,o+40,0xF30A,1,4,0,0)
        struct.pack_into('<IHHI',raw,o+52,0,1,0,physical)

    def dirent(ino,name,typ,record_len=None):
        name_bytes=name.encode('utf-8')
        length=record_len or (8+len(name_bytes)+3)//4*4
        out=bytearray(length)
        struct.pack_into('<IHBB',out,0,ino,length,len(name_bytes),typ)
        out[8:8+len(name_bytes)]=name_bytes
        return out

    inode(2,0x41ED,block,10)
    inode(12,0x81A4,9,11)
    inode(13,0x41ED,block,12)
    inode(14,0x81A4,4,13)
    entries=[dirent(2,'.',2),dirent(2,'..',2),dirent(12,'report.any',1),dirent(13,'Ordner',2)]
    entries[-1]=dirent(13,'Ordner',2,block-sum(len(x) for x in entries[:-1]))
    root=b''.join(entries)
    raw[offset+10*block:offset+11*block]=root
    raw[offset+11*block:offset+11*block+9]=b'HELLOext4'
    inner=[dirent(13,'.',2),dirent(2,'..',2),dirent(14,'tool',1,block-24)]
    raw[offset+12*block:offset+13*block]=b''.join(inner)
    raw[offset+13*block:offset+13*block+4]=b'TOOL'
    return bytes(raw)


class MultiFileSystemTests(unittest.TestCase):
    def exercise(self,raw,filesystem,expected_root,root_file,root_payload,folder,inner_file,inner_payload,offset=0):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'source.raw';src.write_bytes(raw)
            idx=scan_tree(str(src),offset=offset)
            self.assertEqual(idx.filesystem,filesystem)
            roots=idx.list_dir(5)
            self.assertEqual({e.name for e in roots},set(expected_root))
            child=next(e for e in roots if e.name==folder)
            self.assertTrue(child.is_directory)
            self.assertEqual([e.name for e in idx.list_dir(child.record_number)],[inner_file])
            output=Path(d)/'out';output.mkdir()
            report=export_selection(str(src),idx,roots,str(output))
            self.assertEqual((report.exported,report.directories,report.skipped),(2,1,0),report.errors)
            self.assertEqual((output/root_file).read_bytes(),root_payload)
            self.assertEqual((output/folder/inner_file).read_bytes(),inner_payload)
            preview=idx.preview(str(src),next(e for e in roots if e.name==root_file))
            self.assertEqual(preview,root_payload)
            report2=export_selection(str(src),idx,roots,str(output))
            self.assertEqual(report2.exported,2)
            self.assertEqual((output/root_file).read_bytes(),root_payload)
            self.assertEqual(src.read_bytes(),raw,'source must never change')

    def test_fat32_browser_and_export(self):
        self.exercise(fat_img(),'FAT32',['DOCS','README.TXT'],'README.TXT',b'HELLO','DOCS','DATA.BIN',b'ABCDEF')

    def test_exfat_browser_and_export(self):
        self.exercise(exfat_img(),'exFAT',['notes.log','folder'],'notes.log',b'EXFAT!!','folder','nested.bin',b'FOUR')

    def test_ext4_browser_and_export(self):
        self.exercise(ext4_img(),'ext4',['report.any','Ordner'],'report.any',b'HELLOext4','Ordner','tool',b'TOOL')

    def test_ext4_partition_offset_and_recognition(self):
        offset=1024*1024
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'ext.raw';src.write_bytes(ext4_img(offset))
            report=analyze_image(str(src))
            partitions=[p for p in report.partitions if p.filesystem=='ext4']
            self.assertTrue(partitions,report.warnings)
            self.assertEqual(partitions[0].offset_bytes,offset)
            idx=scan_tree(str(src),offset)
            self.assertEqual(idx.filesystem,'ext4')
            self.assertEqual({e.name for e in idx.list_dir(5)},{'report.any','Ordner'})

    def test_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'fat.raw';src.write_bytes(fat_img())
            idx=scan_tree(str(src))
            item=next(e for e in idx.list_dir(5) if e.name=='README.TXT')
            from recoverydesk.filesystems import export_file
            dst=Path(d)/'exists.txt';dst.write_text('ORIGINAL')
            with self.assertRaises(FileExistsError):export_file(str(src),idx,item,str(dst))
            self.assertEqual(dst.read_text(),'ORIGINAL')

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'ext.raw';src.write_bytes(ext4_img())
            from recoverydesk.filesystems import ScanCancelled
            with self.assertRaises(ScanCancelled):scan_tree(str(src),cancel=lambda: True)

    def test_fat32_vfat_long_names(self):
        # Two VFAT LFN entries precede one DOS short entry, in descending order.
        raw=bytearray(fat_img())
        name='Mein sehr langer Name.pdf'
        parts=[name[i:i+13] for i in range(0,len(name),13)]
        short=b'README  TXT'
        ck=0
        for byte in short:
            ck=((ck&1)<<7)+(ck>>1)+byte
            ck&=255
        def lfn_record(number,fragment):
            value=fragment.encode('utf-16le')
            value+=b'\x00\x00'
            value=value.ljust(26,b'\xff')[:26]
            record=bytearray(32)
            record[0]=number
            record[11]=0x0F
            record[13]=ck
            record[1:11]=value[:10]
            record[14:26]=value[10:22]
            record[28:32]=value[22:26]
            return bytes(record)
        root=48*512
        records=b''.join(lfn_record(i|(0x40 if i==len(parts) else 0),parts[i-1]) for i in range(len(parts),0,-1))
        records+=fat_short('README  TXT',0x20,3,5)
        records+=fat_short('DOCS       ',0x10,4)
        raw[root:root+len(records)]=records
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'lfn.raw';src.write_bytes(raw)
            idx=scan_tree(str(src))
            self.assertEqual({e.name for e in idx.list_dir(5)},{name,'DOCS'})

    def test_ext2_ext3_classification(self):
        for fs, journal in [('ext2',False),('ext3',True)]:
            raw=bytearray(ext4_img())
            superblock=1024
            struct.pack_into('<I',raw,superblock+96,0)  # no ext4-only incompatible features
            struct.pack_into('<I',raw,superblock+92,4 if journal else 0)
            # extents still exist in the synthetic inode, but classification uses superblock.
            with tempfile.TemporaryDirectory() as d:
                src=Path(d)/'volume.raw';src.write_bytes(raw)
                idx=scan_tree(str(src))
                self.assertEqual(idx.filesystem,fs)
                result=analyze_image(str(src))
                self.assertEqual(result.partitions[0].filesystem,fs)

    def test_garbage_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'bad.raw';src.write_bytes(bytes(64*1024))
            with self.assertRaises(FileSystemError):scan_tree(str(src))


if __name__=='__main__':unittest.main()
