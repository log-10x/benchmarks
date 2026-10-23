#!/usr/bin/env bash
# Reset the rig's policy branch to the install seed, with the regulator recorded as
# counting events (the rows run refuses a Receiver recorded as counting bytes).
# Copied from elastic-hot-tier-budget/rig/reset-policy-branch.sh. Prints the commit.
set -euo pipefail
BRANCH=${POLICY_BRANCH:?branch}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='!gh auth git-credential'
REPO="https://github.com/${POLICY_REPO:-log-10x/config}.git"
if git ls-remote --exit-code --heads "$REPO" "$BRANCH" >/dev/null 2>&1; then
  git clone --quiet --filter=blob:none --branch "$BRANCH" --single-branch "$REPO" "$TMP/c"
else
  git clone --quiet --filter=blob:none --depth 1 "$REPO" "$TMP/c"
  git -C "$TMP/c" checkout --quiet --orphan "$BRANCH"
  git -C "$TMP/c" rm -rfq . >/dev/null 2>&1 || true
fi
cd "$TMP/c"
mkdir -p log10x/policy
printf 'container,cap\ntenx-seed,1::install seed\n' > log10x/policy/caps.csv
printf 'container,action\ntenx-seed,pass::install seed\n' > log10x/policy/actions.csv
printf 'container,total\ntenx-seed,1::install seed\n' > log10x/policy/totals.csv
printf 'key,value\ngeneration,seed\n' > log10x/policy/config-generation.csv
printf 'events\n' > log10x/policy/regulator-unit
rm -f log10x/policy/rows-per-hour reports/latest.md
git add -A log10x/policy reports 2>/dev/null || git add -A log10x/policy
git -c user.name=log10x-install -c user.email=install@log10x.com commit -q -m "rig: reset the policy files to the install seed (events)" || true
git push -q origin "$BRANCH"
git rev-parse HEAD
