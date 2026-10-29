"""Durable export checksum files; only remove outputs recorded as our own."""
import hashlib
import os
import re
from pathlib import Path

from .secure_target import open_regular_output, mkdir_checked, remove_owned_output

INDIVIDUAL='Pruefsummen_Einzeln'
SUMMARY='SHA256SUMS.sha256'


class ChecksumCheckpointError(OSError):
    """A lost export checkpoint is fatal, unlike optional checksum metadata."""


def checksum_line(relative, digest):
    # Export paths are sanitized, but reject unsafe checksum input independently.
    path=Path(relative)
    if (path.is_absolute() or '..' in path.parts or '\\' in relative or
            any(c in relative for c in '\r\n\0') or not re.fullmatch('[0-9a-f]{64}',digest)):
        raise ValueError('Ungültiger Prüfsummeneintrag.')
    return f'{digest}  files/{relative}\n'.encode('utf-8')


class ExportChecksums:
    def __init__(self,root,source,state,persist):
        self.root=Path(root);self.source=source;self.state=state;self.persist=persist
        self.summary_verified=False
        self.outputs=state.setdefault('checksum_outputs',{})
        if not isinstance(self.outputs,dict):raise ValueError('Ungültiger Prüfsummenstatus.')

    def _write(self,relative,payload):
        path=self.root/relative
        # Summaries may contain hundreds of thousands of paths. Generate lines
        # twice rather than materializing the whole checksum list in memory.
        chunks=payload if callable(payload) else lambda:(payload,)
        digest=hashlib.sha256();size=0
        for chunk in chunks():digest.update(chunk);size+=len(chunk)
        expected=digest.hexdigest()
        record=self.outputs.get(relative)
        if record is not None and (not isinstance(record,dict) or record.get('digest')!=expected):
            raise ValueError('Prüfsummendatei gehört zu anderen Daten und bleibt erhalten.')
        new=record is None or not os.path.lexists(path)
        identity=None if new else tuple(record.get('identity',()))
        if not new and (len(identity)!=2 or not all(isinstance(n,int) for n in identity)):
            raise ValueError('Prüfsummen-Dateikennung fehlt.')
        with open_regular_output(str(path),'xb' if new else 'r+b',self.source,
                                 expected_identity=identity) as stream:
            if new:
                meta=os.fstat(stream.fileno())
                record={'identity':[meta.st_dev,meta.st_ino],'digest':expected,'complete':False}
                self.outputs[relative]=record
                # Persist ownership before a write can fail; incomplete owned
                # metadata can be retried without touching an unrelated file.
                self.persist()
            if not record.get('complete'):
                if not new:
                    # An interrupted own write may contain a valid prefix.
                    # A user edit is not permission to overwrite the metadata.
                    for chunk in chunks():
                        prior=stream.read(len(chunk))
                        if prior!=chunk[:len(prior)]:
                            raise ValueError('Unvollständige Prüfsummendatei wurde verändert und bleibt erhalten.')
                        if len(prior)<len(chunk):break
                    if stream.read(1):
                        raise ValueError('Unvollständige Prüfsummendatei wurde verändert und bleibt erhalten.')
                stream.seek(0)
                for chunk in chunks():
                    remaining=memoryview(chunk)
                    while remaining:
                        count=stream.write(remaining)
                        if not count:raise OSError('Prüfsummendatei konnte nicht vollständig gespeichert werden.')
                        remaining=remaining[count:]
                stream.truncate(size);stream.flush();os.fsync(stream.fileno())
            stream.seek(0)
            checked=hashlib.sha256();read=0
            while read<=size:
                chunk=stream.read(min(1024*1024,size-read+1))
                if not chunk:break
                checked.update(chunk);read+=len(chunk)
            if read!=size or checked.hexdigest()!=expected:
                raise ValueError('Prüfsummendatei wurde verändert und bleibt erhalten.')
        if os.name!='nt':
            from .secure_target import secure_parent
            with secure_parent(str(path),self.source) as parent_fd:
                if parent_fd is not None:os.fsync(parent_fd)
        record['complete']=True
        self.persist()
        return path

    @staticmethod
    def name(number,relative):
        return f'{INDIVIDUAL}/{number:06d}_{Path(relative).name[:80]}.sha256'

    def save_file(self,number,relative,digest):
        folder=self.root/INDIVIDUAL
        if not folder.exists():mkdir_checked(str(folder),self.source)
        return self._write(self.name(number,relative),checksum_line(relative,digest))

    def finish(self,confirmed,cancel=None):
        """Save and verify the summary first; cleanup never globs user files."""
        if not confirmed or (cancel and cancel()):return ''
        payload=lambda:(checksum_line(relative,digest) for _,relative,digest in confirmed)
        result=str(self._write(SUMMARY,payload))
        self.summary_verified=True
        try:
            for number,relative,digest in confirmed:
                if cancel and cancel():break
                name=self.name(number,relative)
                record=self.outputs.get(name)
                if record is None:continue
                try:
                    remove_owned_output(str(self.root/name),self.source,tuple(record['identity']),
                                        checksum_line(relative,digest))
                except FileNotFoundError:
                    pass
                self.outputs.pop(name)
        finally:
            # Missing owned files are safe to recreate exclusively on resume;
            # do not rewrite a potentially large manifest after every unlink.
            self.persist()
        return result
