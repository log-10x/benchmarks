#!/usr/bin/env bash
# One rows run: tenx-recur from the log10x-mcp branch build against the rig's
# ClickHouse (127.0.0.1:8123) and Prometheus (127.0.0.1:9090), committing to the
# policy branch the Receiver pulls. Every run's files, report and commit land in
# results/budget-runs/<stamp>/. Copied from elastic-hot-tier-budget/rig/budget-run.sh.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
MCP=${MCP:?log10x-mcp checkout with build/}
CLONE=${CLONE:-$RESULTS/policy-clone}
BRANCH=$(awk '/policy_branch:/{print $2}' "$RESULTS/policy.yaml")
export CLICKHOUSE_URL=${CLICKHOUSE_URL:-http://127.0.0.1:8123}
export CLICKHOUSE_USER=${CLICKHOUSE_USER:-default}
export CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-}
export LOG10X_CUSTOMER_METRICS_URL=${LOG10X_CUSTOMER_METRICS_URL:-http://127.0.0.1:9090}
export GIT_CONFIG_COUNT=3
export GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='!gh auth git-credential'
export GIT_CONFIG_KEY_1=user.name GIT_CONFIG_VALUE_1='log10x rows run (rig)'
export GIT_CONFIG_KEY_2=user.email GIT_CONFIG_VALUE_2='install@log10x.com'
unset GH_TOKEN
[ -d "$CLONE/.git" ] || git clone --quiet --filter=blob:none "https://github.com/${POLICY_REPO:-log-10x/config}.git" "$CLONE"
export LOG10X_GITOPS_REPO_PATH=$CLONE
stamp=$(date -u +%Y%m%dT%H%M%SZ)
out=$RESULTS/budget-runs/$stamp
mkdir -p "$out"
before=$(git -C "$CLONE" ls-remote origin "refs/heads/$BRANCH" | cut -f1)
node "$MCP/build/bin/tenx-recur.js" --policy "$RESULTS/policy.yaml" --verbose "$@" > "$out/run.json" 2> "$out/report.txt"
rc=$?
echo "$rc" > "$out/exit"
git -C "$CLONE" fetch --quiet origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
after=$(git -C "$CLONE" rev-parse "refs/remotes/origin/$BRANCH")
echo "{\"before\":\"$before\",\"after\":\"$after\",\"exit\":$rc}" > "$out/commit.json"
for f in caps.csv actions.csv totals.csv config-generation.csv rows-per-hour; do
  git -C "$CLONE" show "refs/remotes/origin/$BRANCH:log10x/policy/$f" > "$out/$f" 2>/dev/null || true
done
git -C "$CLONE" show "refs/remotes/origin/$BRANCH:reports/latest.md" > "$out/latest.md" 2>/dev/null || true
[ "$before" != "$after" ] && git -C "$CLONE" diff "$before" "$after" > "$out/commit.diff"
echo "{\"event\":\"budget_run\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"dir\":\"budget-runs/$stamp\",\"exit\":$rc,\"commit\":\"$after\",\"dry_run\":$([ "${1:-}" = --dry-run ] && echo true || echo false)}" >> "$RESULTS/timeline.jsonl"
exit $rc
