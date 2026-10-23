#!/bin/bash
# One hot-tier run: log10x-mcp's tenx-recur on policy.yaml, gitops delivery (a direct commit to the
# policy branch the Receiver pulls). Reads the rig cluster at LOG10X_ES_URL (default the rig's).
# git authenticates through gh's credential helper, passed as environment-only git config.
#   MCP=<log10x-mcp package> budget-run.sh [--dry-run]
# Writes RESULTS/budget-runs/<UTC stamp>/: run.json (stdout), report.txt (stderr), the files and the
# report as committed on the branch, and the commit's diff.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$HERE/../results}
MCP=${MCP:?log10x-mcp package}
CLONE=${CLONE:-$RESULTS/policy-clone}
BRANCH=$(awk '/policy_branch:/{print $2}' "$RESULTS/policy.yaml")
export LOG10X_ES_URL=${LOG10X_ES_URL:-http://127.0.0.1:9200}
export GIT_CONFIG_COUNT=3
export GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='!gh auth git-credential'
export GIT_CONFIG_KEY_1=user.name GIT_CONFIG_VALUE_1='log10x hot-tier run (rig)'
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
for f in caps.csv actions.csv totals.csv config-generation.csv; do
  git -C "$CLONE" show "refs/remotes/origin/$BRANCH:log10x/policy/$f" > "$out/$f" 2>/dev/null
done
git -C "$CLONE" show "refs/remotes/origin/$BRANCH:reports/latest.md" > "$out/latest.md" 2>/dev/null
[ "$before" != "$after" ] && git -C "$CLONE" diff "$before" "$after" > "$out/commit.diff"
echo "{\"event\":\"budget_run\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s),\"dir\":\"budget-runs/$stamp\",\"exit\":$rc,\"commit\":\"$after\",\"dry_run\":$([ "${1:-}" = --dry-run ] && echo true || echo false)}" >> "$RESULTS/timeline.jsonl"
exit $rc
