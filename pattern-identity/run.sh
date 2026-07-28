#!/usr/bin/env bash
#
# One command. Builds an isolated environment, downloads the public sample if it
# is not already cached, runs every experiment in this directory, and writes
# every artifact under results/.
#
#   ./run.sh              full run
#   PIB_QUICK=1 ./run.sh  reduced identity run (60,000 lines, 3 trials)
#
# Timings measured on an Intel macOS laptop, drain3 0.9.11, Python 3.13:
#   replay        under 1s, no download needed, runs FIRST
#   engine_side   about 5s
#   identifier    about 25s
#   multiline     about 65s
#   coverage      about 2 minutes with the Docker image present, skipped without
#   identity      about 19 minutes at full scale, about 3 with PIB_QUICK=1
# The identity experiment is the long pole: three arms, ten trials each, two
# instances trained per trial. Time it on the machine that publishes rather than
# trusting these figures.
#
# Environment:
#   PIB_PYTHON   interpreter to build the virtualenv from (default: python3)
#   PIB_VENV     virtualenv location (default: <repo>/.venv)
#   PIB_DATA_DIR download cache (default: <repo>/data)
#   PIB_QUICK    set to 1 for the reduced identity configuration
#
# The three otel-sample assets come from
# https://github.com/log-10x/config/releases/tag/otel-sample-v1
# and are cached in their gzipped form. Every script reads the gzipped file in
# place, so the working tree stays small. bench/coverage.py additionally caches
# two LogHub log sets from Zenodo record 3227177 under data/.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"

BOOTSTRAP_PYTHON="${PIB_PYTHON:-python3}"
VENV="${PIB_VENV:-$REPO/.venv}"
PY="$VENV/bin/python"

say() { printf '\n=== %s\n' "$*"; }

# ---------------------------------------------------------------- environment
if [ ! -x "$PY" ]; then
  say "creating virtualenv at $VENV"
  "$BOOTSTRAP_PYTHON" -m venv "$VENV"
  "$PY" -m pip install --quiet --upgrade pip
fi

say "installing pinned dependencies"
"$PY" -m pip install --quiet -r requirements.txt

"$PY" - <<'EOF'
import importlib.metadata as im, platform, sys
print(f"python  {platform.python_version()} ({sys.executable})")
print(f"drain3  {im.version('drain3')}")
EOF

mkdir -p results

# --------------------------------------------------------------- experiments
# The replay runs first and leads results/: it needs no download, finishes in
# under a second, and it is the exhibit everything else on the page depends on.
# After it, cheapest first, so a broken environment surfaces in seconds.
# Wall-clock timings are written to stderr and never into an artifact, so
# `git diff --exit-code results/` is a usable gate after a rerun.

say "replay: a name moves inside one process (< 1s, no download)"
"$PY" bench/replay.py > results/replay.txt
cat results/replay.txt

# ---------------------------------------------------------------------- data
say "fetching the public sample (cached after the first run)"
"$PY" bench/data.py
"$PY" bench/data.py --stats > results/data_provenance.txt
cat results/data_provenance.txt

say "engine_side: naming granularity and literal anchoring (~5s)"
"$PY" bench/engine_side.py

say "identifier: template string against integer cluster id (~25s)"
"$PY" bench/identifier.py > results/identifier.txt
cat results/identifier.txt

say "multiline: one logical event, several names (~65s)"
"$PY" bench/multiline.py --full-line > results/multiline.txt
cat results/multiline.txt

say "coverage: invented vocabulary and LogHub through the engine (~2min; skips without Docker)"
"$PY" bench/coverage.py

if [ "${PIB_QUICK:-0}" = "1" ]; then
  say "identity: two instances, split halves, 60,000 lines, 3 trials (~3min)"
  "$PY" bench/identity.py --lines 60000 --trials 3
else
  say "identity: two instances, split halves, full file, 10 trials (~19min)"
  "$PY" bench/identity.py
fi

say "done. artifacts written to $REPO/results"
ls -la results
