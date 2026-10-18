"""Hand-constructed XFS and Btrfs metadata fixtures; no physical disk writes."""
import os
import struct
import tempfile
import unittest
from pathlib import Path

from recoverydesk.filesystems import scan_tree, export_selection, FileSystemError
from recoverydesk.partition_scan import analyze_image


def xfs_img(offset=0):
    raw = bytearray(offset + 1024*4096)
    sb = bytearray(512)
    sb[:4]=b'XFSB'
    struct.pack_into('>I',sb,4,4096)
    struct.pack_into('>Q',sb,8,1024)
    struct.pack_into('>Q',sb,56,160)
    struct.pack_into('>I',sb,84,1024)
    struct.pack_into('>I',sb,88,1)
    struct.pack_into('>H',sb,100,5)
    struct.pack_into('>H',sb,102,512)
    struct.pack_into('>H',sb,104,512)
    struct.pack_into('>H',sb,106,8)
    sb[120]=12;sb[122]=9;sb[123]=3;sb[124]=10
    raw[offset:offset+512]=sb

    def dirent(name,ino,typ):
        name=name.encode()
        return bytes((len(name),)) + b'\x00\x20' + name + bytes((typ,)) + struct.pack('>I',ino)

    def inode(number,mode,fmt,size,data=b'',extents=0):
        block=number//8
        pos=offset+block*4096+(number%8)*512
        record=bytearray(512)
        record[:2]=b'IN'
        struct.pack_into('>H',record,2,mode)
        record[4]=3;record[5]=fmt
        struct.pack_into('>Q',record,56,size)
        struct.pack_into('>I',record,76,extents)
        record[176:176+len(data)]=data
        raw[pos:pos+512]=record

    def extent(logical,block,count):
        value=(logical<<73)|(block<<21)|count
        return value.to_bytes(16,'big')

    root = bytes((2,0)) + struct.pack('>I',160) + dirent('hello.any',168,1) + dirent('folder',176,2)
    nested = bytes((1,0)) + struct.pack('>I',160) + dirent('inner.txt',184,1)
    inode(160,0x41ed,1,len(root),root)
    inode(168,0x81a4,2,5,extent(0,30,1),1)
    inode(176,0x41ed,1,len(nested),nested)
    inode(184,0x81a4,2,6,extent(0,31,1),1)
    raw[offset+30*4096:offset+30*4096+5]=b'HELLO'
    raw[offset+31*4096:offset+31*4096+6]=b'INSIDE'
    return bytes(raw)


