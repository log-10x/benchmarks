#!/usr/bin/env bash
# The Receiver's memory and CPU on the run's own traffic.
#
#   rig/memory/run.sh
#
# Replays results/data/raw.jsonl.gz from the moment the Receiver came up with the fleet
# values (receiver_ready in results/timeline.jsonl) to the end of the capture, at the pace
# it was captured, through Fluent Bit into edge-10x launched with exactly the arguments,
# environment, policy files and limits in results/values-fleet/launch.json. docker stats
# samples the Receiver every 10 s. Everything runs on a private, internal Docker network;
# no port is published. Writes results/memory/.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DC=$(cd "$HERE/../.." && pwd)
VALUES=$DC/results/values-fleet
OUT=$DC/results/memory
DATA=$(mktemp -d "${TMPDIR:-/tmp}/rmem-data.XXXXXX")
NET=rmem-net
FB_IMAGE=fluent/fluent-bit:4.2@sha256:6806769c10acf11b41d14083b3101a24433b4ca113a1ab7a6b1a1b7cad86a7e8
PY_IMAGE=python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
INTERVAL=10

mkdir -p "$OUT"
rm -f "$OUT"/stats.tsv "$OUT"/replay.out "$OUT"/receiver.log "$OUT"/inspect.json "$OUT"/returned.json

read -r TENX_IMAGE CPUS MEM START END < <(python3 - "$VALUES/launch.json" "$DC/results/timeline.jsonl" "$DC/results/data/raw.jsonl.gz" <<'PY'
import gzip, json, sys
v = json.load(open(sys.argv[1]))
ready = [json.loads(l) for l in open(sys.argv[2])]
start = [e["epoch"] for e in ready if e["event"] == "receiver_ready" and e.get("cap")][-1]
end = max(float(json.loads(l)["fb_ts"]) for l in gzip.open(sys.argv[3], "rt"))
r = v["resources_limits"]
print(v["image"], r["cpus"], r["memory"], start, end)
PY
)
# RMEM_MINUTES shortens the replay for a trial of the rig; the published run leaves it unset.
if [ -n "${RMEM_MINUTES:-}" ]; then END=$(python3 -c "print(min($END, $START + 60 * $RMEM_MINUTES))"); fi
echo "image $TENX_IMAGE cpus $CPUS memory $MEM replay $START..$END"

ENV_ARGS=()
while IFS= read -r kv; do ENV_ARGS+=(-e "$kv"); done < <(python3 - "$VALUES/launch.json" <<'PY'
import json, sys
v = json.load(open(sys.argv[1]))
for e in v["env_applied"]:
    print(f"{e['name']}={e['value']}")
for e in v["env_substituted"]:
    print(f"{e['name']}={e['rig_value']}")
for k, val in v["rig_env"]:
    print(f"{k}={val}")
PY
)
APP_ARGS=()
while IFS= read -r a; do APP_ARGS+=("$a"); done < <(python3 -c 'import json,sys; v=json.load(open(sys.argv[1])); print("\n".join(v["args_from_values"]+v["measurement_args"]))' "$VALUES/launch.json")

cleanup() {
  [ -n "${SAMPLER:-}" ] && kill "$SAMPLER" 2>/dev/null || true
  docker rm -f rmem-replay rmem-tenx rmem-fluent-bit >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -rf "$DATA"
}
trap cleanup EXIT
cleanup_quiet() { docker rm -f rmem-replay rmem-tenx rmem-fluent-bit >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
cleanup_quiet

docker network create --internal "$NET" >/dev/null
docker run -d --name rmem-fluent-bit --network "$NET" --network-alias fluent-bit --memory 300m \
  -v "$HERE":/fluent-bit/etc/rig-memory:ro -v "$DC/rig/fluent-bit":/fluent-bit/etc/rig:ro -v "$DATA":/data \
  "$FB_IMAGE" /fluent-bit/bin/fluent-bit -c /fluent-bit/etc/rig-memory/fluent-bit.conf >/dev/null
docker run -d --name rmem-tenx --network "$NET" --network-alias tenx --cpus "$CPUS" --memory "$MEM" \
  "${ENV_ARGS[@]}" \
  -v "$VALUES/caps.csv":/etc/tenx/lookups/caps.csv:ro \
  -v "$VALUES/actions.csv":/etc/tenx/lookups/actions.csv:ro \
  "$TENX_IMAGE" "${APP_ARGS[@]}" >/dev/null
until docker logs rmem-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field'; do
  docker inspect rmem-tenx --format '{{.State.Running}}' | grep -q true || { docker logs rmem-tenx | tail -20; exit 1; }
  sleep 3
done
echo "receiver ready $(date -u +%FT%TZ)"

# One sample every INTERVAL seconds on a fixed grid: epoch, CPU %, memory used, limit, memory %.
(
  t0=$(date +%s); k=0
  while :; do
    line=$(docker stats --no-stream --format '{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' rmem-tenx 2>/dev/null || true)
    [ -n "$line" ] && printf '%s\t%s\n' "$(date +%s)" "$line" | sed 's| / |\t|' >> "$OUT/stats.tsv"
    k=$((k + 1)); next=$((t0 + k * INTERVAL)); now=$(date +%s)
    [ "$next" -gt "$now" ] && sleep $((next - now))
  done
) &
SAMPLER=$!

sleep 30   # idle samples before the first record
echo "replay start $(date -u +%FT%TZ) epoch $(date +%s)" | tee -a "$OUT/replay.out"
docker run --rm --name rmem-replay --network "$NET" \
  -v "$DC/results/data/raw.jsonl.gz":/in/raw.jsonl.gz:ro -v "$HERE/replay.py":/replay.py:ro \
  "$PY_IMAGE" python -I /replay.py /in/raw.jsonl.gz fluent-bit 24224 "$START" "$END" | tee -a "$OUT/replay.out"
echo "replay end $(date -u +%FT%TZ) epoch $(date +%s)" | tee -a "$OUT/replay.out"
sleep 60   # the last groups flush and come back
kill "$SAMPLER" 2>/dev/null || true; SAMPLER=

docker inspect rmem-tenx --format '{"oom_killed":{{.State.OOMKilled}},"restart_count":{{.RestartCount}},"running":{{.State.Running}},"memory_limit_bytes":{{.HostConfig.Memory}},"nano_cpus":{{.HostConfig.NanoCpus}},"image":"{{.Config.Image}}"}' > "$OUT/inspect.json"
docker logs rmem-tenx > "$OUT/receiver.log" 2>&1 || true
docker stop -t 30 rmem-fluent-bit >/dev/null
python3 - "$DATA" > "$OUT/returned.json" <<'PY'
import json, os, sys
d = sys.argv[1]
out = {}
for r in ("pass", "offload", "tier_down", "other"):
    p = os.path.join(d, r + ".jsonl")
    out[r] = sum(1 for _ in open(p, errors="replace")) if os.path.exists(p) else 0
print(json.dumps(out))
PY
python3 "$HERE/summarize.py"
