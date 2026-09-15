#!/usr/bin/env python3
"""Compose the results file from the per-gap JSON each script wrote.

Every number in the output comes from `results/gap<N>.json`, which the gap
scripts write from the run. The prose for each gap is read from
`notes/gap<N>.md` when that file exists, so the words are written by hand and
the numbers are not.

  render.py --results results --notes notes --out results/clickstack-e2e-gaps-<date>.md
"""
import argparse
import json
import pathlib
import time


def load(results: pathlib.Path, n: int):
    p = results / f"gap{n}.json"
    return json.loads(p.read_text()) if p.exists() else None


def note(notes: pathlib.Path, n: int) -> list[str]:
    p = notes / f"gap{n}.md"
    return [p.read_text().rstrip(), ""] if p.exists() else []


def fmt(v) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "" if v is None else str(v)


def secs(us) -> str:
    try:
        return f"{int(us) / 1_000_000:.1f}"
    except (TypeError, ValueError):
        return ""


def query_table(rows, cols=("read_rows", "read_bytes", "s3_get", "s3_list", "ms", "ms_warm")) -> list[str]:
    head = {"read_rows": "Rows read", "read_bytes": "Bytes read", "s3_get": "S3 GET",
            "s3_list": "S3 LIST", "ms": "ms", "ms_warm": "ms warm", "cpu_us": "CPU us"}
    out = ["| Query | Answer | " + " | ".join(head[c] for c in cols) + " |",
           "|---|---|" + "---:|" * len(cols)]
    for r in rows or []:
        answer = (r.get("answer") or "").replace("|", "/").replace("\t", " = ")[:70]
        out.append(f"| {r['name']} | {answer} | " +
                   " | ".join(fmt(r.get(c)) for c in cols) + " |")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    results, notes = pathlib.Path(args.results), pathlib.Path(args.notes)
    md = [f"# ClickStack end to end: the six gaps, {time.strftime('%Y-%m-%d')}", "",
          "Every number below comes from a run of the script named in its section, over the",
          "whole 197,430 line capture, against the PATCHED engine. A gap that could not be",
          "closed says so in its own section and says why.", ""]

    # ------------------------------------------------------------------ gap 1
    g = load(results, 1)
    md += ["## Gap 1: multi-day pruning", ""]
    md += note(notes, 1)
    if g:
        md += [f"One run of the route over {fmt(g['feed_lines'])} lines: "
               f"{fmt(g['wire_records'])} records returned by the receiver, "
               f"{fmt(g['hot_rows'])} into the hot table, {fmt(g['cold_rows'])} into "
               f"{g['run_objects']} objects. Those objects were then replicated across "
               f"{g['days']} day partitions, {g['batches_per_service_day']} objects per "
               f"service and day: {fmt(g['replicated_objects'])} objects, "
               f"{g['replicated_bytes']}, {fmt(g['replicated_rows'])} rows. "
               f"One day holds {fmt(g['objects_one_day'])} objects; all days hold "
               f"{fmt(g['objects_all_days'])}. The day probed is {g['day_probed']}, the "
               f"service {g['service_probed']}.", ""]
        md += query_table(g["queries"]) + [""]
    else:
        md += ["The run did not produce `results/gap1.json`.", ""]

    # ------------------------------------------------------------------ gap 2
    g = load(results, 2)
    md += ["## Gap 2: the cold branch in Vector", ""]
    md += note(notes, 2)
    if g:
        md += ["| Question | Answer |", "|---|---|",
               f"| Vector build | `{g['vector_version']}` |",
               f"| `encoding.codec: parquet` accepted, on the build above | "
               f"{'yes' if g['parquet_codec_accepted'] else 'NO'} |",
               f"| codec the run used | `{g['codec_used']}` |",
               f"| objects Vector wrote | {g['vector_objects']} |",
               f"| bytes Vector wrote | {g['vector_bytes']} |",
               f"| rows readable through the S3 table | {fmt(g['cold_rows_readable'])} |",
               f"| rows on the wire | {fmt(g['wire']['total'])} |",
               f"| rows in the hot table | {fmt(g['hot_rows'])} |",
               f"| Parquet copy, written by ClickHouse | {fmt(g['parquet_objects'])} objects, "
               f"{g['parquet_bytes']}, {fmt(g['parquet_rows'])} rows |", ""]
        md += ["What Vector's own binary says about the parquet codec:", "", "```",
               g["parquet_probe_output"].strip(), "```", ""]
        md += query_table(g["queries"]) + [""]
    else:
        md += ["The run did not produce `results/gap2.json`.", ""]

    # ------------------------------------------------------------------ gap 3
    g = load(results, 3)
    md += ["## Gap 3: the Retriever over this layout", ""]
    md += note(notes, 3)
    if g:
        a, j = g.get("index_as_written") or {}, g.get("index_as_jsonl") or {}
        md += ["| Shape indexed | Objects attempted | Exit code | Index artifacts written |",
               "|---|---:|---:|---:|",
               f"| as the collector wrote it, one JSON array per object | "
               f"{fmt(a.get('objects_attempted'))} | {fmt(a.get('exit_code'))} | "
               f"{fmt(a.get('index_artifacts'))} |",
               f"| the same records, one JSON object per line | "
               f"{fmt(j.get('objects_attempted'))} | {fmt(j.get('exit_code'))} | "
               f"{fmt(j.get('index_artifacts'))} |", "",
               f"Objects indexed: {fmt(g.get('objects_indexed'))} of "
               f"{fmt(g.get('objects_in_export'))} in the export, written by "
               f"{(g.get('cold_export') or {}).get('written_by', 'an earlier gap run')}. "
               f"The query asked for pattern hash `{g['hash_probed']}` over a one day window "
               f"against the {g['query_shape']} index: exit {g['query_exit']} in "
               f"{fmt(g['query_ms'])} ms.", ""]
        if a.get("log_tail"):
            md += ["The indexer's last words on the objects as written:", "", "```",
                   a["log_tail"].strip()[-1200:], "```", ""]
    else:
        md += ["The run did not produce `results/gap3.json`.", ""]

    # ------------------------------------------------------------------ gap 4
    g = load(results, 4)
    md += ["## Gap 4: durable handoff under failure", ""]
    md += note(notes, 4)
    if g:
        md += ["| Measure | " + " | ".join(a["arm"] for a in g["arms"]) + " |",
               "|---|" + "---:|" * len(g["arms"])]
        rows = [("input lines", "input_lines"), ("hot rows at the kill", "killed_at_hot_rows"),
                ("seconds down", "down_seconds"),
                ("records the receiver returned", "wire_records"),
                ("rows in the hot table", "hot_rows"), ("rows in the objects", "cold_rows"),
                ("sequence numbers found", "seq_occurrences"),
                ("distinct sequence numbers", "seq_distinct"),
                ("sequence numbers seen more than once", "seq_duplicated"),
                ("duplicate deliveries", "seq_duplicate_lines"),
                ("input lines never stored", "seq_missing"),
                ("pattern hashes on the wire", "hashes_on_wire"),
                ("pattern hashes stored", "hashes_stored"),
                ("records short, counted by hash", "records_short_by_hash"),
                ("records over, counted by hash", "records_over_by_hash")]
        for label, key in rows:
            md.append(f"| {label} | " + " | ".join(fmt(a.get(key)) for a in g["arms"]) + " |")
        md.append("")
    else:
        md += ["The run did not produce `results/gap4.json`.", ""]

    # ------------------------------------------------------------------ gap 5
    g = load(results, 5)
    md += ["## Gap 5: query and alert correctness", ""]
    md += note(notes, 5)
    if g:
        md += [f"Before: {fmt(g['before']['hot_rows'])} rows in the hot table, "
               f"{g['before']['objects']} objects. After: {fmt(g['after']['hot_rows'])} hot, "
               f"{fmt(g['after']['cold_rows'])} in {g['after']['objects']} objects. "
               f"The type asked for is `{g['type_hash']}`; the word is `{g['word']}`, "
               f"{'only on the cold side' if g['word_only_cold'] else 'NOT only on the cold side'}.",
               ""]
        d = g.get("duplicates")
        if d:
            md += ["| Side | Rows stored | Distinct (Timestamp, Body) | Stored more than once |",
                   "|---|---:|---:|---:|"]
            for label, a, b in (("before, hot table", "before_total", "before_distinct"),
                                ("after, hot table", "after_hot_total", "after_hot_distinct"),
                                ("after, the objects", "after_cold_total", "after_cold_distinct")):
                md.append(f"| {label} | {fmt(d[a])} | {fmt(d[b])} | {fmt(d[a] - d[b])} |")
            md.append("")
        surfaces = ["before, hot table", "after, hot table", "after, merge table",
                    "before, counts table", "after, counts table"]
        by_q: dict[str, dict[str, str]] = {}
        for r in g["queries"] or []:
            q, _, surface = r["name"].partition(": ")
            by_q.setdefault(q, {})[surface] = ((r.get("answer") or "")
                                              .replace("|", "/").replace("\t", " = ")[:60])
        md += ["| Question | " + " | ".join(surfaces) + " |",
               "|---|" + "---|" * len(surfaces)]
        for q, answers in by_q.items():
            md.append(f"| {q} | " + " | ".join(answers.get(s, "") for s in surfaces) + " |")
        md.append("")
        alert = g.get("alert")
        if alert:
            md += ["The alert, over the HyperDX API. The rule is "
                   f"\"{alert['threshold_rule']}\", threshold {fmt(alert['threshold'])}.", "",
                   "| Surface | Count the surface returns | Would fire | Saved search | Alert |",
                   "|---|---:|---|---|---|"]
            keymap = {"before, hot table": "before", "after, hot table": "after",
                      "after, merge table": "merge", "after, counts table": None}
            for surface, count in alert["counts"].items():
                key = keymap.get(surface)
                created = (alert.get("alerts") or {}).get(key, {}) if key else {}
                md.append(f"| {surface} | {fmt(count)} | "
                          f"{'yes' if alert['would_fire'][surface] else 'no'} | "
                          f"{created.get('saved_search_status', 'not attempted')} | "
                          f"{created.get('alert_status', 'not attempted')} |")
            md.append("")
    else:
        md += ["The run did not produce `results/gap5.json`.", ""]

    # ------------------------------------------------------------------ gap 6
    g = load(results, 6)
    md += ["## Gap 6: incremental economics against a collector-only policy", ""]
    md += note(notes, 6)
    if g:
        arms = g["arms"]
        md += [f"The two chattiest services, read off the first arm's hot table: "
               f"{', '.join(x for x in g['chattiest'] if x)}. The type asked for is "
               f"`{g.get('type_hash','')}`, the word is `{g.get('word','')}`.", ""]
        md += ["| Measure | " + " | ".join(a["arm"] for a in arms) + " |",
               "|---|" + "---:|" * len(arms)]
        rows = [("rows in the hot table", lambda a: fmt(a["hot_rows"])),
                ("bytes in the hot table", lambda a: fmt(a["hot_bytes"])),
                ("active parts", lambda a: fmt(a["hot_parts"])),
                ("insert CPU, seconds", lambda a: secs(a["insert_cpu_us"])),
                ("insert statements", lambda a: fmt(a["inserts"])),
                ("merge CPU, seconds", lambda a: secs(a["merge_cpu_us"])),
                ("merges", lambda a: fmt(a["merges"])),
                ("insert plus merge CPU, seconds",
                 lambda a: secs(a["insert_cpu_us"] + a["merge_cpu_us"])),
                ("counts table merge CPU, seconds",
                 lambda a: secs(a.get("counts_merge_cpu_us", 0))),
                ("objects written", lambda a: str(a["objects"])),
                ("rows in the objects", lambda a: fmt(a["cold_rows"]))]
        for label, f in rows:
            md.append(f"| {label} | " + " | ".join(f(a) for a in arms) + " |")
        md.append("")
        md += ["The three questions, per arm:", "",
               "| Question | " + " | ".join(a["arm"] for a in arms) + " |",
               "|---|" + "---|" * len(arms)]
        names: list[str] = []
        for a in arms:
            for r in a.get("queries") or []:
                if r["name"] not in names:
                    names.append(r["name"])
        for name in names:
            cells = []
            for a in arms:
                hit = next((r for r in (a.get("queries") or []) if r["name"] == name), None)
                cells.append(((hit.get("answer") or "").replace("|", "/").replace("\t", " = ")[:60])
                             if hit else "not asked")
            md.append(f"| {name} | " + " | ".join(cells) + " |")
        md.append("")
    else:
        md += ["The run did not produce `results/gap6.json`.", ""]

    tail = notes / "tail.md"
    if tail.exists():
        md += [tail.read_text().rstrip(), ""]

    pathlib.Path(args.out).write_text("\n".join(md) + "\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
