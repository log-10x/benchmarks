#!/usr/bin/env bash
#
# run.sh — one command, end to end.
#
#   ./run.sh
#
# Starts a pinned ClickHouse in a memory-pinned container, builds the corpus,
# installs the SHIPPED (buggy) decode functions, shows that the published
# `SELECT count()` never decoded a row, forces a real decode (it dies), applies
# the fix, forces the same decode again (it completes), proves the output is
# byte-identical, and prints a results table. Writes results.json.
#
# Env knobs:
#   MEM=8g      container memory limit. THE ABORT THRESHOLD IS A FUNCTION OF
#               THIS. ClickHouse's default max_server_memory_usage_to_ram_ratio
#               is 0.9, so it caps itself at 0.9 x the RAM it can see, and the
#               pre-fix decode dies at that cap. 8g -> 6.89-7.2 GiB. See README.
#   CPUS=8      container CPU limit.
#   ROWS=137418 rows in the table (the row count the post reports).
#   KEEP=1      leave the container running after the run.
#
set -euo pipefail

IMAGE=${IMAGE:-clickhouse/clickhouse-server:25.8.28.1}
CTR=${CTR:-tenx-inflate-bench}
MEM=${MEM:-8g}
CPUS=${CPUS:-8}
ROWS=${ROWS:-137418}
KEEP=${KEEP:-0}
REPS=${REPS:-3}
SKIP_PREFIX=${SKIP_PREFIX:-0}   # 1 = skip the two pre-fix OOM probes (~19 min).
                                # The pre-fix reference decode (byte-identity) still runs.          # timed runs per query; the first is discarded

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$HERE/.work"
FACTS="$WORK/facts.tsv"

