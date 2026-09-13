#!/usr/bin/env bash
#
# One command. Fetches the public capture, encodes it in INNER mode with the
# pinned engine image, maps both forms into ClickHouse's own ClickStack
# `otel_logs` schema, loads three arms at three codecs, force-merges them, reads
# the byte counts out of system.parts and system.parts_columns, times one text
# filter per arm, and writes results/results.json and
# results/clickstack-storage-<date>.md.
#
#   ./run.sh              everything, reusing whatever is already in data/
#   FRESH=1 ./run.sh      drop the cached engine output and rebuild it
#   KEEP=1 ./run.sh       leave the ClickHouse container up afterwards
#
# Needs Docker, about 4 GB of free disk, and roughly 20 minutes on a warm host.
#
# Environment:
#   CCS_DATA_DIR   download and derived-input cache (default: <dir>/data)
#   CCS_ENGINE     engine image   (default: log10x/pipeline-10x:1.1.5)
#   CCS_CH_IMAGE   ClickHouse image (default: clickhouse/clickhouse-server:latest)

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

DATA_DIR="${CCS_DATA_DIR:-$HERE/data}"
ENGINE="${CCS_ENGINE:-log10x/pipeline-10x:1.1.5}"
CH_IMAGE="${CCS_CH_IMAGE:-clickhouse/clickhouse-server:latest}"
CTR=ch-clickstack
RESULTS="$HERE/results"

# The public capture. Both arms are built from this one file, so the two sides
# are the same source logs by construction rather than by assertion.
RELEASE="https://github.com/log-10x/config/releases/download/otel-sample-v2"
ASSET="otel-sample-200mb.log"
ASSET_GZ_SHA256="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"

# The term the query arm filters on: 2,316 of the 197,430 lines, 1.17%.
TERM="checkout"

ARMS=(native compact native_folded)
CODECS=(zstd1 zstd3 lz4)
codec_expr() {
  case "$1" in
    zstd1) echo "ZSTD(1)" ;;
    zstd3) echo "ZSTD(3)" ;;
    lz4)   echo "LZ4" ;;
  esac
}

say() { printf '\n=== %s\n' "$*"; }
ch() { docker exec "$CTR" clickhouse-client --allow_experimental_full_text_index=1 "$@"; }

mkdir -p "$DATA_DIR" "$RESULTS"
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

# ------------------------------------------------------------------- the data
say "public capture"
GZ="$DATA_DIR/$ASSET.gz"
PLAIN="$DATA_DIR/$ASSET"
[ -s "$GZ" ] || curl -fsSL -o "$GZ" "$RELEASE/$ASSET.gz"
[ -s "$PLAIN" ] || gunzip -c "$GZ" > "$PLAIN"
GZ_SHA="$(shasum -a 256 "$GZ" | cut -d' ' -f1)"
PLAIN_SHA="$(shasum -a 256 "$PLAIN" | cut -d' ' -f1)"
if [ "$GZ_SHA" != "$ASSET_GZ_SHA256" ] || [ "$PLAIN_SHA" != "$ASSET_SHA256" ]; then
  echo "the release asset does not match the sha256 this results table was measured on." >&2
  echo "rerun and recommit results/ rather than reporting the committed numbers." >&2
  exit 1
fi
echo "$ASSET  $(wc -c < "$PLAIN" | tr -d ' ') bytes  sha256 $PLAIN_SHA"

# ----------------------------------------------------------- the compact form
say "engine image"
docker image inspect "$ENGINE" >/dev/null 2>&1 || docker pull "$ENGINE"
ENGINE_DIGEST="$(docker image inspect "$ENGINE" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "$ENGINE")"
echo "$ENGINE_DIGEST"

INNER="$DATA_DIR/inner"
[ "${FRESH:-0}" = "1" ] && rm -rf "$INNER"
if [ ! -s "$INNER/encoded.log" ]; then
  say "INNER encode: keep the Fluentd envelope, compact the message"
  rm -rf "$INNER"; mkdir -p "$INNER"
  docker run --rm \
    -e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out \
    -v "$INNER":/out -v "$PLAIN":/in/events.log:ro \
    -v "$HERE/tenx-encode-inner.config.yaml":/cfg/enc.yaml:ro \
    "$ENGINE" @/cfg/enc.yaml > "$INNER/encode.stdout" 2>&1
fi
echo "encoded.log    $(wc -c < "$INNER/encoded.log" | tr -d ' ') bytes, $(wc -l < "$INNER/encoded.log" | tr -d ' ') records"
echo "templates.json $(wc -c < "$INNER/templates.json" | tr -d ' ') bytes, $(wc -l < "$INNER/templates.json" | tr -d ' ') templates"

