"""CSV snapshot of visible signature findings; never opens the source image."""
import csv
import io

from .sources import ensure_safe_destination

FIELDS = ('generated_name', 'type', 'size_bytes', 'absolute_offset_bytes',
          'source_image', 'search_area', 'partition_offset_bytes', 'categories',
          'parser_revision', 'inspection_limit_bytes', 'scan_complete',
          'total_findings', 'visible_findings', 'notice')
NOTICE = ('Signature findings have no original names, folders or deletion status. '
          'Readable structures do not prove complete original contents. '
          'Fragments are not reassembled. This is a findings list, not an export or integrity report.')


def _cell(value):
    # Quoting CSV cells alone does not prevent spreadsheet formula execution.
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


def report_csv(source, index, entries):
    """Keep the captured view order and the completed scan's scope, not UI options."""
    entries = tuple(entries)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, delimiter=';', lineterminator='\r\n')
    writer.writerow(FIELDS)
    metadata = (source, getattr(index, 'signature_search_area', 'all'),
                getattr(index, 'signature_partition_offset', 0),
                ','.join(index.signature_categories), index.signature_parser_revision,
                index.signature_file_limit, str(index.signature_complete).lower(),
                len(index.entries), len(entries), NOTICE)
    for entry in entries:
        writer.writerow([_cell(value) for value in
                         (entry.name, entry.name.split('_', 1)[0], entry.size,
                          entry.locator[1], *metadata)])
    return stream.getvalue()


def save_csv(destination, text, source):
    """Protect the source and existing files; BOM makes UTF-8 explicit for Excel."""
    ensure_safe_destination(source, destination)
    with open(destination, 'x', encoding='utf-8-sig', newline='') as stream:
        stream.write(text)
