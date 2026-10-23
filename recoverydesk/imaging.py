"""Safe, resumable, read-only disk-to-image copier.

Source: an existing image or Windows raw disk/volume opened exclusively for reading.
Destination: a NEW regular file (never a block device), with a JSON checkpoint.

On unreadable regions, the copier substitutes zero bytes and records byte ranges;
zero substitution is *not* recovery of the original data.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
from hashlib import sha256
from pathlib import PureWindowsPath
import json
import os
import sys
import tempfile
import time
from typing import Callable

from .diagnostics import traced
from .sources import (validate_source, open_source, source_size, is_device_source,
                      physical_sector_size, ensure_safe_destination)
from .secure_target import open_regular_output, open_regular_input, atomic_json_checkpoint

FORMAT_VERSION = 1
DEFAULT_BLOCK_SIZE = 1024 * 1024
DEFAULT_FALLBACK_UNIT = 4096
MAX_READ_RETRIES = 3
MAX_RETRY_DELAY_MS = 2000
BAD_SECTOR_POLICIES = ("zero", "stop")


class ImagingError(Exception):
    """Source, destination or checkpoint is unsafe or inconsistent."""


class ImagingPaused(Exception):
    """A pause was requested while an uncommitted source block was being read."""


@dataclass(frozen=True)
class ImagingProgress:
    processed: int
    total: int
    unreadable_bytes: int
    bad_range_count: int
    state: str


def _real(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def sidecar_path(destination: str) -> str:
    return str(destination) + '.recovery.json'


def _source_identity(source: str, total: int, sector: int) -> dict:
    identity = {'path': _real(source) if not is_device_source(source) else (source.lower() if os.name == 'nt' else os.path.realpath(source)),
                'size': total, 'sector_size': sector,
                'device': bool(is_device_source(source))}
    if not is_device_source(source):
        st = os.stat(source)
        identity['mtime_ns'] = st.st_mtime_ns
        identity['inode'] = st.st_ino
    return identity


# A separate append-only checkpoint journal is used if Windows refuses to
# replace an existing .recovery.json (often a lock from antivirus/indexers).
# The original checkpoint is not modified in this fallback mode.
JOURNAL_INTERVAL = 16 * 1024 * 1024
MAX_JOURNAL_RECORD_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024 * 1024
REPLACE_RETRY_DELAYS = (0.04, 0.12, 0.30, 0.60)


def journal_path(manifest_path: str) -> str:
    return manifest_path + '.journal'


def _is_sharing_denial(exc: OSError) -> bool:
    return (getattr(exc, 'winerror', None) in (5, 32, 33) or
            isinstance(exc, PermissionError))


def _atomic_json(path: str, info: dict, *, source: str | None = None) -> None:
    if source is not None and sys.platform.startswith('linux'):
        atomic_json_checkpoint(path, info, source)
        return
    directory = os.path.dirname(os.path.abspath(path)) or '.'
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                         prefix='.recoverydesk-', suffix='.tmp', delete=False) as stream:
            name = stream.name
            json.dump(info, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        for attempt, delay in enumerate((*REPLACE_RETRY_DELAYS, None)):
            try:
                os.replace(name, path)
                name = None
                return
            except OSError as exc:
                if not _is_sharing_denial(exc) or delay is None:
                    raise
                time.sleep(delay)
    finally:
        if name and os.path.exists(name):
            # A virus scanner can transiently lock the temporary file too.
            try:
                os.unlink(name)
            except OSError:
                pass


def _journal_encoding(state: dict) -> bytes:
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
    record = {'checkpoint': state, 'sha256': sha256(payload).hexdigest()}
    return (json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def _read_journal(path: str, *, source: str | None = None) -> tuple[dict | None, int]:
    """Return the newest intact record and the end of its committed line.

    A final truncated line, e.g. after sudden power loss, is ignored. A
    malformed *complete* line is rejected rather than trusting older data.
    """
    if os.path.islink(path):
        raise ImagingError('Symbolische Links als Prüfpunkt-Journal werden nicht unterstützt.')
    if not os.path.exists(path):
        return None, 0
    last = None
    good_end = 0
    reader = open_regular_input(path, source) if source is not None else open(path, 'rb')
    with reader as f:
        while True:
            line = f.readline(MAX_JOURNAL_RECORD_BYTES + 1)
            if not line:
                break
            if len(line) > MAX_JOURNAL_RECORD_BYTES:
                raise ImagingError('Prüfpunkt-Journal enthält einen übergroßen Eintrag.')
            if not line.endswith(b'\n'):
                break  # torn trailing journal record, safe to ignore
            try:
                record = json.loads(line)
                state = record['checkpoint']
                if (not isinstance(state, dict) or
                        type(state.get('processed')) is not int or state['processed'] < 0):
                    raise ValueError('bad checkpoint')
                payload = json.dumps(state, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')
                if sha256(payload).hexdigest() != record['sha256']:
                    raise ValueError('bad checksum')
                if last is not None and state['processed'] < last['processed']:
                    raise ValueError('nonmonotonic checkpoint')
            except (ValueError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
                raise ImagingError('Prüfpunkt-Journal enthält einen beschädigten vollständigen Eintrag.') from exc
            last = state
            good_end = f.tell()
    return last, good_end


def _append_journal(path: str, state: dict, *,
                    previous: dict | None = None,
                    valid_end: int | None = None) -> int:
    if os.path.islink(path):
        raise ImagingError('Symbolische Links als Prüfpunkt-Journal werden nicht unterstützt.')
    try:
        if valid_end is None:
            previous, valid_end = _read_journal(path, source=state['source']['path'])
        if previous is not None:
            if previous.get('source') != state.get('source') or previous.get('destination') != state.get('destination'):
                raise ImagingError('Das Prüfpunkt-Journal gehört zu einer anderen Sicherung.')
            if previous.get('processed', -1) > state.get('processed', -1):
                raise ImagingError('Prüfpunkt-Journal liegt vor dem aktuellen Status.')
        data = _journal_encoding(state)
        # Correct a truncated final record before appending new records.
        if os.path.exists(path):
            with open_regular_output(path, 'r+b', state['source']['path']) as f:
                if os.fstat(f.fileno()).st_size < valid_end:
                    raise ImagingError('Prüfpunkt-Journal wurde extern verkürzt.')
                f.truncate(valid_end)
                f.seek(valid_end)
                _write_all(f, data)
                os.fsync(f.fileno())
        else:
            if valid_end:
                raise ImagingError('Prüfpunkt-Journal wurde während der Sicherung entfernt.')
            # Exclusive creation prevents overwriting a foreign file.
            with open_regular_output(path, 'xb', state['source']['path']) as f:
                _write_all(f, data)
                os.fsync(f.fileno())
        return valid_end + len(data)
    except OSError as exc:
        raise ImagingError(
            'Windows verweigert das Schreiben der Imaging-Prüfpunkte. '
            'Bitte Image und Statusdateien unverändert lassen und prüfen, ob '
            'der Zielordner beschreibbar ist, ein Virenschutz die Dateien sperrt '
            'oder der Ziel-Datenträger voll ist. Originaldaten wurden nicht beschrieben. '
            f'Technischer Fehler: {exc}') from exc


class _CheckpointWriter:
    """Replace checkpoints normally, switch to append-only journal on EACCES."""
    def __init__(self, path: str, source: str | None = None):
        self.source = source
        self.path = path
        self.journal = journal_path(path)
        self.use_journal = os.path.isfile(self.journal)
        # Cache the validated end offset so large disks do not reread a
        # growing journal on every checkpoint (which would be quadratic).
        self.journal_state, self.journal_end = (_read_journal(self.journal, source=self.source)
            if self.use_journal else (None, 0))
        self.last_saved = 0

    def save(self, state: dict) -> None:
        # In journal mode checkpoint at least every 16 MiB (or on pause/end).
        # Avoids a huge append-only log for very large disks.
        if (self.use_journal and state['state'] == 'running' and
                state['processed'] - self.last_saved < JOURNAL_INTERVAL):
            return
        if not self.use_journal:
            try:
                _atomic_json(self.path, state, source=self.source)
                self.last_saved = state['processed']
                return
            except OSError as exc:
                if not _is_sharing_denial(exc):
                    raise
                self.use_journal = True
        self.journal_end = _append_journal(self.journal, state,
            previous=self.journal_state, valid_end=self.journal_end)
        self.journal_state = state
        self.last_saved = state['processed']


def _append_bad(bad_ranges: list[list[int]], offset: int, length: int) -> None:
    if not length:
        return
    if bad_ranges and bad_ranges[-1][0] + bad_ranges[-1][1] == offset:
        bad_ranges[-1][1] += length
    else:
        bad_ranges.append([offset, length])


def _is_media_error(exc: OSError) -> bool:
    """Only confirmed device CRC/I/O errors justify a bad-sector decision."""
    win_code = getattr(exc, 'winerror', None)
    if win_code is not None:
        return win_code in (23, 1117)
    return getattr(exc, 'errno', None) == errno.EIO


def _recover_read(reader, offset: int, count: int, unit: int,
                  bad: list[list[int]], strict_short_read: bool = False, *,
                  read_retries: int = 0, retry_delay_ms: int = 0,
                  bad_sector_policy: str = 'zero',
                  cancel: Callable[[], bool] | None = None,
                  retry_counter: list[int] | None = None) -> bytes:
    """Isolate defective units; optionally re-read only the smallest failing unit.

    No extra retries occur for larger ranges: these are split immediately to
    avoid re-reading whole healthy regions. Access/connection errors are always
    fatal; only confirmed media errors may be retried or zero-filled. Cancellation
    never commits a partially assembled image block.
    """
    if count <= 0:
        return b''
    if cancel is not None and cancel():
        raise ImagingPaused()
    attempts = read_retries + 1 if count <= unit else 1
    for attempt in range(attempts):
        if cancel is not None and cancel():
            raise ImagingPaused()
        try:
            reader.seek(offset)
            raw = reader.read(count)
            if len(raw) == count:
                return raw
            if strict_short_read:
                raise ImagingError('Physischer Datenträger lieferte einen zu kurzen Block. '
                                   'Imaging abgebrochen; bitte Verbindung prüfen.')
            # A short read is not a confirmed sector failure; do not retry.
            break
        except OSError as exc:
            if not _is_media_error(exc):
                raise ImagingError('Quelllaufwerk ist nicht zuverlässig lesbar (Zugriff, '
                                   'Verbindung oder ungültiger Leseauftrag). Sicherung '
                                   'wurde angehalten; fehlende Daten werden NICHT '
                                   'stillschweigend mit Nullen ersetzt.') from exc
            if attempt + 1 < attempts:
                if retry_counter is not None:
                    retry_counter[0] += 1
                if retry_delay_ms:
                    # Split sleeps into slices so a pause request is responsive.
                    deadline = time.monotonic() + retry_delay_ms / 1000.0
                    while time.monotonic() < deadline:
                        if cancel is not None and cancel():
                            raise ImagingPaused()
                        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    if count <= unit:
        if bad_sector_policy == 'stop':
            raise ImagingError('Medien-Lesefehler bei Byteoffset '
                               f'{offset} (Länge {count}). Sicherung sicher angehalten; '
                               'der nicht bestätigte Block wurde nicht gespeichert.')
        _append_bad(bad, offset, count)
        return bytes(count)
    # Binary split into sector-aligned ranges; both children nonempty.
    left_len = (count // 2 // unit) * unit
    if left_len <= 0:
        left_len = unit
    if left_len >= count:
        left_len = count - unit
    if left_len <= 0:
        if bad_sector_policy == 'stop':
            raise ImagingError(f'Medien-Lesefehler bei Byteoffset {offset}; Sicherung angehalten.')
        _append_bad(bad, offset, count)
        return bytes(count)
    opts = dict(read_retries=read_retries, retry_delay_ms=retry_delay_ms,
                bad_sector_policy=bad_sector_policy, cancel=cancel,
                retry_counter=retry_counter)
    return (_recover_read(reader, offset, left_len, unit, bad, strict_short_read, **opts) +
            _recover_read(reader, offset + left_len, count - left_len, unit, bad,
                          strict_short_read, **opts))


def _write_all(out, data: bytes) -> None:
    """Handle partial unbuffered writes (e.g. low disk space) safely."""
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        written = out.write(view[offset:])
        if written is None or written <= 0:
            raise ImagingError('Zieldatenträger konnte nicht vollständig beschrieben werden.')
        offset += written


def _hash_region(handle, start: int, count: int) -> str:
    handle.seek(start)
    chunk = handle.read(count)
    if len(chunk) != count:
        raise ImagingError('Bereits gesicherter Image-Bereich ist unvollständig.')
    return sha256(chunk).hexdigest()



def _verify_full_copy(source: str, destination: str, identity: dict,
                      total: int, chunk_size: int,
                      expected_inode: tuple[int, int],
                      cancel: Callable[[], bool] | None,
                      progress: Callable[[ImagingProgress], None] | None,
                      state: dict, checkpoint_writer: _CheckpointWriter) -> bool:
    """Independently reread the source and image. Return False if cancelled.

    An unreadable source is not verified; the caller must avoid rereading
    known damaged devices unless verification was explicitly requested.
    A failed comparison persists a distinct failure state before raising.
    """
    state['state'] = 'verifying'
    state['verification'] = {'status': 'running', 'checked': 0}
    checkpoint_writer.save(state)
    if progress:
        progress(ImagingProgress(total, total, state['unreadable_bytes'],
                                 len(state['bad_ranges']), 'verifying'))

    checked = 0
    try:
        with open_source(source) as reader, open_regular_input(destination, source) as copied:
            opened = os.fstat(copied.fileno())
            if (opened.st_dev, opened.st_ino) != expected_inode:
                raise ImagingError('Image-Datei wurde vor der Integritätsprüfung ausgetauscht.')
            if opened.st_size != total:
                raise ImagingError('Image-Größe hat sich vor der Integritätsprüfung verändert.')
            while checked < total:
                if cancel is not None and cancel():
                    state['state'] = 'paused'
                    state['verification'] = {'status': 'interrupted', 'checked': checked}
                    checkpoint_writer.save(state)
                    if progress:
                        progress(ImagingProgress(total, total, state['unreadable_bytes'],
                                                 len(state['bad_ranges']), 'paused'))
                    return False
                n = min(chunk_size, total - checked)
                reader.seek(checked)
                copied.seek(checked)
                original = reader.read(n)
                image = copied.read(n)
                if len(original) != n or len(image) != n:
                    raise ImagingError('Integritätsprüfung: unvollständiger Leseblock bei Offset '
                                       f'{checked}. Image ist nicht verifiziert.')
                if original != image:
                    first = next(i for i, (a, b) in enumerate(zip(original, image)) if a != b)
                    raise ImagingError('INTEGRITÄTSFEHLER: Image weicht bei Byteoffset '
                                       f'{checked + first} von der Quelle ab. '
                                       'Image nicht als bitgenaue Sicherung verwenden.')
                checked += n
            if not is_device_source(source) and _source_identity(
                    source, total, identity['sector_size']) != identity:
                raise ImagingError('Quelldatei wurde während der Integritätsprüfung verändert.')
    except (OSError, ImagingError) as exc:
        state['state'] = 'integrity_failed'
        state['verification'] = {'status': 'failed', 'checked': checked, 'message': str(exc)}
        checkpoint_writer.save(state)
        if isinstance(exc, ImagingError):
            raise
        raise ImagingError('Integritätsprüfung konnte nicht abgeschlossen werden: '
                           f'{exc}. Image bleibt ungeprüft.') from exc
    state['verification'] = {'status': 'verified', 'checked': total}
    state['state'] = 'complete'
    checkpoint_writer.save(state)
    if progress:
        progress(ImagingProgress(total, total, state['unreadable_bytes'],
                                 len(state['bad_ranges']), 'complete'))
    return True


def _check_same_file(source: str, destination: str) -> None:
    if _real(source) == _real(destination):
        raise ImagingError('Quelldatei und Ziel dürfen niemals identisch sein.')
    if os.path.exists(destination):
        try:
            if not is_device_source(source) and os.path.samefile(source, destination):
                raise ImagingError('Quelle und Ziel zeigen auf dieselbe Datei.')
        except FileNotFoundError:
            pass


def _load_manifest(manifest_path: str, destination: str, source_identity: dict) -> dict:
    if os.path.islink(manifest_path) or os.path.islink(destination) or os.path.islink(journal_path(manifest_path)):
        raise ImagingError('Symbolische Links als Imaging-Ziele werden nicht unterstützt.')
    try:
        with open_regular_input(manifest_path, source_identity['path']) as f:
            payload = f.read(MAX_MANIFEST_BYTES + 1)
            if len(payload) > MAX_MANIFEST_BYTES:
                raise ImagingError('Statusdatei überschreitet die erlaubte Größe.')
            obj = json.loads(payload)
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        raise ImagingError('Statusdatei fehlt oder ist unlesbar; bestehende Images werden nicht überschrieben.') from exc
    candidate, _end = _read_journal(journal_path(manifest_path), source=source_identity['path'])
    if candidate is not None:
        if (not isinstance(obj, dict) or
                type(obj.get('processed')) is not int or obj['processed'] < 0):
            raise ImagingError('Die ursprüngliche Statusdatei ist beschädigt.')
        # Older journal records must never roll back a newer successful JSON
        # replacement. At equal positions, prefer the journal for a paused state.
        if candidate.get('processed', -1) >= obj.get('processed', -1):
            obj = candidate
    if (not isinstance(obj, dict) or obj.get('format') != FORMAT_VERSION or
            obj.get('source') != source_identity or obj.get('destination') != _real(destination)):
        raise ImagingError('Statusdatei passt nicht zur ausgewählten Quelle bzw. zum Ziel. Fortsetzung verweigert.')
    if not {'first', 'last', 'state', 'bad_ranges', 'unreadable_bytes'} <= obj.keys():
        raise ImagingError('Pflichtfelder fehlen in der Statusdatei.')
    phase = obj['state']
    if phase not in ('running', 'paused', 'verifying', 'complete', 'integrity_failed'):
        raise ImagingError('Ungültiger Zustand in der Statusdatei.')
    total = source_identity['size']
    completed = obj.get('processed')
    block_size = obj.get('block_size')
    if (not isinstance(completed, int) or isinstance(completed, bool) or
        not 0 <= completed <= total or not isinstance(block_size, int) or
        not 4096 <= block_size <= 16 * 1024 * 1024 or block_size % source_identity['sector_size']):
        raise ImagingError('Ungültige Prüfpunkte in der Statusdatei.')
    if completed and completed != total and completed % block_size:
        raise ImagingError('Die Statusdatei enthält einen nicht ausgerichteten Fortschritt.')
    def valid_digest(checkpoint, start, length):
        if not isinstance(checkpoint, dict):
            return False
        digest = checkpoint.get('sha256')
        return (type(checkpoint.get('start')) is int and
                type(checkpoint.get('length')) is int and
                checkpoint['start'] == start and checkpoint['length'] == length and
                isinstance(digest, str) and len(digest) == 64 and
                all(char in '0123456789abcdef' for char in digest))

    if completed:
        last_start = ((completed - 1) // block_size) * block_size
        if not valid_digest(obj.get('last'), last_start, completed - last_start):
            raise ImagingError('Letzte Prüfsumme in der Statusdatei ist ungültig.')
        if not valid_digest(obj.get('first'), 0, min(block_size, total)):
            raise ImagingError('Erste Prüfsumme in der Statusdatei ist ungültig.')
    elif obj.get('first') is not None or obj.get('last') is not None:
        raise ImagingError('Prüfsummen ohne bestätigten Fortschritt sind ungültig.')
    if phase in ('verifying', 'complete', 'integrity_failed') and completed != total:
        raise ImagingError('Status und bestätigter Fortschritt widersprechen sich.')
    ranges = obj['bad_ranges']
    if not isinstance(ranges, list):
        raise ImagingError('Fehlerbereichsliste in der Statusdatei ist ungültig.')
    previous_end = 0
    unreadable_total = 0
    for item in ranges:
        if (not isinstance(item, list) or len(item) != 2 or
                any(type(value) is not int for value in item)):
            raise ImagingError('Fehlerbereichsliste in der Statusdatei ist ungültig.')
        start, length = item
        if start < previous_end or length <= 0 or start + length > completed:
            raise ImagingError('Fehlerbereiche überschneiden sich oder liegen außerhalb des bestätigten Images.')
        previous_end = start + length
        unreadable_total += length
    if type(obj['unreadable_bytes']) is not int or obj['unreadable_bytes'] != unreadable_total:
        raise ImagingError('Fehlerzähler passt nicht zu den gespeicherten Fehlerbereichen.')
    for key, limit in (('read_retries', MAX_READ_RETRIES),
                       ('retry_delay_ms', MAX_RETRY_DELAY_MS)):
        value = obj.get(key, 0)
        if type(value) is not int or not 0 <= value <= limit:
            raise ImagingError('Ungültige Imaging-Option in der Statusdatei.')
    if obj.get('bad_sector_policy', 'zero') not in BAD_SECTOR_POLICIES:
        raise ImagingError('Ungültige Medienfehlerstrategie in der Statusdatei.')
    counter = obj.get('read_retries_performed', 0)
    if type(counter) is not int or counter < 0:
        raise ImagingError('Ungültiger Wiederholungszähler in der Statusdatei.')
    return obj


def _make_manifest(source_identity: dict, destination: str, block_size: int) -> dict:
    return {'format': FORMAT_VERSION, 'source': source_identity,
            'destination': _real(destination), 'block_size': block_size,
            'processed': 0, 'unreadable_bytes': 0, 'bad_ranges': [],
            'last': None, 'first': None, 'state': 'running',
            'read_retries': 0, 'retry_delay_ms': 0, 'bad_sector_policy': 'zero',
            'read_retries_performed': 0}


@traced("imaging")
def create_image(source: str, destination: str, *,
                 resume: bool = False, block_size: int = DEFAULT_BLOCK_SIZE,
                 cancel: Callable[[], bool] | None = None,
                 progress: Callable[[ImagingProgress], None] | None = None,
                 read_retries: int = 0, retry_delay_ms: int = 250,
                 bad_sector_policy: str = 'zero',
                 verify: bool | None = None) -> dict:
    """Create or resume a raw image with a durable checkpoint.

    No source writes. Never opens Windows raw devices as destinations. Resuming
    requires a matching manifest and verifies the first and last checkpointed
    blocks; it does not cryptographically verify the entire previous image.
    """
    if verify is not None and type(verify) is not bool:
        raise ImagingError('Ungültige Integritätsprüfung-Einstellung.')
    if (type(read_retries) is not int or not 0 <= read_retries <= MAX_READ_RETRIES or
            type(retry_delay_ms) is not int or not 0 <= retry_delay_ms <= MAX_RETRY_DELAY_MS or
            bad_sector_policy not in BAD_SECTOR_POLICIES):
        raise ImagingError('Ungültige Lesefehler-Einstellungen (0–3 Wiederholungen, '
                           '0–2000 ms Wartezeit, Fehlerbehandlung zero/stop).')
    source = validate_source(source)
    # Regular RAW image verification is automatic. On real physical drives,
    # another complete read may burden failing media: explicit opt-in only.
    verify_full = (not is_device_source(source)) if verify is None else verify
    destination = os.fspath(destination)
    if not destination or '\x00' in destination:
        raise ImagingError('Ungültige Zieldatei.')
    # Keep only regular files on disk as destinations; not physical devices.
    normalized_win = destination.replace('/', '\\')
    basename = PureWindowsPath(normalized_win).name.split('.')[0].upper().strip()
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {
        f'{prefix}{i}' for prefix in ('COM', 'LPT') for i in range(1, 10)
    }
    if (is_device_source(destination) or normalized_win.startswith('\\\\.\\') or
            normalized_win.startswith('\\\\?\\') or normalized_win.startswith('\\\\') or
            basename in reserved):
        raise ImagingError('Windows-Gerätepfade und reservierte Gerätenamen dürfen keine Imaging-Ziele sein.')
    if (os.path.islink(destination) or os.path.islink(sidecar_path(destination)) or
            os.path.islink(journal_path(sidecar_path(destination)))):
        raise ImagingError('Symbolische Links als Ziel sind nicht erlaubt.')
    _check_same_file(source, destination)
    if is_device_source(source):
        ensure_safe_destination(source, os.path.dirname(os.path.abspath(destination)))
    total = source_size(source)
    sector = physical_sector_size(source) if is_device_source(source) else DEFAULT_FALLBACK_UNIT
    if total <= 0:
        raise ImagingError('Datenträgergröße ist ungültig.')
    if is_device_source(source) and total % sector:
        raise ImagingError('Quell-Datenträgergröße ist nicht durch die logische Sektorgröße teilbar.')
    if block_size < sector or block_size > 16 * 1024 * 1024 or block_size % sector:
        raise ImagingError('Blockgröße muss sektorausgerichtet sein und maximal 16 MiB betragen.')
    identity = _source_identity(source, total, sector)
    sidecar = sidecar_path(destination)
    expected_output_inode = None
    if not resume:
        if (os.path.lexists(destination) or os.path.lexists(sidecar) or
                os.path.lexists(journal_path(sidecar))):
            raise ImagingError('Ziel oder Statusdatei existiert bereits. Für Fortsetzen dieselbe Datei wählen; sonst neuen Namen verwenden.')
        # The exclusive create prevents overwriting an unrelated file.
        with open_regular_output(destination, 'xb', source) as initial_output:
            st = os.fstat(initial_output.fileno())
            expected_output_inode = (st.st_dev, st.st_ino)
        state = _make_manifest(identity, destination, block_size)
        try:
            if sys.platform.startswith('linux'):
                with open_regular_output(sidecar, 'xb', source) as f:
                    f.write(json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))
                    f.flush()
                    os.fsync(f.fileno())
            else:
                with open(sidecar, 'x', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
        except BaseException:
            # Source remains untouched; do not silently remove partial output.
            raise
    else:
        if not os.path.isfile(destination) or not os.path.isfile(sidecar):
            raise ImagingError('Zum Fortsetzen sind Image und passende Statusdatei erforderlich.')
        state = _load_manifest(sidecar, destination, identity)
        block_size = state['block_size']
    # Options apply to the remaining, not-yet-committed blocks on a resumed job.
    # Existing defect maps and checksums are never discarded by a new setting.
    state['read_retries'] = read_retries
    state['retry_delay_ms'] = retry_delay_ms
    state['bad_sector_policy'] = bad_sector_policy
    state.setdefault('read_retries_performed', 0)
    checkpoint_writer = _CheckpointWriter(sidecar, source)
    checkpoint_writer.last_saved = state['processed']
    position = state['processed']
    opened_output_inode = None
    if progress:
        progress(ImagingProgress(position, total, state['unreadable_bytes'],
                                 len(state['bad_ranges']), state['state']))

    with open_source(source) as reader, open_regular_output(
            destination, 'r+b', source, expected_identity=expected_output_inode) as out:
        output_info = os.fstat(out.fileno())
        opened_output_inode = (output_info.st_dev, output_info.st_ino)
        output_size = output_info.st_size
        if output_size < position or output_size > total:
            raise ImagingError('Image-Dateigröße passt nicht zum gesicherten Fortschritt.')
        if resume and position:
            last = state['last']
            if _hash_region(out, last['start'], last['length']) != last['sha256']:
                raise ImagingError('Letzter bestätigter Block wurde verändert. Fortsetzen verweigert.')
            first = state.get('first')
            if first and _hash_region(out, first['start'], first['length']) != first['sha256']:
                raise ImagingError('Anfang des Image wurde verändert. Fortsetzen verweigert.')
        # Crash may have left an uncommitted tail. It belongs to THIS image;
        # overwrite only after manifest and block digests are verified.
        out.truncate(position)
        out.seek(position)
        # A previous 'complete' state may predate full verification.
        # An explicit resume must still run the requested verification.
        if state['state'] == 'complete' and position == total and not verify_full:
            return state
        state['state'] = 'running'
        while position < total:
            if cancel and cancel():
                state['state'] = 'paused'
                checkpoint_writer.save(state)
                if progress:
                    progress(ImagingProgress(position, total, state['unreadable_bytes'],
                                             len(state['bad_ranges']), 'paused'))
                return state
            # A source image changed during copying must not produce an apparently
            # consistent checkpoint for bytes from two different revisions.
            if not is_device_source(source):
                current = _source_identity(source, total, sector)
                if current != identity:
                    raise ImagingError('Quelldatei wurde während der Sicherung verändert. '
                                       'Abbild ist nur bis zum letzten Prüfpunkt gültig.')
            n = min(block_size, total - position)
            new_bad: list[list[int]] = []
            retry_counter = [0]
            try:
                payload = _recover_read(reader, position, n, sector, new_bad,
                                        strict_short_read=is_device_source(source),
                                        read_retries=read_retries,
                                        retry_delay_ms=retry_delay_ms,
                                        bad_sector_policy=bad_sector_policy,
                                        cancel=cancel, retry_counter=retry_counter)
            except ImagingPaused:
                # No bytes from the current in-flight block were committed.
                state['state'] = 'paused'
                checkpoint_writer.save(state)
                if progress:
                    progress(ImagingProgress(position, total, state['unreadable_bytes'],
                                             len(state['bad_ranges']), 'paused'))
                return state
            if len(payload) != n:
                raise ImagingError('Interner Fehler beim Lesen: unerwartete Blocklänge.')
            if not is_device_source(source) and _source_identity(source, total, sector) != identity:
                raise ImagingError('Quelle wurde während der Leseoperation verändert. '
                                   'Aktueller Block wird nicht übernommen.')
            _write_all(out, payload)
            out.flush()
            os.fsync(out.fileno())
            # Commit only AFTER the image data is durable.
            digest = sha256(payload).hexdigest()
            checkpoint = {'start': position, 'length': n, 'sha256': digest}
            if not state['first']:
                state['first'] = checkpoint.copy()
            for start, length in new_bad:
                _append_bad(state['bad_ranges'], start, length)
                state['unreadable_bytes'] += length
            position += n
            state['read_retries_performed'] += retry_counter[0]
            state['last'] = checkpoint
            state['processed'] = position
            state['state'] = ('verifying' if position == total and verify_full and
                              not state['unreadable_bytes'] else
                              'complete' if position == total else 'running')
            checkpoint_writer.save(state)
            if progress:
                progress(ImagingProgress(position, total, state['unreadable_bytes'],
                                         len(state['bad_ranges']), state['state']))
        out.flush()
        os.fsync(out.fileno())
    if state['unreadable_bytes']:
        state['verification'] = {'status': 'not_possible',
                                 'reason': 'Gemeldete Medienfehler / Nullersatz'}
        state['state'] = 'complete'
        checkpoint_writer.save(state)
    elif verify_full:
        if not _verify_full_copy(source, destination, identity, total,
                                 min(block_size, 1024 * 1024),
                                 opened_output_inode, cancel, progress, state,
                                 checkpoint_writer):
            return state
    else:
        state['verification'] = {'status': 'not_requested'}
        state['state'] = 'complete'
        checkpoint_writer.save(state)
    return state


def describe_bad_ranges(state: dict) -> str:
    """Human-readable report in source byte offsets."""
    lines = [f"Status: {state.get('state', 'unbekannt')}",
             f"Verarbeitet: {state.get('processed', 0):,} / {state['source']['size']:,} Bytes",
             f"Nicht lesbare Bytes (mit Nullen ersetzt): {state.get('unreadable_bytes', 0):,}",
             f"Fehlerbereiche: {len(state.get('bad_ranges', []))}",
             f"Wiederholte Sektor-Leseversuche: {state.get('read_retries_performed', 0)}",
             f"Strategie: {state.get('bad_sector_policy', 'zero')}", 
             '', 'Start-Byteoffset;Länge in Bytes']
    lines.extend(f'{off};{length}' for off, length in state.get('bad_ranges', []))
    return '\n'.join(lines) + '\n'
