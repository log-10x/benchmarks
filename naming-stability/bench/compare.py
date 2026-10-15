#!/usr/bin/env python3
"""Compare the names consecutive engine releases give the same capture.

    python3 bench/compare.py <cache dir> <version> <version> [<version> ...]
    python3 bench/compare.py --render     # results.md from the committed compare.json

Reads <cache>/engine-<version>/<capture>/events.jsonl.gz for rec1155 and otel215,
each written by bench/engine.sh, and compares every pair of consecutive versions.
Writes results/compare.json and results/results.md.

Each events file holds one record per event, in input order: the pattern name
(`message_pattern`), the pattern hash (`tenx_hash`, the hash of the name), the
template hash (`templateHash`) and the event's text (its input records joined by
newlines). When two releases cut the capture into the same events, events are
compared one for one. When they do not, every input record is given the names of
the event that holds it, and records are compared, so a change in where an event
starts or ends shows up as a change for the records it moved.

Per pair:
  events (or records) whose pattern name changed, whose pattern hash changed,
  whose name or hash changed, and whose template hash changed;
  distinct patterns of the earlier release with at least one event renamed, by
  name and by hash; every such pattern listed with the names its events took.
"""

import collections
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")
CAPTURES = ("rec1155", "otel215")
ANSI_DIM = "\u001b[2m"


def load(path):
    out = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out.append((d["text"], d.get("message_pattern") or "", d.get("tenx_hash") or "",
                        d.get("templateHash") or ""))
    return out


def log_of(record):
    try:
        return json.loads(record).get("log", "")
    except ValueError:
        return record


def per_record(events):
    """One entry per input record: (record, name, hash, template, event index, position)."""
    out = []
    for k, (text, name, h, t) in enumerate(events):
        for j, rec in enumerate(text.split("\n")):
            out.append((rec, name, h, t, k, j))
    return out


def pct(a, b):
    return round(100.0 * a / b, 3) if b else None


def compare(old, new):
    same_events = len(old) == len(new) and all(a[0] == b[0] for a, b in zip(old, new))
    if same_events:
        units = [(a[1], a[2], a[3], b[1], b[2], b[3], a[0], False) for a, b in zip(old, new)]
        unit = "event"
    else:
        ro, rn = per_record(old), per_record(new)
        if len(ro) != len(rn) or any(a[0] != b[0] for a, b in zip(ro, rn)):
            sys.exit("the two runs did not read the same records")
        # A record whose event starts or ends elsewhere in the newer release.
        span_o = collections.Counter(a[4] for a in ro)
        span_n = collections.Counter(b[4] for b in rn)
        units = []
        for a, b in zip(ro, rn):
            moved = (a[5], span_o[a[4]]) != (b[5], span_n[b[4]])
            units.append((a[1], a[2], a[3], b[1], b[2], b[3], a[0], moved))
        unit = "record"
    n = len(units)
    name_ch = [u for u in units if u[0] != u[3]]
    hash_ch = [u for u in units if u[1] != u[4]]
    either = [u for u in units if u[0] != u[3] or u[1] != u[4]]
    tpl_ch = [u for u in units if u[2] != u[5]]
    moved = [u for u in units if u[7]]

    by_name = collections.defaultdict(collections.Counter)
    by_hash = collections.defaultdict(collections.Counter)
    for u in units:
        by_name[u[0]][u[3]] += 1
        by_hash[u[1]][u[4]] += 1
    changed_names = {p for p, c in by_name.items() if set(c) != {p}}
    changed_hashes = {h for h, c in by_hash.items() if set(c) != {h}}
    new_names = {u[3] for u in units} - set(by_name)

    affected_by = collections.defaultdict(list)
    for u in name_ch:
        affected_by[u[0]].append(u)
    changed = []
    for p in sorted(changed_names, key=lambda p: (-len(affected_by[p]), p)):
        affected = affected_by[p]
        sample = log_of(affected[0][6].split("\n")[0])
        changed.append({
            "name": p,
            "hash": affected[0][1],
            "units": sum(by_name[p].values()),
            "renamed_units": len(affected),
            "new_names": by_name[p].most_common(),
            "moved_between_events": sum(1 for u in affected if u[7]),
            "ansi_dim_code": sum(1 for u in affected if ANSI_DIM in u[6]),
            "sample": sample[:200],
        })
    return {
        "unit": unit,
        "same_events": same_events,
        "events_old": len(old),
        "events_new": len(new),
        "units": n,
        "name_changed": len(name_ch), "name_changed_pct": pct(len(name_ch), n),
        "hash_changed": len(hash_ch), "hash_changed_pct": pct(len(hash_ch), n),
        "name_or_hash_changed": len(either), "name_or_hash_changed_pct": pct(len(either), n),
        "template_changed": len(tpl_ch), "template_changed_pct": pct(len(tpl_ch), n),
        "moved_between_events": len(moved),
        "patterns_old": len(by_name),
        "patterns_renamed": len(changed_names), "patterns_renamed_pct": pct(len(changed_names), len(by_name)),
        "hashes_old": len(by_hash),
        "hashes_changed": len(changed_hashes), "hashes_changed_pct": pct(len(changed_hashes), len(by_hash)),
        "names_new_in_later": len(new_names),
        "changed_patterns": changed,
    }


