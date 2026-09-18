#!/usr/bin/env python3
"""
Renders results/results.md and results/results.json from the run's artifacts.

Two primary sources, and the run reports both because neither alone answers the
question.

`type=RolloverSummary` is the daily rollup, and on Splunk 10.4.3 it is a single
line per licence pool carrying the day's total and no `idx` at all. It gives the
licence day's total and nothing per arm.

`type=Usage` is the per-minute record and does carry `idx` and `st`, so the split
between the two arms comes from there, binned to the same day. That is not a
workaround: it is what Splunk's own Monitoring Console does, whose Historic
License Usage view reads RolloverSummary when unsplit and switches to Usage the
moment you split it by index.

The two have to agree, so the run checks it: the per-index Usage bytes must sum
to the rollup's own total, to the byte. `--check` re-runs that arithmetic against
the committed results.json, so a figure edited without a rerun fails there.
"""

import argparse
import json
import pathlib
import re
import sys

GB = 1024 ** 3

ARM_OF = {
    "tenx_base/tenx_raw_json": ("baseline", "the capture as it is"),
    "tenx_enc/tenx_encoded": ("compact", "the compact events"),
    "tenx_dml/tenx_dml_raw_json": ("compact", "the template dictionary"),
    "tenx_dml/tenx_dml_pure": ("compact", "the app re-indexing each template"),
}


def num(value, places=6):
    """Fixed precision with insignificant trailing zeros dropped."""
    if value is None:
        return "n/a"
    return f"{value:.{places}f}".rstrip("0").rstrip(".") or "0"


def parse_rollover(path: pathlib.Path):
    """The licence day's total from the daily rollup, and the day it was written."""
    total, days, per_index = 0, set(), {}
    if not path.exists():
        return total, [], per_index
    for line in path.read_text(errors="replace").splitlines():
        if "type=RolloverSummary" not in line:
            continue
        b = re.search(r"\sb=(\d+)", line)
        if not b:
            continue
        total += int(b.group(1))
        day = re.match(r"(\d{2}-\d{2}-\d{4})", line)
        if day:
            days.add(day.group(1))
        # Kept for Splunk versions whose rollup does carry a per-index breakdown.
        idx = re.search(r'idx="([^"]*)"', line)
        if idx:
            per_index[idx.group(1)] = per_index.get(idx.group(1), 0) + int(b.group(1))
    return total, sorted(days), per_index


