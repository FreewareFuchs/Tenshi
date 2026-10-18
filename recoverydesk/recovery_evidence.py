"""Conservative, read-only NTFS cluster-ownership evidence for deleted files.

The current MFT's *live* nonresident streams provide positive evidence that a
cluster referenced by a deleted record has been reused.  No overlap does NOT
prove the old content survives: the scan can be incomplete, bitmap allocations
may not be represented by a scanned file, and the image may have changed.

All ranges are half-open logical cluster numbers (LCNs); sparse runs are not
physical allocations.  Hard links may repeat the same live record: merged
ranges make duplicate reports harmless.  No source I/O is performed here.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

MAX_LIVE_RUNS = 2_000_000


@dataclass(frozen=True)
class LiveClusterEvidence:
    spans: tuple[tuple[int, int], ...]
    starts: tuple[int, ...]

    def overlaps(self, start: int, end: int) -> bool:
        """O(log n) intersection with union of known live-file data extents."""
        if start >= end or not self.starts:
            return False
        pos = bisect_right(self.starts, start) - 1
        if pos >= 0 and self.spans[pos][1] > start:
            return True
        next_pos = pos + 1
        return next_pos < len(self.spans) and self.spans[next_pos][0] < end


def build_live_cluster_evidence(index) -> LiveClusterEvidence:
    """Build a bounded merged union from currently linked NTFS streams.

    Only live, supported nonresident file data is considered.  Corrupt or
    unrecognized live streams cannot be evidence of free space.  The caller
    must still treat any negative finding as inconclusive.
    """
    ranges: list[tuple[int, int]] = []
    for entry in getattr(index, 'entries', ()):
        if (getattr(entry, 'is_deleted', True) or
                getattr(entry, 'is_directory', False) or
                getattr(entry, 'data_kind', None) != 'nonresident' or
                getattr(entry, 'unsupported_reason', '')):
            continue
        for run in getattr(entry, 'data_runs', ()):
            clusters, lcn = getattr(run, 'clusters', 0), getattr(run, 'lcn', None)
            if lcn is None or not isinstance(lcn, int) or not isinstance(clusters, int):
                continue
            if lcn < 0 or clusters <= 0:
                continue
            if len(ranges) >= MAX_LIVE_RUNS:
                raise ValueError('Zu viele NTFS-Datenbereiche für eine sichere Überlappungsprüfung.')
            ranges.append((lcn, lcn + clusters))
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    spans = tuple(merged)
    return LiveClusterEvidence(spans, tuple(start for start, _ in spans))


def deleted_stream_claim_issue(entry, evidence: LiveClusterEvidence) -> str | None:
    """Return a definitive metadata conflict, not a content-health estimate."""
    if not (getattr(entry, 'is_deleted', False) and
            getattr(entry, 'data_kind', None) == 'nonresident'):
        return None
    for run in getattr(entry, 'data_runs', ()):
        lcn, clusters = getattr(run, 'lcn', None), getattr(run, 'clusters', 0)
        if isinstance(lcn, int) and isinstance(clusters, int) and clusters > 0:
            if evidence.overlaps(lcn, lcn + clusters):
                return ('NTFS-Cluster der gelöschten Datei werden laut aktuellen '
                        'MFT-Metadaten bereits von einer vorhandenen Datei genutzt. '
                        'Der ursprüngliche Dateiinhalt ist an diesen Stellen nicht zuverlässig zuordenbar.')
    return None


def self_overlap_issue(entry) -> str | None:
    """Detect impossible repeated physical allocations within one NTFS stream."""
    if getattr(entry, 'data_kind', None) != 'nonresident':
        return None
    intervals: list[tuple[int, int]] = []
    for run in getattr(entry, 'data_runs', ()):
        lcn, count = getattr(run, 'lcn', None), getattr(run, 'clusters', 0)
        if isinstance(lcn, int) and isinstance(count, int) and count > 0:
            intervals.append((lcn, lcn + count))
    intervals.sort()
    last_end = -1
    for start, end in intervals:
        if start < last_end:
            return 'NTFS-Datenstrom enthält überlappende physische Clusterbereiche.'
        last_end = end
    return None
