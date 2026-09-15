#!/usr/bin/env bash
#
# Two lossless levers nobody has measured, on the real capture.
#
# A. Insert batch shape. ClickHouse merges every part it receives up a ladder of
#    levels, so many small inserts cost more merge CPU than few large ones for
#    the same rows. The engine sits upstream of ClickHouse and already batches,
#    so batch size is a knob it owns. Same 197,430 rows, same schema, loaded in
#    batches of 1,000, 5,000, 20,000 and 100,000 rows; insert plus merge CPU
#    read from system.query_log and system.part_log; three passes each after a
#    discarded warm-up, fastest kept. Nothing is lost: every arm holds every row.
#
# B. Recompression on real log text. run_policy.sh found TTL RECOMPRESS fires
#    and does nothing against ClickStack's per-column codecs, and measured 2.1%
#    on synthetic digits where it does fire. That number is not quotable. This
#    loads the real 197,430-line Body at ZSTD(1), ZSTD(3), ZSTD(9) and ZSTD(12)
#    with no column codec in the way, so the ceiling of a recompress policy on
#    this text is known. Every row stays.
#
#   KEEP=1 ./run.sh && ./run_lossless.sh

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"
RESULTS="$HERE/results"
CTR=ch-clickstack
REPEATS="${REPEATS:-3}"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }
docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1 \
  || { echo "no $CTR container: run KEEP=1 ./run.sh first" >&2; exit 1; }

COLS="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName"
STAGE_COLS="Timestamp DateTime64(9), TraceId String, SpanId String, TraceFlags UInt8, SeverityText LowCardinality(String), SeverityNumber UInt8, ServiceName LowCardinality(String), Body String, ResourceSchemaUrl LowCardinality(String), ResourceAttributes Map(LowCardinality(String), String), ScopeSchemaUrl LowCardinality(String), ScopeName String, ScopeVersion LowCardinality(String), ScopeAttributes Map(LowCardinality(String), String), LogAttributes Map(LowCardinality(String), String), EventName String"

say "row source"
if [ "$(ch --query "SELECT count() FROM system.tables WHERE database='bench' AND name='stage_full'")" != "1" ]; then
  ch --query "CREATE TABLE bench.stage_full ($STAGE_COLS) ENGINE = MergeTree ORDER BY tuple()"
  docker exec "$CTR" bash -c "clickhouse-client --query 'INSERT INTO bench.stage_full FORMAT JSONEachRow' < /arms/native.jsonl"
fi
ROWS="$(ch --query "SELECT count() FROM bench.stage_full")"; echo "  $ROWS rows"

settle() { for _ in 1 2 3; do until [ "$(ch --query "SELECT count() FROM system.merges WHERE database='bench' AND table='$1'")" = "0" ]; do sleep 2; done; sleep 4; done; }

# ------------------------------------------------------------ A. batch shape
say "A. batch shape: warm-up pass, discarded"
ch --query "DROP TABLE IF EXISTS bench.warmup SYNC"
sed -e "s/__TABLE__/warmup/g" -e "s/__CODEC__/ZSTD(1)/g" schema.sql.tpl | ch --multiquery
ch --query "INSERT INTO bench.warmup ($COLS) SELECT $COLS FROM bench.stage_full"; settle warmup
ch --query "DROP TABLE IF EXISTS bench.warmup SYNC"

for size in 1000 5000 20000 100000; do
  table="batch_$size"; batches=$(( (ROWS + size - 1) / size ))
  say "A. $size rows per batch, $batches batches, $REPEATS passes"
  for pass in $(seq 1 "$REPEATS"); do
    ch --query "DROP TABLE IF EXISTS bench.$table SYNC"
    sed -e "s/__TABLE__/$table/g" -e "s/__CODEC__/ZSTD(1)/g" schema.sql.tpl | ch --multiquery
    for i in $(seq 0 $((batches - 1))); do
      ch --query "/*bload-$table-p$pass*/ INSERT INTO bench.$table ($COLS) SELECT $COLS FROM bench.stage_full LIMIT $size OFFSET $((i * size))"
    done
    settle "$table"
  done
  printf '  parts after settle: %s\n' "$(ch --query "SELECT count() FROM system.parts WHERE database='bench' AND table='$table' AND active")"
