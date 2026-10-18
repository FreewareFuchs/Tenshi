"""Bounded, non-executable analysis-session persistence (Tenshi 2.6.0).

Only regular read-only image files are eligible. A sampled fingerprint plus
strict size/mtime checks detect common source changes; samples are NOT a
cryptographic attestation of every byte of a large image. Session files are
untrusted and never unpickled or executed. Export safety checks remain active.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import os
import stat
import zipfile

from .sources import is_device_source, open_source
from .partition_scan import AnalysisReport, Partition
from .ntfs import NTFSInfo, DataRun, parse_boot_sector
from .ntfs_browser import FileEntry, FileIndex
from .filesystems import GenericEntry, GenericIndex, detect_volume

FORMAT = 'tenshi-analysis-session'
VERSION = 1
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 96 * 1024 * 1024
MAX_ENTRIES = 3_000_000
MAX_NAME = 4096
MAX_RESIDENT_BYTES = 16 * 1024 * 1024
SAMPLE_BYTES = 65536


class SessionError(ValueError):
    """Invalid, outdated, or unverifiable analysis session."""


@dataclass
class RestoredSession:
    source: str
    report: AnalysisReport | None
    index: FileIndex | GenericIndex | None
    filesystem: str | None
    offset: int
    fingerprint: dict


def _plain_image(path: str) -> tuple[str, os.stat_result]:
    if is_device_source(path):
        raise SessionError('Sitzungen können nur für reguläre Image-Dateien gespeichert und geladen werden. '
                           'Für physische Datenträger bitte ein Image erstellen.')
    absolute = os.path.abspath(path)
    try:
        info = os.stat(absolute)
    except OSError as exc:
        raise SessionError('Das Quell-Image ist nicht erreichbar.') from exc
    if not stat.S_ISREG(info.st_mode) or info.st_size < 512:
        raise SessionError('Die Datenquelle muss eine reguläre Image-Datei sein.')
    return absolute, info


def fingerprint_image(path: str, offsets=()) -> dict:
    """Sample the beginning/end and spaced regions, plus observed boot offsets.

    Restoring also requires unchanged mtime for the original path; a moved image
    can be explicitly selected if its sampled contents and size still match.
    """
    source, st = _plain_image(path)
    length = st.st_size
    locations = {0, max(0, length - SAMPLE_BYTES)}
    locations.update(max(0, min(length - SAMPLE_BYTES, length * n // 8)) for n in range(1, 8))
    for offset in offsets:
        if not isinstance(offset, int) or offset < 0 or offset >= length:
            raise SessionError('Partitionsoffset außerhalb des Images.')
        locations.add(offset)
    hashes = []
    try:
        with open_source(source) as f:
            for offset in sorted(locations):
                f.seek(offset)
                data = f.read(min(SAMPLE_BYTES, length - offset))
                if len(data) != min(SAMPLE_BYTES, length - offset):
                    raise SessionError('Das Quell-Image konnte nicht vollständig geprüft werden.')
                hashes.append([offset, hashlib.sha256(data).hexdigest()])
        after = os.stat(source)
    except OSError as exc:
        raise SessionError('Das Quell-Image konnte nicht gelesen werden.') from exc
    if (after.st_size, after.st_mtime_ns) != (st.st_size, st.st_mtime_ns):
        raise SessionError('Das Quell-Image wurde während der Prüfung verändert.')
    return {'size': length, 'mtime_ns': st.st_mtime_ns, 'samples': hashes}


def check_fingerprint(source: str, saved: dict, *, original: str | None = None) -> dict:
    if not isinstance(saved, dict) or not isinstance(saved.get('samples'), list):
        raise SessionError('Ungültiger Quellenfingerabdruck in der Sitzung.')
    points = saved['samples']
    if len(points) < 2 or len(points) > 80:
        raise SessionError('Ungültige Prüfpunkte in der Sitzung.')
    offsets = []
    for point in points:
        if (not isinstance(point, list) or len(point) != 2 or
            type(point[0]) is not int or point[0] < 0 or
            not isinstance(point[1], str) or len(point[1]) != 64):
            raise SessionError('Ungültige Prüfpunkte in der Sitzung.')
        offsets.append(point[0])
    actual = fingerprint_image(source, offsets)
    if actual['size'] != saved.get('size'):
        raise SessionError('Die Größe des Quell-Images stimmt nicht mit der Sitzung überein.')
    if (original is not None and os.path.normcase(os.path.abspath(source)) ==
            os.path.normcase(os.path.abspath(original)) and
            actual['mtime_ns'] != saved.get('mtime_ns')):
        raise SessionError('Das Quell-Image wurde seit dem Speichern geändert. Bitte neu analysieren.')
    actual_map = {o: h for o, h in actual['samples']}
    if any(actual_map.get(offset) != digest for offset, digest in points):
        raise SessionError('Die Inhaltsprüfung des Quell-Images ist fehlgeschlagen. Bitte neu analysieren.')
    return actual


def _entry_map(entries: list, children: dict) -> dict:
    reference = {id(e): i for i, e in enumerate(entries)}
    return {str(parent): [reference[id(entry)] for entry in values]
            for parent, values in children.items()}


def _encode_index(index) -> dict:
    if len(index.entries) > MAX_ENTRIES:
        raise SessionError('Zu viele Einträge für eine Sitzung.')
    if isinstance(index, FileIndex):
        entries = []
        for entry in index.entries:
            d = asdict(entry)
            data = d.pop('resident_data')
            if data is not None and len(data) > MAX_RESIDENT_BYTES:
                raise SessionError('Zu viele residente Dateidaten für eine Sitzung.')
            d['resident_data_b64'] = base64.b64encode(data).decode('ascii') if data is not None else None
            entries.append(d)
        props = {f.name: getattr(index, f.name) for f in fields(FileIndex)
                 if f.name not in ('info', 'entries', 'by_record', 'children')}
        return {'type': 'ntfs', 'info': asdict(index.info), 'entries': entries,
                'children': _entry_map(index.entries, index.children), 'properties': props}
    if isinstance(index, GenericIndex):
        props = {f.name: getattr(index, f.name) for f in fields(GenericIndex)
                 if f.name not in ('filesystem', 'offset', 'entries', 'volumes', 'children')}
        return {'type': 'generic', 'filesystem': index.filesystem, 'offset': index.offset,
                'entries': [asdict(e) for e in index.entries],
                'children': _entry_map(index.entries, index.children), 'properties': props}
    raise SessionError('Unbekannter Dateisystemindex.')


def _bounded_integer(value, name: str, *, negative=False) -> int:
    if type(value) is not int or not (-1 if negative else 0) <= value <= (1 << 64):
        raise SessionError(f'Ungültiges Feld: {name}')
    return value


def _encode_json(obj) -> bytes:
    try:
        data = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError) as exc:
        raise SessionError('Die Sitzung enthält nicht serialisierbare Metadaten.') from exc
    if len(data) > MAX_FILE_BYTES:
        raise SessionError('Die Sitzung überschreitet das sichere Größenlimit.')
    return data


def _source_offsets(report, index) -> list[int]:
    offsets = [p.offset_bytes for p in report.partitions] if report else []
    if index is not None:
        offsets.append(index.info.partition_offset if isinstance(index, FileIndex) else index.offset)
    return offsets


def save_session(destination: str, source: str, report=None, index=None,
                 filesystem: str | None = None, *, expected_fingerprint=None) -> None:
    """Atomically create a new session; never overwrite or write to source."""
    if report is None and index is None:
        raise SessionError('Bitte zunächst eine Partition oder ein Dateisystem analysieren.')
    source, _ = _plain_image(source)
    dest = os.path.abspath(destination)
    if os.path.normcase(dest) == os.path.normcase(source):
        raise SessionError('Sitzungsdatei und Quell-Image dürfen nicht identisch sein.')
    # Also reuse existing physical-destination safety rules.
    from .sources import ensure_safe_destination
    ensure_safe_destination(source, dest)
    if os.path.lexists(dest):
        raise FileExistsError('Die Sitzungsdatei existiert bereits. Bitte einen neuen Namen wählen.')
    offsets = _source_offsets(report, index)
    fingerprint = fingerprint_image(source, offsets)
    if expected_fingerprint is not None:
        check_fingerprint(source, expected_fingerprint, original=source)
    if report and report.image_size != fingerprint['size']:
        raise SessionError('Die Partitionsanalyse passt nicht mehr zur Image-Größe.')
    payload = {
        'report': asdict(report) if report else None,
        'index': _encode_index(index) if index is not None else None,
        'filesystem': (filesystem or ('NTFS' if isinstance(index, FileIndex) else index.filesystem)) if index is not None else None,
        'offset': index.info.partition_offset if isinstance(index, FileIndex) else (index.offset if index else 0),
    }
    raw = _encode_json(payload)
    manifest = _encode_json({'format': FORMAT, 'version': VERSION, 'source': source,
                            'fingerprint': fingerprint, 'sha256': hashlib.sha256(raw).hexdigest()})
    # Use exclusive creation to avoid replacing existing unrelated data. If an
    # error occurs, delete only the file this invocation created.
    created = False
    try:
        with open(dest, 'xb') as output:
            created = True
            with zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=6, allowZip64=True) as archive:
                archive.writestr('manifest.json', manifest)
                archive.writestr('analysis.json', raw)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        if created:
            try:
                os.unlink(dest)
            except OSError:
                pass
        raise


def _strict_json(raw: bytes):
    def no_duplicates(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise SessionError('Doppelte Schlüssel in einer Sitzungsdatei.')
            obj[key] = value
        return obj
    try:
        return json.loads(raw, object_pairs_hook=no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(SessionError('Ungültige Zahl')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise SessionError('Beschädigte oder ungültige Sitzungsdaten.') from exc


def _read_session(filename: str) -> tuple[dict, dict]:
    try:
        if os.path.getsize(filename) > MAX_ARCHIVE_BYTES:
            raise SessionError('Sitzungsdatei ist zu groß.')
        with zipfile.ZipFile(filename, 'r') as zf:
            if sorted(zf.namelist()) != ['analysis.json', 'manifest.json']:
                raise SessionError('Unbekannte Dateien in der Sitzung.')
            def take(name):
                info = zf.getinfo(name)
                if info.file_size > MAX_FILE_BYTES or info.compress_size > MAX_ARCHIVE_BYTES:
                    raise SessionError('Sitzungsdaten sind zu groß.')
                with zf.open(name) as stream:
                    raw = stream.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES:
                    raise SessionError('Sitzungsdaten sind zu groß.')
                return raw
            manifest_raw = take('manifest.json')
            raw = take('analysis.json')
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, EOFError) as exc:
        raise SessionError('Sitzungsdatei ist nicht lesbar oder beschädigt.') from exc
    manifest = _strict_json(manifest_raw)
    if not isinstance(manifest, dict) or manifest.get('format') != FORMAT or manifest.get('version') != VERSION:
        raise SessionError('Unbekannte oder nicht unterstützte Sitzungsversion.')
    if not isinstance(manifest.get('source'), str) or not manifest.get('source'):
        raise SessionError('Quellenangabe in Sitzung fehlt.')
    if hashlib.sha256(raw).hexdigest() != manifest.get('sha256'):
        raise SessionError('Sitzungsdaten wurden verändert oder beschädigt.')
    payload = _strict_json(raw)
    if not isinstance(payload, dict):
        raise SessionError('Ungültige Sitzungsdaten.')
    return manifest, payload


def _decode_report(raw, image_size: int):
    if raw is None:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get('partitions'), list):
        raise SessionError('Ungültige gespeicherte Partitionsanalyse.')
    if len(raw['partitions']) > 100_000 or raw.get('image_size') != image_size:
        raise SessionError('Gespeicherte Partitionsanalyse passt nicht zum Image.')
    parts = []
    allowed = {f.name for f in fields(Partition)}
    for p in raw['partitions']:
        if not isinstance(p, dict) or set(p) != allowed:
            raise SessionError('Ungültiger Partitionseintrag.')
        part = Partition(**p)
        if (type(part.start_lba) is not int or type(part.sectors) is not int or
            part.start_lba < 0 or part.sectors < 0 or
            part.sector_size not in (512, 4096) or part.offset_bytes > image_size or
            part.size_bytes > image_size - part.offset_bytes):
            raise SessionError('Partitionsbereich außerhalb der geprüften Quelle.')
        parts.append(part)
    fields_allowed = {f.name for f in fields(AnalysisReport)}
    if set(raw) != fields_allowed:
        raise SessionError('Ungültiger Partitionsbericht.')
    return AnalysisReport(partitions=parts, **{k: v for k, v in raw.items() if k != 'partitions'})


def _decode_locator(value, depth=0):
    if depth > 8 or not isinstance(value, (list, tuple)) or len(value) > 100_000:
        raise SessionError('Ungültiger Dateisystem-Locator.')
    result = []
    for element in value:
        if isinstance(element, list):
            result.append(_decode_locator(element, depth + 1))
        elif type(element) in (int, bool) or element is None:
            result.append(element)
        else:
            raise SessionError('Ungültiger Dateisystem-Locator.')
    return tuple(result)


def _decode_index(raw: dict, source: str):
    if raw is None:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get('entries'), list):
        raise SessionError('Ungültiger Dateisystemindex.')
    rows = raw['entries']
    if len(rows) > MAX_ENTRIES:
        raise SessionError('Zu viele Einträge in der Sitzungsdatei.')
    kind = raw.get('type')
    props = raw.get('properties')
    if not isinstance(props, dict):
        raise SessionError('Ungültige Indexeigenschaften.')
    entries = []
    if kind == 'ntfs':
        info_raw = raw.get('info')
        if not isinstance(info_raw, dict) or set(info_raw) != {f.name for f in fields(NTFSInfo)}:
            raise SessionError('Ungültige NTFS-Geometrie.')
        info = NTFSInfo(**info_raw)
        with open_source(source) as stream:
            actual = parse_boot_sector(stream, info.partition_offset)
        if actual != info:
            raise SessionError('Die gespeicherte NTFS-Geometrie stimmt nicht mehr mit der Quelle überein.')
        allowed = {f.name for f in fields(FileEntry)} - {'resident_data'}
        for d in rows:
            if not isinstance(d, dict) or set(d) != allowed | {'resident_data_b64'}:
                raise SessionError('Ungültiger NTFS-Dateieintrag.')
            data = d['resident_data_b64']
            if data is not None:
                if not isinstance(data, str) or len(data) > (MAX_RESIDENT_BYTES * 4 // 3 + 10):
                    raise SessionError('Zu große residente Daten.')
                try:
                    data = base64.b64decode(data, validate=True)
                except (ValueError, base64.binascii.Error) as exc:
                    raise SessionError('Ungültige residente Daten.') from exc
            if not isinstance(d.get('data_runs'), list) or len(d['data_runs']) > 1_000_000:
                raise SessionError('Ungültige NTFS-Datenläufe.')
            runs = []
            total_clusters = info.total_sectors // info.sectors_per_cluster
            running_clusters = 0
            for run in d['data_runs']:
                if (not isinstance(run, dict) or set(run) != {'lcn', 'clusters'} or
                    (run['lcn'] is not None and type(run['lcn']) is not int) or
                    type(run['clusters']) is not int or run['clusters'] < 0):
                    raise SessionError('Ungültiger NTFS-Datenlauf.')
                if (run['clusters'] <= 0 or run['clusters'] > total_clusters or
                    (run['lcn'] is not None and
                     (run['lcn'] < 0 or run['lcn'] + run['clusters'] > total_clusters))):
                    raise SessionError('NTFS-Datenlauf außerhalb des Images.')
                running_clusters += run['clusters']
                if running_clusters > total_clusters:
                    raise SessionError('Unplausible NTFS-Datenlauf-Summe.')
                runs.append(DataRun(**run))
            entry = FileEntry(**{k: v for k, v in d.items() if k not in ('resident_data_b64', 'data_runs')},
                              resident_data=data, data_runs=runs)
            if not isinstance(entry.name, str) or len(entry.name) > MAX_NAME:
                raise SessionError('Ungültiger Dateiname in Sitzung.')
            if (type(entry.size) is not int or not 0 <= entry.size <= (1 << 44) or
                type(entry.initialized_size) is not int or not 0 <= entry.initialized_size <= entry.size or
                entry.data_kind not in ('none', 'resident', 'nonresident')):
                raise SessionError('Ungültige NTFS-Dateigröße oder Datenart.')
            if entry.data_kind == 'resident' and entry.resident_data is not None and len(entry.resident_data) != entry.size:
                raise SessionError('Inkonsistente residente Daten in der Sitzung.')
            if (entry.data_kind == 'nonresident' and entry.recoverable and
                running_clusters * info.cluster_size < entry.size):
                raise SessionError('Unvollständige NTFS-Datenläufe in der Sitzung.')
            entries.append(entry)
        permitted = {f.name for f in fields(FileIndex)} - {'info', 'entries', 'children', 'by_record'}
        if set(props) != permitted:
            raise SessionError('Ungültige NTFS-Indexfelder.')
        index = FileIndex(info, entries, **props)
        index.by_record = {}
        for entry in entries:
            index.by_record.setdefault(entry.record_number, entry)
    elif kind == 'generic':
        offset = _bounded_integer(raw.get('offset'), 'offset')
        with open_source(source) as stream:
            volume = detect_volume(stream, offset)
        if volume.label != raw.get('filesystem'):
            raise SessionError('Das gespeicherte Dateisystem passt nicht mehr zum Image.')
        allowed = {f.name for f in fields(GenericEntry)}
        for d in rows:
            if not isinstance(d, dict) or set(d) != allowed:
                raise SessionError('Ungültiger Dateisystemeintrag.')
            d = dict(d)
            d['locator'] = _decode_locator(d['locator'])
            entry = GenericEntry(**d)
            if not isinstance(entry.name, str) or len(entry.name) > MAX_NAME:
                raise SessionError('Ungültiger Dateiname in Sitzung.')
            if (type(entry.size) is not int or not 0 <= entry.size <= (1 << 44) or
                type(entry.record_number) is not int or entry.record_number < 0 or
                type(entry.parent_record) is not int or entry.parent_record < -1):
                raise SessionError('Ungültige Dateisystem-Metadaten in Sitzung.')
            entries.append(entry)
        permitted = {f.name for f in fields(GenericIndex)} - {'filesystem', 'offset', 'entries', 'volumes', 'children'}
        if set(props) != permitted:
            raise SessionError('Ungültige Dateisystem-Indexfelder.')
        index = GenericIndex(volume.label, offset, entries, volume, **props)
    else:
        raise SessionError('Unbekannter Dateisystem-Indextyp.')
    mapping = raw.get('children')
    if not isinstance(mapping, dict) or len(mapping) > len(entries) + 10:
        raise SessionError('Ungültige Ordnerstruktur.')
    children = {}
    total = 0
    for key, indices in mapping.items():
        try:
            parent = int(key)
        except (TypeError, ValueError) as exc:
            raise SessionError('Ungültiger Ordnerverweis.') from exc
        if not isinstance(indices, list):
            raise SessionError('Ungültige Ordnerliste.')
        total += len(indices)
        if total > len(entries) + 100:
            raise SessionError('Zu viele Verknüpfungen im Ordnerbaum.')
        group = []
        for n in indices:
            if type(n) is not int or n < 0 or n >= len(entries):
                raise SessionError('Ungültiger Eintragsverweis im Ordnerbaum.')
            group.append(entries[n])
        children[parent] = group
    index.children = children
    return index


def load_session(filename: str, *, source_override: str | None = None) -> RestoredSession:
    """Verify the source BEFORE producing any usable cached index/partition data."""
    manifest, payload = _read_session(filename)
    source = source_override if source_override is not None else manifest['source']
    source, _ = _plain_image(source)
    verified = check_fingerprint(source, manifest['fingerprint'], original=manifest['source'])
    report = _decode_report(payload.get('report'), verified['size'])
    index = _decode_index(payload.get('index'), source)
    if report is None and index is None:
        raise SessionError('Sitzung enthält keine Analyseergebnisse.')
    if index is not None:
        offset = index.info.partition_offset if isinstance(index, FileIndex) else index.offset
        if offset != payload.get('offset'):
            raise SessionError('Ungültiger gespeicherter Partitionsoffset.')
        fs = 'NTFS' if isinstance(index, FileIndex) else index.filesystem
        if payload.get('filesystem') != fs:
            raise SessionError('Gespeichertes Dateisystem ist inkonsistent.')
    else:
        offset, fs = 0, None
    # Reject a source that changed during the deserialization / boot checks.
    check_fingerprint(source, manifest['fingerprint'], original=manifest['source'])
    return RestoredSession(source, report, index, fs, offset, verified)