# ------------------------------------------------------------------- the arms
ARMS_DIR="$DATA_DIR/arms"
if [ ! -s "$ARMS_DIR/manifest.json" ]; then
  say "map both forms into the ClickStack schema"
  python3 build_arms.py --raw "$PLAIN" --encoded "$INNER/encoded.log" \
    --templates "$INNER/templates.json" --out-dir "$ARMS_DIR"
fi

# ------------------------------------------------------------------ ClickHouse
say "ClickHouse"
docker rm -f "$CTR" >/dev/null 2>&1 || true
docker image inspect "$CH_IMAGE" >/dev/null 2>&1 || docker pull "$CH_IMAGE"
docker run -d --name "$CTR" --memory 8g --cpus 8 \
  -v "$ARMS_DIR":/arms:ro -v "$INNER":/inner:ro "$CH_IMAGE" >/dev/null
until docker exec "$CTR" clickhouse-client --query "SELECT 1" >/dev/null 2>&1; do sleep 1; done
CH_VERSION="$(docker exec "$CTR" clickhouse-client --query "SELECT version()")"
echo "ClickHouse $CH_VERSION"
ch --query "CREATE DATABASE IF NOT EXISTS bench"

# The decode path the compact arm reads through. This is the CORRECTED install
# from ../clickhouse-inflate, not the one the product repo ships: the shipped
# tenx_inflate_core builds its result with an index lambda that captures the
# literals and slots arrays, which is quadratic and aborts on a full-table
# decode. ../clickhouse-inflate/README.md has the measurement; the fix has not
# been applied back to log-10x/clickhouse-app.
say "install the decode path (corrected inflate functions + template dictionary)"
docker exec -i "$CTR" clickhouse-client --multiquery < ../clickhouse-inflate/install-fixed.sql
docker exec "$CTR" bash -c \
  "clickhouse-client --query 'INSERT INTO tenx.templates (templateHash, template) FORMAT JSONEachRow' < /inner/templates.json"
ch --query "SYSTEM RELOAD DICTIONARY tenx.templates_dict"
ch --query "SELECT 'templates loaded: ' || toString(count()) FROM tenx.templates"

# -------------------------------------------------------------- load the arms
for arm in "${ARMS[@]}"; do
  for codec in "${CODECS[@]}"; do
    table="otel_logs_${arm}_${codec}"
    say "$table"
    sed -e "s/__TABLE__/$table/g" -e "s/__CODEC__/$(codec_expr "$codec")/g" \
      schema.sql.tpl > "$DATA_DIR/$table.sql"
    docker exec -i "$CTR" clickhouse-client --allow_experimental_full_text_index=1 \
      --multiquery < "$DATA_DIR/$table.sql"
    docker exec "$CTR" bash -c \
      "clickhouse-client --allow_experimental_full_text_index=1 \
         --query 'INSERT INTO bench.$table FORMAT JSONEachRow' < /arms/$arm.jsonl"
    ch --query "OPTIMIZE TABLE bench.$table FINAL" --receive_timeout 1200
    ch --query "SELECT '  rows: ' || toString(sum(rows)) || ', on disk: ' ||
                formatReadableSize(sum(bytes_on_disk))
                FROM system.parts WHERE database='bench' AND table='$table' AND active"
  done
done

# ---------------------------------------------------- is the text still there
# The SQL decode path gets most rows wrong. That is only worth reporting once it
# is clear whether the compact form lost the text or the SQL misreads it, so
# this decodes the same events with the four rules install.sql does not
# implement and counts how many come back byte-identical.
say "reference decode: is the original text still in the compact form"
python3 reference_decode.py --arms "$ARMS_DIR" --templates "$INNER/templates.json" \
  --json "$RESULTS/reference-decode.json" --show 2 || true

# ------------------------------------------------------------------ the report
say "measure"
python3 report.py \
  --container "$CTR" \
  --manifest "$ARMS_DIR/manifest.json" \
  --results "$RESULTS" \
  --ch-version "$CH_VERSION" \
  --ch-image "$CH_IMAGE" \
  --engine-digest "$ENGINE_DIGEST" \
  --asset-sha256 "$PLAIN_SHA" \
  --term "$TERM" \
  --reference-decode "$RESULTS/reference-decode.json"

if [ "${KEEP:-0}" != "1" ]; then docker rm -f "$CTR" >/dev/null; fi
say "done. artifacts in $RESULTS"
