#!/usr/bin/env bash
#
# Elasticsearch 9.5.5 store size, four ways, on the published OpenTelemetry demo sample: a raw
# index, logsdb, logsdb with message as pattern_text, and the engine's compact form. METHOD.md is
# the plan, written before the run.
#
#   ./run.sh           encode the sample twice and decode it once with the engine, start one
#                      Elasticsearch node on a trial licence, index and measure the variants
#                      ES4_REPS times, report, tear down
#   ./run.sh report    re-render results/results.{json,md} from results/
#
# Environment:
#   ES4_SAMPLE    path to otel-sample-200mb.log (default data/otel-sample-200mb.log, fetched from the
#                 otel-sample-v1 release of log-10x/config when absent); always checked by sha256
#   ES4_IMAGE     engine image (default ghcr.io/log-10x/edge-10x:1.1.150, by digest)
#   ES4_ES_IMAGE  Elasticsearch image (default 9.5.5, by digest)
#   ES4_PORT      port on 127.0.0.1 for Elasticsearch (default 9205)
#   ES4_HEAP      Elasticsearch heap (default 1g); ES4_MEM the container limit (default 2g)
#   ES4_REPS      repetitions (default 2)
#   ES4_VARIANTS  comma-separated (default raw,logsdb,pattern,compact; compact_logsdb also exists)
#   ES4_KEEP=1    leave Elasticsearch up and keep data/out
#
# Containers are started detached under fixed names and removed with `docker rm -f -v`, on exit too.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="$HERE/data"
OUT="$DATA/out"
RESULTS="$HERE/results"
CFG="$HERE/../drain3-vs-log10x"
IMAGE="${ES4_IMAGE:-ghcr.io/log-10x/edge-10x:1.1.150@sha256:3e755bbc14780a27e643e09b76dfd7ec9616cab67833f70daf9420eff646d350}"
ES_IMAGE="${ES4_ES_IMAGE:-docker.elastic.co/elasticsearch/elasticsearch:9.5.5@sha256:13b4a40bb095774f5fda635e45fd5677cc6a26565e42b24997b0c72b88e75984}"
PORT="${ES4_PORT:-9205}"
HEAP="${ES4_HEAP:-1g}"
MEM="${ES4_MEM:-2g}"
REPS="${ES4_REPS:-2}"
VARIANTS="${ES4_VARIANTS:-raw,logsdb,pattern,compact}"
export ES4_URL="http://127.0.0.1:$PORT"
ES_NAME=es4-es
ENGINE_NAME=es4-engine

RELEASE="https://github.com/log-10x/config/releases/download/otel-sample-v1"
ASSET="otel-sample-200mb.log"
ASSET_GZ_SHA256="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
ASSET_BYTES=215039161
ASSET_LINES=197430

say() { printf '\n=== %s\n' "$*"; }
die() { echo "error: $*" >&2; exit 1; }
sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }

if [ "${1:-}" = report ]; then
  exec python3 "$HERE/bench.py" report --results "$RESULTS"
fi
[ "$#" -eq 0 ] || die "usage: ./run.sh | ./run.sh report"

teardown() {
  docker rm -f -v "$ENGINE_NAME" >/dev/null 2>&1 || true
  if [ "${ES4_KEEP:-0}" = 1 ]; then echo "ES4_KEEP=1: $ES_NAME left up on $ES4_URL"; return; fi
  docker rm -f -v "$ES_NAME" >/dev/null 2>&1 || true
}

# engine <config> <log file> [docker run options...]: one engine run to completion, detached, then removed
engine() {
  local cfg="$1" log="$2" waited=0 rc
  shift 2
  docker rm -f -v "$ENGINE_NAME" >/dev/null 2>&1 || true
  docker run -d --name "$ENGINE_NAME" -e TZ=UTC "$@" -v "$cfg":/cfg/run.yaml:ro "$IMAGE" @/cfg/run.yaml >/dev/null
  while [ "$(docker inspect -f '{{.State.Running}}' "$ENGINE_NAME")" = true ]; do
    sleep 2
    waited=$((waited + 2))
    if [ "$waited" -ge 1800 ]; then
      docker logs "$ENGINE_NAME" > "$log" 2>&1 || true
      docker rm -f -v "$ENGINE_NAME" >/dev/null
      die "the engine did not finish within 1800 s; its log is $log"
    fi
  done
  rc="$(docker inspect -f '{{.State.ExitCode}}' "$ENGINE_NAME")"
  docker logs "$ENGINE_NAME" > "$log" 2>&1 || true
  docker rm -f -v "$ENGINE_NAME" >/dev/null
  [ "$rc" = 0 ] || { tail -20 "$log" >&2; die "the engine exited $rc; its log is $log"; }
  echo "  done in ${waited}s"
}

say "preflight"
command -v docker >/dev/null || die "docker is required"
command -v python3 >/dev/null || die "python3 is required"
if curl -s -m 3 -o /dev/null "$ES4_URL"; then die "something already answers on $ES4_URL; set ES4_PORT"; fi
for n in "$ES_NAME" "$ENGINE_NAME"; do
  if docker inspect "$n" >/dev/null 2>&1; then die "a container named $n exists; remove it first (docker rm -f -v $n)"; fi
