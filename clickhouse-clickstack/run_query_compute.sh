#!/usr/bin/env bash
#
# Does QUERY compute follow rows too?
#
# run_compute.sh showed insert-plus-merge CPU tracking row count, better than
# linearly. Queries are the other half of a cluster's work and were not
# measured. This runs a fixed mix against the same reduction arms and reads CPU
# and bytes from system.query_log, ten runs each, fastest and median kept.
#
# Arms come from run_compute.sh's staging tables; if the compute_* tables are
# not present they are loaded here in one pass, which is fine for a query test.
#
#   KEEP=1 ./run.sh && ./run_compute.sh && ./run_query_compute.sh

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"
ARMS_DIR="$DATA_DIR/arms"
INNER="$DATA_DIR/inner"
RESULTS="$HERE/results"
CTR=ch-clickstack
RUNS="${RUNS:-11}"

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }
docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1 \
  || { echo "no $CTR container: run KEEP=1 ./run.sh first" >&2; exit 1; }

ARMS=(full sampled_75 sampled_50 sampled_25 bypattern_75 bypattern_50 bypattern_25)
source_for() { [ "$1" = "full" ] && echo "native.jsonl" || echo "native_$1.jsonl"; }
COLS="Timestamp, TraceId, SpanId, TraceFlags, SeverityText, SeverityNumber, ServiceName, Body, ResourceSchemaUrl, ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion, ScopeAttributes, LogAttributes, EventName"
STAGE_COLS="Timestamp DateTime64(9), TraceId String, SpanId String, TraceFlags UInt8, SeverityText LowCardinality(String), SeverityNumber UInt8, ServiceName LowCardinality(String), Body String, ResourceSchemaUrl LowCardinality(String), ResourceAttributes Map(LowCardinality(String), String), ScopeSchemaUrl LowCardinality(String), ScopeName String, ScopeVersion LowCardinality(String), ScopeAttributes Map(LowCardinality(String), String), LogAttributes Map(LowCardinality(String), String), EventName String"

if [ ! -s "$ARMS_DIR/reduction.manifest.json" ]; then
  say "build the reduction arms"
  python3 build_reduction.py --raw "$DATA_DIR/otel-sample-200mb.log" --encoded "$INNER/encoded.log" \
    --templates "$INNER/templates.json" --arms "$ARMS_DIR"
fi
say "arms present"
for arm in "${ARMS[@]}"; do
  t="compute_$arm"; s="stage_$arm"
  if [ "$(ch --query "SELECT count() FROM system.tables WHERE database='bench' AND name='$t'")" != "1" ]; then
    if [ "$(ch --query "SELECT count() FROM system.tables WHERE database='bench' AND name='$s'")" != "1" ]; then
      ch --query "CREATE TABLE bench.$s ($STAGE_COLS) ENGINE = MergeTree ORDER BY tuple()"
      docker exec "$CTR" bash -c "clickhouse-client --query 'INSERT INTO bench.$s FORMAT JSONEachRow' < /arms/$(source_for "$arm")"
    fi
    sed -e "s/__TABLE__/$t/g" -e "s/__CODEC__/ZSTD(1)/g" schema.sql.tpl | ch --multiquery
    ch --query "INSERT INTO bench.$t ($COLS) SELECT $COLS FROM bench.$s"
    ch --query "OPTIMIZE TABLE bench.$t FINAL" --receive_timeout 1200
  fi
  printf '  %-14s %s rows\n' "$arm" "$(ch --query "SELECT count() FROM bench.$t")"
done

# ---------------------------------------------------------------- the mix
# Four shapes a log user actually runs. Each is tagged so query_log can be read
# back per arm per query.
declare -A Q
Q[word]="SELECT count() FROM bench.__T__ WHERE hasToken(lower(Body), 'checkout')"
Q[service_window]="SELECT count(), max(length(Body)) FROM bench.__T__ WHERE ServiceName = 'frontend' AND Timestamp >= toDateTime64('2025-10-01 22:00:00', 9) AND Timestamp < toDateTime64('2025-10-02 02:00:00', 9)"
Q[top_services]="SELECT ServiceName, count() c FROM bench.__T__ GROUP BY ServiceName ORDER BY c DESC LIMIT 10"
Q[recent_tail]="SELECT Timestamp, ServiceName, Body FROM bench.__T__ ORDER BY Timestamp DESC LIMIT 200 FORMAT Null"
Q[substring]="SELECT count() FROM bench.__T__ WHERE position(Body, 'userId=') > 0"

