#!/usr/bin/env python3
"""Read the second-rung measurement out of ClickHouse and write results/typed-layout-<date>.md."""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys

TABLES = [
    ("native", "otel_logs_native_zstd1", "one row per captured line, Body is the message"),
    ("native_folded", "otel_logs_native_folded_zstd1", "one row per event, Body is the original text"),
    ("compact_text", "otel_logs_compact_zstd1", "Body is the compact event as one string, ClickStack sort key"),
    ("compact_sorted", "otel_logs_compact_sorted", "same, template hash materialised and added to the sort key"),
    ("compact_typed", "otel_logs_compact_typed", "Body replaced by hash + typed value arrays, hash in the sort key"),
    ("compact_typed_bytemplate", "otel_logs_compact_typed_bytemplate", "typed, sorted by (service, template, time)"),
]
PAYLOAD = {"Body", "templateHash", "slot_kinds", "ts_vals", "num_vals", "str_vals"}


def ch(container, sql):
    out = subprocess.run(["docker", "exec", "-i", container, "clickhouse-client",
                          "--allow_experimental_full_text_index=1", "--format", "TabSeparated",
                          "--query", sql], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"{sql}\n{out.stderr.strip()}")
    return [line.split("\t") for line in out.stdout.strip().splitlines() if line]


def fmt(n):
    return f"{int(n):,}"


def rel(value, control):
    """'3.7% smaller' or '4.6% larger', never a signed percentage next to a direction word."""
    d = (value / control - 1) * 100
    return f"{abs(d):.1f}% {'larger' if d > 0 else 'smaller'}"


