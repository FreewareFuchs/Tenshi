"""Read-only bounded input and cancellable, isolated content decoders."""
from __future__ import annotations
import ctypes
import base64
from ctypes import wintypes
import json
import os
from pathlib import Path
import signal
import struct
import stat
import subprocess
import sys
import time

from .content_worker import MAX_INPUT, content_kind, result
from .sources import open_source
from .device_identity import check_device_identity
from .ntfs import iter_stream


class ContentCancelled(Exception):
    pass


def _stop(cancel):
    if cancel and cancel():
        raise ContentCancelled('Prüfung abgebrochen.')


def read_file(source, index, entry, filesystem, *, limit=MAX_INPUT, cancel=None, opener=None):
    """Read at most limit logical bytes, honoring initialized NTFS sizes."""
    _stop(cancel)
    if entry.is_directory or not entry.recoverable or type(entry.size) is not int or entry.size < 0:
        raise ValueError('Kein unterstützter Dateidatenstrom vorhanden.')
    if type(limit) is not int or not 0 < limit <= MAX_INPUT:
        raise ValueError('Ungültige Lesegrenze.')
    expected = min(entry.size, limit)
    identity = getattr(index, '_device_identity', None)
    check_device_identity(source, identity)
    output = bytearray()
    def collect(chunks):
        for block in chunks:
            _stop(cancel)
            if not isinstance(block, (bytes, bytearray, memoryview)) or len(block) > expected - len(output):
                raise ValueError('Dateidatenstrom überschreitet die Lesegrenze.')
            output.extend(block)
    with (opener or open_source)(source) as stream:
        if filesystem == 'NTFS':
            if entry.data_kind == 'resident':
                if entry.resident_data is None or len(entry.resident_data) != entry.size:
                    raise ValueError('Inkonsistenter residenter NTFS-Datenstrom.')
                collect((entry.resident_data[:expected],))
            elif entry.data_kind == 'nonresident':
                if not 0 <= entry.initialized_size <= entry.size:
                    raise ValueError('Ungültige NTFS-Größe des initialisierten Datenbereichs.')
                initialized = min(entry.initialized_size, expected)
                collect(iter_stream(stream, index.info, entry.data_runs, 0, initialized))
                if len(output) != initialized:
                    raise ValueError('Dateidatenstrom unvollständig.')
                while len(output) < expected:
                    collect((bytes(min(64 * 1024, expected - len(output))),))
            else:
                raise ValueError('Nicht unterstützter NTFS-Datenstrom.')
        else:
            collect(index.volumes.iter_file(stream, entry, max_bytes=expected))
    _stop(cancel)
    check_device_identity(source, identity)
    if len(output) != expected:
        raise ValueError('Dateidatenstrom unvollständig.')
    return bytes(output)


