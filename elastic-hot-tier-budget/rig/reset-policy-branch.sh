#!/bin/bash
# Put the policy branch back to the install seed (every line passes) before a run: the seed script
# writes only missing files, so a branch left by an earlier run keeps that run's last limits.
# git authenticates through gh's credential helper, passed as environment-only git config.
set -euo pipefail
BRANCH=${POLICY_BRANCH:?branch}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='!gh auth git-credential'
git clone --quiet --filter=blob:none --branch "$BRANCH" --single-branch "https://github.com/${POLICY_REPO:-log-10x/config}.git" "$TMP/c"
cd "$TMP/c"
mkdir -p log10x/policy
printf 'container,cap\ntenx-seed,1::install seed\n' > log10x/policy/caps.csv
printf 'container,action\ntenx-seed,pass::install seed\n' > log10x/policy/actions.csv
printf 'container,total\ntenx-seed,1::install seed\n' > log10x/policy/totals.csv
printf 'key,value\ngeneration,seed\n' > log10x/policy/config-generation.csv
printf 'bytes\n' > log10x/policy/regulator-unit
rm -f reports/latest.md
git add -A log10x/policy reports 2>/dev/null || git add -A log10x/policy
git -c user.name=log10x-install -c user.email=install@log10x.com commit -q -m "rig: reset the policy files to the install seed" > /dev/null || true
git push -q origin "$BRANCH"
git rev-parse HEAD