def pct(new, old):
    return f"{(1 - new / old) * 100:.1f}%" if old else "n/a"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--typed-manifest", required=True)
    args = ap.parse_args()
    q = lambda sql: ch(args.container, sql)
    names = [t[1] for t in TABLES]
    in_list = ",".join(f"'{n}'" for n in names)

    totals = {r[0]: {"rows": int(r[1]), "bytes_on_disk": int(r[2])} for r in q(f"""
        SELECT table, sum(rows), sum(bytes_on_disk) FROM system.parts
        WHERE database='bench' AND active AND table IN ({in_list}) GROUP BY table""")}
    columns = {}
    for table, column, comp, uncomp in q(f"""
        SELECT table, column, sum(column_data_compressed_bytes), sum(column_data_uncompressed_bytes)
        FROM system.parts_columns WHERE database='bench' AND active AND table IN ({in_list})
        GROUP BY table, column"""):
        columns.setdefault(table, {})[column] = {"c": int(comp), "u": int(uncomp)}
    indexes = {r[0]: int(r[1]) for r in q(f"""
        SELECT table, sum(data_compressed_bytes) FROM system.data_skipping_indices
        WHERE database='bench' AND table IN ({in_list}) GROUP BY table""")}
    dictionary = int(q("SELECT sum(bytes_on_disk) FROM system.parts WHERE database='tenx' AND table='templates' AND active")[0][0])

    ingest = {}
    for kind, table, cpus, walls, rows in q("""
        SELECT extract(query, '/\\*(ingest|merge)-') AS k,
               extract(query, '/\\*(?:ingest|merge)-([a-z_0-9]+)\\*/') AS t,
               arrayStringConcat(groupArray(toString(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds'])), ' '),
               arrayStringConcat(groupArray(toString(query_duration_ms)), ' '),
               max(written_rows)
        FROM system.query_log WHERE type='QueryFinish' AND t != '' GROUP BY k, t"""):
        cpu_runs = sorted(int(c) for c in cpus.split())
        wall_runs = sorted(int(w) for w in walls.split())
        ingest.setdefault(table.removesuffix("_clone"), {})[kind] = {
            "cpu_us_fastest": cpu_runs[0], "cpu_us_runs": cpu_runs,
            "wall_ms_fastest": wall_runs[0], "wall_ms_runs": wall_runs, "rows": int(rows)}
    text_index = {r[0]: int(r[1]) for r in q(f"""
        SELECT table, data_compressed_bytes FROM system.data_skipping_indices
        WHERE database='bench' AND name='idx_lower_body' AND table IN ({in_list})""")}

    typed_manifest = json.loads(pathlib.Path(args.typed_manifest).read_text())
    results = {"totals": totals, "columns": columns, "skip_indexes": indexes,
               "text_index_bytes": text_index,
               "dictionary_bytes_on_disk": dictionary, "ingest": ingest,
               "typed_manifest": typed_manifest}
    out_dir = pathlib.Path(args.results)
    (out_dir / "typed.json").write_text(json.dumps(results, indent=2) + "\n")

    def payload(table):
        return sum(v["c"] for k, v in columns[table].items() if k in PAYLOAD)

    def others(table):
        return sum(v["c"] for k, v in columns[table].items() if k not in PAYLOAD)

    def total(table):
        return totals[table]["bytes_on_disk"] + (dictionary if "compact" in table else 0)

    native = "otel_logs_native_zstd1"
    folded = "otel_logs_native_folded_zstd1"
    L = []
    add = L.append
    date = datetime.date.today().isoformat()
    add("# The second rung: compact events stored the way ClickHouse wants them")
    add("")
    add(f"Measured {date} by `run_typed.sh`, on the container `run.sh` left up. Same capture, "
        "same ClickHouse, same ZSTD(1). Everything is `system.parts`, `system.parts_columns`, "
        "`system.data_skipping_indices` and `system.query_log` after `OPTIMIZE FINAL`.")
    add("")
    add("## Why this exists")
    add("")
    add("`clickstack-storage` stored the compact event as one text string in `Body`, which is "
        "what the ClickHouse app does today and the worst shape ClickHouse allows for it. "
        "ClickHouse's own log-clustering post measured that rung at 22x against 19x raw, then "
        "45x once the template sat in a low-cardinality column and the values in typed columns. "
        "This file climbs the same ladder with the same compact events: first add the template "
        "hash to the sort key, then replace the text with typed arrays.")
    add("")
    add("## The layouts")
    add("")
    add("| Layout | Rows | What it is |")
    add("|---|---:|---|")
    for key, table, desc in TABLES:
        add(f"| `{key}` | {fmt(totals[table]['rows'])} | {desc} |")
    add("")
    add(f"The typed layout carries {fmt(typed_manifest['value_slots'])} value slots: "
        f"{fmt(typed_manifest['timestamp_values'])} timestamps, "
        f"{fmt(typed_manifest['integer_values'])} integers, "
        f"{fmt(typed_manifest['text_values'])} text. Every row was reversed to its compact "
        "event byte for byte before it was written, and `run_typed.sh` rebuilds it again "
        "inside ClickHouse and compares hash sums with the text layout.")
    add("")
    add("## On disk")
    add("")
    add("`payload` is the column or columns that hold the message: `Body`, or the five typed "
        "columns. `total` is `bytes_on_disk`, plus the template dictionary for every compact "
        "layout. Skip indexes are shown because the typed layouts have no `Body` and so no "
        "`idx_lower_body`; that is a real saving and a real loss of the text index, both.")
    add("")
    add("| Layout | payload | payload vs native_folded | other columns | text index on Body | all skip indexes | total + dict | total vs native | total vs native_folded |")
    add("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for key, table, _ in TABLES:
        add(f"| `{key}` | {fmt(payload(table))} | {pct(payload(table), payload(folded))} | "
            f"{fmt(others(table))} | {fmt(text_index.get(table, 0))} | {fmt(indexes.get(table, 0))} | "
            f"{fmt(total(table))} | {pct(total(table), total(native))} | "
            f"{pct(total(table), total(folded))} |")
    add("")
    add(f"Template dictionary on disk: {fmt(dictionary)} bytes, included in every compact total.")
    add("")
    add("## The typed columns, one by one")
    add("")
    add("| Column | compact_typed compressed | uncompressed | bytemplate compressed |")
    add("|---|---:|---:|---:|")
    t1, t2 = "otel_logs_compact_typed", "otel_logs_compact_typed_bytemplate"
    for col in ("templateHash", "slot_kinds", "ts_vals", "num_vals", "str_vals"):
        add(f"| `{col}` | {fmt(columns[t1][col]['c'])} | {fmt(columns[t1][col]['u'])} | "
            f"{fmt(columns[t2][col]['c'])} |")
    add(f"| `Body`, in compact_text, for scale | {fmt(columns['otel_logs_compact_zstd1']['Body']['c'])} | "
        f"{fmt(columns['otel_logs_compact_zstd1']['Body']['u'])} | |")
    add(f"| `Body`, in native_folded, for scale | {fmt(columns[folded]['Body']['c'])} | "
        f"{fmt(columns[folded]['Body']['u'])} | |")
    add("")
    add("## Ingest cost, measured cleanly")
    add("")
    add("Each layout copied table-to-table with `INSERT ... SELECT` into a fresh table of the same "
        "shape, then `OPTIMIZE FINAL`. No JSON is parsed on any side, so the CPU is what "
        "ClickHouse spends turning rows into compressed columns for that layout, and then "
        "merging them. `clickstack-storage` could not separate this from JSON parsing; this can.")
    add("")
    add("Three copies per layout, fastest kept, every run shown. The first copy of `native` on "
        "a loaded host read 10 s in one run and 4.7 s the next, so a single run is not a number.")
    add("")
    add("| Layout | insert CPU s, fastest | every run | merge CPU s | rows |")
    add("|---|---:|---|---:|---:|")
    for key, table, _ in TABLES:
        i = ingest.get(table, {}).get("ingest", {})
        m = ingest.get(table, {}).get("merge", {})
        runs = ", ".join(f"{c / 1e6:.2f}" for c in i.get("cpu_us_runs", []))
        add(f"| `{key}` | {i.get('cpu_us_fastest', 0) / 1e6:.2f} | {runs} | "
            f"{m.get('cpu_us_fastest', 0) / 1e6:.2f} | {fmt(i.get('rows', 0))} |")
    add("")
    add("## What this says")
    add("")
    ct, cs, cty, ctb = ("otel_logs_compact_zstd1", "otel_logs_compact_sorted",
                        "otel_logs_compact_typed", "otel_logs_compact_typed_bytemplate")
    add(f"**The generic typed layout loses on the payload.** Five typed arrays compress to "
        f"{fmt(payload(cty))} bytes against {fmt(payload(ct))} for the same events as one text "
        f"string, and {fmt(payload(ctb))} even sorted by template. Each array carries its own "
        "offsets stream and the values lose the neighbouring context ZSTD was using inside the "
        "string. ClickHouse's 45x rung came from one typed column per variable in a hand-built "
        "per-service table. A layout with no schema per template does not reach it, and this "
        "run is the evidence.")
    add("")
    add(f"**The sort key alone is worth having.** Adding the template hash to ClickStack's own "
        f"sort key, and changing nothing else, takes the payload from {fmt(payload(ct))} to "
        f"{fmt(payload(cs))} bytes, {pct(payload(cs), payload(ct))} on top of the text form, and "
        f"the other columns from {fmt(others(ct))} to {fmt(others(ctb))} when the template leads "
        "the key, because rows of one template share their attributes. It is the one change here "
        "that a ClickHouse engineer would make unprompted, and it needs nothing but a "
        "materialised column.")
    add("")
    ctrl = totals[folded]["bytes_on_disk"] - text_index[folded]
    add(f"**Against the right control the typed layout is not a saving.** Take the folded native "
        f"table and simply drop its text index: {fmt(totals[folded]['bytes_on_disk'])} minus "
        f"{fmt(text_index[folded])} is {fmt(ctrl)} bytes, arithmetic rather than a rebuilt table. "
        f"The typed layout is {fmt(totals[cty]['bytes_on_disk'])} bytes, "
        f"{rel(totals[cty]['bytes_on_disk'], ctrl)} than that, and "
        f"{fmt(totals[cty]['bytes_on_disk'] + dict_disk)} with its dictionary, "
        f"{rel(totals[cty]['bytes_on_disk'] + dict_disk, ctrl)}. The type-sorted typed layout is "
        f"{fmt(totals[ctb]['bytes_on_disk'])}, {rel(totals[ctb]['bytes_on_disk'], ctrl)}. Every headline saving in "
        "the totals table is the index leaving, and a customer can drop an index with one "
        "statement.")
    add("")
    add(f"**The text index is the elephant.** `idx_lower_body`, ClickStack's full-text index on "
        f"`Body`, is {fmt(text_index[folded])} of the {fmt(totals[folded]['bytes_on_disk'])} bytes "
        f"the folded native table occupies, {text_index[folded] / totals[folded]['bytes_on_disk'] * 100:.0f}%. "
        "Every large total saving in the table above is that index shrinking or disappearing, not "
        "the data compressing better. On a compact `Body` it still indexes the values, so value "
        "search works without expansion, but it cannot index the template's words because they "
        "are not in the row. A deployment that searches by pattern instead of by word can drop "
        "it and take the saving. One that needs word search keeps it and keeps most of the cost.")
    add("")
    nf = ingest[folded]["ingest"]["cpu_us_fastest"]
    nn = ingest[native]["ingest"]["cpu_us_fastest"]
    ctx = ingest[ct]["ingest"]["cpu_us_fastest"]
    cs_cpu = ingest[cs]["ingest"]["cpu_us_fastest"]
    cty_cpu = ingest[cty]["ingest"]["cpu_us_fastest"]
    add(f"**Ingest, row for row, is not cheaper for the compact text.** {ctx / 1e6:.2f} s against "
        f"{nf / 1e6:.2f} s to build and compress the same {fmt(totals[folded]['rows'])} rows. The "
        f"deployment-level gap, {nn / 1e6:.2f} s for the {fmt(totals[native]['rows'])} native rows "
        f"against {ctx / 1e6:.2f} s, is the row count: it is the folding, not the compaction. The "
        f"sort key takes {pct(cs_cpu, ctx)} off and the typed layout {pct(cty_cpu, ctx)}, because "
        "there is less text to tokenise for the index and fewer bytes to compress. The app README "
        "claims 25 to 30 percent less ingest CPU; on ClickHouse's own insert path, with parsing "
        "taken out, that claim does not hold for the text form. What a smaller payload does save "
        "is the parsing upstream of ClickHouse, in the collector and on the wire, which this run "
        "deliberately does not measure.")
    add("")
    out = out_dir / f"typed-layout-{date}.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out}")
    print("\n".join(L[L.index("## On disk"):L.index("## The typed columns, one by one")]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
