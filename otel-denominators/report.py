#!/usr/bin/env python3
"""Render results/results.md from results/results.csv.

Separate from run.sh so the table can be regenerated from a committed CSV
without another engine run, and so the one derived quantity on the page, the
reduction percentage, is recomputed here from the byte counts rather than
copied from the run's own log.
"""

import argparse
import csv
import pathlib
import sys

LABELS = {
    "a_asis": ("(a) as captured",
               "the release asset, untouched"),
    "b_siem": ("(b) SIEM-billed",
               "the injected `tenx_tag` field removed, the collector's "
               "debug-exporter lines dropped, envelope kept"),
    "c_msg": ("(c) message only",
              "the `log` value alone, one message per line"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", default="unrecorded")
    ap.add_argument("--asset-sha256", default="unrecorded")
    ap.add_argument("--asset-gz-sha256", default="unrecorded")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv)))
    if not rows:
        print("no rows in the csv", file=sys.stderr)
        return 1

    out = []
    A = out.append
    A("# OTel sample on three denominators")
    A("")
    A("Written by `run.sh`. Every byte count is `wc -c` on a file this run "
      "produced; the percentage is recomputed from those counts by `report.py`.")
    A("")
    A(f"- engine image: `{args.image}`")
    A("- configs: `../drain3-vs-log10x/tenx-encode.config.yaml` and "
      "`tenx-decode.config.yaml`")
    A(f"- capture, gzipped as published: sha256 `{args.asset_gz_sha256}`")
    A(f"- capture, expanded: sha256 `{args.asset_sha256}`")
    A("")
    A("| Case | Input bytes | Lines | Encoded | Templates bytes | Compact | "
      "Reduction | Templates | Round trip |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in rows:
        label = LABELS.get(r["case"], (r["case"], ""))[0]
        ib = int(r["input_bytes"])
        compact = int(r["compact_bytes"])
        pct = (1 - compact / ib) * 100
        A(f"| {label} | {ib:,} | {int(r['input_lines']):,} | "
          f"{int(r['encoded_bytes']):,} | {int(r['templates_bytes']):,} | "
          f"{compact:,} | **{pct:.2f}%** | {int(r['templates']):,} | "
          f"{r['roundtrip'].lower()} |")
    A("")
    A("What each denominator is:")
    A("")
    for r in rows:
        label, description = LABELS.get(r["case"], (r["case"], ""))
        A(f"- **{label}**: {description}.")
    A("")
    A("Round trip is `cmp` against that case's own input, so each row decodes "
      "back to the bytes it was measured on, not to some other file.")
    A("")

    trips = {r["roundtrip"] for r in rows}
    if trips == {"BYTE-IDENTICAL"}:
        A("Every case returned byte-identical.")
    else:
        A(f"**Round trip is not byte-identical in every case: {sorted(trips)}.** "
          "A row that differs is a defect, not a caveat.")
    A("")

    pathlib.Path(args.out).write_text("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
