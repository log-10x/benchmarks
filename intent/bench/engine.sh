#!/usr/bin/env bash
#
# Run one engine image over one capture and write the events the scorer reads.
#
#   bench/engine.sh <image> <input file> <output dir>
#
# The dev app names every event and reads, besides the given file, the sample
# file the image ships in /etc/tenx/config/data/sample/input. An empty
# directory is mounted over that folder so the run sees the capture alone.
# Output: <output dir>/events.jsonl (message_pattern, tenx_origin, text per
# event) and <output dir>/engine.log.

set -euo pipefail

IMAGE="$1"; INPUT="$2"; OUT="$3"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
INPUT="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"
EMPTY="$(mktemp -d)"
trap 'rmdir "$EMPTY"' EXIT
rm -f "$OUT/events.jsonl"

docker run --rm \
  -e OUTPUT_DIR=/out \
  -v "$OUT":/out \
  -v "$INPUT":/in/input.log:ro \
  -v "$EMPTY":/etc/tenx/config/data/sample/input:ro \
  -v "$HERE/events.config.yaml":/cfg/events.config.yaml:ro \
  "$IMAGE" @apps/dev @/cfg/events.config.yaml \
  inputFilePath /in/input.log symbolOriginField tenx_origin \
  > "$OUT/engine.log" 2>&1
