#!/usr/bin/env python3
"""
Ground truth for the expansion check.

The compact arm indexes one Splunk event per compact record. To say whether the
10x Splunk app gives back the original text, something has to know what the
original text of each compact record was. This builds that from the three files
the run already has, and refuses to write anything unless two invariants hold.

How a compact record's line span is recovered: the engine folds a multi-line
event into one compact record and joins the folded lines with a newline, so the
record's own template carries K-1 newlines for a K-line event. Walking the
capture and the encoded stream together in order therefore assigns each compact
record exactly the lines it covers.

Invariants, both fatal:

1. the lines assigned across every record equal the lines in the capture, with
   none left over;
2. every record's template agrees with the text assigned to it at both ends:
   the literal run before the template's first slot is a prefix of that text,
   and the run after its last slot is a suffix. A walk that slipped by even one
   record fails this on almost every record after the slip, so it is what stands
   behind the ordering assumption rather than an assertion that the engine
   preserves order. Both ends are used because either alone is weak: many
   templates end in the same few bytes of the capture's envelope.

Output is a JSON file of sha256(compact record) -> sha256(original text), plus a
few full pairs so a reader can see one without holding the capture.
"""

import argparse
import hashlib
import json
import pathlib
import sys


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()


def load_templates(path: pathlib.Path) -> dict:
    templates = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            record = json.loads(line)
            template = record["template"]
            templates[record["templateHash"]] = {
                "text": template,
                "lines": template.count("\n") + 1,
            }
    return templates


def literal_runs(template: str):
    """
    Split a template into its literal runs, undoing the engine's escaping.

    In a template `$` marks a variable slot and `/` escapes the next character,
    so `//` is a literal `/` and `/$` a literal `$`. A timestamp slot is
    `$(<format>)`; a plain `$` followed by an ordinary `(` is a slot and a
    literal bracket, and the two cannot be told apart from the text alone. This
    resolves that in the direction that can only weaken the check and never fail
    it wrongly: a bracket group is swallowed into the slot when it is short and
    carries no quote, which is what a date format looks like.
    """
    runs, current, i, n = [], [], 0, len(template)
    while i < n:
        c = template[i]
        if c == "/" and i + 1 < n:
            current.append(template[i + 1])
            i += 2
            continue
        if c == "$":
            if current:
                runs.append("".join(current))
                current = []
            i += 1
            if i < n and template[i] == "(":
                close = template.find(")", i)
                if 0 <= close <= i + 40 and '"' not in template[i:close]:
                    i = close + 1
            continue
        current.append(c)
        i += 1
    if current:
        runs.append("".join(current))
    return runs


def ends_agree(template: str, text: str) -> bool:
    """
    The template's leading and trailing literal runs against the text's ends.

    Only the two outermost runs are used. Interior runs would need a position to
    search from, and a template's slots are not always separable from a literal
    bracket, so an interior walk can drift on text it should accept. A prefix and
    a suffix have no position to get wrong.
    """
    runs = literal_runs(template)
    if not runs:
        return True
    if not template.startswith("$") and not text.startswith(runs[0]):
        return False
    if not template.endswith("$") and not text.endswith(runs[-1]):
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--encoded", required=True)
    ap.add_argument("--templates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args()

    templates = load_templates(pathlib.Path(args.templates))
    print(f"templates: {len(templates)}")

    mapping, examples, end_failures = {}, [], []
    collisions = lines_used = records = unknown_hash = checked = 0

    raw = open(args.raw, encoding="utf-8", errors="surrogateescape")
    with open(args.encoded, encoding="utf-8", errors="surrogateescape") as enc:
        for record_line in enc:
            record = record_line.rstrip("\n")
            records += 1
            if not record.startswith("~"):
                print(f"record {records} is not a compact record: {record[:60]!r}",
                      file=sys.stderr)
                return 2
            comma = record.find(",")
            hash_part = record[1:comma] if comma >= 0 else record[1:]
            template = templates.get(hash_part)
            if template is None:
                unknown_hash += 1
                span, template_text = 1, None
            else:
                span, template_text = template["lines"], template["text"]

            original_lines = []
            for _ in range(span):
                nxt = raw.readline()
                if not nxt:
                    print(f"capture ran out at record {records}", file=sys.stderr)
                    return 2
                original_lines.append(nxt.rstrip("\n"))
            lines_used += span
            original = "\n".join(original_lines)

            if template_text is not None:
                checked += 1
                if not ends_agree(template_text, original):
                    end_failures.append(records)

            if len(examples) < args.examples and span == 1:
                examples.append({"compact": record, "original": original})

            key, value = sha(record), sha(original)
            previous = mapping.get(key)
            if previous is None:
                mapping[key] = value
            elif previous != value:
                collisions += 1
    leftover = raw.readline()
    raw.close()

    print(f"records: {records}  lines assigned: {lines_used}  "
          f"distinct compact records: {len(mapping)}")
    print(f"template-ends check: {checked} records, {len(end_failures)} failures")
    if unknown_hash:
        print(f"records whose template hash was not in templates.json: {unknown_hash}")

    if leftover:
        print("capture has lines left over after the last compact record", file=sys.stderr)
        return 2
    if end_failures:
        print(f"template-ends check failed on records {end_failures[:5]}", file=sys.stderr)
        return 2
    if collisions:
        print(f"{collisions} compact records map to more than one original text",
              file=sys.stderr)
        return 2

    pathlib.Path(args.out).write_text(json.dumps({
        "records": records,
        "lines_assigned": lines_used,
        "distinct_compact_records": len(mapping),
        "template_ends_checked": checked,
        "unknown_template_hash": unknown_hash,
        "examples": examples,
        "map": mapping,
    }) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
