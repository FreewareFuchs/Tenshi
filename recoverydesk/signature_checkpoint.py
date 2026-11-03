"""Bounded, untrusted signature-search checkpoints; never cache file contents."""
import json
import hashlib
import os
from pathlib import Path
import stat
import sys
import time

from .resilience import atomic_replace_json
from .secure_target import atomic_json_checkpoint, open_regular_input
from .sources import ensure_safe_destination

SCHEMA = 'tenshi-signature-search-v1'
MAX_BYTES = 512 * 1024
CATEGORIES = ('images', 'office', 'archives', 'audio', 'video')


def checkpoint_digest(state):
    payload = {key:value for key,value in state.items() if key != 'checksum'}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()


def _plain_target(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Suchstand darf nicht über einen Link geöffnet werden.')
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Suchstand muss eine reguläre Datei sein.')
    return path


def validate_checkpoint(data):
    from .signature_search import MAX_HITS, MAX_CANDIDATES, MAX_INSPECTION, SCAN_BLOCK
    try:
        if not isinstance(data, dict) or data['schema'] != SCHEMA:
            raise ValueError()
        revision = data.get('parser_revision',1)
        if type(revision) is not int or revision not in (1,2):raise ValueError()
        source = data['source']
        if not isinstance(source, str) or not 0 < len(source) <= 32768 or '\0' in source or not os.path.isabs(source):
            raise ValueError()
        fingerprint = data['fingerprint']
        if not isinstance(fingerprint, dict):
            raise ValueError()
        total = fingerprint['size']
        if type(total) is not int or total < 512:
            raise ValueError()
        categories = data['categories']
        if (not isinstance(categories, list) or not 0 < len(categories) <= 5 or
                any(not isinstance(c, str) or c not in CATEGORIES for c in categories) or
                len(set(categories)) != len(categories)):
            raise ValueError()
        if type(data['file_limit']) is not int or data['file_limit'] not in tuple(m*1024**2 for m in (32,64,128,256)):
            raise ValueError()
        for key, maximum in (('position', total), ('candidates', MAX_CANDIDATES), ('inspection', MAX_INSPECTION)):
            if type(data[key]) is not int or not 0 <= data[key] <= maximum:
                raise ValueError()
        position = data['position']
        if position != total and position % SCAN_BLOCK:
            raise ValueError()
        if type(data['last']) is not int or not (-1 <= data['last'] < position or (position == 0 and data['last'] == -1)):
            raise ValueError()
        if (data['candidates'] == 0) != (data['last'] == -1):
            raise ValueError()
        if type(data['limited']) is not bool:
            raise ValueError()
        hits = data['hits']
        if not isinstance(hits, list) or len(hits) > min(MAX_HITS, data['candidates']):
            raise ValueError()
        previous = -1
        for hit in hits:
            if (not isinstance(hit, list) or len(hit) != 3 or type(hit[0]) is not int or
                    not previous < hit[0] <= data['last'] or type(hit[1]) is not int or
                    not 0 < hit[1] <= total - hit[0] or not isinstance(hit[2], str) or len(hit[2]) > 16):
                raise ValueError()
            previous = hit[0]
        if data.get('checksum') != checkpoint_digest(data):
            raise ValueError()
        return data
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Ungültiger gespeicherter Suchstand.') from exc


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Ungültiger gespeicherter Suchstand.')
        result[key] = value
    return result


def read_checkpoint(path):
    path = _plain_target(path)
    before = path.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError('Gespeicherter Suchstand ist zu groß.')
    with open_regular_input(str(path), str(path) + '.source') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino) != (before.st_dev,before.st_ino):
            raise ValueError('Suchstand wurde während des Öffnens geändert.')
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Gespeicherter Suchstand ist zu groß.')
    try:
        return validate_checkpoint(json.loads(raw, object_pairs_hook=_pairs))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError('Ungültiger gespeicherter Suchstand.') from exc


class CheckpointWriter:
    def __init__(self, path, source, fingerprint, snapshot):
        self.path = str(_plain_target(path))
        self.source = source
        ensure_safe_destination(source, self.path)
        if os.path.exists(self.path) and os.path.samefile(source, self.path):
            raise ValueError('Quelle und Suchstand dürfen nicht identisch sein.')
        self.fingerprint = fingerprint
        self.snapshot = snapshot
        self.pending = None
        self.saved_position = -16 * 1024**2
        self.saved_time = float('-inf')

    def update(self, state):
        self.pending = dict(schema=SCHEMA, source=os.path.abspath(self.source),
                            fingerprint=self.fingerprint, **state)
        self.pending['checksum'] = checkpoint_digest(self.pending)
        if state['position'] - self.saved_position >= 16*1024**2 or time.monotonic() - self.saved_time >= 2:
            self.flush()

    def flush(self):
        if self.pending is None:
            return
        from .signature_search import _snapshot
        if _snapshot(os.stat(self.source)) != self.snapshot:
            raise ValueError('Quell-Image wurde geändert.')
        _plain_target(self.path)
        ensure_safe_destination(self.source, self.path)
        if os.path.exists(self.path) and os.path.samefile(self.source, self.path):
            raise ValueError('Quelle und Suchstand dürfen nicht identisch sein.')
        if sys.platform.startswith('linux'):
            atomic_json_checkpoint(self.path, self.pending, self.source)
        else:
            atomic_replace_json(self.path, self.pending)
        self.saved_position = self.pending['position']
        self.saved_time = time.monotonic()
