#!/usr/bin/env python3
"""Label every captured line with its message type, and build the reduction arms.

The storage question is settled: on ClickHouse, compaction is worth about 7% of
the table at scale, because ClickHouse Cloud bills storage on compressed bytes
at $25.30 per TB per month and its own compression is already excellent. The
open question is compute, which is the larger half of a ClickHouse bill, and
the claim to test is that compute scales with ROWS, so removing rows is the
lever and making each row smaller is not.

This script writes the arms that test it. Every arm is the same ClickStack
mapping and the same original log text; the only thing that changes is which
rows are present.

  full           every captured line, the baseline a collector produces
  sampled_75/50/25    a uniform random sample, seeded, of the lines.
                 Content mix is unchanged, so this isolates row count.
  bypattern_75/50/25  whole message types removed, largest first, until the
                 target row count is reached. This is the lever the product
                 actually pulls, and it removes variety as well as rows, so
                 comparing it against the uniform sample at the same row count
                 separates "fewer rows" from "fewer kinds of row".

Each captured line is labelled with the message type of the compact event that
covers it, recovered from the template's newline count exactly as
`build_arms.py` does, with the same two invariants checked before anything is
written.
"""

import argparse
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_arms import envelope, load_templates, split_encoded  # noqa: E402

TARGETS = (75, 50, 25)


def spans(encoded, raw, templates):
    """(start, lines, templateHash) per compact event, with both invariants checked."""
    out, cursor = [], 0
    for record in encoded:
        template_hash, _ = split_encoded(record.get("log", ""))
        template = templates.get(template_hash) if template_hash else None
        lines = template["lines"] if template else 1
        if envelope(record) != envelope(raw[cursor]):
            print(f"alignment broke at compact record {len(out)}, raw line {cursor}",
                  file=sys.stderr)
            return None
        out.append((cursor, lines, template_hash or ""))
        cursor += lines
    if cursor != len(raw):
        print(f"reconstructed {cursor} lines, capture has {len(raw)}", file=sys.stderr)
        return None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--encoded", required=True)
    ap.add_argument("--templates", required=True)
    ap.add_argument("--arms", required=True, help="directory build_arms.py wrote")
    ap.add_argument("--seed", type=int, default=20260913)
    args = ap.parse_args()
    arms = pathlib.Path(args.arms)

    templates = load_templates(pathlib.Path(args.templates))
    raw = [json.loads(line) for line in open(args.raw, encoding="utf-8")]
    encoded = [json.loads(line) for line in open(args.encoded, encoding="utf-8")]
    layout = spans(encoded, raw, templates)
    if layout is None:
        return 1

    # native.jsonl is one row per captured line, in capture order, so the spans
    # index it directly.
    native = [line for line in open(arms / "native.jsonl", encoding="utf-8")]
    if len(native) != len(raw):
        print(f"native.jsonl has {len(native)} rows, capture has {len(raw)}", file=sys.stderr)
        return 1

    pattern_of = [""] * len(raw)
    per_pattern = {}
    for start, lines, template_hash in layout:
        for j in range(start, start + lines):
            pattern_of[j] = template_hash
        per_pattern[template_hash] = per_pattern.get(template_hash, 0) + lines

    total = len(raw)
    ranked = sorted(per_pattern.items(), key=lambda kv: -kv[1])
    summary = {"captured_lines": total, "message_types": len(per_pattern),
               "top_20_by_lines": [{"templateHash": h, "lines": n,
                                    "share_pct": round(n / total * 100, 2)}
                                   for h, n in ranked[:20]],
               "arms": {}}

    # ---- uniform sample: same mix, fewer rows -------------------------------
    rng = random.Random(args.seed)
    roll = [rng.random() for _ in range(total)]
    for target in TARGETS:
        keep = [i for i in range(total) if roll[i] < target / 100]
        name = f"native_sampled_{target}"
        with open(arms / f"{name}.jsonl", "w", encoding="utf-8") as out:
            for i in keep:
                out.write(native[i])
        summary["arms"][name] = {"rows": len(keep),
                                 "share_pct": round(len(keep) / total * 100, 2)}

    # ---- by pattern: drop whole message types, largest first ----------------
    for target in TARGETS:
        budget = total - int(total * target / 100)   # lines to remove
        dropped, removed = set(), 0
        for template_hash, lines in ranked:
            if removed >= budget:
                break
            dropped.add(template_hash)
            removed += lines
        keep = [i for i in range(total) if pattern_of[i] not in dropped]
        name = f"native_bypattern_{target}"
        with open(arms / f"{name}.jsonl", "w", encoding="utf-8") as out:
            for i in keep:
                out.write(native[i])
        summary["arms"][name] = {"rows": len(keep),
                                 "share_pct": round(len(keep) / total * 100, 2),
                                 "message_types_dropped": len(dropped),
                                 "message_types_kept": len(per_pattern) - len(dropped)}

    (arms / "reduction.manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2)[:1400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