def btrfs_img(offset=0, dup=False, subvolume=False):
    n=4096
    total=2*1024*1024
    raw=bytearray(offset+total)
    sb=bytearray(4096)
    sb[0x40:0x48]=b'_BHRfS_M'
    struct.pack_into('<Q',sb,0x30,65536)
    struct.pack_into('<Q',sb,0x50,327680)
    struct.pack_into('<Q',sb,0x58,262144)
    struct.pack_into('<Q',sb,0x70,total)
    struct.pack_into('<Q',sb,0x88,1)
    struct.pack_into('<I',sb,0x90,n)
    struct.pack_into('<I',sb,0x94,n)
    # system mapping: logical 0..total, single physical stripe offset 0
    stripe=struct.pack('<QQ',1,0)+bytes(16)
    stripes=stripe+(struct.pack('<QQ',1,1024*1024)+bytes(16) if dup else b'')
    chunk=(struct.pack('<QBQ',256,228,0)+
           struct.pack('<QQQQIIIHH',total,2,65536,2|0x20 if dup else 2,4096,4096,4096,2 if dup else 1,1)+
           stripes)
    struct.pack_into('<I',sb,0xa0,len(chunk))
    sb[0x32b:0x32b+len(chunk)]=chunk
    raw[offset+65536:offset+65536+4096]=sb

    def tree(block_addr,items):
        items=sorted(items,key=lambda item:item[0])
        b=bytearray(n)
        struct.pack_into('<Q',b,48,block_addr)
        struct.pack_into('<I',b,96,len(items))
        b[100]=0
        p=n
        for i,(key,data) in enumerate(items):
            p-=len(data)
            b[p:p+len(data)]=data
            o=101+i*25
            struct.pack_into('<QBQII',b,o,key[0],key[1],key[2],p-101,len(data))
        assert p>=101+25*len(items)
        raw[offset+block_addr:offset+block_addr+n]=b

    inode=lambda size,mode: struct.pack('<QQQ',1,1,size)+bytes(28)+struct.pack('<I',mode)+bytes(104)
    def diridx(target,name,kind):
        name=name.encode()
        return struct.pack('<QBQ',target,1,0)+struct.pack('<QHHB',1,0,len(name),kind)+name
    def inline(data):
        return struct.pack('<QQBBHB',1,len(data),0,0,0,0)+data
    def regular(block,size):
        return struct.pack('<QQBBHBQQQQ',1,size,0,0,0,1,block,size,0,size)
    tree(262144,[])
    root = bytearray(240)
    struct.pack_into('<Q',root,176,393216)
    root_items=[((5,132,0),bytes(root))]
    if subvolume:
        subroot=bytearray(240)
        struct.pack_into('<Q',subroot,176,458752)
        root_items.append(((256,132,0),bytes(subroot)))
    tree(327680,root_items)
    fs_items=[
       ((256,1,0),inode(0,0x41ed)),
       ((256,96,2),diridx(257,'folder',2)),
       ((256,96,3),diridx(258,'hello.any',1)),
       ((257,1,0),inode(0,0x41ed)),
       ((257,96,2),diridx(259,'inside',1)),
       ((258,1,0),inode(5,0x81a4)),
       ((258,108,0),inline(b'HELLO')),
       ((259,1,0),inode(6,0x81a4)),
       ((259,108,0),regular(524288,6)),
    ]
    if subvolume:
        fs_items.append(((256,96,4),struct.pack('<QBQ',256,132,0)+struct.pack('<QHHB',1,0,5,2)+b'@home'))
        tree(458752,[
            ((256,1,0),inode(0,0x41ed)),
            ((256,96,2),diridx(260,'notes',1)),
            ((260,1,0),inode(7,0x81a4)),
            ((260,108,0),inline(b'SUBVOL!')),
        ])
    tree(393216,fs_items)
    raw[offset+524288:offset+524288+6]=b'INSIDE'
    return bytes(raw)


