#!/usr/bin/env bash
#
# Gap 4: kill a container mid-stream, restart it, let the run finish, then
# reconcile. Every input line carries a sequence number inside its own body
# (make_seq_input.py), so hot plus cold can be counted line by line and not only
# in total: a line that arrived twice is a duplicate, a line that arrived never
# is a gap. The per-type count is reconciled beside it, wire against stored.
#
# Each arm is a full run over the whole capture. The first three run the
# collector the way the shipped OpenTelemetry Collector recipe
# (modules: input/forwarder/otel-collector/conf/tenx-sidecar.yaml) runs it: the
# file position and the exporter queues in a file_storage extension, the queue
# into the receiver with one sender, a 30 s timeout and retries without a
# deadline, no batch processor between a receiver and a persisted queue, and
# the file receiver emitting synchronously. The receiver answers an export only
# once every line of it is written back and acknowledged, filtered out or
# rejected, so they need a receiver built with that change (PATCHED_JAR or
# CSE_ENGINE_IMAGE).
#
#   router  the routing collector is killed mid-stream and restarted.
#   engine  the receiver is killed mid-stream and restarted.
#   both    the collector and the receiver are killed together and both
#           restarted.
#
# The pass bar: no input line stored nowhere, on every arm. The script exits
# non-zero when any arm's seq_missing is above zero, after writing the results.
# Duplicates are reported, not asserted: a request answered whole is resent
# whole, so the lines of a request in flight at the kill can arrive twice.
#
# Two more arms keep the comparison the first pass ran, on the collector config
# it ran with (file position checkpointed, default queues, the batch processor
# on the cold route), against whichever receiver the run starts:
#   owners  the `router` arm again, with the collector configured the way the
#           component's own code owners prescribe. Andrzej Stencel, who owns the
#           component, on contrib issue 40741, 2025-06-24: "I recommend to remove
#           the Batch processor from the pipeline... Try disabling the [sending
#           queue] with `sending_queue::enabled: false` or make it blocking with
#           `sending_queue::wait_for_result: true`", and the reporter answered
#           "you were right, with that configuration it works as expected".
#           paulojmdias supplies the receiver half, on contrib issue 46945: "The
#           filelog receiver has a `retry_on_failure` option (disabled by
#           default)... If you set `max_elapsed_time: 0`... the offset only
#           advances after successful delivery." All three are applied here, and
#           the arm reports what they cost in wall clock beside what they save.
#   persist the `router` arm again, with every exporter queue backed by the same
#           file_storage extension that already holds the file position. The
#           checkpoint arms persist where the reader got to; nothing persists
#           what the exporters were still holding, so a kill drops those queues.
#           This arm keeps the queues enabled and the batch processor in place
#           and writes each queue to disk, which is the only shape that can
#           carry an accepted but undelivered batch across the restart.
#
#   ./gap4_durable_handoff.sh                the three custody arms
#   ./gap4_durable_handoff.sh router owners  the pair the first comparison ran
#
# The arm list also names the output: any run whose arms are not exactly
# `router engine` writes results/gap4-<arms joined>.json, so the committed first
# pass is never overwritten.
#
# Environment: as lib.sh. KILL_AFTER_ROWS (default 20000) is the hot row count
# that triggers the kill, DOWN_SECONDS (default 20) how long the container stays
# down.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

KILL_AFTER_ROWS="${KILL_AFTER_ROWS:-20000}"
DOWN_SECONDS="${DOWN_SECONDS:-20}"
OUT="$RESULTS/gap4.json"
SEQ_RE='tenxseq[^0-9]{0,4}([0-9]+)'

trap g_teardown EXIT
g_require
say "input"
g_input
SEQ_INPUT="$DATA_DIR/gaps-seq.log"
if [ ! -s "$SEQ_INPUT" ] || [ "$SEQ_INPUT" -ot "$FEED" ]; then
  python3 "$GAPS_HERE/make_seq_input.py" --in "$FEED" --out "$SEQ_INPUT"
fi
SEQ_LINES="$(wc -l < "$SEQ_INPUT" | tr -d ' ')"
FEED="$SEQ_INPUT"; FEED_NAME="$(basename "$SEQ_INPUT")"; FEED_DIR="$(dirname "$SEQ_INPUT")"
echo "  numbered input: $SEQ_LINES lines"

g_render_harness_conf
# The collector keeps its file position across a restart. Nothing else in the
# route changes.
python3 - "$BUILD/conf/router.yaml" "$BUILD/conf/router_ckpt.yaml" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
t = t.replace("extensions:\n  json_log_encoding/cold:",
              "extensions:\n  file_storage/ckpt:\n    directory: /ckpt\n    timeout: 10s\n"
              "  json_log_encoding/cold:", 1)
