"""Non-destructive text diagnosis for a local flat RAW disk or volume image.

Usage: py -3 diagnose_raw.py "D:\\Images\\platte.raw" --deep --limit-mb 8192
       py -3 diagnose_raw.py "D:\\Images\\platte.raw" --deep --limit-mb 0
"""
from __future__ import annotations
import argparse
import sys
from recoverydesk.partition_scan import analyze_image


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Tenshi: RAW-Abbild nur lesend untersuchen.")
    parser.add_argument("image", help="Pfad zu einem flachen, unkomprimierten RAW-Image")
    parser.add_argument("--deep", action="store_true", help="Bootsektoren außerhalb der ersten 64 MiB suchen")
    parser.add_argument("--limit-mb", type=int, default=4096,
                        help="Maximale Tiefe in MiB für --deep; 0 = gesamtes Image (Standard: 4096)")
    parser.add_argument("--sector-size", choices=("auto", "512", "4096"), default="auto",
                        help="Logische Sektorgröße des Images für MBR/GPT (Standard: auto)")
    args = parser.parse_args(argv)
    last_progress = -1
    def progress(done, total):
        nonlocal last_progress
        bucket = done // (256 * 1024 * 1024)
        if bucket != last_progress and total >= 256 * 1024 * 1024:
            last_progress = bucket
            print(f"{done/1024**2:.0f} / {total/1024**2:.0f} MiB untersucht", file=sys.stderr)
    try:
        report = analyze_image(args.image, deep_scan=args.deep,
                               max_scan_mb=args.limit_mb,
                               sector_size=args.sector_size, progress=progress)
    except (OSError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    print("\nTenshi RAW-Diagnose (schreibgeschützt)")
    print(f"Imagegröße: {report.image_size:,} Bytes ({report.image_size/1024**3:.3f} GiB)")
    print(f"Partitionsschema: {report.table_type}; angenommene Sektorgröße: {report.sector_size} Bytes")
    print(f"Dateisystem-Suchbereich: {report.scanned_bytes/1024**2:.0f} MiB")
    print(f"Einträge: {len(report.partitions)}")
    for p in report.partitions:
        print(f"  [{p.index}] {p.scheme:12} Offset={p.offset_bytes:,} B  "
              f"Größe={p.size_bytes:,} B  FS={p.filesystem}  Typ={p.type_code}  Plausibilität={p.confidence}")
        for item in p.evidence:
            print(f"       Hinweis: {item}")
        if p.name:
            print(f"       Name: {p.name}")
        if p.warning:
            print(f"       HINWEIS: {p.warning}")
    if report.warnings:
        print("\nHinweise:")
        for item in report.warnings:
            print("  -", item)
    if not report.partitions:
        print("\nEmpfehlung: Falls nur die Schnellanalyse lief, --deep verwenden. "
              "Bei großen Images --limit-mb erhöhen oder 0 für das gesamte Abbild nutzen.")
    print("\nOriginal-Image wurde nicht verändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
