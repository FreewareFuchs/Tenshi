"""Completed copies may be verified again only with a recorded stream digest."""
from contextlib import contextmanager
import hashlib
import json
import os
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk import batch_export
from recoverydesk.batch_export import export_batch, _hash_file
from recoverydesk.export_io import ExportCancelled, write_chunks
import test_export_interruptions as fixtures


class PendingVerificationTests(unittest.TestCase):
    def fixture(self, root, ntfs):
        return fixtures.ExportInterruptionTests().fixture(root, ntfs)

    def stop_after_copy(self, fixture):
        src,index,entry,target,_,_=fixture
        with patch.object(batch_export, '_hash_file', side_effect=ExportCancelled()):
            result=export_batch(str(src),index,[entry],str(target))
        self.assertTrue(result.cancelled)
        return result

    def run_again(self, f):
        return export_batch(str(f[0]),f[1],[f[2]],str(f[3]))

    def test_read_only_retry_and_second_cancel_preserve_checkpoint(self):
        for ntfs in (True,False):
            with self.subTest(ntfs=ntfs), tempfile.TemporaryDirectory() as tmp:
                f=self.fixture(Path(tmp),ntfs);source_before=f[0].read_bytes()
                first=self.stop_after_copy(f)
                path=Path(first.root)/'files'/f[4]
                metadata=path.stat();before=json.loads(Path(first.manifest).read_text())['results']
                with patch.object(batch_export,'_hash_file',side_effect=ExportCancelled()):
                    again=self.run_again(f)
                self.assertTrue(again.cancelled)
                self.assertEqual(json.loads(Path(first.manifest).read_text())['results'],before)
                with patch.object(batch_export,'export_ntfs_file') as n, patch.object(batch_export,'export_other_file') as g:
                    success=self.run_again(f)
                    n.assert_not_called();g.assert_not_called()
                self.assertEqual((success.exported,success.verified_existing,success.failed),(0,1,0))
                self.assertEqual((path.stat().st_ino,path.stat().st_mtime_ns),(metadata.st_ino,metadata.st_mtime_ns))
                self.assertEqual(path.read_bytes(),f[5]);self.assertEqual(f[0].read_bytes(),source_before)
                record=json.loads(Path(first.manifest).read_text())['results'][f[4]]
                self.assertEqual(record['sha256'],hashlib.sha256(f[5]).hexdigest())
                self.assertNotIn('verification_pending',record)

    def test_same_size_corruption_is_rejected_and_never_adopted(self):
        for ntfs in (True,False):
            with self.subTest(ntfs=ntfs),tempfile.TemporaryDirectory() as tmp:
                f=self.fixture(Path(tmp),ntfs);first=self.stop_after_copy(f)
                path=Path(first.root)/'files'/f[4];path.write_bytes(b'WRONG')
                result=self.run_again(f)
                self.assertEqual(result.failed,1);self.assertEqual(result.verified_existing,0)
                self.assertEqual(path.read_bytes(),b'WRONG')
                record=json.loads(Path(first.manifest).read_text())['results'][f[4]]
                self.assertEqual(record['copied_sha256'],hashlib.sha256(f[5]).hexdigest())
                self.assertNotIn('sha256',record)
                path.write_bytes(f[5])
                self.assertEqual(self.run_again(f).verified_existing,1)

    def test_old_cancelled_record_without_digest_stays_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp),True);first=self.stop_after_copy(f)
            p=Path(first.manifest);state=json.loads(p.read_text());record=state['results'][f[4]]
            record.pop('copied_sha256');record.pop('verification_pending')
            p.write_text(json.dumps(state))
            self.assertEqual(self.run_again(f).failed,1)

    def test_pending_marker_requires_exact_machine_readable_fields(self):
        valid={'verification_pending':True,'status':'Abgebrochen','bytes':5,
               'copied_sha256':hashlib.sha256(b'HELLO').hexdigest()}
        self.assertTrue(batch_export._pending_copy(valid,5))
        for changes in [{'verification_pending':1},{'status':'Erfolgreich'},
                        {'bytes':True},{'bytes':4},{'copied_sha256':'not-a-hash'},
                        {'copied_sha256':None}]:
            with self.subTest(changes=changes):
                self.assertFalse(batch_export._pending_copy({**valid,**changes},5))

    def test_source_changed_since_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp),False);first=self.stop_after_copy(f)
            f[0].write_bytes(f[0].read_bytes()+b'changed')
            # A different identity gets a different export root, never adopts the old file.
            self.assertNotEqual(self.run_again(f).root,first.root)

    def test_silent_write_corruption_does_not_receive_success(self):
        import recoverydesk.filesystems as fs
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp),False);real_open=fs.open_regular_output
            @contextmanager
            def corrupt(*args,**kwargs):
                with real_open(*args,**kwargs) as out:
                    class Writer:
                        def write(self,data):return out.write(b'X'*len(data))
                        def flush(self):out.flush()
                        def fileno(self):return out.fileno()
                    yield Writer()
            with patch.object(fs,'open_regular_output',side_effect=corrupt):
                result=self.run_again(f)
            self.assertEqual(result.failed,1);self.assertEqual(result.exported,0)
            self.assertIn('kopierten Daten',Path(result.log).read_text())

    def test_hash_rejects_file_modified_during_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'file';p.write_bytes(b'original')
            def mutate(count):
                if count:
                    old=p.stat()
                    p.write_bytes(b'tampered')
                    os.utime(p,ns=(old.st_atime_ns,old.st_mtime_ns+2_000_000_000))
            with self.assertRaisesRegex(OSError,'geändert'):
                _hash_file(p,progress=mutate)

    def test_handle_and_path_timestamps_need_not_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'file';p.write_bytes(b'unchanged')
            real_fstat=os.fstat
            def shifted(fd):
                meta=real_fstat(fd)
                values={key:getattr(meta,key) for key in
                        ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns')}
                values['st_mtime_ns']-=500
                values['st_ctime_ns']+=12345
                return SimpleNamespace(**values)
            with patch('recoverydesk.batch_export.os.fstat',side_effect=shifted):
                self.assertEqual(_hash_file(p),hashlib.sha256(b'unchanged').hexdigest())

    def test_path_change_is_detected_even_if_handle_metadata_is_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'file';p.write_bytes(b'original')
            with p.open('rb') as stream:cached=os.fstat(stream.fileno())
            def mutate(count):
                if count:
                    p.write_bytes(b'tampered')
                    os.utime(p,ns=(cached.st_atime_ns,cached.st_mtime_ns+2_000_000_000))
            with patch('recoverydesk.batch_export.os.fstat',return_value=cached):
                with self.assertRaisesRegex(OSError,'geändert'):
                    _hash_file(p,progress=mutate)

    def test_stream_digest_handles_partial_writes(self):
        class ShortWriter:
            def __init__(self):self.data=bytearray()
            def write(self,piece):
                count=min(2,len(piece));self.data.extend(piece[:count]);return count
        out=ShortWriter();digest=hashlib.sha256()
        count=write_chunks(out,[b'hello',b'world'],data_digest=digest)
        self.assertEqual(count,10);self.assertEqual(out.data,b'helloworld')
        self.assertEqual(digest.hexdigest(),hashlib.sha256(out.data).hexdigest())


if __name__=='__main__':unittest.main()