# ---------------------------------------------------------------------------
# plumbing
# ---------------------------------------------------------------------------
cleanup() {
  if [ "$KEEP" = "1" ]; then
    echo "[run] KEEP=1, container '$CTR' left running. Remove with: docker rm -f $CTR"
  else
    docker rm -f "$CTR" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

fact() { printf '%s\t%s\n' "$1" "$2" >> "$FACTS"; }
say()  { printf '\n\033[1m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }

ch()   { docker exec "$CTR" clickhouse-client "$@"; }
q()    { docker exec "$CTR" clickhouse-client --query "$1"; }
qid()  { echo "b$(date +%s%N)"; }

# run a query REPS times, discard the first, report avg ms / peak mem / read stats
bench() {
  local label="$1" sql="$2" stamp; stamp="$(qid)"
  local r rc=0
  for r in $(seq 1 "$REPS"); do
    docker exec "$CTR" clickhouse-client --query_id "${stamp}_r${r}" --query "$sql" >/dev/null 2>&1 || rc=$?
  done
  q "SYSTEM FLUSH LOGS" >/dev/null
  q "SELECT round(avgIf(query_duration_ms, query_id NOT LIKE '%_r1')) AS ms,
            max(memory_usage) AS peak_bytes,
            any(read_rows) AS read_rows,
            any(read_bytes) AS read_bytes,
            countIf(type='QueryFinish') AS ok
     FROM system.query_log
     WHERE query_id LIKE '${stamp}_r%' AND type != 'QueryStart'
     FORMAT TSVRaw"
  return 0
}

# run a query ONCE, expecting it to blow up; report the exception + peak memory
attempt() {
  local label="$1" sql="$2" stamp; stamp="$(qid)"
  local rc=0
  docker exec "$CTR" clickhouse-client --query_id "$stamp" --query "$sql" >/dev/null 2>&1 || rc=$?
  q "SYSTEM FLUSH LOGS" >/dev/null
  q "SELECT type, round(query_duration_ms), memory_usage,
            replaceAll(substring(exception, 1, 160), '\n', ' ')
     FROM system.query_log
     WHERE query_id = '$stamp' AND type != 'QueryStart'
     ORDER BY event_time_microseconds DESC LIMIT 1
     FORMAT TSVRaw"
  return 0
}

# count ALL function nodes in a query plan's action DAG
function_nodes() {
  q "EXPLAIN actions = 1 $1" | grep -c 'FUNCTION ' || true
}

# count decode-function nodes in a query plan
decode_nodes() {
  local sql="$1"
  q "EXPLAIN actions = 1 $sql" \
    | grep -oE 'FUNCTION [A-Za-z0-9_]+' \
    | grep -cE 'dictGetOrDefault|arrayMap|arrayStringConcat|arrayResize|formatDateTimeInJodaSyntax|multiIf|splitByChar|fromUnixTimestamp64Milli|toInt64OrZero' \
    || true
}

# ---------------------------------------------------------------------------
# 0. workspace + container
# ---------------------------------------------------------------------------
rm -rf "$WORK"; mkdir -p "$WORK"; : > "$FACTS"

say "pulling $IMAGE"
docker pull -q "$IMAGE" >/dev/null

say "starting ClickHouse: mem=$MEM cpus=$CPUS"
docker rm -f "$CTR" >/dev/null 2>&1 || true
docker run -d --name "$CTR" -m "$MEM" --cpus "$CPUS" \
  --ulimit nofile=262144:262144 "$IMAGE" >/dev/null
for _ in $(seq 1 90); do q "SELECT 1" >/dev/null 2>&1 && break; sleep 1; done
q "SELECT 1" >/dev/null || { echo "ClickHouse did not come up"; docker logs "$CTR" | tail -20; exit 1; }

CH_VERSION=$(q "SELECT version()")
CGROUP_MAX=$(docker exec "$CTR" cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unknown)
HOST_MEMTOTAL=$(docker exec "$CTR" awk '/MemTotal/{printf "%.0f", $2*1024}' /proc/meminfo)
SRV_MEM_CAP=$(q "SELECT value FROM system.server_settings WHERE name='max_server_memory_usage'")
SRV_RATIO=$(q "SELECT value FROM system.server_settings WHERE name='max_server_memory_usage_to_ram_ratio'")
Q_MEM_LIMIT=$(q "SELECT value FROM system.settings WHERE name='max_memory_usage'")
Q_BLOCK=$(q "SELECT value FROM system.settings WHERE name='max_block_size'")
Q_THREADS=$(q "SELECT value FROM system.settings WHERE name='max_threads'")

fact image "$IMAGE"; fact clickhouse_version "$CH_VERSION"
fact container_mem_limit "$MEM"; fact container_cpus "$CPUS"
fact cgroup_memory_max_bytes "$CGROUP_MAX"; fact host_memtotal_bytes "$HOST_MEMTOTAL"
fact max_server_memory_usage_bytes "$SRV_MEM_CAP"
fact max_server_memory_usage_to_ram_ratio "$SRV_RATIO"
fact default_max_memory_usage "$Q_MEM_LIMIT"
fact default_max_block_size "$Q_BLOCK"
fact default_max_threads "$Q_THREADS"

echo "  version ............... $CH_VERSION"
echo "  cgroup memory.max ..... $CGROUP_MAX"
echo "  RAM ClickHouse sees ... $HOST_MEMTOTAL (min of cgroup limit and host RAM)"
echo "  server memory cap ..... $SRV_MEM_CAP  (= $SRV_RATIO x the above; THIS is where the pre-fix decode dies)"
echo "  per-query mem limit ... $Q_MEM_LIMIT  (0 = unlimited: the server cap governs)"

# ---------------------------------------------------------------------------
# 1. corpus
# ---------------------------------------------------------------------------
say "building corpus: $ROWS rows"
(cd "$HERE/corpus" && shasum -a 256 -c SHA256SUMS >/dev/null) \
  || { echo "corpus checksum mismatch"; exit 1; }
awk -v n="$ROWS" '{a[NR]=$0} END{for(i=0;i<n;i++) print a[(i%NR)+1]}' \
  "$HERE/corpus/sample-500.jsonl" > "$WORK/encoded-$ROWS.jsonl"
CORPUS_SHA=$(shasum -a 256 "$WORK/encoded-$ROWS.jsonl" | cut -d' ' -f1)
fact corpus_rows "$ROWS"; fact corpus_sha256 "$CORPUS_SHA"
echo "  $WORK/encoded-$ROWS.jsonl  sha256=$CORPUS_SHA"

docker cp "$WORK/encoded-$ROWS.jsonl" "$CTR:/tmp/encoded.jsonl" >/dev/null
docker cp "$HERE/corpus/templates.json" "$CTR:/tmp/templates.json" >/dev/null

# ---------------------------------------------------------------------------
# 2. install the SHIPPED (buggy) decoder, load the table
# ---------------------------------------------------------------------------
say "installing tenx-for-clickhouse (pre-fix: install-buggy.sql)"
docker exec -i "$CTR" clickhouse-client --multiquery < "$HERE/install-buggy.sql"
docker exec "$CTR" bash -c "clickhouse-client --query \"INSERT INTO tenx.templates (templateHash, template) FORMAT JSONEachRow\" < /tmp/templates.json"
docker exec "$CTR" bash -c "clickhouse-client --query \"INSERT INTO tenx.encoded_events (raw) FORMAT LineAsString\" < /tmp/encoded.jsonl"
q "SYSTEM RELOAD DICTIONARY tenx.templates_dict" >/dev/null
q "OPTIMIZE TABLE tenx.encoded_events FINAL" >/dev/null
N_ROWS=$(q "SELECT count() FROM tenx.encoded_events")
N_TPL=$(q "SELECT count() FROM tenx.templates")
fact table_rows "$N_ROWS"; fact templates "$N_TPL"
echo "  tenx.encoded_events: $N_ROWS rows   tenx.templates: $N_TPL templates"

# ---------------------------------------------------------------------------
# 3. FIGURE 1 — the published query never decoded a row
# ---------------------------------------------------------------------------
say "FIGURE 1: the pruned count (what the original post timed)"
q "EXPLAIN actions = 1 SELECT count() FROM tenx.events"                   > "$WORK/explain-count.txt"
q "EXPLAIN actions = 1 SELECT sum(length(decoded_log)) FROM tenx.events"  > "$WORK/explain-forced.txt"
NODES_COUNT=$(decode_nodes "SELECT count() FROM tenx.events")
NODES_FORCED=$(decode_nodes "SELECT sum(length(decoded_log)) FROM tenx.events")
FN_COUNT=$(function_nodes "SELECT count() FROM tenx.events")
FN_FORCED=$(function_nodes "SELECT sum(length(decoded_log)) FROM tenx.events")
fact explain_function_nodes_count_query "$FN_COUNT"
fact explain_function_nodes_forced_prefix "$FN_FORCED"
IFS=$'\t' read -r C_MS C_MEM C_RR C_RB C_OK < <(bench pruned_count "SELECT count() FROM tenx.events")
fact pruned_count_ms "$C_MS";  fact pruned_count_read_rows "$C_RR"
fact pruned_count_read_bytes "$C_RB"; fact pruned_count_peak_bytes "$C_MEM"
fact explain_decode_nodes_count_query "$NODES_COUNT"
fact explain_decode_nodes_forced_query "$NODES_FORCED"
echo "  SELECT count() FROM tenx.events   -> ${C_MS} ms, read_rows=${C_RR}, read_bytes=${C_RB}"
echo "  EXPLAIN, count() plan:        ${FN_COUNT} function nodes total, ${NODES_COUNT} of them decode"
echo "  EXPLAIN, forced-decode plan:  ${FN_FORCED} function nodes total, ${NODES_FORCED} of them decode builtins"

# ---------------------------------------------------------------------------
# 4. FIGURE 2 — forced decode, PRE-FIX, at ClickHouse default settings
# ---------------------------------------------------------------------------
say "FIGURE 2: forced decode, PRE-FIX, default settings (expect: out of memory)"
if [ "$SKIP_PREFIX" = "1" ]; then
  echo "  SKIP_PREFIX=1 -- skipping the two OOM probes (they take ~19 minutes to die)"
  fact prefix_sumlen_type skipped; fact prefix_column_type skipped
else
echo "  each probe runs to the memory cap and dies; ~9 minutes each. SKIP_PREFIX=1 skips them."
echo "  probe A: SELECT sum(length(decoded_log)) FROM tenx.events"
IFS=$'\t' read -r A_TYPE A_MS A_MEM A_EXC < <(attempt pre_sumlen "SELECT sum(length(decoded_log)) FROM tenx.events")
fact prefix_sumlen_type "$A_TYPE"; fact prefix_sumlen_ms "$A_MS"
fact prefix_sumlen_peak_bytes "$A_MEM"; fact prefix_sumlen_exception "${A_EXC:-}"
echo "    -> $A_TYPE  ${A_MS} ms  peak=${A_MEM}  ${A_EXC:-}"

echo "  probe B: SELECT decoded_log FROM tenx.events FORMAT Null"
IFS=$'\t' read -r B_TYPE B_MS B_MEM B_EXC < <(attempt pre_column "SELECT decoded_log FROM tenx.events FORMAT Null")
fact prefix_column_type "$B_TYPE"; fact prefix_column_ms "$B_MS"
fact prefix_column_peak_bytes "$B_MEM"; fact prefix_column_exception "${B_EXC:-}"
echo "    -> $B_TYPE  ${B_MS} ms  peak=${B_MEM}  ${B_EXC:-}"

echo "  probe C: the same forced decode with the blow-up BOUNDED, so it can finish."
echo "           SETTINGS max_block_size = 64, max_threads = 4, max_memory_usage = 6000000000"
IFS=$'\t' read -r BD_MS BD_MEM BD_RR BD_RB BD_OK < <(bench pre_bounded "SELECT sum(length(decoded_log)) FROM tenx.events SETTINGS max_block_size = 64, max_threads = 4, max_memory_usage = 6000000000")
fact prefix_bounded_ms "$BD_MS"; fact prefix_bounded_peak_bytes "$BD_MEM"
fact prefix_bounded_read_rows "$BD_RR"; fact prefix_bounded_read_bytes "$BD_RB"
fact prefix_bounded_ok_runs "$BD_OK"
echo "    -> ${BD_MS} ms  peak=${BD_MEM}  read_rows=${BD_RR}  read_bytes=${BD_RB}  completed_runs=${BD_OK}/${REPS}"
fi

# ---------------------------------------------------------------------------
# 5. FIGURE 5 — the quadratic term, counted on the corpus
# ---------------------------------------------------------------------------
say "FIGURE 5: necessary vs materialized array elements"
read -r NECESSARY MATERIALIZED < <(q "
  SELECT sum(n), sum(toUInt64(n) * toUInt64(n))
  FROM (SELECT length(t.literals) AS n
        FROM tenx.encoded_events AS e
        INNER JOIN tenx.templates AS t ON e.templateHash = t.templateHash)
  FORMAT TSVRaw")
read -r FAT_HASH FAT_LITS FAT_ROWS FAT_SHARE < <(q "
  SELECT t.templateHash, length(t.literals) AS lits, count() AS rows,
         round(100 * (toUInt64(lits) * toUInt64(lits) * rows) / $MATERIALIZED, 1)
  FROM tenx.encoded_events AS e
  INNER JOIN tenx.templates AS t ON e.templateHash = t.templateHash
  GROUP BY t.templateHash, t.literals
  ORDER BY toUInt64(lits) * toUInt64(lits) * rows DESC
  LIMIT 1 FORMAT TSVRaw")
fact necessary_elements "$NECESSARY"; fact materialized_elements "$MATERIALIZED"
fact fat_template_hash "$FAT_HASH"; fact fat_template_literals "$FAT_LITS"
fact fat_template_rows "$FAT_ROWS"; fact fat_template_share_pct "$FAT_SHARE"
echo "  necessary   sum(length(literals))   = $NECESSARY"
echo "  materialized sum(length(literals)^2) = $MATERIALIZED"
echo "  widest template: $FAT_LITS literals, $FAT_ROWS rows, ${FAT_SHARE}% of the materialized total"

# ---------------------------------------------------------------------------
# 6. pre-fix reference output (small blocks, so the buggy path can finish)
# ---------------------------------------------------------------------------
say "byte-identity, part 1: decode all $N_ROWS rows with the PRE-FIX functions"
echo "  (max_block_size=64 keeps the quadratic path under the memory cap)"
docker exec "$CTR" clickhouse-client --query "
  SELECT decoded_log FROM tenx.events ORDER BY encoded_log
  SETTINGS max_block_size = 64
  FORMAT TabSeparatedRaw" > "$WORK/decoded-prefix.txt"
PRE_SHA=$(shasum -a 256 "$WORK/decoded-prefix.txt" | cut -d' ' -f1)
PRE_LINES=$(wc -l < "$WORK/decoded-prefix.txt" | tr -d ' ')
PRE_BYTES=$(wc -c < "$WORK/decoded-prefix.txt" | tr -d ' ')
fact prefix_output_sha256 "$PRE_SHA"; fact prefix_output_bytes "$PRE_BYTES"
echo "  $PRE_BYTES bytes  sha256=$PRE_SHA"

# ---------------------------------------------------------------------------
# 7. the trap: replacing the functions does NOT fix the views
# ---------------------------------------------------------------------------
say "replacing ONLY the functions (fix-functions-only.sql)"
docker exec -i "$CTR" clickhouse-client --multiquery < "$HERE/fix-functions-only.sql"
STALE=$(q "SHOW CREATE VIEW tenx.events" | grep -c 'range(1' || true)
fact view_still_holds_old_body "$STALE"
if [ "$STALE" -gt 0 ]; then
  echo "  SHOW CREATE VIEW tenx.events still contains the OLD body (range(1, length(...))):"
  echo "  the view inlined the function at CREATE VIEW time. The fix has not landed yet."
else
  echo "  view no longer contains the old body -- the inlining trap did NOT reproduce"
fi

# ---------------------------------------------------------------------------
# 8. FIGURE 3 — apply the real fix (views recreated), decode again
# ---------------------------------------------------------------------------
say "applying install-fixed.sql (functions + views recreated; tables untouched)"
docker exec -i "$CTR" clickhouse-client --multiquery < "$HERE/install-fixed.sql"
q "SYSTEM RELOAD DICTIONARY tenx.templates_dict" >/dev/null
POST_ROWS=$(q "SELECT count() FROM tenx.encoded_events")
[ "$POST_ROWS" = "$N_ROWS" ] || { echo "install-fixed.sql lost data: $POST_ROWS != $N_ROWS"; exit 1; }
STALE_AFTER=$(q "SHOW CREATE VIEW tenx.events" | grep -c 'range(1' || true)
fact view_old_body_after_install_fixed "$STALE_AFTER"

q "EXPLAIN actions = 1 SELECT sum(length(decoded_log)) FROM tenx.events" > "$WORK/explain-forced-postfix.txt"
FN_FORCED_POST=$(function_nodes "SELECT sum(length(decoded_log)) FROM tenx.events")
ND_FORCED_POST=$(decode_nodes "SELECT sum(length(decoded_log)) FROM tenx.events")
fact explain_function_nodes_forced_postfix "$FN_FORCED_POST"
fact explain_decode_nodes_forced_postfix "$ND_FORCED_POST"
echo "  EXPLAIN, forced-decode plan POST-fix: ${FN_FORCED_POST} function nodes total, ${ND_FORCED_POST} decode builtins"

say "FIGURE 3: forced decode, POST-FIX, default settings"
IFS=$'\t' read -r P_MS P_MEM P_RR P_RB P_OK < <(bench post_sumlen "SELECT sum(length(decoded_log)) FROM tenx.events")
fact postfix_sumlen_ms "$P_MS"; fact postfix_sumlen_peak_bytes "$P_MEM"
fact postfix_sumlen_read_rows "$P_RR"; fact postfix_sumlen_read_bytes "$P_RB"
fact postfix_sumlen_ok_runs "$P_OK"
echo "  sum(length(decoded_log))       -> ${P_MS} ms  peak=${P_MEM}  read_rows=${P_RR}  read_bytes=${P_RB}"

IFS=$'\t' read -r PC_MS PC_MEM PC_RR PC_RB PC_OK < <(bench post_column "SELECT decoded_log FROM tenx.events FORMAT Null")
fact postfix_column_ms "$PC_MS"; fact postfix_column_peak_bytes "$PC_MEM"
fact postfix_column_ok_runs "$PC_OK"
echo "  SELECT decoded_log FORMAT Null -> ${PC_MS} ms  peak=${PC_MEM}   (this is the query that aborted pre-fix)"

IFS=$'\t' read -r NV_MS NV_MEM NV_RR NV_RB NV_OK < <(bench post_native "SELECT sum(length(decoded_log)) FROM tenx.events_native")
fact postfix_native_sumlen_ms "$NV_MS"; fact postfix_native_peak_bytes "$NV_MEM"
echo "  same, tenx.events_native       -> ${NV_MS} ms  peak=${NV_MEM}   (format-preserving view)"

# ---------------------------------------------------------------------------
# 9. FIGURE 4 — byte-identity
# ---------------------------------------------------------------------------
say "byte-identity, part 2: decode all $N_ROWS rows with the POST-FIX functions"
docker exec "$CTR" clickhouse-client --query "
  SELECT decoded_log FROM tenx.events ORDER BY encoded_log
  FORMAT TabSeparatedRaw" > "$WORK/decoded-postfix.txt"
POST_SHA=$(shasum -a 256 "$WORK/decoded-postfix.txt" | cut -d' ' -f1)
POST_BYTES=$(wc -c < "$WORK/decoded-postfix.txt" | tr -d ' ')
fact postfix_output_sha256 "$POST_SHA"; fact postfix_output_bytes "$POST_BYTES"
if cmp -s "$WORK/decoded-prefix.txt" "$WORK/decoded-postfix.txt"; then
  IDENTICAL=yes
  echo "  IDENTICAL: $POST_BYTES bytes, sha256=$POST_SHA"
else
  IDENTICAL=no
  echo "  DIFFERENT: pre=$PRE_SHA post=$POST_SHA"
  diff <(head -c 2000 "$WORK/decoded-prefix.txt") <(head -c 2000 "$WORK/decoded-postfix.txt") | head -5 || true
fi
fact byte_identical "$IDENTICAL"; fact byte_identical_rows "$N_ROWS"

# ---------------------------------------------------------------------------
# 10. results
# ---------------------------------------------------------------------------
say "results"
python3 - "$FACTS" "$HERE/results.json" <<'PY'
import json, sys, datetime
facts = {}
for line in open(sys.argv[1]):
    k, _, v = line.rstrip("\n").partition("\t")
    facts[k] = v
def num(k):
    try: return int(facts[k])
    except Exception:
        try: return float(facts[k])
        except Exception: return facts.get(k)
def gib(b):
    try: return round(int(b) / 1024**3, 2)
    except Exception: return None
def mib(b):
    try: return round(int(b) / 1024**2, 1)
    except Exception: return None

out = {
  "measured_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "host": {
    "image": facts["image"],
    "clickhouse_version": facts["clickhouse_version"],
    "container_memory_limit": facts["container_mem_limit"],
    "container_cpus": facts["container_cpus"],
    "cgroup_memory_max_bytes": num("cgroup_memory_max_bytes"),
    "ram_clickhouse_sees_bytes": num("host_memtotal_bytes"),
    "max_server_memory_usage_bytes": num("max_server_memory_usage_bytes"),
    "max_server_memory_usage_gib": gib(facts["max_server_memory_usage_bytes"]),
    "max_server_memory_usage_to_ram_ratio": facts["max_server_memory_usage_to_ram_ratio"],
    "default_max_memory_usage": facts["default_max_memory_usage"],
    "default_max_block_size": facts["default_max_block_size"],
    "default_max_threads": facts["default_max_threads"],
  },
  "corpus": {
    "rows": num("table_rows"),
    "templates": num("templates"),
    "sha256": facts["corpus_sha256"],
  },
  "figure_1_pruned_count": {
    "query": "SELECT count() FROM tenx.events",
    "ms": num("pruned_count_ms"),
    "read_rows": num("pruned_count_read_rows"),
    "read_bytes": num("pruned_count_read_bytes"),
    "explain_decode_nodes": num("explain_decode_nodes_count_query"),
    "explain_function_nodes_total": num("explain_function_nodes_count_query"),
    "explain_decode_nodes_forced_query": num("explain_decode_nodes_forced_query"),
    "explain_function_nodes_forced_prefix": num("explain_function_nodes_forced_prefix"),
    "explain_function_nodes_forced_postfix": num("explain_function_nodes_forced_postfix"),
    "explain_decode_nodes_forced_postfix": num("explain_decode_nodes_forced_postfix"),
  },
  "figure_2_prefix_forced_decode": {
    "settings": "ClickHouse defaults",
    "sum_length": {
      "type": facts["prefix_sumlen_type"], "ms": num("prefix_sumlen_ms"),
      "peak_bytes": num("prefix_sumlen_peak_bytes"),
      "peak_gib": gib(facts["prefix_sumlen_peak_bytes"]),
      "exception": facts.get("prefix_sumlen_exception", ""),
    },
    "select_column": {
      "type": facts["prefix_column_type"], "ms": num("prefix_column_ms"),
      "peak_bytes": num("prefix_column_peak_bytes"),
      "peak_gib": gib(facts["prefix_column_peak_bytes"]),
      "exception": facts.get("prefix_column_exception", ""),
    },
    "sum_length_bounded_settings": {
      "settings": "max_block_size = 64, max_threads = 4, max_memory_usage = 6000000000",
      "ms": num("prefix_bounded_ms"),
      "peak_bytes": num("prefix_bounded_peak_bytes"),
      "peak_gib": gib(facts.get("prefix_bounded_peak_bytes", "")),
      "read_rows": num("prefix_bounded_read_rows"),
      "read_bytes": num("prefix_bounded_read_bytes"),
      "read_mib": mib(facts.get("prefix_bounded_read_bytes", "")),
      "completed_runs": num("prefix_bounded_ok_runs"),
    },
  },
  "figure_3_postfix_forced_decode": {
    "settings": "ClickHouse defaults",
    "sum_length": {"ms": num("postfix_sumlen_ms"),
                   "peak_bytes": num("postfix_sumlen_peak_bytes"),
                   "peak_mib": mib(facts["postfix_sumlen_peak_bytes"]),
                   "read_rows": num("postfix_sumlen_read_rows"),
                   "read_bytes": num("postfix_sumlen_read_bytes")},
    "select_column": {"ms": num("postfix_column_ms"),
                      "peak_bytes": num("postfix_column_peak_bytes"),
                      "peak_mib": mib(facts["postfix_column_peak_bytes"])},
    "events_native_sum_length": {"ms": num("postfix_native_sumlen_ms"),
                                 "peak_bytes": num("postfix_native_peak_bytes"),
                                 "peak_mib": mib(facts["postfix_native_peak_bytes"])},
  },
  "figure_4_byte_identity": {
    "identical": facts["byte_identical"] == "yes",
    "rows": num("byte_identical_rows"),
    "prefix_sha256": facts["prefix_output_sha256"],
    "postfix_sha256": facts["postfix_output_sha256"],
    "bytes": num("postfix_output_bytes"),
  },
  "figure_5_quadratic_term": {
    "necessary_elements": num("necessary_elements"),
    "materialized_elements": num("materialized_elements"),
    "widest_template": {
      "literals": num("fat_template_literals"),
      "rows": num("fat_template_rows"),
      "share_of_materialized_pct": num("fat_template_share_pct"),
    },
  },
  "view_inlining_trap": {
    "old_body_still_in_view_after_function_replace": num("view_still_holds_old_body") > 0,
    "old_body_in_view_after_install_fixed": num("view_old_body_after_install_fixed") > 0,
  },
}
json.dump(out, open(sys.argv[2], "w"), indent=2)
open(sys.argv[2], "a").write("\n")

f1, f2, f3, f4, f5 = (out["figure_1_pruned_count"], out["figure_2_prefix_forced_decode"],
                      out["figure_3_postfix_forced_decode"], out["figure_4_byte_identity"],
                      out["figure_5_quadratic_term"])
print()
print(f"  ClickHouse {out['host']['clickhouse_version']}  |  container {out['host']['container_memory_limit']}"
      f"  |  server memory cap {out['host']['max_server_memory_usage_gib']} GiB"
      f"  |  {out['corpus']['rows']} rows")
print("  " + "-" * 76)
print(f"  1  SELECT count()                    {f1['ms']} ms, read {f1['read_rows']} row / "
      f"{f1['read_bytes']} bytes, {f1['explain_decode_nodes']} decode nodes in plan")
print(f"     forced decode plan                {f1['explain_decode_nodes_forced_query']} decode nodes")
print(f"  2  forced decode, PRE-fix            sum(length): {f2['sum_length']['type']} "
      f"@ {f2['sum_length']['peak_gib']} GiB")
b = f2.get("sum_length_bounded_settings", {})
print(f"     PRE-fix, bounded settings         {b.get('ms')} ms, {b.get('peak_gib')} GiB peak, "
      f"read {b.get('read_mib')} MiB")
print(f"                                       SELECT col : {f2['select_column']['type']} "
      f"@ {f2['select_column']['peak_gib']} GiB")
print(f"  3  forced decode, POST-fix           sum(length): {f3['sum_length']['ms']} ms, "
      f"{f3['sum_length']['peak_mib']} MiB peak")
print(f"                                       SELECT col : {f3['select_column']['ms']} ms, "
      f"{f3['select_column']['peak_mib']} MiB peak")
print(f"                                       events_native: {f3['events_native_sum_length']['ms']} ms")
print(f"  4  byte-identical output             {f4['identical']}  ({f4['rows']} rows, {f4['bytes']} bytes)")
print(f"  5  necessary array elements          {f5['necessary_elements']}")
print(f"     materialized (pre-fix)            {f5['materialized_elements']}")
print(f"     widest template                   {f5['widest_template']['literals']} literals, "
      f"{f5['widest_template']['rows']} rows, {f5['widest_template']['share_of_materialized_pct']}% of it")
print("  " + "-" * 76)
print(f"  results.json written to {sys.argv[2]}")
PY

say "done"
