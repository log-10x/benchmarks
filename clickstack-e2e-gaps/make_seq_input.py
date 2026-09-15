#!/usr/bin/env python3
"""Write a copy of the capture with a sequence number inside every log line.

The reconciliation in gap 4 needs a per-line identity that survives the whole
route: the receiver groups a multi-line event into one record, the collector
re-batches, the offload writer keeps only the body and the log attributes, and
ClickHouse sees the two sides through two different tables. The body is the one
field every hop carries unchanged, so the number rides in the body.

Half the capture's lines are themselves JSON, and the shape of that JSON is what
the OTel return path defects turned on, so the number is added in a way that
leaves each line the shape it had: a JSON line keeps its object and its first
key and gains a `tenxseq` member at the end, a plain line gains a `tenxseq=<n>`
prefix. `tenxseq[^0-9]{0,4}([0-9]+)` reads both.

A grouped event keeps every line's marker inside one body, so counting
`extractAll(Body, 'tenxseq[^0-9]{0,4}([0-9]+)')` over hot plus cold counts input
lines however the receiver grouped them.

  make_seq_input.py --in capture.log --out seq.log
"""
import argparse
import json
import pathlib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    args = ap.parse_args()
    src, dst = pathlib.Path(args.src), pathlib.Path(args.dst)
    n = skipped = as_json = as_text = 0
    with src.open() as fh, dst.open("w") as out:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if "log" not in doc:
                skipped += 1
                continue
            n += 1
            body = doc["log"]
            inner = None
            if isinstance(body, str) and body.lstrip().startswith("{"):
                try:
                    inner = json.loads(body)
                except json.JSONDecodeError:
                    inner = None
            if isinstance(inner, dict):
                inner["tenxseq"] = n
                doc["log"] = json.dumps(inner)
                as_json += 1
            else:
                doc["log"] = f"tenxseq={n} " + str(body)
                as_text += 1
            out.write(json.dumps(doc) + "\n")
    print(f"  {n} numbered lines written to {dst.name}: {as_json} inside their own JSON, "
          f"{as_text} as a prefix, {skipped} lines skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
