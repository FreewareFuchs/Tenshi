from pathlib import Path
from contextlib import contextmanager
import tempfile
import unittest
from unittest.mock import patch
from recoverydesk.imaging_blocks import ImagingBlocks
from recoverydesk.imaging import ImagingProgress,create_image


class ImagingBlockTests(unittest.TestCase):
    def test_committed_defects_are_emitted_once_and_survive_resume(self):
        from test_imaging import BadSectorFile
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';data=b'A'*(2*1024*1024);source.write_bytes(data)
            dest=Path(temp)/'image';events=[]
            @contextmanager
            def reader(_):yield BadSectorFile(data,4096,8192)
            with patch('recoverydesk.imaging.open_source',reader):
                paused=create_image(str(source),str(dest),progress=events.append,
                    verify=False,cancel=lambda:bool(events and events[-1].processed>=1024*1024))
            self.assertEqual(paused['state'],'paused')
            self.assertEqual([r for event in events for r in event.bad_ranges],[(4096,4096)])
            events.clear()
            final=create_image(str(source),str(dest),resume=True,progress=events.append,verify=False)
            self.assertEqual(events[0].bad_ranges,((4096,4096),))
            b=ImagingBlocks()
            for event in events:b.handle(event)
            self.assertEqual(b.mapped_bad,4096)
            self.assertEqual(sum(b.bad),409600)
            self.assertIn('error',b.cell_states())
            self.assertNotEqual(final['verification']['status'],'verified')
            self.assertEqual(dest.read_bytes()[4096:8192],bytes(4096))
            self.assertEqual(source.read_bytes(),data)

    def test_precise_ranges_and_no_verification_reset(self):
        b=ImagingBlocks()
        b.handle(ImagingProgress(50,100,1,1,'running',((23,1),)))
        self.assertEqual(b.cell_states().count('confirmed'),49)
        self.assertEqual(b.cell_states()[23],'error')
        self.assertEqual(b.cell_states().count('pending'),50)
        b.handle(ImagingProgress(100,100,1,1,'complete'))
        self.assertEqual(b.cell_states().count('confirmed'),99)
        self.assertEqual(b.cell_states()[23],'error')
        self.assertEqual(len(b.bad),100)

    def test_large_offsets_are_exact_and_missing_map_is_not_green(self):
        total=2**60+9;b=ImagingBlocks()
        offset=total//2
        b.handle(ImagingProgress(total,total,1,1,'complete',((offset,1),)))
        self.assertIn('error',b.cell_states())
        self.assertEqual(sum(b.bad),100)
        unknown=ImagingBlocks()
        unknown.handle(ImagingProgress(50,100,1,1,'running'))
        self.assertNotIn('confirmed',unknown.cell_states())
        self.assertEqual(unknown.cell_states().count('unconfirmed'),50)

    def test_partial_cell_is_not_claimed_complete(self):
        b=ImagingBlocks();b.handle(ImagingProgress(1,300,0,0,'running'))
        self.assertEqual(b.cell_states()[0],'mixed')
        self.assertNotIn('confirmed',b.cell_states())

    def test_tampered_resume_never_publishes_a_saved_map(self):
        from recoverydesk.imaging import ImagingError
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.write_bytes(b'A'*(2*1024*1024))
            dest=Path(temp)/'image';events=[]
            create_image(str(source),str(dest),progress=events.append,
                         cancel=lambda:bool(events and events[-1].processed>=1024*1024))
            with dest.open('r+b') as output:output.write(b'X')
            events.clear()
            with self.assertRaises(ImagingError):
                create_image(str(source),str(dest),resume=True,progress=events.append)
            self.assertEqual(events,[])

    def test_actual_copy_and_resume_map_need_no_additional_source_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.write_bytes(bytes(range(256))*8192)
            dest=Path(temp)/'image';events=[]
            first=create_image(str(source),str(dest),progress=events.append,
                               block_size=1024*1024,verify=False,
                               cancel=lambda:bool(events and events[-1].processed>=1024*1024))
            self.assertEqual(first['state'],'paused')
            events.clear()
            final=create_image(str(source),str(dest),resume=True,progress=events.append,verify=True)
            b=ImagingBlocks()
            for event in events:b.handle(event)
            self.assertEqual(events[0].processed,1024*1024)
            self.assertEqual(set(b.cell_states()),{'confirmed'})
            self.assertEqual(final['verification']['status'],'verified')
            self.assertEqual(source.read_bytes(),dest.read_bytes())