def read_json_rows(path: pathlib.Path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("preview"):
            continue
        if "result" in payload:
            rows.append(payload["result"])
    return rows


def usage_split(results: pathlib.Path):
    """Per index and sourcetype, from the per-minute Usage records."""
    per_pair, per_index = {}, {}
    for row in read_json_rows(results / "usage_by_index_sourcetype.json"):
        idx, st = row.get("idx"), row.get("st")
        b = int(row.get("bytes", 0))
        per_pair[f"{idx}/{st}"] = per_pair.get(f"{idx}/{st}", 0) + b
        per_index[idx] = per_index.get(idx, 0) + b
    return per_pair, per_index


def text_or_none(path: pathlib.Path):
    return path.read_text().strip() if path.exists() else None


def figures(results: pathlib.Path):
    rollup_total, days, rollup_per_index = parse_rollover(
        results / "license_usage_rollover.log")
    per_pair, per_index = usage_split(results)
    baseline = sum(v for k, v in per_pair.items() if ARM_OF.get(k, ("", ""))[0] == "baseline")
    compact = sum(v for k, v in per_pair.items() if ARM_OF.get(k, ("", ""))[0] == "compact")
    reindex = per_pair.get("tenx_dml/tenx_dml_pure", 0)
    return {
        "rollup_total": rollup_total,
        "days": days,
        "rollup_per_index": rollup_per_index,
        "per_pair": per_pair,
        "per_index": per_index,
        "baseline": baseline,
        "compact": compact,
        "reindex": reindex,
    }


def pct(part, whole):
    return round(100.0 * (1 - part / whole), 2) if whole else None


def check(results: pathlib.Path) -> int:
    """
    The falsifier. Recomputes from the two primary files and compares with the
    committed results.json, and separately asserts the identity the whole table
    rests on: the per-index Usage bytes sum to the rollup's own daily total.
    """
    f = figures(results)
    committed = json.loads((results / "results.json").read_text())
    lic = committed["licence_metered"]
    problems = []

    def same(label, got, want):
        if got != want:
            problems.append(f"{label}: recomputed {got}, results.json says {want}")

    same("per index and sourcetype", f["per_pair"], lic["per_index_sourcetype_bytes"])
    same("baseline bytes", f["baseline"], lic["baseline_bytes"])
    same("compact bytes", f["compact"], lic["compact_bytes"])
    same("app re-index bytes", f["reindex"], lic["app_reindex_bytes"])
    same("rollup total", f["rollup_total"], lic["licence_day_total_bytes"])
    same("reduction pct", pct(f["compact"], f["baseline"]), lic["reduction_pct"])
    same("rollup day", f["days"], committed["licence_day_rollup_written"])

    summed = sum(f["per_index"].values())
    if summed != f["rollup_total"]:
        problems.append(
            f"the per-index Usage bytes sum to {summed:,} and the daily rollup "
            f"says {f['rollup_total']:,}; the split and the total disagree")

    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        return 1
    print(f"the committed figures follow from the primary files: baseline "
          f"{f['baseline']:,} bytes, compact {f['compact']:,} bytes, reduction "
          f"{pct(f['compact'], f['baseline'])}%, and the per-index bytes sum to "
          f"the rollup's own {f['rollup_total']:,}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--engine", default="")
    ap.add_argument("--splunk-version", default="")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    results = pathlib.Path(args.results)
    if args.check:
        return check(results)

    data = pathlib.Path(args.data)
    capture = data / "base" / "otel-sample-200mb.log"
    capture_bytes = capture.stat().st_size
    capture_lines = sum(1 for _ in open(capture, "rb"))

    encoded, templates = data / "compact" / "encoded.log", data / "compact" / "templates.json"
    encoded_bytes, templates_bytes = encoded.stat().st_size, templates.stat().st_size
    encoded_records = sum(1 for _ in open(encoded, "rb"))
    template_count = sum(1 for _ in open(templates, "rb"))

    control_facts = {}
    facts = data / "encode_facts.txt"
    if facts.exists():
        control_facts = dict(line.split("=", 1)
                             for line in facts.read_text().split() if "=" in line)

    f = figures(results)
    baseline, compact, reindex = f["baseline"], f["compact"], f["reindex"]
    wire = compact - reindex

    expansion = json.loads((results / "expansion.json").read_text())
    local_path = results / "expansion_local_tz.json"
    expansion_local = json.loads(local_path.read_text()) if local_path.exists() else None

    payload = {
        "splunk_version": args.splunk_version,
        "engine_image": args.engine,
        "container_timezone": text_or_none(data / "tz.txt"),
        "splunk_app_commit": text_or_none(data / "app_sha.txt"),
        "forwarder_path": "Universal Forwarder, file monitor, S2S to the indexer on 9997",
        "licence": "Splunk Enterprise download trial, 500 MB/day",
        "licence_day_rollup_written": f["days"],
        "dataset": {
            "name": "otel-sample-200mb.log (otel-sample-v2)",
            "bytes": capture_bytes,
            "lines": capture_lines,
            "sha256": "aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432",
        },
        "on_disk": {
            "capture_bytes": capture_bytes,
            "encoded_bytes": encoded_bytes,
            "templates_bytes": templates_bytes,
            "compact_bytes": encoded_bytes + templates_bytes,
            "reduction_pct": pct(encoded_bytes + templates_bytes, capture_bytes),
            "encoded_records": encoded_records,
            "templates": template_count,
            "roundtrip": text_or_none(data / "roundtrip.txt"),
        },
        "licence_metered": {
            "source_of_total": "type=RolloverSummary, the daily rollup",
            "source_of_split": "type=Usage, the per-minute records, binned to the day",
            "licence_day_total_bytes": f["rollup_total"],
            "per_index_bytes": f["per_index"],
            "per_index_sourcetype_bytes": f["per_pair"],
            "rollup_carries_per_index": bool(f["rollup_per_index"]),
            "baseline_bytes": baseline,
            "compact_bytes": compact,
            "app_reindex_bytes": reindex,
            "compact_bytes_without_app_reindex": wire,
            "baseline_gb_per_day": round(baseline / GB, 6),
            "compact_gb_per_day": round(compact / GB, 6),
            "reduction_pct": pct(compact, baseline),
            "reduction_pct_without_app_reindex": pct(wire, baseline),
            "split_sums_to_rollup_total": sum(f["per_index"].values()) == f["rollup_total"],
        },
        "expansion": expansion,
        "expansion_local_tz": expansion_local,
    }
    if control_facts:
        ctl = int(control_facts.get("control_encoded_bytes", 0)) + \
              int(control_facts.get("control_templates_bytes", 0))
        payload["on_disk"]["control_compact_bytes"] = ctl
        payload["on_disk"]["control_reduction_pct"] = pct(ctl, capture_bytes)

    lic, disk = payload["licence_metered"], payload["on_disk"]
    md = ["# What 10x in front of Splunk does to licence-metered volume\n"]
    md.append(f"**{args.splunk_version}**. Forwarder path: {payload['forwarder_path']}. "
              f"Licence: {payload['licence']}. Rollup written "
              f"{', '.join(f['days']) or 'none'} at local midnight, closing the "
              f"licence day that holds the whole run. Container timezone "
              f"`{payload['container_timezone']}`.\n")

    md.append("## The two arms, in Splunk's own meter\n")
    md.append("| Arm | Index / sourcetype | What it is | Licence-metered bytes | GB/day |")
    md.append("|---|---|---|---:|---:|")
    for key, (arm, what) in ARM_OF.items():
        if key in f["per_pair"]:
            b = f["per_pair"][key]
            md.append(f"| {arm} | `{key}` | {what} | {b:,} | {num(b / GB)} |")
    md.append(f"| **baseline** | | **total** | **{baseline:,}** | "
              f"**{num(lic['baseline_gb_per_day'])}** |")
    md.append(f"| **compact** | | **total** | **{compact:,}** | "
              f"**{num(lic['compact_gb_per_day'])}** |")
    md.append("")
    md.append(f"**Licence-metered reduction: {num(lic['reduction_pct'], 2)}%.** "
              f"Counting only what crosses the wire, with the app's own re-index "
              f"of the templates left out, it is "
              f"{num(lic['reduction_pct_without_app_reindex'], 2)}%; that re-index "
              f"costs {reindex:,} metered bytes and no measurement taken on files "
              f"can see it.\n")

    md.append("## Where each figure comes from\n")
    md.append(f"The daily rollup, `type=RolloverSummary`, is one line per licence "
              f"pool on this version and carries no `idx`, so it gives the licence "
              f"day's total and nothing per arm: **{f['rollup_total']:,} bytes**, "
              f"{num(f['rollup_total'] / GB)} GB. The split between the arms comes "
              f"from `type=Usage`, the per-minute records, binned to the same day. "
              f"That is what Splunk's own Monitoring Console does: its Historic "
              f"License Usage view reads RolloverSummary when unsplit and switches "
              f"to Usage the moment it is split by index.\n")
    md.append(f"The two agree to the byte. The per-index Usage bytes sum to "
              f"{sum(f['per_index'].values()):,}, which is the rollup's own total: "
              f"**{'yes' if lic['split_sums_to_rollup_total'] else 'NO'}**.\n")
    for label, path in (("no split, from the rollup", "mc_no_split.txt"),
                        ("split by index, from the per-minute records", "mc_by_index.txt")):
        body = text_or_none(results / path)
        if body:
            md.append(f"Monitoring Console, Historic License Usage, {label}:\n")
            md.append("```")
            md.append(body)
            md.append("```\n")

    md.append("## The same data measured as files, for comparison\n")
    md.append(f"- capture {capture_bytes:,} bytes, {capture_lines:,} lines")
    md.append(f"- compact form {disk['compact_bytes']:,} bytes ({encoded_bytes:,} "
              f"encoded + {templates_bytes:,} templates), {encoded_records:,} "
              f"records, {template_count:,} templates")
    md.append(f"- file reduction **{num(disk['reduction_pct'], 2)}%**, round trip "
              f"{disk['roundtrip']}")
    if "control_reduction_pct" in disk:
        md.append(f"- with the engine's own `maxRecurIndexes: 10`, which this app "
                  f"cannot decode, the file reduction would be "
                  f"{num(disk['control_reduction_pct'], 2)}%")
    md.append("")

    slice_path = results / "worst_slice.json"
    if slice_path.exists():
        sl = json.loads(slice_path.read_text())
        ranked = sl["ranked_worst_first"]
        payload["worst_slice"] = ranked[0] if ranked else None
        md.append("## Where the gap is smallest\n")
        md.append(f"Per Kubernetes container, compact events against the text they "
                  f"came from, both on the meter's basis. The template dictionary "
                  f"is not split across containers and is left out of this table, "
                  f"so each row reads slightly better than the same slice would in "
                  f"a deployment. Containers with fewer than "
                  f"{sl['min_events_to_rank']} events are not ranked.\n")
        md.append("| | Container | Events | Raw bytes | Compact bytes | Reduction |")
        md.append("|---|---|---:|---:|---:|---:|")
        rows = [("**worst**", ranked[0])] + [("", r) for r in ranked[1:3]] \
               + [("best", ranked[-1])] if ranked else []
        for label, row in rows:
            md.append(f"| {label} | `{row['container']}` | {row['events']:,} | "
                      f"{row['raw_bytes']:,} | {row['compact_bytes']:,} | "
                      f"{num(row['reduction_pct'], 2)}% |")
        md.append("")

    md.append("## Expansion\n")
    md.append("Every compact event read back through the app's own `tenx-inflate` "
              "macro and compared, byte for byte, with the text that went in.\n")
    md.append("| Search head timezone | Events | Byte-identical | Wrong text | Unexpanded |")
    md.append("|---|---:|---:|---:|---:|")
    md.append(f"| UTC | {expansion['rows']:,} | {expansion['matched']:,} "
              f"({num(expansion['match_pct'], 2)}%) | {expansion['wrong_text']:,} | "
              f"{expansion['unexpanded']:,} |")
    if expansion_local:
        md.append(f"| {payload['container_timezone']} | {expansion_local['rows']:,} | "
                  f"{expansion_local['matched']:,} "
                  f"({num(expansion_local['match_pct'], 2)}%) | "
                  f"{expansion_local['wrong_text']:,} | "
                  f"{expansion_local['unexpanded']:,} |")
    md.append("")
    md.append(f"Engine `{args.engine}`. 10x Splunk app "
              f"`{payload['splunk_app_commit']}`.\n")

    (results / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    (results / "results.md").write_text("\n".join(md) + "\n")
    print(f"wrote {results/'results.md'} and {results/'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