say "run the mix, $RUNS runs each"
for arm in "${ARMS[@]}"; do
  t="compute_$arm"
  for name in word service_window top_services recent_tail substring; do
    sql="${Q[$name]//__T__/$t}"
    for _ in $(seq 1 "$RUNS"); do ch --query "/*qc-$arm-$name*/ $sql" >/dev/null; done
  done
  echo "  $arm"
done
ch --query "SYSTEM FLUSH LOGS"

say "measure"
python3 - "$CTR" "$RESULTS" "$RUNS" <<'PY'
import datetime, json, pathlib, subprocess, sys, statistics
ctr, results, runs = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3])
def q(sql):
    o = subprocess.run(["docker","exec","-i",ctr,"clickhouse-client","--format","TabSeparated","--query",sql],capture_output=True,text=True)
    if o.returncode: raise RuntimeError(o.stderr)
    return [l.split("\t") for l in o.stdout.strip().splitlines() if l]
ARMS=["full","sampled_75","sampled_50","sampled_25","bypattern_75","bypattern_50","bypattern_25"]
QS=["word","service_window","top_services","recent_tail","substring"]
rows = {r[0]:int(r[1]) for r in q("SELECT table,sum(rows) FROM system.parts WHERE database='bench' AND active AND table LIKE 'compute_%' GROUP BY table")}
data = {}
for arm,name,cpus,rb in q(f"""
    SELECT extract(query,'/\\\\*qc-([a-z_0-9]+)-[a-z_]+\\\\*/') AS a,
           extract(query,'/\\\\*qc-[a-z_0-9]+-([a-z_]+)\\\\*/') AS n,
           arrayStringConcat(arraySlice(groupArray(toString(ProfileEvents['UserTimeMicroseconds']+ProfileEvents['SystemTimeMicroseconds'])), 2), ' '),
           max(read_bytes)
    FROM (SELECT * FROM system.query_log WHERE type='QueryFinish' AND position(query,'/*qc-')>0 ORDER BY event_time_microseconds)
    GROUP BY a,n"""):
    c = sorted(int(x) for x in cpus.split())
    data.setdefault(arm,{})[name] = {"cpu_us_fastest":c[0],"cpu_us_median":int(statistics.median(c)),"read_bytes":int(rb),"runs":c}
def fmt(n): return f"{int(n):,}"
L=[]; a=L.append; d=datetime.date.today().isoformat()
a("# Does query compute follow rows"); a("")
a(f"Measured {d} by `run_query_compute.sh`. Five query shapes, {runs} runs each with the first discarded, CPU as user plus system time from `system.query_log`, fastest kept. Same ClickStack schema at ZSTD(1); only the rows present differ between arms."); a("")
a("| Query | " + " | ".join(ARMS) + " |"); a("|---|" + "---:|"*len(ARMS))
for name in QS:
    a(f"| `{name}` CPU ms | " + " | ".join(f"{data[arm][name]['cpu_us_fastest']/1000:.1f}" for arm in ARMS) + " |")
a("| rows | " + " | ".join(fmt(rows[f'compute_{arm}']) for arm in ARMS) + " |")
a(""); a("Total CPU across the mix, fastest runs, relative to `full`:"); a("")
a("| Arm | rows vs full | mix CPU ms | CPU vs full |"); a("|---|---:|---:|---:|")
base = sum(data["full"][n]["cpu_us_fastest"] for n in QS)
for arm in ARMS:
    tot = sum(data[arm][n]["cpu_us_fastest"] for n in QS)
    a(f"| `{arm}` | {rows[f'compute_{arm}']/rows['compute_full']*100:.0f}% | {tot/1000:.1f} | {tot/base*100:.0f}% |")
a(""); a("Bytes read per query, `full` arm: " + ", ".join(f"`{n}` {fmt(data['full'][n]['read_bytes'])}" for n in QS) + ".")
a(""); a("## What it says"); a("")
half = sum(data["sampled_50"][n]["cpu_us_fastest"] for n in QS)/base
a(f"Half the rows cost {half*100:.0f}% of the query CPU across the mix. " + ("Query compute follows rows about as insert and merge do." if 0.35<=half<=0.65 else "Query compute does NOT track rows the way insert and merge do; see the per-query rows above for which shapes break the pattern."))
a(""); a("Per-shape: a time-window filter and a recent tail read a fixed slice and barely move with table size; a word search, a substring scan and a group-by walk the whole table and move with it. Which shape dominates a cluster's query load is a property of that cluster.")
out = results / f"query-compute-{d}.md"; out.write_text("\n".join(L)+"\n"); print(f"wrote {out}"); print("\n".join(L[L.index('Total CPU across the mix, fastest runs, relative to `full`:'):]))
(results / "query_compute.json").write_text(json.dumps({"rows":rows,"data":data},indent=2))
PY
say "done"