done
free_kb="$(df -Pk "$HERE" | awk 'NR == 2 { print $4 }')"
[ "$free_kb" -gt 3000000 ] || die "under 3 GB free where data/ lives"
trap teardown EXIT
mkdir -p "$DATA" "$RESULTS"
rm -rf "$RESULTS"/rep[0-9]* "$RESULTS/results.json" "$RESULTS/results.md"

say "sample"
SAMPLE="${ES4_SAMPLE:-$DATA/$ASSET}"
if [ ! -s "$SAMPLE" ]; then
  [ -z "${ES4_SAMPLE:-}" ] || die "$SAMPLE not found"
  echo "downloading $RELEASE/$ASSET.gz"
  curl -fsSL -o "$DATA/$ASSET.gz" "$RELEASE/$ASSET.gz"
  [ "$(sha256 "$DATA/$ASSET.gz")" = "$ASSET_GZ_SHA256" ] || die "the gzipped asset's sha256 differs from the release's"
  gunzip -c "$DATA/$ASSET.gz" > "$SAMPLE.part" && mv "$SAMPLE.part" "$SAMPLE"
fi
SAMPLE="$(cd "$(dirname "$SAMPLE")" && pwd)/$(basename "$SAMPLE")"
[ "$(sha256 "$SAMPLE")" = "$ASSET_SHA256" ] || die "$SAMPLE: sha256 differs from the release's"
[ "$(wc -c < "$SAMPLE" | tr -d ' ')" = "$ASSET_BYTES" ] || die "$SAMPLE: byte count differs"
[ "$(wc -l < "$SAMPLE" | tr -d ' ')" = "$ASSET_LINES" ] || die "$SAMPLE: line count differs"
echo "$SAMPLE: $ASSET_BYTES bytes, $ASSET_LINES lines, sha256 matches"

say "images"
for img in "$IMAGE" "$ES_IMAGE"; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img" >/dev/null
done
ENGINE_DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
ES_DIGEST="$(docker image inspect "$ES_IMAGE" --format '{{index .RepoDigests 0}}')"
echo "$ENGINE_DIGEST"
echo "$ES_DIGEST"

# The published round-trip configs, read where they live (as otel-denominators/ does), unchanged.
for n in 1 2; do
  say "encode, run $n of 2"
  d="$OUT/encode$n"
  rm -rf "$d"; mkdir -p "$d"; chmod 777 "$d"
  engine "$CFG/tenx-encode.config.yaml" "$OUT/encode$n.log" \
    -e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out -v "$SAMPLE":/in/events.log:ro -v "$d":/out
  [ -s "$d/encoded.log" ] && [ -s "$d/templates.json" ] || die "encode run $n wrote no encoded.log or templates.json"
done

say "decode, compared with the sample"
d="$OUT/decode"
rm -rf "$d"; mkdir -p "$d"; chmod 777 "$d"
cat "$OUT/encode1/templates.json" "$OUT/encode1/encoded.log" > "$d/compact.log"
engine "$CFG/tenx-decode.config.yaml" "$OUT/decode.log" -e INPUT_FILE=/out/compact.log -e OUTPUT_DIR=/out -v "$d":/out
[ -s "$d/decoded.log" ] || die "decode wrote no decoded.log"
python3 "$HERE/bench.py" compact-record --sample "$SAMPLE" --enc1 "$OUT/encode1" --enc2 "$OUT/encode2" \
  --decoded "$d/decoded.log" --image "$ENGINE_DIGEST" --encode-config "$CFG/tenx-encode.config.yaml" \
  --decode-config "$CFG/tenx-decode.config.yaml" --out "$RESULTS/compact.json"
rm -f "$d/compact.log" "$d/decoded.log"

say "Elasticsearch"
docker run -d --name "$ES_NAME" -p "127.0.0.1:$PORT:9200" --memory "$MEM" \
  --ulimit memlock=-1:-1 --ulimit nofile=65536:65536 \
  -e discovery.type=single-node -e cluster.name=es4 -e node.name=es4 \
  -e xpack.security.enabled=false -e xpack.ml.enabled=false \
  -e cluster.routing.allocation.disk.threshold_enabled=false \
  -e "ES_JAVA_OPTS=-Xms$HEAP -Xmx$HEAP" "$ES_IMAGE" >/dev/null
up=0
for _ in $(seq 1 60); do
  if curl -s -m 5 "$ES4_URL/_cluster/health?wait_for_status=green&timeout=4s" 2>/dev/null | grep -q '"status":"green"'; then up=1; break; fi
  sleep 5
done
[ "$up" = 1 ] || { docker logs --tail 40 "$ES_NAME" >&2; die "Elasticsearch did not come up on $ES4_URL"; }
python3 "$HERE/bench.py" licence --es-image "$ES_DIGEST" --out "$RESULTS/licence.json"

for rep in $(seq 1 "$REPS"); do
  say "repetition $rep of $REPS"
  python3 "$HERE/bench.py" measure --rep "$rep" --sample "$SAMPLE" --compact-dir "$OUT/encode1" \
    --results "$RESULTS" --variants "$VARIANTS"
done
docker logs "$ES_NAME" > "$DATA/es.log" 2>&1 || true

say "report"
status=0
python3 "$HERE/bench.py" report --results "$RESULTS" || status=$?
if [ "${ES4_KEEP:-0}" != 1 ]; then rm -rf "$OUT"; fi
[ "$status" = 0 ] || die "a check failed; see results/results.md"
