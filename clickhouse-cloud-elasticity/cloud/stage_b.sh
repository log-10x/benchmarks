#!/usr/bin/env bash
# Build bench.stage_b from bench.stage's kept rows, renumbered from 0, so arm B reads only
# what it writes. Then check it against the kept rows of bench.stage, row for row.
#
#   cloud/stage_b.sh          # after cloud/stage.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
CLIENT="${CLIENT:-$HOME/git/l1x-co/.claude-tmp/chce-bin/clickhouse}"
CONF="${CONF:-$HOME/git/l1x-co/.claude-tmp/chce-secrets/client.yaml}"
ch() { "$CLIENT" client --config-file "$CONF" "$@"; }

ch --query "CREATE TABLE IF NOT EXISTS bench.stage_b AS bench.stage"
ch --query "TRUNCATE TABLE bench.stage_b"
ch --log_comment chce:build:stage_b --query "INSERT INTO bench.stage_b SELECT * REPLACE (toUInt32(row_number() OVER (ORDER BY i) - 1) AS i) FROM bench.stage WHERE kept = 1"
ch --log_comment chce:build:stage_b --query "OPTIMIZE TABLE bench.stage_b FINAL"
ch --format JSONEachRow --query "SELECT count() rows, sum(kept) kept_rows, min(i) i_min, max(i) + 1 n, sum(length(Body)) body_bytes FROM bench.stage_b" | tee "$ROOT/results/stage_b.json"
ch --format JSONEachRow --log_comment chce:build:stage_b --query "SELECT count() compared, countIf(a.hb != cityHash64(b.Body, b.ServiceName, toString(b.ResourceAttributes))) mismatched FROM (SELECT toUInt32(row_number() OVER (ORDER BY i) - 1) r, cityHash64(Body, ServiceName, toString(ResourceAttributes)) hb FROM bench.stage WHERE kept = 1) a INNER JOIN bench.stage_b b ON a.r = b.i" | tee "$ROOT/results/stage_b-check.json"
