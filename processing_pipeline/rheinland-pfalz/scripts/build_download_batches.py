#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Split ``input/laz_tiles.csv`` into Metalink 4.0 batches for pre-downloading
the tiles with aria2c.

Each batch holds at most ``--batch-tb`` terabytes (decimal, 10^12 bytes), filled
in samplesheet order -- west to east, then south to north -- so every batch is a
contiguous north-south strip of the state.  Size and SHA-256 go into the
Metalink, so aria2c checks every file once it lands.

Usage
-----
    uv run scripts/build_download_batches.py
    aria2c -M input/laz_tiles_batch_01.meta4 -d /data/rlp/laz \\
        -j 16 -x 4 --check-integrity=true --continue=true
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

HERE = Path(__file__).resolve().parent.parent


def write_meta4(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<metalink xmlns="urn:ietf:params:xml:ns:metalink">\n')
        for r in rows:
            f.write(f"  <file name={quoteattr(r['tile'])}>\n")
            f.write(f"    <size>{int(r['size_bytes'])}</size>\n")
            f.write(f'    <hash type="sha-256">{r["sha256"]}</hash>\n')
            f.write(f"    <url>{escape(r['url'])}</url>\n")
            f.write("  </file>\n")
        f.write("</metalink>\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("-i", "--input", type=Path, default=HERE / "input/laz_tiles.csv")
    p.add_argument("-o", "--outdir", type=Path, default=HERE / "input")
    p.add_argument("--batch-tb", type=float, default=1.5, help="max batch size in TB (10^12 bytes)")
    args = p.parse_args()

    limit = int(args.batch_tb * 1e12)
    with args.input.open(newline="") as f:
        rows = list(csv.DictReader(f))

    batches: list[list[dict[str, str]]] = [[]]
    size = 0
    for r in rows:
        n = int(r["size_bytes"])
        if batches[-1] and size + n > limit:
            batches.append([])
            size = 0
        batches[-1].append(r)
        size += n

    for i, batch in enumerate(batches, 1):
        out = args.outdir / f"laz_tiles_batch_{i:02d}.meta4"
        write_meta4(out, batch)
        total = sum(int(r["size_bytes"]) for r in batch)
        print(f"{out.name}: {len(batch):>6} tiles, {total / 1e12:.3f} TB ({total / 2**40:.3f} TiB), "
              f"{batch[0]['tile']} .. {batch[-1]['tile']}")


if __name__ == "__main__":
    main()
