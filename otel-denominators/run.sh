#!/usr/bin/env bash
#
# One command. Fetches the public capture, derives the two other denominators,
# runs the engine over all three, decodes each one back and compares it to its
# own input byte for byte, then writes results/results.csv and
# results/results.md.
#
#   ./run.sh                    all three cases
#   ./run.sh a_asis c_msg       a subset, same order
#
# Needs Docker and about 1.2 GB of free disk for the derived inputs and the
# engine outputs. Timings on an Intel macOS laptop, engine 1.1.5: the capture
# downloads once at 8.4 MB gzipped, the derived inputs take about 15s to build,
# and each case is roughly 30s to encode and 15s to decode.
#
# Environment:
#   OTD_DATA_DIR   download and derived-input cache (default: <dir>/data)
#   OTD_IMAGE      engine image (default: log10x/pipeline-10x:1.1.5)
#   OTD_KEEP       set to 1 to keep each case's encoded/decoded output

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

DATA_DIR="${OTD_DATA_DIR:-$HERE/data}"
IMAGE="${OTD_IMAGE:-log10x/pipeline-10x:1.1.5}"
# The two round-trip configs published with the compaction benchmark. They are
# cited elsewhere as the reference configs, so this benchmark reads them from
# where they already live rather than keeping a second copy.
CFG="$HERE/../drain3-vs-log10x"
RESULTS="$HERE/results"

ASSET="otel-sample-200mb.log"
RELEASE="https://github.com/log-10x/config/releases/download/otel-sample-v1"
# sha256 of the release asset as published (gzipped) and expanded. Both are
# checked on every run, so a re-cut of the release fails here rather than
# silently moving a figure in the table.
ASSET_GZ_SHA256="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"

say() { printf '\n=== %s\n' "$*"; }

mkdir -p "$DATA_DIR" "$RESULTS"

# ------------------------------------------------------------------ the image
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required: the engine runs as $IMAGE" >&2
  exit 1
fi
say "engine image"
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull "$IMAGE"
IMAGE_DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "$IMAGE (no digest recorded)")"
echo "$IMAGE_DIGEST"

# ------------------------------------------------------------------- the data
say "public capture"
GZ="$DATA_DIR/$ASSET.gz"
if [ ! -s "$GZ" ]; then
  echo "downloading $RELEASE/$ASSET.gz"
  curl -fsSL -o "$GZ.part" "$RELEASE/$ASSET.gz"
  mv "$GZ.part" "$GZ"
fi
PLAIN="$DATA_DIR/$ASSET"
if [ ! -s "$PLAIN" ]; then
  echo "expanding $ASSET.gz"
  gunzip -c "$GZ" > "$PLAIN.part"
  mv "$PLAIN.part" "$PLAIN"
fi
GZ_SHA="$(shasum -a 256 "$GZ" | cut -d' ' -f1)"
PLAIN_SHA="$(shasum -a 256 "$PLAIN" | cut -d' ' -f1)"
echo "gz     $(wc -c < "$GZ" | tr -d ' ') bytes  sha256 $GZ_SHA"
echo "plain  $(wc -c < "$PLAIN" | tr -d ' ') bytes  sha256 $PLAIN_SHA"
if [ "$GZ_SHA" != "$ASSET_GZ_SHA256" ] || [ "$PLAIN_SHA" != "$ASSET_SHA256" ]; then
  echo "the release asset does not match the sha256 this results table was measured on." >&2
  echo "expected gz    $ASSET_GZ_SHA256" >&2
  echo "expected plain $ASSET_SHA256" >&2
  echo "rerun and recommit results/ rather than reporting the committed numbers." >&2
  exit 1
fi

say "derived inputs (b) SIEM-billed and (c) message only"
python3 build_inputs.py --src "$PLAIN" --out-dir "$DATA_DIR"

# ------------------------------------------------------------------ the cases
declare -a ORDER
if [ "$#" -gt 0 ]; then ORDER=("$@"); else ORDER=(a_asis b_siem c_msg); fi