done
ch --query "SYSTEM FLUSH LOGS"

# ------------------------------------------------ B. recompression, real text
say "B. real Body text at four ZSTD levels, no column codec in the way"
for lvl in 1 3 9 12; do
  table="zstd_$lvl"
  ch --query "DROP TABLE IF EXISTS bench.$table SYNC"
  # ClickStack DDL with the codec substituted everywhere, which is what a table
  # created at that level, or recompressed to it, would hold.
  sed -e "s/__TABLE__/$table/g" -e "s/__CODEC__/ZSTD($lvl)/g" schema.sql.tpl | ch --multiquery
  ch --query "INSERT INTO bench.$table ($COLS) SELECT $COLS FROM bench.stage_full"
  ch --query "OPTIMIZE TABLE bench.$table FINAL" --receive_timeout 1200
  printf '  ZSTD(%-2s) Body %s bytes, table %s bytes\n' "$lvl" \
    "$(ch --query "SELECT sum(column_data_compressed_bytes) FROM system.parts_columns WHERE database='bench' AND table='$table' AND active AND column='Body'")" \
    "$(ch --query "SELECT sum(bytes_on_disk) FROM system.parts WHERE database='bench' AND table='$table' AND active")"
done

# ------------------------------------------------------------------- report
say "measure"
python3 - "$CTR" "$RESULTS" "$ROWS" <<'PY'
import datetime, json, pathlib, subprocess, sys
ctr, results, rows = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3])
def q(sql):
    o = subprocess.run(["docker","exec","-i",ctr,"clickhouse-client","--format","TabSeparated","--query",sql],capture_output=True,text=True)
    if o.returncode: raise RuntimeError(o.stderr)
    return [l.split("\t") for l in o.stdout.strip().splitlines() if l]
def fmt(n): return f"{int(n):,}"
# batches: per pass insert cpu + merges in that pass's window
passes = {}
for t, p, cpu, n, lo in q(r"""
    SELECT extract(query,'/\*bload-([a-z_0-9]+)-p[0-9]+\*/') AS t, extract(query,'/\*bload-[a-z_0-9]+-p([0-9]+)\*/') AS p,
           sum(ProfileEvents['UserTimeMicroseconds']+ProfileEvents['SystemTimeMicroseconds']), count(), toString(min(event_time_microseconds))
    FROM system.query_log WHERE type='QueryFinish' AND t!='' GROUP BY t,p"""):
    passes.setdefault(t,{})[int(p)] = {"insert_us":int(cpu),"batches":int(n),"from":lo}
for t, ps in passes.items():
    order = sorted(ps)
    for i, p in enumerate(order):
        nxt = ps[order[i+1]]["from"] if i+1 < len(order) else "2999-01-01 00:00:00"
        got = q(f"""SELECT sum(ProfileEvents['UserTimeMicroseconds']+ProfileEvents['SystemTimeMicroseconds']), count()
                    FROM system.part_log WHERE database='bench' AND event_type='MergeParts' AND table='{t}'
                      AND event_time_microseconds >= '{ps[p]["from"]}' AND event_time_microseconds < '{nxt}'""")
        m = got[0] if got and got[0][0] else ["0","0"]
        ps[p]["merge_us"] = int(m[0] or 0); ps[p]["merges"] = int(m[1] or 0); ps[p]["total_us"] = ps[p]["insert_us"] + ps[p]["merge_us"]
zstd = {r[0]: (int(r[1]), int(r[2])) for r in q("""
    SELECT c.table, sum(c.column_data_compressed_bytes), any(p.b) FROM system.parts_columns AS c
    INNER JOIN (SELECT table, sum(bytes_on_disk) b FROM system.parts WHERE database='bench' AND active AND table LIKE 'zstd_%' GROUP BY table) AS p ON p.table = c.table
    WHERE c.database='bench' AND c.active AND c.table LIKE 'zstd_%' AND c.column='Body' GROUP BY c.table""")}