class _WindowsJob:
    """Memory bound and kill-on-close for the decoder and its process tree."""
    def __init__(self, process):
        class BASIC(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
                        ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),
                        ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),
                        ('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name,ctypes.c_ulonglong) for name in ('ReadOperationCount','WriteOperationCount',
                'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class EXTENDED(ctypes.Structure):
            _fields_ = [('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),
                        ('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),
                        ('PeakJobMemoryUsed',ctypes.c_size_t)]
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype=wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.kernel.CreateJobObjectW(None,None)
        if not self.handle:
            raise OSError('Decoder process limits unavailable')
        limits=EXTENDED();limits.BasicLimitInformation.LimitFlags=0x2000|0x200
        limits.JobMemoryLimit=768 * 1024**2
        if not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not self.kernel.AssignProcessToJobObject(self.handle,int(process._handle)):
            self.close();raise OSError('Decoder process limits unavailable')
    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle);self.handle=None


def analyze(data, filename='', *, preview=False, cancel=None, timeout=15):
    _stop(cancel)
    if len(data) > MAX_INPUT:
        return result('limited', '', 'input_limit')
    extension = Path(filename).suffix.lower()[:16]
    command = ([sys.executable] if getattr(sys,'frozen',False) else
               [sys.executable,str(Path(__file__).resolve().parent.parent/'main.py')])
    command += ['--content-worker','preview' if preview else 'check',extension or '-']
    options = dict(stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    if os.name=='nt':
        options['creationflags']=subprocess.CREATE_NO_WINDOW
    else:
        options['start_new_session']=True
    process=subprocess.Popen(command,**options)
    job=None
    def kill():
        if os.name=='nt':
            if job:job.close()
            try:process.kill()
            except OSError:pass
        else:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
    try:
        if os.name=='nt':job=_WindowsJob(process)
        end=time.monotonic()+timeout
        payload=data
        while True:
            _stop(cancel)
            if time.monotonic()>=end:
                return result('limited','','processing_limit')
            try:
                output,_=process.communicate(input=payload,timeout=.1)
                break
            except subprocess.TimeoutExpired:
                payload=None
        if process.returncode or len(output)>4 * 1024 * 1024:
            return result('limited','','decoder_stopped')
        answer=json.loads(output)
        if (not isinstance(answer,dict) or answer.get('status') not in
                ('checked','partial','unreadable','limited','unsupported','encrypted') or
                not isinstance(answer.get('image'),str) or not isinstance(answer.get('text'),str)):
            raise ValueError('Invalid content decoder result')
        if answer.get('code') not in MESSAGES or not isinstance(answer.get('values'),dict) or len(answer['text'])>32768:
            raise ValueError('Invalid content decoder result')
        if answer['image']:
            image=base64.b64decode(answer['image'],validate=True)
            if len(image)>2*1024*1024 or len(image)<33 or image[:8]!=b'\x89PNG\r\n\x1a\n' or image[12:16]!=b'IHDR':
                raise ValueError('Invalid preview image')
            width,height=struct.unpack('>II',image[16:24])
            if not 0<width<=720 or not 0<height<=360:
                raise ValueError('Preview image exceeds display limits')
        return answer
    finally:
        if process.poll() is None:kill()
        process.communicate()
        if job:job.close()


def check_file(source,index,entry,filesystem,*,preview=False,cancel=None):
    _stop(cancel)
    if entry.size > MAX_INPUT:
        return result('limited','','input_limit')
    data=read_file(source,index,entry,filesystem,cancel=cancel)
    return analyze(data,entry.name,preview=preview,cancel=cancel)


def check_path(filename, *, cancel=None):
    """Check a chosen exported regular file without changing it or its report."""
    _stop(cancel)
    path=Path(filename)
    before=path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ValueError('Bitte eine reguläre Datei ohne symbolische Verknüpfung wählen.')
    if before.st_size>MAX_INPUT:
        return result('limited','','input_limit')
    descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(descriptor,'rb') as stream:
        opened=os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):
            raise ValueError('Datei wurde während der Prüfung geändert.')
        data=bytearray()
        while len(data)<=MAX_INPUT:
            _stop(cancel)
            block=stream.read(min(64*1024,MAX_INPUT+1-len(data)))
            if not block:break
            data.extend(block)
        after=os.fstat(stream.fileno())
    if (opened.st_size,opened.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or len(data)!=opened.st_size:
        raise ValueError('Datei wurde während der Prüfung geändert.')
    return analyze(bytes(data),path.name,cancel=cancel)


STATUS = {
    'checked':'Struktur lesbar', 'partial':'Teilprüfung',
    'unreadable':'Nicht als unterstütztes Format lesbar', 'limited':'Prüfgrenze erreicht',
    'unsupported':'Nicht geprüft', 'encrypted':'Verschlüsselt / geschützt',
}
MESSAGES = {
    'image_decoded':'Bilddaten dekodiert: {width} × {height} Pixel.',
    'image_first_frame':'Erstes Bild dekodiert: {width} × {height} Pixel. Weitere Animationsbilder sind nicht geprüft.',
    'pdf_first_page':'PDF mit {pages} Seiten erkannt. Nur die erste Seite wurde gerendert; weitere Seiten, Anhänge und aktive Inhalte sind nicht geprüft.',
    'office_container':'Office-Paket mit {members} Einträgen: ZIP-Prüfsummen und XML-Struktur lesbar. Darstellung, eingebettete Dateien und Makros sind nicht inhaltlich geprüft.',
    'pdf_encrypted':'Das PDF benötigt ein Passwort oder erlaubt keine Vorschau. Es wurde nicht entschlüsselt.',
    'office_encrypted':'Das Office-Paket ist geschützt. Es wurde nicht entschlüsselt.',
    'office_ole':'OLE-/geschützter Office-Container. Alte Office-Formate und verschlüsselte Office-Dateien werden hier nicht geprüft.',
    'input_limit':'Die Inhaltsprüfung und erweiterte Vorschau sind auf 32 MiB pro Datei begrenzt.',
    'processing_limit':'Zeit-, Speicher- oder Formatgrenze erreicht. Daraus folgt keine Beschädigung der Datei.',
    'decoder_stopped':'Die getrennte Verarbeitung wurde beendet. Eine Beurteilung des Dateiinhalts ist nicht möglich.',
    'parse_failed':'Die Daten lassen sich nicht als unterstütztes Format lesen. Eine Beschädigung oder ein abweichender Dateityp ist möglich.',
    'dependency_missing':'Eine benötigte Komponente für dieses Format fehlt.',
    'zip_scope':'Für ZIP-Archive steht die ZIP-Prüfung im Exportbericht zur Verfügung.',
    'unsupported':'Für diesen Dateityp ist keine Inhaltsprüfung verfügbar.',
}
CONTENT_SCOPE='Die Prüfung bewertet lesbare Strukturen und Darstellbarkeit. Sie bestätigt weder vollständige Originalinhalte noch die Rettbarkeit gelöschter Daten. Links, Makros und Dokumentaktionen werden nicht ausgeführt.'


def describe_result(answer, language='de'):
    from .i18n import translate
    status=translate(STATUS[answer['status']],language)
    message=translate(MESSAGES.get(answer.get('code'),MESSAGES['unsupported']),language).format(**answer.get('values',{}))
    return status+' · '+(answer.get('format') or '—')+'\n'+message+'\n\n'+translate(CONTENT_SCOPE,language)
