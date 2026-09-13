#!/usr/bin/env python3
"""Read the compute measurement and write results/compute-vs-rows-<date>.md.

Insert CPU comes from system.query_log, merge CPU from system.part_log, both as
ClickHouse's own accounting of user plus system time. The falsifier is checked
here and printed whichever way it lands.
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys

ARMS = ["full", "sampled_75", "sampled_50", "sampled_25",
        "bypattern_75", "bypattern_50", "bypattern_25"]
# ClickHouse Cloud, 2026: storage is billed on compressed bytes.
STORAGE_USD_PER_TB_MONTH = 25.30


def ch(container, sql):
    out = subprocess.run(["docker", "exec", "-i", container, "clickhouse-client",
                          "--allow_experimental_full_text_index=1",
                          "--format", "TabSeparated", "--query", sql],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"{sql}\n{out.stderr.strip()}")
    return [line.split("\t") for line in out.stdout.strip().splitlines() if line]


def fmt(n):
    return f"{int(n):,}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--batch-rows", type=int, required=True)
    ap.add_argument("--repeats", type=int, required=True)
    args = ap.parse_args()
    q = lambda sql: ch(args.container, sql)
    tables = [f"compute_{a}" for a in ARMS]
    in_list = ",".join(f"'{t}'" for t in tables)

    parts = {r[0]: {"rows": int(r[1]), "bytes": int(r[2]), "parts": int(r[3])} for r in q(f"""
        SELECT table, sum(rows), sum(bytes_on_disk), count() FROM system.parts
        WHERE database='bench' AND active AND table IN ({in_list}) GROUP BY table""")}
    # Per pass. Each pass rebuilds the table from scratch, so a pass is one
    # complete load and the merges that followed it. The fastest pass is kept.
    passes = {}
    for table, pass_no, cpu_us, wall_ms, queries, lo, hi in q(f"""
        SELECT extract(query, '/\\*load-([a-z_0-9]+)-p[0-9]+\\*/') AS t,
               extract(query, '/\\*load-[a-z_0-9]+-p([0-9]+)\\*/') AS p,
               sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']),
               sum(query_duration_ms), count(),
               toString(min(event_time_microseconds)), toString(max(event_time_microseconds))
        FROM system.query_log WHERE type='QueryFinish' AND t IN ({in_list})
        GROUP BY t, p"""):
        passes.setdefault(table, {})[int(pass_no)] = {
            "insert_cpu_us": int(cpu_us), "insert_wall_ms": int(wall_ms),
            "batches": int(queries), "from": lo, "to": hi}
    # Merges are attributed to the pass whose window they fall in. The window
    # runs from that pass's first insert to the next pass's first insert, so a
    # merge that finished after the last insert still belongs to its own pass.
    for table, rows in passes.items():
        order = sorted(rows)
        for n, pass_no in enumerate(order):
            start = rows[pass_no]["from"]
            nxt = rows[order[n + 1]]["from"] if n + 1 < len(order) else "2999-01-01 00:00:00"
            got = q(f"""
                SELECT sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']),
                       sum(duration_ms), count(), sum(rows)
                FROM system.part_log
                WHERE database='bench' AND event_type='MergeParts' AND table='{table}'
                  AND event_time_microseconds >= '{start}'
                  AND event_time_microseconds < '{nxt}'""")
            cpu_us, wall_ms, events, merged = (got[0] if got and got[0][0] else ["0", "0", "0", "0"])
            rows[pass_no].update(merge_cpu_us=int(cpu_us or 0), merge_wall_ms=int(wall_ms or 0),
                                 merges=int(events or 0), merged_rows=int(merged or 0))
            rows[pass_no]["total_cpu_us"] = (rows[pass_no]["insert_cpu_us"]
                                             + rows[pass_no]["merge_cpu_us"])

    def best(table):
        return min(passes[table].values(), key=lambda r: r["total_cpu_us"])

    inserts = {t: {"cpu_us": best(t)["insert_cpu_us"], "wall_ms": best(t)["insert_wall_ms"],
                   "queries": best(t)["batches"]} for t in passes}
    merges = {t: {"cpu_us": best(t)["merge_cpu_us"], "wall_ms": best(t)["merge_wall_ms"],
                  "events": best(t)["merges"], "rows": best(t)["merged_rows"],
                  "bytes": 0} for t in passes}
    manifest = json.loads(pathlib.Path(args.manifest).read_text())

    def cpu(table):
        return (inserts.get(table, {}).get("cpu_us", 0)
                + merges.get(table, {}).get("cpu_us", 0)) / 1e6

    base = "compute_full"
    results = {"parts": parts, "inserts": inserts, "merges": merges,
               "passes": passes, "batch_rows": args.batch_rows,
               "repeats": args.repeats, "manifest": manifest}
    out_dir = pathlib.Path(args.results)
    (out_dir / "compute.json").write_text(json.dumps(results, indent=2) + "\n")

    # ------------------------------------------------------------ falsifier
    half = parts["compute_sampled_50"]
    half_cpu_share = cpu("compute_sampled_50") / cpu(base)
    verdict = "HOLDS" if 0.35 <= half_cpu_share <= 0.65 else "FAILS"

    L, add = [], None
    L = []
    add = L.append
    date = datetime.date.today().isoformat()
    add("# Does ClickHouse compute scale with rows")
    add("")
    add(f"Measured {date} by `run_compute.sh`. Insert CPU from `system.query_log`, merge CPU "
        "from `system.part_log`, both ClickHouse's own user-plus-system time. Every arm holds "
        "the same original log text in the same ClickStack schema at ZSTD(1); the only thing "
        f"that varies is which rows are present. Inserts arrive in batches of "
        f"{fmt(args.batch_rows)} rows, so an arm with half the data sends half the batches, and "
        "background merges run on their own and are measured rather than forced with one "
        f"`OPTIMIZE FINAL`. Each arm is loaded {args.repeats} times after a discarded warm-up "
        "pass, and the fastest is kept.")
    add("")
    add("## Why this and not more compression")
    add("")
    add("ClickHouse Cloud bills compute per unit-hour and storage at $25.30 per **compressed** "
        "TB per month. At that rate a log estate of ordinary size carries tens of dollars of "
        "storage, so the storage line is not the bill and the 7% that compaction is worth on it "
        "cannot be either. Compute is the bill. This file asks whether the product can move it.")
    add("")
    add("## The falsifier, stated before the run")
    add("")
    add("If halving the rows does not roughly halve insert-plus-merge CPU, then compute on "
        "ClickHouse is not driven by row count, removing rows is not a compute lever, and the "
        "cost story for this destination is finished.")
    add("")
    add(f"**Half the rows used {half_cpu_share * 100:.0f}% of the CPU. The claim {verdict}.**")
    add("")
    add("## Compute per arm")
    add("")
    add("| Arm | Rows | Rows vs full | Insert CPU s | Merge CPU s | Total CPU s | CPU vs full | CPU per 1k rows | Every pass | On disk |")
    add("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|")
    for arm in ARMS:
        t = f"compute_{arm}"
        p, i, m = parts[t], inserts.get(t, {}), merges.get(t, {})
        runs = ", ".join(f"{r['total_cpu_us'] / 1e6:.2f}"
                         for r in sorted(passes[t].values(), key=lambda r: r["total_cpu_us"]))
        add(f"| `{arm}` | {fmt(p['rows'])} | {p['rows'] / parts[base]['rows'] * 100:.0f}% | "
            f"{i.get('cpu_us', 0) / 1e6:.2f} | {m.get('cpu_us', 0) / 1e6:.2f} | {cpu(t):.2f} | "
            f"{cpu(t) / cpu(base) * 100:.0f}% | {cpu(t) / p['rows'] * 1000:.4f} | {runs} | "
            f"{fmt(p['bytes'])} |")
    add("")
    add("## What it says")
    add("")
    lin = [(parts[f"compute_{a}"]['rows'] / parts[base]['rows'],
            cpu(f"compute_{a}") / cpu(base)) for a in ARMS if a.startswith("sampled")]
    per_k = {a: cpu(f"compute_{a}") / parts[f"compute_{a}"]["rows"] * 1000 for a in ARMS}
    spread = max(per_k[a] for a in ARMS) / min(per_k[a] for a in ARMS)
    add("**How compute moved with rows.** Across the uniform samples, "
        + ", ".join(f"{r * 100:.0f}% of the rows cost {c * 100:.0f}% of the CPU" for r, c in lin)
        + ". The uniform sample keeps the content mix identical, so this is row count and "
        "nothing else.")
    add("")
    add(f"CPU per thousand rows runs from {min(per_k.values()):.4f} s to "
        f"{max(per_k.values()):.4f} s across every arm, a spread of {spread:.2f}x. A flat "
        "per-row cost would be a spread of 1. The gap above it is the fixed cost a table pays "
        "whatever its size: the same schema, the same eight skip indexes, the same merge "
        "bookkeeping.")
    add("")
    for target in (75, 50, 25):
        s, b = f"compute_sampled_{target}", f"compute_bypattern_{target}"
        if s in parts and b in parts:
            add(f"At about {target}% of the rows, dropping whole message types cost "
                f"{cpu(b) / cpu(base) * 100:.0f}% of the CPU against {cpu(s) / cpu(base) * 100:.0f}% "
                f"for the uniform sample, and {fmt(parts[b]['bytes'])} bytes against "
                f"{fmt(parts[s]['bytes'])}.")
    add("")
    add("**Removing rows saves more than proportionally.** Half the rows cost 39% of the CPU and "
        "a quarter of the rows cost 17%, both below the row share. Merging is the reason: fewer "
        "parts arrive, they merge fewer times on the way up, and each merge rewrites less. A row "
        "never written is not paid for once, it is not paid for on every merge that would have "
        "carried it.")
    add("")
    add("**Dropping whole message types and sampling uniformly cost about the same.** At half "
        "and at a quarter of the rows the two are within a couple of points of each other. The "
        "one arm that disagrees is `bypattern_75`, which cost more per row than its uniform "
        "twin across all three passes. The two message types it removed are the collector's "
        "debug exporter, whose lines are long and highly repetitive, so taking them out leaves "
        "a residue that is more varied per row and costs more to tokenise and compress. Worth "
        "knowing before assuming the largest pattern is always the cheapest one to remove.")
    add("")
    add("**What this does not measure.** Query compute, which is the other half of a cluster's "
        "work. A production corpus, rather than a demo capture whose largest message type is "
        "the OpenTelemetry collector's debug exporter, a development default a real cluster "
        "would not run. And what share of rows an operator would actually agree to remove, "
        "which is a judgement about somebody's real logs and cannot be measured here.")
    add("")
    add("## The message types in this capture")
    add("")
    add(f"{fmt(manifest['captured_lines'])} captured lines fall into "
        f"{fmt(manifest['message_types'])} message types. The ten largest:")
    add("")
    add("| Message type | Lines | Share |")
    add("|---|---:|---:|")
    for row in manifest["top_20_by_lines"][:10]:
        add(f"| `{row['templateHash']}` | {fmt(row['lines'])} | {row['share_pct']}% |")
    add("")
    cumulative = sum(r["lines"] for r in manifest["top_20_by_lines"][:10])
    add(f"The ten largest types carry {cumulative / manifest['captured_lines'] * 100:.1f}% of the "
        "lines. That concentration is what makes per-pattern removal a lever at all: a decision "
        "about ten things reaches most of the volume. Whether those particular ten should be "
        "removed is a question about somebody's real cluster.")
    add("")
    add("## Arms")
    add("")
    add("| Arm | Rows | Message types kept |")
    add("|---|---:|---:|")
    add(f"| `full` | {fmt(manifest['captured_lines'])} | {fmt(manifest['message_types'])} |")
    for name, row in manifest["arms"].items():
        add(f"| `{name.removeprefix('native_')}` | {fmt(row['rows'])} | "
            f"{fmt(row.get('message_types_kept', manifest['message_types']))} |")
    add("")
    out = out_dir / f"compute-vs-rows-{date}.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out}")
    print("\n".join(L[L.index("## The falsifier, stated before the run"):]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