L=[]; a=L.append; d=datetime.date.today().isoformat()
a("# Two lossless levers on the real capture: batch shape and recompression"); a("")
a(f"Measured {d} by `run_lossless.sh`. Same {fmt(rows)} rows, same ClickStack schema, every row present in every arm. CPU is ClickHouse's own user plus system time.")
a(""); a("## A. Insert batch shape"); a("")
a("Fewer, larger inserts make fewer parts, and fewer parts merge fewer times. The engine already batches upstream, so this is a knob it owns. Three passes after a discarded warm-up, fastest kept, every pass shown.")
a(""); a("| Rows per batch | Batches | Insert CPU s | Merge CPU s | Total CPU s | vs 5,000 | Every pass total |"); a("|---:|---:|---:|---:|---:|---:|---|")
base = None
for size in (1000, 5000, 20000, 100000):
    t = f"batch_{size}"; best = min(passes[t].values(), key=lambda r: r["total_us"])
    if size == 5000: base = best["total_us"]
for size in (1000, 5000, 20000, 100000):
    t = f"batch_{size}"; best = min(passes[t].values(), key=lambda r: r["total_us"])
    runs = ", ".join(f"{r['total_us']/1e6:.2f}" for r in sorted(passes[t].values(), key=lambda r: r["total_us"]))
    a(f"| {fmt(size)} | {best['batches']} | {best['insert_us']/1e6:.2f} | {best['merge_us']/1e6:.2f} | {best['total_us']/1e6:.2f} | {best['total_us']/base*100:.0f}% | {runs} |")
a(""); a("## B. Recompression ceiling on real log text"); a("")
a("`run_policy.sh` showed `TTL RECOMPRESS` is a no-op against ClickStack's explicit column codecs and measured 2.1% on synthetic digits where it does fire. This is the real `Body` at four levels with nothing in the way, which is the most a recompress policy could ever return on this text.")
a(""); a("| Codec | Body bytes | vs ZSTD(1) | Whole table | vs ZSTD(1) |"); a("|---|---:|---:|---:|---:|")
b1, t1 = zstd["zstd_1"]
for lvl in (1, 3, 9, 12):
    b, t = zstd[f"zstd_{lvl}"]
    a(f"| ZSTD({lvl}) | {fmt(b)} | {(1-b/b1)*100:.1f}% | {fmt(t)} | {(1-t/t1)*100:.1f}% |")
a(""); a("## What it says"); a("")
b5 = min(passes["batch_5000"].values(), key=lambda r: r["total_us"])["total_us"]; b1k = min(passes["batch_1000"].values(), key=lambda r: r["total_us"])["total_us"]; b100k = min(passes["batch_100000"].values(), key=lambda r: r["total_us"])["total_us"]
a(f"Batch shape moves insert-plus-merge CPU from {b1k/1e6:.2f} s at a thousand rows per insert to {b100k/1e6:.2f} s at a hundred thousand, {(1-b100k/b1k)*100:.0f}% less for the same rows with nothing removed. This is a compute lever a collector or the engine controls upstream of ClickHouse, and it costs nothing but latency between a line being logged and being queryable.")
a(""); a("**Two caveats that bound this.** The inserts here are `INSERT ... SELECT` from a staging table, which ClickHouse does not route through `async_insert`; a client sending small HTTP inserts to 26.3 or later gets server-side coalescing by default, so the thousand-row baseline is pessimistic for such a client and the lever is the part count that reaches merges, not the statement count. And the CPU a collector spends holding and shipping larger batches is not in these numbers; only ClickHouse's side is.")
a(""); bb12, tt12 = zstd["zstd_12"]
a(f"Recompressing the real text from ZSTD(1) to ZSTD(12) takes {(1-bb12/b1)*100:.1f}% off the Body column and {(1-tt12/t1)*100:.1f}% off the table. Disk is about a tenth of a thirty-day bill, so the most a recompress policy can return on that bill is roughly a tenth of that figure, and only after the ClickStack column codecs are removed so the TTL can act.")
a(""); a('The write cost of the higher level is not measured here. ZSTD(12) spends more CPU compressing on insert and on every merge than ZSTD(1) does, so a recompress policy that applies it only to parts past their hot window, which is what `TTL RECOMPRESS` is for, is the shape that keeps that cost off the ingest path.')
out = results / f"lossless-levers-{d}.md"; out.write_text("\n".join(L)+"\n"); print(f"wrote {out}"); print("\n".join(L[L.index("## A. Insert batch shape"):]))
(results / "lossless.json").write_text(json.dumps({"batches": passes, "zstd": zstd}, indent=2))
PY
say "done"
