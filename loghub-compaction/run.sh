#!/usr/bin/env bash
#
# The LogHub compaction measurement: 14 full LogHub datasets through the released engine
# 1.1.133 with its default library, each corpus cold, reduction = 1 - (encoded.log +
# templates.json) / input, no codec.
#
#   ./run.sh                   every corpus in corpora.tsv
#   ./run.sh Apache Linux      some corpora
#   ./run.sh report            render results.json, results.md and the README table
#
# Environment:
#   LC_DATA_DIR   tarball cache and scratch (default: <dir>/data); about 4.5 GB free at peak (Spark)
#   LC_IMAGE      engine image (default: log10x/pipeline-10x:1.1.133, by digest)
#   LC_KEEP=1     keep each corpus's extracted input and outputs (default: deleted once hashed)

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${LC_DATA_DIR:-$HERE/data}"
IMAGE="${LC_IMAGE:-log10x/pipeline-10x:1.1.133@sha256:fe3dcdefdc2f42fa7117c4f63fe97b28508fbf1356725422703f0dfab55f2360}"
ZENODO="https://zenodo.org/records/3227177/files"
mkdir -p "$DATA/tar" "$HERE/results"

say() { printf '\n=== %s\n' "$*"; }
die() { echo "error: $*" >&2; exit 1; }

md5of() { if command -v md5sum >/dev/null; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }

corpus() {
  local name="$1" file md5 members
  IFS=$'\t' read -r _ file md5 members < <(awk -F'\t' -v n="$name" '$1 == n' "$HERE/corpora.tsv")
  [ -n "${file:-}" ] || die "$name is not in corpora.tsv"
  say "$name"
  local tar="$DATA/tar/$file"
  [ -s "$tar" ] || curl -fL --retry 3 -o "$tar" "$ZENODO/$file?download=1"
  [ "$(md5of "$tar")" = "$md5" ] || die "$file md5 differs from Zenodo's ($md5)"
  local src="$DATA/src/$name" out="$DATA/out/$name"
  rm -rf "$src" "$out"; mkdir -p "$src" "$out"
  tar xzf "$tar" -C "$src"
  # The engine walks the input directory and reads every file whose name matches, in one run.
  docker run --rm -e TZ=UTC -e INPUT_FILE="/in/$members" -e OUTPUT_DIR=/out \
    -v "$src":/in:ro -v "$out":/out -v "$HERE/tenx-encode.config.yaml":/cfg/encode.yaml:ro \
    "$IMAGE" @/cfg/encode.yaml > "$out/engine.log" 2>&1 || { tail -20 "$out/engine.log"; die "$name: engine run failed"; }
  python3 "$HERE/measure.py" --corpus "$name" --input-dir "$src" --members "$members" --out-dir "$out" \
    --result "$HERE/results/$name.json" --source "$ZENODO/$file" --image "$IMAGE"
  if [ "${LC_KEEP:-0}" != 1 ]; then rm -rf "$src" "$out"; fi
}

if [ "${1:-}" = report ]; then
  python3 "$HERE/report.py"
  python3 "$HERE/report.py" --check
  exit 0
fi
if [ "$#" -gt 0 ]; then NAMES=("$@"); else NAMES=($(awk -F'\t' 'NR > 1 { print $1 }' "$HERE/corpora.tsv")); fi
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull -q "$IMAGE" >/dev/null
for n in "${NAMES[@]}"; do corpus "$n"; done
missing=$(awk -F'\t' 'NR > 1 { print $1 }' "$HERE/corpora.tsv" | while read -r c; do [ -s "$HERE/results/$c.json" ] || echo "$c"; done)
if [ -n "$missing" ]; then echo "no report yet; still to measure: $(echo $missing)"; exit 0; fi
python3 "$HERE/report.py"
python3 "$HERE/report.py" --check
