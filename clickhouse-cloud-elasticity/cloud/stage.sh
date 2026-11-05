#!/usr/bin/env bash
# Load the split's records into bench.stage, once. The feed reads them from there.
#
#   cloud/stage.sh            # split/build/wire/returned.json -> data/rows.jsonl -> bench.stage
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
CLIENT="${CLIENT:-$HOME/git/l1x-co/.claude-tmp/chce-bin/clickhouse}"
CONF="${CONF:-$HOME/git/l1x-co/.claude-tmp/chce-secrets/client.yaml}"
WIRE="${WIRE:-$ROOT/split/build/wire/returned.json}"
ROWS="$ROOT/data/rows.jsonl"
ch() { "$CLIENT" client --config-file "$CONF" "$@"; }

mkdir -p "$ROOT/data"
python3 "$ROOT/split/build_arms.py" "$WIRE" "$ROWS" | tee "$ROOT/results/stage-build.json"
ch --query "TRUNCATE TABLE bench.stage"
ch --async_insert=0 --max_insert_block_size=50000 --query "INSERT INTO bench.stage FORMAT JSONEachRow" < "$ROWS"
ch --query "OPTIMIZE TABLE bench.stage FINAL"
ch --format JSONEachRow --query "SELECT count() rows, sum(kept) kept_rows, round(kept_rows / rows, 4) kept_share, max(i) + 1 n,
  sum(length(Body)) body_bytes, sumIf(length(Body), kept = 1) kept_body_bytes FROM bench.stage" | tee "$ROOT/results/stage.json"
