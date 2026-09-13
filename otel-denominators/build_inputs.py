#!/usr/bin/env python3
"""Build the two derived denominators from the public capture.

The published figure is measured on the file as captured: a Fluentd envelope
around each container's stdout line. Two objections follow from that and each
one names a different denominator, so all three are built here from one input
and measured by the same engine and the same configs.

    (a) as captured    the release asset, untouched
    (b) SIEM-billed    the field this project injects is removed and the
                       collector's debug-exporter lines are dropped; the
                       Kubernetes and Docker envelope is kept, because a log
                       platform bills it
    (c) message only   the `log` value alone, one message per line, no envelope

(b) drops a line only when its container is `opentelemetry-collector` AND its
message matches zap's tab-separated debug-exporter prefix. Ordinary collector
error logs are kept: a platform bills those, and the 3,745 lines reading
`failed to upload metrics` are a misconfiguration in the captured cluster
rather than debug output.

(c) writes every message including the collector's, so (b) and (c) differ in
line count on purpose: 111,691 against 197,430.

Usage:
    python build_inputs.py --src <path to otel-sample-200mb.log[.gz]> --out-dir <dir>
"""

import argparse
import gzip
import json
import pathlib
import re
import sys

# zap's tab format, which is what the collector's debug exporter writes. A match
# on "[info]" finds nothing in this capture: the literal separator is a tab.
DEBUG_EXPORTER = re.compile(r"^\S+\tinfo\t(Traces|Logs|Metrics)\t")
COLLECTOR = "opentelemetry-collector"


def open_maybe_gzip(path: pathlib.Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return open(path, "rb")


def build(src: pathlib.Path, out_dir: pathlib.Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    b_path = out_dir / "b_siem.log"
    c_path = out_dir / "c_msg.log"
    n_b = n_c = dropped = unparseable = 0
    with open_maybe_gzip(src) as fin, \
            open(b_path, "wb") as fb, open(c_path, "wb") as fc:
        for raw in fin:
            try:
                record = json.loads(raw)
            except ValueError:
                unparseable += 1
                continue
            message = record.get("log") or ""
            kubernetes = record.get("kubernetes") or {}
            is_debug = (kubernetes.get("container_name") == COLLECTOR
                        and DEBUG_EXPORTER.match(message))
            if is_debug:
                dropped += 1
            else:
                record.pop("tenx_tag", None)
                fb.write((json.dumps(record, separators=(",", ":")) + "\n").encode())
                n_b += 1
            fc.write((message + "\n").encode())
            n_c += 1
    return {
        "b_siem_lines": n_b,
        "b_siem_bytes": b_path.stat().st_size,
        "c_msg_lines": n_c,
        "c_msg_bytes": c_path.stat().st_size,
        "collector_debug_lines_dropped": dropped,
        "unparseable_lines": unparseable,
    }


# The committed run. run.sh checks the build against these before it spends an
# engine run on it, so a change in the source asset or in Python's JSON
# serialisation is caught at the input rather than shrugged off in the table.
EXPECTED = {
    "b_siem_lines": 111691,
    "b_siem_bytes": 88975911,
    "c_msg_lines": 197430,
    "c_msg_bytes": 40551755,
    "collector_debug_lines_dropped": 85739,
    "unparseable_lines": 0,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--no-check", action="store_true",
                    help="build without comparing against the committed counts")
    args = ap.parse_args()

    got = build(pathlib.Path(args.src), pathlib.Path(args.out_dir))
    width = max(len(k) for k in got)
    for key, value in got.items():
        expected = EXPECTED[key]
        flag = "" if value == expected else f"  != committed {expected:,}"
        print(f"{key:<{width}}  {value:>12,}{flag}")

    if args.no_check:
        return 0
    bad = {k: (v, EXPECTED[k]) for k, v in got.items() if v != EXPECTED[k]}
    if bad:
        print("\nthe derived inputs do not reproduce the committed run:", file=sys.stderr)
        for key, (value, expected) in bad.items():
            print(f"  {key}: got {value:,}, committed {expected:,}", file=sys.stderr)
        return 1
    print("\nboth derived inputs reproduce the committed byte and line counts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
