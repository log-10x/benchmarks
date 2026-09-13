#!/usr/bin/env python3
"""Fold one run's rows into results/results.csv without losing the other cases.

`./run.sh c_msg` measures one case. Its row replaces that case's row in the
committed table and leaves the other two alone, so a subset run updates the
table rather than truncating it. Rows are written back in the canonical case
order rather than in the order they happened to be measured.
"""

import argparse
import csv
import pathlib
import sys

ORDER = ["a_asis", "b_siem", "c_msg"]


def read(path: pathlib.Path) -> tuple[list[str], dict]:
    if not path.exists() or path.stat().st_size == 0:
        return [], {}
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), {r["case"]: r for r in reader}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--into", required=True, help="the committed results.csv")
    ap.add_argument("--from", dest="src", required=True, help="this run's rows")
    args = ap.parse_args()

    into = pathlib.Path(args.into)
    fields, existing = read(into)
    new_fields, fresh = read(pathlib.Path(args.src))

    if not fresh:
        print("this run produced no rows; results.csv left alone", file=sys.stderr)
        return 1
    if fields and fields != new_fields:
        print(f"column layout changed: committed {fields}, this run {new_fields}",
              file=sys.stderr)
        return 1

    merged = dict(existing)
    merged.update(fresh)
    known = [c for c in ORDER if c in merged]
    other = sorted(c for c in merged if c not in ORDER)

    with open(into, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=new_fields)
        writer.writeheader()
        for case in known + other:
            writer.writerow(merged[case])

    replaced = sorted(set(fresh) & set(existing))
    added = sorted(set(fresh) - set(existing))
    kept = sorted(set(existing) - set(fresh))
    print(f"replaced {replaced or 'none'}, added {added or 'none'}, kept {kept or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
