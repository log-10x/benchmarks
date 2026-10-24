# needs GH_TOKEN exported: a PAT with Contents write on log-10x/config
set -euo pipefail
AUTH="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GH_TOKEN" | base64 | tr -d '\n')"
SEED=$(mktemp -d)
trap 'rm -rf "$SEED"' EXIT
git -c "http.https://github.com/.extraheader=$AUTH" clone --quiet "https://github.com/log-10x/config.git" "$SEED"
cd "$SEED"
if git -c "http.https://github.com/.extraheader=$AUTH" ls-remote --exit-code --heads origin test/elastic-hot-tier-policy >/dev/null; then git -c "http.https://github.com/.extraheader=$AUTH" fetch --quiet origin test/elastic-hot-tier-policy && git checkout --quiet -B test/elastic-hot-tier-policy FETCH_HEAD; else git checkout --quiet -b test/elastic-hot-tier-policy; fi
mkdir -p log10x/policy
[ -f log10x/policy/caps.csv ] || printf 'container,cap\ntenx-seed,1::install seed\n' > log10x/policy/caps.csv
[ -f log10x/policy/actions.csv ] || printf 'container,action\ntenx-seed,pass::install seed\n' > log10x/policy/actions.csv
[ -f log10x/policy/totals.csv ] || printf 'container,total\ntenx-seed,1::install seed\n' > log10x/policy/totals.csv
[ -f log10x/policy/config-generation.csv ] || printf 'key,value\ngeneration,seed\n' > log10x/policy/config-generation.csv
printf 'bytes\n' > log10x/policy/regulator-unit
git add log10x/policy
git -c user.name=log10x-install -c user.email=install@log10x.com commit --quiet -m "log10x: seed the policy files" || true
git -c "http.https://github.com/.extraheader=$AUTH" push --quiet origin test/elastic-hot-tier-policy