t = t.replace("  filelog:\n    include:", "  filelog:\n    storage: file_storage/ckpt\n    include:", 1)
t = t.replace("  extensions: [ json_log_encoding/cold ]",
              "  extensions: [ json_log_encoding/cold, file_storage/ckpt ]", 1)
open(dst, "w").write(t)
print("  router config with a file_storage checkpoint written")
PY

# The code owners' prescription, applied on top of the checkpoint config:
# the file receiver retries forever and advances its offset only after delivery,
# no batch processor stands between the route and a sink, and every exporter
# queue is off so an export is synchronous with the receiver's read.
python3 - "$BUILD/conf/router_ckpt.yaml" "$BUILD/conf/router_owners.yaml" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
t = t.replace("  filelog:\n    storage: file_storage/ckpt\n",
              "  filelog:\n    storage: file_storage/ckpt\n"
              "    retry_on_failure:\n      enabled: true\n      max_elapsed_time: 0\n", 1)
# g_render_harness_conf turns the drop into backpressure with block_on_overflow.
# The owners' arm goes further and takes the queue out of the path entirely.
t = t.replace("  otlp/engine:\n    sending_queue:\n      block_on_overflow: true\n",
              "  otlp/engine:\n    sending_queue:\n      enabled: false\n", 1)
t = t.replace("  otlp/clickstack:\n", "  otlp/clickstack:\n    sending_queue:\n      enabled: false\n", 1)
t = t.replace("  awss3/cold:\n", "  awss3/cold:\n    sending_queue:\n      enabled: false\n", 1)
t = t.replace("      processors: [ transform/cold, batch/cold ]",
              "      processors: [ transform/cold ]", 1)
open(dst, "w").write(t)
for needle in ("retry_on_failure", "enabled: false", "[ transform/cold ]"):
    assert needle in t, needle
print("  router config with the code owners' prescription written")
PY

# The persistent sending queue, applied on top of the checkpoint config. The
# same file_storage extension that holds the file position now holds each
# exporter's queue, so a batch the collector had accepted but not yet delivered
# is on disk when the container dies and is replayed when it comes back. The
# batch processor stays in the cold pipeline, and otlp/engine keeps blocking on
# overflow.
python3 - "$BUILD/conf/router_ckpt.yaml" "$BUILD/conf/router_persist.yaml" <<'PQ'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
t = t.replace("  otlp/engine:\n    sending_queue:\n      block_on_overflow: true\n",
              "  otlp/engine:\n    sending_queue:\n      enabled: true\n"
              "      block_on_overflow: true\n      storage: file_storage/ckpt\n", 1)
t = t.replace("  otlp/clickstack:\n",
              "  otlp/clickstack:\n    sending_queue:\n      enabled: true\n"
              "      storage: file_storage/ckpt\n", 1)
t = t.replace("  awss3/cold:\n",
              "  awss3/cold:\n    sending_queue:\n      enabled: true\n"
              "      storage: file_storage/ckpt\n", 1)
assert t.count("\n      storage: file_storage/ckpt\n") == 3, t
assert t.count("\n    storage: file_storage/ckpt\n") == 1, t
for needle in ("  file_storage/ckpt:", "      block_on_overflow: true",
               "[ transform/cold, batch/cold ]", "  filelog:\n    storage: file_storage/ckpt"):
    assert needle in t, needle
open(dst, "w").write(t)
print("  router config with a persistent sending queue written")
PQ

# The recipe's settings, applied on top of the checkpoint config. The same
# file_storage extension holds the file position and every exporter queue.
# Batching moves into the persisted queues: into the receiver, by bytes, under
# the 4 MiB gRPC message the receiver accepts; on the cold route, by records,
# as batch/cold did. The recipe's recombine operator is left out: every plain
# numbered line starts with `tenxseq=`, so no continuation rule can match, and
# the operator would still hold the newest line in memory across a kill. The
# `batch` key under awss3/cold's sending_queue is not checked against that
# exporter's source; the other keys are checked against the v0.143.0 sources of
# the core exporter helper and the contrib file receiver.
python3 - "$BUILD/conf/router_ckpt.yaml" "$BUILD/conf/router_custody.yaml" <<'PC'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
retry = "    retry_on_failure:\n      enabled: true\n      max_elapsed_time: 0\n"
t = t.replace("  otlp/engine:\n    sending_queue:\n      block_on_overflow: true\n",
              "  otlp/engine:\n    timeout: 30s\n" + retry +
              "    sending_queue:\n      enabled: true\n      num_consumers: 1\n"
              "      block_on_overflow: true\n      storage: file_storage/ckpt\n"
              "      batch:\n        flush_timeout: 1s\n        sizer: bytes\n"
              "        min_size: 1048576\n        max_size: 2097152\n", 1)
