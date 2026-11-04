"""Persistent search progress, revalidated hits, source safety and interrupted blocks."""
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from recoverydesk import signature_search as search
from recoverydesk.signature_checkpoint import read_checkpoint, checkpoint_digest, MAX_BYTES
from recoverydesk.filesystems import ScanCancelled
from test_signature_search import picture


class SignatureCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'test.img'
        self.checkpoint = self.root / 'test.tenshi-search.json'
        data = bytearray(b'X' * (3*1024**2))
        for offset, kind in ((512,'PNG'), (1024**2-3,'PNG'), (2*1024**2+100,'JPEG')):
            payload = picture(kind)
            data[offset:offset+len(payload)] = payload
        self.source.write_bytes(data)

    def pause(self):
        stopped = []
        with self.assertRaises(ScanCancelled):
            search.scan_signatures(str(self.source), categories=('images','archives'),
                max_file_bytes=64*1024**2, checkpoint_path=str(self.checkpoint),
                progress=lambda done,total: stopped.append(done), cancel=lambda: bool(stopped))
        return read_checkpoint(self.checkpoint)

    def test_restart_revalidates_hits_and_keeps_boundary_signatures(self):
        before = self.source.read_bytes()
        state = self.pause()
        self.assertEqual(state['position'], 1024**2)
        self.assertEqual(len(state['hits']), 1)
        child_checkpoint = self.root / 'restart.tenshi-search.json'
        child_checkpoint.write_bytes(self.checkpoint.read_bytes())
        script = 'from recoverydesk.signature_search import scan_signatures; import sys; i=scan_signatures(sys.argv[1],checkpoint_path=sys.argv[2],resume=True); print(len(i.entries))'
        child = subprocess.run([sys.executable,'-c',script,str(self.source),str(child_checkpoint)],
                               cwd=Path(__file__).parent.parent,capture_output=True,text=True,timeout=30,check=True)
        self.assertEqual(child.stdout.strip(), '3')
        progress = []
        result = search.scan_signatures(str(self.source), checkpoint_path=str(self.checkpoint), resume=True,
                                       progress=lambda done,total: progress.append(done))
        full = search.scan_signatures(str(self.source), categories=('images','archives'),max_file_bytes=64*1024**2)
        self.assertEqual([(e.name,e.size) for e in result.entries],[(e.name,e.size) for e in full.entries])
        self.assertEqual(len(result.entries), 3)
        self.assertEqual(progress[0], 1024**2)
        self.assertEqual(result.signature_file_limit, 64*1024**2)
        self.assertEqual(result.signature_categories, ('images','archives'))
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(read_checkpoint(self.checkpoint)['position'], self.source.stat().st_size)

    @unittest.skipUnless(sys.platform.startswith('linux'),'Linux shared directory sync')
    def test_save_and_reopen_on_shared_folder_without_directory_fsync(self):
        import errno,stat
        real_sync=os.fsync
        def sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError(errno.EINVAL,'Directory sync unsupported')
            real_sync(fd)
        with patch('recoverydesk.secure_target.os.fsync',side_effect=sync):
            first=search.scan_signatures(str(self.source),checkpoint_path=self.checkpoint)
            again=search.scan_signatures(str(self.source),checkpoint_path=self.checkpoint,resume=True)
        self.assertEqual([e.name for e in first.entries],[e.name for e in again.entries])
        self.assertEqual(len(again.entries),3)

    def test_partial_block_is_repeated_after_cancellation(self):
        checks = []
        def cancel():
            checks.append(1)
            return len(checks) > 4
        with self.assertRaises(ScanCancelled):
            search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),cancel=cancel)
        self.assertEqual(read_checkpoint(self.checkpoint)['position'], 0)
        result = search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),resume=True)
        self.assertEqual(len(result.entries), 3)

    def test_changed_source_and_forged_hit_extent_are_rejected(self):
        self.pause()
        original = self.checkpoint.read_bytes()
        data = json.loads(original)
        data['hits'][0][1] += 1
        data['checksum'] = checkpoint_digest(data)
        self.checkpoint.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'bestätigt'):
            search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),resume=True)
        self.checkpoint.write_bytes(original)
        meta = self.source.stat()
        os.utime(self.source, ns=(meta.st_atime_ns,meta.st_mtime_ns+1_000_000_000))
        with self.assertRaises(ValueError):
            search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),resume=True)
        self.assertEqual(self.checkpoint.read_bytes(), original)

    def test_invalid_metadata_rejected_without_opening_source(self):
        state = self.pause()
        for options in ({'categories':('audio',)}, {'max_file_bytes':32*1024**2}):
            with self.assertRaisesRegex(ValueError,'Sucheinstellungen'):
                search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),resume=True,**options)
        for key, value in (('position',1),('inspection',-1),('file_limit',True),('categories',[]),('last',2**60)):
            altered = dict(state); altered[key] = value
            self.checkpoint.write_text(json.dumps(altered),encoding='utf-8')
            with patch.object(search,'open_source',side_effect=AssertionError('source read')):
                with self.assertRaises(ValueError):read_checkpoint(self.checkpoint)
        self.checkpoint.write_bytes(b'x' * (MAX_BYTES+1))
        with self.assertRaises(ValueError):read_checkpoint(self.checkpoint)

    def test_source_cannot_be_used_as_checkpoint(self):
        before = self.source.read_bytes()
        with self.assertRaises(ValueError):
            search.scan_signatures(str(self.source),checkpoint_path=str(self.source))
        self.assertEqual(self.source.read_bytes(), before)
        try:
            os.link(self.source,self.checkpoint)
        except OSError:
            return
        with self.assertRaises(ValueError):
            search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint))
        self.assertEqual(self.source.read_bytes(), before)

    def test_failed_checkpoint_replace_preserves_previous_state(self):
        self.pause()
        before = self.checkpoint.read_bytes()
        from recoverydesk import signature_checkpoint as module
        target = 'atomic_json_checkpoint' if sys.platform.startswith('linux') else 'atomic_replace_json'
        with patch.object(module,target,side_effect=OSError('target full')):
            with self.assertRaises(OSError):
                search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),resume=True)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_exhausted_limits_cannot_be_reset_by_resuming(self):
        with patch.object(search,'MAX_HITS',1):
            result=search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint))
        self.assertFalse(result.signature_complete)
        with self.assertRaisesRegex(ValueError,'Prüfgrenze'):
            search.scan_signatures(str(self.source),checkpoint_path=str(self.checkpoint),resume=True)


if __name__ == '__main__':
    unittest.main()
