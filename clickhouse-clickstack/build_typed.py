#!/usr/bin/env python3
"""Lay the compact events out the way ClickHouse wants them: typed, not text.

`build_arms.py` puts the compact event into `Body` as one string,
`~<hash>,<v1>,<v2>,...`. That is the shape the ClickHouse app stores today and it
is the worst shape ClickHouse allows: values of every type, mashed into one
string, compressed as text. ClickHouse's own log-clustering post measured the
same rung at 22x against 19x raw, and then 45x once the template sat in a
low-cardinality column and the values in typed columns.

This script produces that second rung from the same compact events, with no
per-template schema, so it is a layout a product could ship without a schema
per customer:

  templateHash   LowCardinality(String)  the template, once per row
  slot_kinds     Array(UInt8)            per value slot: 0 timestamp, 1 integer, 2 text
  ts_vals        Array(Int64)            the timestamp slots, epoch integers as the engine wrote them
  num_vals       Array(Int64)            the integer slots
  str_vals       Array(String)           everything else

A value goes to an integer column only when `str(int(v)) == v`, so `007`, `-0`
and ` 12` stay text and the layout is byte-exact reversible. Every row is
reversed in this script before it is written, and the run refuses to produce
output if a single row does not come back identical to the compact event it
was built from.

Back-reference slots (`$N`) carry no value in the compact event and get no
entry in any array; the template supplies them at read time.
"""

import argparse
import json
import pathlib
import re
import sys

SLOT = re.compile(r"\$\([^)]*\)|\$[0-9]+|\$")
INT_RANGE = (-(2 ** 63), 2 ** 63 - 1)

KIND_TS, KIND_INT, KIND_STR = 0, 1, 2


def slots_of(template: str):
    """Value-bearing slots in order, honouring the `/` escape.

    Mirrors reference_decode.parse: `/` escapes the next character, `$(...)` is a
    timestamp slot, `$N` is a back-reference and carries no value, `$` is a plain
    value slot.
    """
    out, i, n = [], 0, len(template)
    while i < n:
        c = template[i]
        if c == "/" and i + 1 < n:
            i += 2
        elif c == "$":
            if i + 1 < n and template[i + 1] == "(":
                close = template.find(")", i)
                if close < 0:
                    i += 1
                    continue
                out.append("ts")
                i = close + 1
            else:
                j = i + 1
                while j < n and template[j].isdigit():
                    j += 1
                if j == i + 1:
                    out.append("val")
                i = j
        else:
            i += 1
    return out


def as_exact_int(value: str):
    """The integer this string is, only if printing it back gives the same string."""
    if not value or len(value) > 20:
        return None
    body = value[1:] if value[0] == "-" else value
    if not body.isdigit():
        return None
    number = int(value)
    if str(number) != value or not INT_RANGE[0] <= number <= INT_RANGE[1]:
        return None
    return number


def split(compact: str, template: str):
    """Compact event to (kinds, ts, nums, strs). Returns None if not a compact event."""
    if not compact.startswith("~"):
        return None
    comma = compact.find(",")
    values = compact[comma + 1:].split(",") if comma >= 0 else []
    kinds, ts, nums, strs = [], [], [], []
    slot_types = slots_of(template)
    for i, value in enumerate(values):
        slot = slot_types[i] if i < len(slot_types) else "val"
        number = as_exact_int(value)
        if slot == "ts" and number is not None:
            kinds.append(KIND_TS)
            ts.append(number)
        elif number is not None:
            kinds.append(KIND_INT)
            nums.append(number)
        else:
            kinds.append(KIND_STR)
            strs.append(value)
    return kinds, ts, nums, strs


def join(template_hash: str, kinds, ts, nums, strs) -> str:
    """The exact inverse of split: rebuild `~<hash>,<values>`."""
    out, it, ni, si = [], 0, 0, 0
    for kind in kinds:
        if kind == KIND_TS:
            out.append(str(ts[it])); it += 1
        elif kind == KIND_INT:
            out.append(str(nums[ni])); ni += 1
        else:
            out.append(strs[si]); si += 1
    return "~" + template_hash + ("," + ",".join(out) if kinds else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", required=True, help="directory build_arms.py wrote")
    ap.add_argument("--templates", required=True, help="INNER templates.json")
    args = ap.parse_args()
    arms = pathlib.Path(args.arms)

    templates = {}
    for line in open(args.templates, encoding="utf-8"):
        record = json.loads(line)
        templates[record["templateHash"]] = record["template"]

    rows = ts_total = num_total = str_total = 0
    out_path = arms / "compact_typed.jsonl"
    with open(arms / "compact.jsonl", encoding="utf-8") as src, \
            open(out_path, "w", encoding="utf-8") as dst:
        for line in src:
            row = json.loads(line)
            compact = row["Body"]
            comma = compact.find(",")
            template_hash = compact[1:comma] if comma > 0 else compact[1:]
            parts = split(compact, templates.get(template_hash, ""))
            if parts is None:
                print(f"row {rows}: Body is not a compact event: {compact[:80]!r}",
                      file=sys.stderr)
                return 1
            kinds, ts, nums, strs = parts
            rebuilt = join(template_hash, kinds, ts, nums, strs)
            if rebuilt != compact:
                print(f"row {rows}: typed layout does not reverse to the compact event\n"
                      f"  compact: {compact[:120]!r}\n  rebuilt: {rebuilt[:120]!r}",
                      file=sys.stderr)
                return 1
            del row["Body"]
            row["templateHash"] = template_hash
            row["slot_kinds"] = kinds
            row["ts_vals"] = ts
            row["num_vals"] = nums
            row["str_vals"] = strs
            dst.write(json.dumps(row) + "\n")
            rows += 1
            ts_total += len(ts); num_total += len(nums); str_total += len(strs)

    summary = {
        "rows": rows,
        "value_slots": ts_total + num_total + str_total,
        "timestamp_values": ts_total,
        "integer_values": num_total,
        "text_values": str_total,
        "every_row_reversed_byte_identical": True,
    }
    (arms / "compact_typed.manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