t = t.replace("  otlp/clickstack:\n",
              "  otlp/clickstack:\n" + retry +
              "    sending_queue:\n      enabled: true\n      storage: file_storage/ckpt\n", 1)
t = t.replace("  awss3/cold:\n",
              "  awss3/cold:\n" + retry +
              "    sending_queue:\n      enabled: true\n      storage: file_storage/ckpt\n"
              "      batch:\n        flush_timeout: 5s\n        sizer: items\n        min_size: 5000\n", 1)
t = t.replace("      processors: [ transform/cold, batch/cold ]",
              "      processors: [ transform/cold ]", 1)
assert t.count("\n      storage: file_storage/ckpt\n") == 3, t
assert t.count("      max_elapsed_time: 0\n") == 3, t
for needle in ("    timeout: 30s\n", "      num_consumers: 1\n", "[ transform/cold ]",
               "  filelog:\n    storage: file_storage/ckpt"):
    assert needle in t, needle
assert "batch/cold ]" not in t, t
open(dst, "w").write(t)
print("  router config with the recipe's custody settings written")
PC

# Without the gate the file receiver hands lines on from a buffer it fills in
# the background, and its checkpoint can pass lines still in that buffer.
CUSTODY_COMMAND="--config=/etc/otelcol-contrib/config.yaml --feature-gates=stanza.synchronousLogEmitter"

g_images "$CS_IMAGE" "$OTEL_IMAGE" "$MINIO_IMAGE" "$MC_IMAGE" "$EDGE_IMAGE"