CSV_HEADER="case,input_bytes,input_lines,encoded_bytes,templates_bytes,compact_bytes,reduction_pct,templates,decoded_bytes,decoded_lines,roundtrip"

input_for() {
  case "$1" in
    a_asis) echo "$PLAIN" ;;
    b_siem) echo "$DATA_DIR/b_siem.log" ;;
    c_msg)  echo "$DATA_DIR/c_msg.log" ;;
    *) echo "unknown case $1, expected a_asis, b_siem or c_msg" >&2; exit 2 ;;
  esac
}

CSV="$RESULTS/results.csv"
# This run's rows land in a scratch file and are merged into results.csv at the
# end, so `./run.sh c_msg` updates one row instead of truncating the table to
# the single case it ran.
RUN_CSV="$(mktemp)"
trap 'rm -f "$RUN_CSV"' EXIT
echo "$CSV_HEADER" > "$RUN_CSV"

run_case() {
  local label="$1"
  local in out
  in="$(input_for "$label")"
  out="$DATA_DIR/out_$label"
  rm -rf "$out"; mkdir -p "$out"

  local ib il
  ib="$(wc -c < "$in" | tr -d ' ')"
  il="$(wc -l < "$in" | tr -d ' ')"
  say "$label: encode, $ib bytes, $il lines"
  docker run --rm \
    -e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out \
    -v "$out":/out -v "$in":/in/events.log:ro \
    -v "$CFG/tenx-encode.config.yaml":/cfg/tenx-encode.config.yaml:ro \
    "$IMAGE" @/cfg/tenx-encode.config.yaml > "$out/encode.stdout" 2>&1

  local enc tpl compact ntpl pct
  enc="$(wc -c < "$out/encoded.log" | tr -d ' ')"
  tpl="$(wc -c < "$out/templates.json" | tr -d ' ')"
  compact=$((enc + tpl))
  ntpl="$(wc -l < "$out/templates.json" | tr -d ' ')"
  pct="$(python3 -c "print(f'{(1-$compact/$ib)*100:.2f}')")"
  echo "encoded=$enc templates=$tpl compact=$compact templates_n=$ntpl reduction=${pct}%"

  # The compact form the reduction is computed on: the template dictionary
  # followed by the encoded records, which is what the decode step reads.
  cat "$out/templates.json" "$out/encoded.log" > "$out/compact.log"

  say "$label: decode and compare to its own input"
  docker run --rm \
    -e INPUT_FILE=/out/compact.log -e OUTPUT_DIR=/out \
    -v "$out":/out \
    -v "$CFG/tenx-decode.config.yaml":/cfg/tenx-decode.config.yaml:ro \
    "$IMAGE" @/cfg/tenx-decode.config.yaml > "$out/decode.stdout" 2>&1

  local db dl trip
  db="$(wc -c < "$out/decoded.log" | tr -d ' ')"
  dl="$(wc -l < "$out/decoded.log" | tr -d ' ')"
  if cmp -s "$in" "$out/decoded.log"; then trip="BYTE-IDENTICAL"; else trip="DIFFERS"; fi
  echo "decoded=$db bytes $dl lines -> $trip"

  echo "$label,$ib,$il,$enc,$tpl,$compact,$pct,$ntpl,$db,$dl,$trip" >> "$RUN_CSV"

  if [ "${OTD_KEEP:-0}" != "1" ]; then
    # The encoded stream and the decode are each about the size of the input.
    # Keep the stdout logs, drop the bulk.
    rm -f "$out/encoded.log" "$out/compact.log" "$out/decoded.log"
  fi
}

for label in "${ORDER[@]}"; do run_case "$label"; done

# ------------------------------------------------------------------ the table
say "merging this run into $CSV"
python3 merge_results.py --into "$CSV" --from "$RUN_CSV"

# ----------------------------------------------------------------- the report
say "report"
python3 report.py \
  --csv "$CSV" \
  --out "$RESULTS/results.md" \
  --image "$IMAGE_DIGEST" \
  --asset-sha256 "$PLAIN_SHA" \
  --asset-gz-sha256 "$GZ_SHA"
cat "$RESULTS/results.md"

say "done. artifacts in $RESULTS"