class LinuxAdvancedTests(unittest.TestCase):
    def exercise(self, image, filesystem, file_name, folder_name, nested_name, data1, data2, offset=0):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'disk.raw';src.write_bytes(image)
            report=analyze_image(str(src))
            self.assertIn(filesystem, [p.filesystem for p in report.partitions])
            tree=scan_tree(str(src), offset)
            self.assertEqual(tree.filesystem,filesystem)
            top=tree.list_dir(5)
            self.assertEqual({e.name for e in top}, {file_name,folder_name})
            folder=next(e for e in top if e.name==folder_name)
            self.assertEqual([e.name for e in tree.list_dir(folder.record_number)],[nested_name])
            out=Path(d)/'out';out.mkdir()
            result=export_selection(str(src),tree,top,str(out))
            self.assertEqual((result.exported,result.directories,result.skipped),(2,1,0),result.errors)
            self.assertEqual((out/file_name).read_bytes(),data1)
            self.assertEqual((out/folder_name/nested_name).read_bytes(),data2)
            self.assertEqual(src.read_bytes(),image)

    def test_xfs_metadata_and_export(self):
        self.exercise(xfs_img(),'XFS','hello.any','folder','inner.txt',b'HELLO',b'INSIDE')

    def test_btrfs_metadata_and_export(self):
        self.exercise(btrfs_img(),'Btrfs','hello.any','folder','inside',b'HELLO',b'INSIDE')

    def test_nonzero_partition_offset(self):
        self.exercise(xfs_img(4096),'XFS','hello.any','folder','inner.txt',b'HELLO',b'INSIDE',4096)
        self.exercise(btrfs_img(4096),'Btrfs','hello.any','folder','inside',b'HELLO',b'INSIDE',4096)

    def test_xfs_block_directory(self):
        raw=bytearray(xfs_img())
        # Switch root directory from shortform to one extent-based XDB3 block.
        root=20*4096
        raw[root+5]=2
        struct.pack_into('>Q',raw,root+56,4096)
        struct.pack_into('>I',raw,root+76,1)
        rec=((40<<21)|1).to_bytes(16,'big')
        raw[root+176:root+192]=rec
        block=bytearray(4096)
        block[:4]=b'XDB3'
        position=64
        for name, ino, typ in (('hello.any',168,1),('folder',176,2)):
            encoded=name.encode()
            record_size=((8+1+len(encoded)+1+2+7)//8)*8
            struct.pack_into('>Q',block,position,ino)
            block[position+8]=len(encoded)
            block[position+9:position+9+len(encoded)]=encoded
            block[position+9+len(encoded)]=typ
            struct.pack_into('>H',block,position+record_size-2,position)
            position+=record_size
        raw[40*4096:41*4096]=block
        self.exercise(bytes(raw),'XFS','hello.any','folder','inner.txt',b'HELLO',b'INSIDE')

    def test_xfs_damage_is_visible_as_unrecoverable(self):
        raw=bytearray(xfs_img())
        raw[21*4096:21*4096+2]=b'NO'  # damage hello.any inode
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'corrupt.raw';src.write_bytes(raw)
            tree=scan_tree(str(src))
            target=next(e for e in tree.list_dir(5) if e.name=='hello.any')
            self.assertFalse(target.recoverable)
            self.assertIn('beschädigt',target.unsupported_reason)

    def test_btrfs_dup_chunk_and_subvolume(self):
        raw=btrfs_img(dup=True,subvolume=True)
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'dup.raw';src.write_bytes(raw)
            index=scan_tree(str(src))
            names={e.name for e in index.list_dir(5)}
            self.assertEqual(names,{'folder','hello.any','@home'})
            home=next(e for e in index.list_dir(5) if e.name=='@home')
            children=index.list_dir(home.record_number)
            self.assertEqual([e.name for e in children],['notes'])
            out=Path(d)/'out';out.mkdir()
            result=export_selection(str(src),index,[home],str(out))
            self.assertEqual((result.exported,result.skipped),(1,0),result.errors)
            self.assertEqual((out/'@home'/'notes').read_bytes(),b'SUBVOL!')

    def test_btrfs_rejects_multidevice(self):
        blob=bytearray(btrfs_img())
        struct.pack_into('<Q',blob,65536+0x88,2)
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'multi.raw';src.write_bytes(blob)
            report=analyze_image(str(src))
            self.assertEqual(report.partitions[0].filesystem,'Btrfs')
            with self.assertRaisesRegex(FileSystemError,'mehreren Geräten'):
                scan_tree(str(src))

if __name__ == '__main__':unittest.main()

@unittest.skipUnless(os.environ.get('DISPLAY'), 'Display fuer GUI-Integration erforderlich')
class GUIAdvancedTests(unittest.TestCase):
    def test_gui_trees_btrfs_xfs(self):
        from recoverydesk.gui import RecoveryDeskApp
        with tempfile.TemporaryDirectory() as d:
            for label,raw in (('XFS',xfs_img()), ('Btrfs',btrfs_img(subvolume=True))):
                src=Path(d)/(label+'.raw');src.write_bytes(raw)
                idx=scan_tree(str(src))
                app=RecoveryDeskApp();app.withdraw()
                try:
                    app._set_browser_fs(label)
                    app._show_browser_index(str(src),idx)
                    self.assertTrue(app.folder_tree.exists('root'))
                    names={app.file_tree.item(e,'text') for e in app.file_tree.get_children()}
                    self.assertTrue(any('hello.any' in n for n in names),names)
                    self.assertTrue(any('folder' in n for n in names),names)
                finally:
                    app.destroy()