ARMS=("$@")
[ ${#ARMS[@]} -gt 0 ] || ARMS=(router engine both)
ARMS_KEY="$(printf '%s-' "${ARMS[@]}")"; ARMS_KEY="${ARMS_KEY%-}"
[ "$ARMS_KEY" = "router-engine" ] || OUT="$RESULTS/gap4-$ARMS_KEY.json"

arm_result_json="{}"

run_arm() {
  local arm="$1"
  say "arm: $arm"
  g_net
  g_minio_up
  g_clickstack_up
  mkdir -p "$BUILD/policy" "$BUILD/ckpt"
  rm -f "$BUILD/ckpt"/* 2>/dev/null || true
  chmod 777 "$BUILD/ckpt"
  cp "$BUILD/conf/caps.csv" "$BUILD/conf/actions.csv" "$BUILD/policy/"
  touch "$BUILD/policy/caps.csv" "$BUILD/policy/actions.csv"
  g_engine_up "$BUILD/policy"
  local conf="$BUILD/conf/router_custody.yaml" command="$CUSTODY_COMMAND"
  [ "$arm" = "owners" ] && { conf="$BUILD/conf/router_owners.yaml"; command=""; }
  [ "$arm" = "persist" ] && { conf="$BUILD/conf/router_persist.yaml"; command=""; }
  local started_at; started_at="$(date +%s)"
  ROUTER_COMMAND="$command" g_router_up "$conf" -v "$BUILD/ckpt":/ckpt

  # Kill when the hot table passes the mark, and never before data is moving.
  local cur=0 waited=0
  until [ "$cur" -ge "$KILL_AFTER_ROWS" ] || [ "$waited" -ge 900 ]; do
    sleep 5; waited=$((waited + 5))
    cur="$(chq "SELECT count() FROM default.otel_logs" 2>/dev/null || echo 0)"
  done
  local killed_at="$cur"
  local victims=("$ROUTER")
  [ "$arm" = "engine" ] && victims=("$ENGINE")
  [ "$arm" = "both" ] && victims=("$ENGINE" "$ROUTER")
  local killed_after=$(( $(date +%s) - started_at ))
  echo "  killing ${victims[*]} at $killed_at hot rows"
  docker kill "${victims[@]}" >/dev/null
  sleep "$DOWN_SECONDS"
  # The receiver starts first, so the collector's resends find it listening.
  docker start "${victims[@]}" >/dev/null
  echo "  ${victims[*]} back up"
  # A restarted receiver writes its listening line again, after the old one in
  # the same log, so the wait is on a fresh log read and not on the old line.
  case "$arm" in engine|both) sleep 10; g_engine_wait ;; esac

  # The collector restarts on purpose in this gap, which resets the counter
  # the strict check reads, so this one settles on stillness alone and the
  # reconciliation below is what says whether every line arrived.
  g_wait_settle default.otel_logs 8 0
  # Stillness costs eight polls of fifteen seconds, the same in every arm, so
  # the wall clock is comparable across arms once that constant is taken off.
  local run_seconds=$(( $(date +%s) - started_at - 120 - DOWN_SECONDS ))
  g_flush_cold
  g_wait_for_object "$BUCKET" || true
  docker exec -i "$CS" clickhouse-client --multiquery < "$BUILD/conf/schema_cold.sql"

  local hot cold objects
  hot="$(chq "SELECT count() FROM default.otel_logs")"
  cold="$(chq "SELECT count() FROM default.otel_logs_coldv")"
  objects="$(g_objects)"

  # The reconciliation. One pass over hot plus cold through the merge table,
  # every sequence number in every body.
  local seq_sql="SELECT toUInt64(arrayJoin(extractAll(Body, '$SEQ_RE'))) AS seq FROM default.otel_logs_all"
  local occurrences distinct dupes dup_lines missing
  occurrences="$(chq "SELECT count() FROM ($seq_sql)")"
  distinct="$(chq "SELECT uniqExact(seq) FROM ($seq_sql)")"
  dupes="$(chq "SELECT count() FROM (SELECT seq, count() c FROM ($seq_sql) GROUP BY seq HAVING c > 1)")"
  dup_lines="$(chq "SELECT sum(c - 1) FROM (SELECT seq, count() c FROM ($seq_sql) GROUP BY seq HAVING c > 1)")"
  missing="$(chq "SELECT count() FROM (SELECT number + 1 AS n FROM numbers($SEQ_LINES)
                  WHERE n NOT IN (SELECT seq FROM ($seq_sql)))")"

  # And the same reconciliation by pattern hash, wire against stored.
  python3 "$GAPS_HERE/wire_hashes.py" --wire "$BUILD/wire/returned.json" \
    --out "$BUILD/gap4_${arm}_wire.json"
  chq "SELECT LogAttributes['tenx_hash'], count() FROM default.otel_logs_all GROUP BY 1
       FORMAT TSV" > "$BUILD/gap4_${arm}_stored.tsv"

  python3 - "$BUILD/gap4_$arm.json" "$BUILD/gap4_${arm}_wire.json" "$BUILD/gap4_${arm}_stored.tsv" <<PY
import json, sys
out, wire_path, stored_path = sys.argv[1], sys.argv[2], sys.argv[3]
wire = json.load(open(wire_path))
stored = {}
for line in open(stored_path):
    line = line.rstrip("\n")
    if not line:
        continue
    h, n = line.split("\t")
    stored[h] = int(n)
wire_hashes = wire["per_hash"]
short = {h: wire_hashes[h] - stored.get(h, 0) for h in wire_hashes if wire_hashes[h] > stored.get(h, 0)}
over = {h: stored[h] - wire_hashes.get(h, 0) for h in stored if stored[h] > wire_hashes.get(h, 0)}
json.dump({
 "arm": "$arm",
 "input_lines": $SEQ_LINES,
 "killed_at_hot_rows": ${killed_at:-0},
 "killed_after_seconds": ${killed_after:-0},
 "run_seconds": ${run_seconds:-0},
 "down_seconds": $DOWN_SECONDS,
 "wire_records": wire["total"],
 "hot_rows": ${hot:-0}, "cold_rows": ${cold:-0}, "objects": "$objects",
 "seq_occurrences": ${occurrences:-0}, "seq_distinct": ${distinct:-0},
 "seq_duplicated": ${dupes:-0}, "seq_duplicate_lines": ${dup_lines:-0}, "seq_missing": ${missing:-0},
 "hashes_on_wire": len(wire_hashes), "hashes_stored": len(stored),
 "hashes_short": len(short), "hashes_over": len(over),
 "records_short_by_hash": sum(short.values()), "records_over_by_hash": sum(over.values()),
 "worst_short": sorted(short.items(), key=lambda kv: -kv[1])[:5],
 "worst_over": sorted(over.items(), key=lambda kv: -kv[1])[:5],
}, open(out, "w"), indent=1)
print(json.dumps(json.load(open(out)), indent=1)[:900])
PY
  docker rm -f -v "$ROUTER" "$ENGINE" "$CS" "$MINIO" >/dev/null 2>&1 || true
}

for arm in "${ARMS[@]}"; do run_arm "$arm"; done

python3 - "$OUT" "$BUILD" "${ARMS[@]}" <<'PY'
import json, pathlib, sys
out, build = sys.argv[1], pathlib.Path(sys.argv[2])
arms = sys.argv[3:]
results = [json.loads((build / f"gap4_{a}.json").read_text()) for a in arms]
json.dump({"gap": 4, "arms": results}, open(out, "w"), indent=1)
print("wrote", out)
failed = False
for r in results:
    verdict = "PASS" if r["seq_missing"] == 0 else "FAIL"
    failed |= verdict == "FAIL"
    print(f"  {r['arm']:8} {verdict}  missing {r['seq_missing']}, duplicate lines {r['seq_duplicate_lines']}")
sys.exit(1 if failed else 0)
PY

say "done"