def ansi_dim_records(path):
    """Records whose message opens with the ANSI dim code, the case 1.1.141 changed."""
    n = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if log_of(line).startswith(ANSI_DIM):
                n += 1
    return n


def main():
    if sys.argv[1:] == ["--render"]:
        with open(os.path.join(RESULTS, "compare.json")) as f:
            print(render(json.load(f)), end="")
        return
    cache, versions = sys.argv[1], sys.argv[2:]
    out = {"versions": versions, "pairs": {}, "captures": {}}
    for cap in CAPTURES:
        out["captures"][cap] = {"records_opening_with_ansi_dim_code":
                                ansi_dim_records(os.path.join(cache, f"{cap}.log"))}
        runs = {v: load(os.path.join(cache, f"engine-{v}", cap, "events.jsonl.gz")) for v in versions}
        for a, b in zip(versions, versions[1:]):
            out["pairs"][f"{cap} {a} -> {b}"] = compare(runs[a], runs[b])
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "compare.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    with open(os.path.join(RESULTS, "results.md"), "w") as f:
        f.write(render(out))
    print(render(out), end="")


def render(out):
    L = ["# Results", "", "Generated by `bench/compare.py` from the engine runs.", "",
         "| capture | releases | unit | units | name changed | hash changed | name or hash changed | "
         "template hash changed | patterns renamed | hashes changed |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for key, r in out["pairs"].items():
        cap, pair = key.split(" ", 1)
        L.append(f"| {cap} | {pair} | {r['unit']} | {r['units']:,} | {r['name_changed']:,} "
                 f"({r['name_changed_pct']}%) | {r['hash_changed']:,} ({r['hash_changed_pct']}%) | "
                 f"{r['name_or_hash_changed']:,} ({r['name_or_hash_changed_pct']}%) | "
                 f"{r['template_changed']:,} ({r['template_changed_pct']}%) | "
                 f"{r['patterns_renamed']:,} of {r['patterns_old']:,} | "
                 f"{r['hashes_changed']:,} of {r['hashes_old']:,} |")
    L.append("")
    L.append("Records whose message opens with the ANSI dim code (the lines 1.1.141 starts a new event on): "
             + ", ".join(f"{c} {v['records_opening_with_ansi_dim_code']:,}" for c, v in out["captures"].items()) + ".")
    L.append("")
    for key, r in out["pairs"].items():
        L.append(f"## {key}")
        L.append("")
        L.append(f"Events: {r['events_old']:,} and {r['events_new']:,}; "
                 f"{'the same events, compared one for one' if r['same_events'] else 'the events differ, so records are compared'}"
                 f"; {r['moved_between_events']:,} records sit in an event that starts or ends elsewhere. "
                 f"Names in the later release that the earlier did not use: {r['names_new_in_later']:,}.")
        L.append("")
        if r["changed_patterns"]:
            L.append("| pattern | its units | renamed | new names (units) | moved between events | with the ANSI dim code | sample |")
            L.append("|---|---:|---:|---|---:|---:|---|")
            for c in r["changed_patterns"]:
                news = ", ".join(f"`{n}` ({k:,})" for n, k in c["new_names"] if n != c["name"])
                sample = c["sample"].replace("|", "\\|").replace("\u001b", "\\u001b")
                L.append(f"| `{c['name']}` | {c['units']:,} | {c['renamed_units']:,} | {news} | "
                         f"{c['moved_between_events']:,} | {c['ansi_dim_code']:,} | `{sample}` |")
        else:
            L.append("No pattern changed.")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
