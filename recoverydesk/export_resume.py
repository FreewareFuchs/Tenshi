"""Rebuild a saved export selection from metadata after explicit source consent.

No index cache, resident contents or profile history are written. The ordinary
batch signature, source checks and destination protections remain authoritative.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
from types import SimpleNamespace

from .batch_export import (MANIFEST, PLAN_LIMIT, _key, _selected_roots, _identity,
                           _digest, _task_desc, plan_selection, _is_unsafe_link)
from .sources import is_device_source, validate_source, ensure_safe_destination
from .ntfs_browser import scan_ntfs_tree, ScanCancelled
from .filesystems import scan_tree, ScanCancelled as OtherScanCancelled
from .export_target import TargetReviewDeclined
from .signature_search import FILESYSTEM as SIGNATURE_FS,scan_signatures

MAX_STATUS_BYTES = 64*1024*1024
FILESYSTEMS = {'NTFS','FAT32','exFAT','ext2','ext3','ext4','Btrfs','XFS',SIGNATURE_FS}


class ExportResumeError(ValueError):
    pass


def _require(condition):
    if not condition:raise ValueError('Invalid export request')


@dataclass(frozen=True)
class SavedExport:
    root: str
    identity: dict
    signature: str
    keys: tuple[str, ...]
    limit: int
    tolerant: bool

    @property
    def source(self): return self.identity['source']


def resume_metadata(index, selection):
    """Store selected roots and parser options, never cached file contents."""
    total=int(getattr(index,'total_records',0))
    scanned=int(getattr(index,'scanned_records',0))
    limit=scanned if hasattr(index,'info') and 0<scanned<total else 0
    return dict(schema=1,selected=[_key(e) for e in _selected_roots(index,selection)],
                scan=dict(max_records=limit,tolerant=bool(getattr(index,'tolerant',False))))


def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ExportResumeError('Ungültiger Exportauftrag.')
        result[key]=value
    return result


def _read_status(path):
    # No media or source path is opened here. Reject FIFOs before reading,
    # including a replacement between lstat and open; never execute metadata.
    for parent in (path,*path.parents):
        if _is_unsafe_link(parent):raise ExportResumeError('Exportauftrag darf nicht über einen symbolischen Link geöffnet werden.')
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode):raise ExportResumeError('Exportauftrag muss eine reguläre Statusdatei sein.')
    if before.st_size>MAX_STATUS_BYTES:raise ExportResumeError('Export-Statusdatei ist zu groß. Bitte den bisherigen manuellen Wiederaufnahmeweg verwenden.')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    try:
        opened=os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):
            raise ExportResumeError('Export-Statusdatei wurde während des Öffnens geändert.')
        with os.fdopen(fd,'rb') as stream:
            fd=-1
            raw=stream.read(MAX_STATUS_BYTES+1)
            after=os.fstat(stream.fileno())
        if len(raw)>MAX_STATUS_BYTES:raise ExportResumeError('Export-Statusdatei ist zu groß. Bitte den bisherigen manuellen Wiederaufnahmeweg verwenden.')
        if (after.st_size,after.st_mtime_ns)!=(opened.st_size,opened.st_mtime_ns):
            raise ExportResumeError('Export-Statusdatei wurde während des Öffnens geändert.')
    finally:
        if fd>=0:os.close(fd)
    try:return json.loads(raw,object_pairs_hook=_pairs)
    except (UnicodeError,ValueError,RecursionError) as exc:
        raise ExportResumeError('Ungültiger Exportauftrag.') from exc


def read_saved_export(filename):
    """Read the user-selected status file only. Do not inspect its source."""
    path=Path(os.path.abspath(filename));root=path.parent
    if path.name!=MANIFEST:raise ExportResumeError('Bitte recoverydesk_status.json aus dem bisherigen Exportordner auswählen.')
    try:data=_read_status(path)
    except FileNotFoundError as exc:
        raise ExportResumeError('Im gewählten Ordner ist kein gespeicherter Exportauftrag vorhanden. Bitte den erzeugten Export-Unterordner wählen.') from exc
    try:
        _require(isinstance(data,dict) and type(data['schema']) is int and data['schema']==1)
        signature=data['signature']
        _require(isinstance(signature,str) and re.fullmatch('[0-9a-f]{64}',signature))
        _require(root.name in ('Tenshi_Export_'+signature[:16],'RecoveryDesk_Export_'+signature[:16]))
        identity=data['identity'];_require(isinstance(identity,dict))
        source=identity['source']
        _require(isinstance(source,str) and 0<len(source)<=32768 and '\0' not in source and os.path.isabs(source))
        _require(identity['filesystem'] in FILESYSTEMS)
        if identity['filesystem']==SIGNATURE_FS:
            _require(not is_device_source(source) and identity['offset']==0)
        _require(type(identity['size']) is int and identity['size']>=512)
        _require(type(identity['offset']) is int and 0<=identity['offset']<identity['size'] and identity['offset']%512==0)
        if is_device_source(source):_require(isinstance(identity['device_snapshot'],dict))
        else:
            _require(type(identity['modified_ns']) is int)
            _require(re.fullmatch('[0-9a-f]{64}',identity['header_sha256']))
        _require(isinstance(data['results'],dict))
        _require(all(isinstance(k,str) and isinstance(v,dict) for k,v in data['results'].items()))
    except (KeyError,TypeError,ValueError) as exc:
        raise ExportResumeError('Ungültiger Exportauftrag.') from exc
    request=data.get('resume_request')
    if request is None:
        raise ExportResumeError('Dieser Export enthält noch keine gespeicherte Auswahl. Bitte dieselbe Quelle, Auswahl und den ursprünglichen Zielordner manuell wählen.')
    try:
        _require(isinstance(request,dict) and type(request['schema']) is int and request['schema']==1)
        keys=request['selected'];_require(isinstance(keys,list) and 0<len(keys)<=PLAN_LIMIT)
        _require(all(isinstance(k,str) and re.fullmatch(r'-?[0-9]{1,20}:[0-9]{1,10}',k) for k in keys))
        _require(len(set(keys))==len(keys))
        scan=request['scan'];limit=scan['max_records'];tolerant=scan['tolerant']
        _require(type(limit) is int and 0<=limit<=30_000_000 and type(tolerant) is bool)
        _require(identity['filesystem']=='NTFS' or limit==0)
        _require(not (tolerant and is_device_source(source)))
    except (KeyError,TypeError,ValueError) as exc:
        raise ExportResumeError('Ungültige gespeicherte Exportauswahl.') from exc
    return SavedExport(str(root),identity,signature,tuple(keys),limit,tolerant)


def prepare_saved_export(saved, *, cancel=None, progress=None):
    """After consent, read metadata again and verify the exact original plan."""
    def stop():
        if cancel and cancel():raise TargetReviewDeclined()
    stop()
    source=validate_source(saved.source)
    if not is_device_source(source) and not stat.S_ISREG(os.stat(source).st_mode):
        raise ExportResumeError('Die gespeicherte Quelle ist keine reguläre Image-Datei.')
    identity=saved.identity
    stub=SimpleNamespace(filesystem=identity['filesystem'],offset=identity['offset'])
    if _identity(source,stub)!=identity:
        raise ExportResumeError('Die gespeicherte Quelle wurde geändert oder ausgetauscht. Bitte Quelle und Exportauftrag prüfen.')
    # Check the destination before a potentially long scan. This does not create it.
    ensure_safe_destination(source,saved.root)
    try:
        if identity['filesystem']=='NTFS':
            index=scan_ntfs_tree(source,partition_offset=identity['offset'],max_records=saved.limit,
                tolerate_read_errors=saved.tolerant,cancel=cancel,progress=progress)
        elif identity['filesystem']==SIGNATURE_FS:
            index=scan_signatures(source,cancel=cancel,progress=progress)
        else:
            index=scan_tree(source,offset=identity['offset'],tolerate_read_errors=saved.tolerant,
                            cancel=cancel,progress=progress)
    except (ScanCancelled,OtherScanCancelled) as exc:
        raise TargetReviewDeclined() from exc
    stop()
    if is_device_source(source):index._device_identity=identity['device_snapshot']
    if _identity(source,index)!=identity:
        raise ExportResumeError('Die gespeicherte Quelle wurde geändert oder ausgetauscht. Bitte Quelle und Exportauftrag prüfen.')
    by_key={_key(e):e for e in index.entries}
    try:selection=tuple(by_key[k] for k in saved.keys)
    except KeyError as exc:raise ExportResumeError('Die gespeicherte Auswahl ist nicht mehr vollständig vorhanden. Der Export wurde nicht fortgesetzt.') from exc
    plan=plan_selection(index,selection)
    actual=_digest(dict(identity=identity,tasks=[_task_desc(item) for item in plan]))
    if actual!=saved.signature:
        raise ExportResumeError('Der gespeicherte Exportplan passt nicht mehr zur Quelle. Der Export wurde nicht fortgesetzt.')
    stop()
    return dict(source=source,index=index,selection=selection,target=str(Path(saved.root).parent),root=saved.root)
