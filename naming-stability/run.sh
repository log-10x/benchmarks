#!/usr/bin/env bash
#
# One command. Runs three consecutive engine releases over the two OpenTelemetry demo
# captures of ../intent, each with the configuration and symbol library its image ships,
# and compares the names they give the same events.
#
#   ./run.sh
#
# Needs Docker, curl and python3.
#
# Environment:
#   NS_CACHE   where inputs and engine output go (default: ./cache). Pointing it at
#              ../intent/cache reuses that benchmark's downloads.
#   NS_PRUNE   set to 1 to remove each image this script pulled once its runs are done,
#              so only one release image is on disk at a time.
#
# About 10 minutes per release on otel215 and 1 on rec1155 on an Intel macOS laptop.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

CACHE="${NS_CACHE:-$HERE/cache}"
RELEASES=(
  "1.1.140 log10x/pipeline-10x:1.1.140@sha256:fd9c98384a775df13ed41921c2cf95ef1d1313f62f1300aac61da55ca64feb67"
  "1.1.141 log10x/pipeline-10x:1.1.141@sha256:48d1ff07f83be12ccc4a1e8dfec2c59e865fecb67dec5111fa13f24e063d9456"
  "1.1.142 log10x/pipeline-10x:1.1.142@sha256:22ae67148bd7f6cbdf171c1b8da1c9c6c801290d43488693dfd8527e27138d05"
)

OTEL_URL="https://github.com/log-10x/config/releases/download/otel-sample-v1/otel-sample-200mb.log.gz"
OTEL_GZ_SHA="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
OTEL_SHA="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
REC_URL="https://github.com/log-10x/benchmarks/releases/download/intent-data-v1/rec1155.log.gz"
REC_GZ_SHA="d9ebe8c79e3ef6c1ca656599203d588831b6ed72e1f245cc32cd26124b6c4301"
REC_SHA="df78e200d929bc57f826a396fb8e1764717bf6b61544970261f3647163351b77"

say() { printf '\n=== %s\n' "$*"; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }

mkdir -p "$CACHE" results

fetch() {  # name url gz_sha sha
  local f="$CACHE/$1.log"
  if [ ! -f "$f" ] || [ "$(sha "$f")" != "$4" ]; then
    say "$1: downloading"
    curl -fsSL "$2" -o "$f.gz"
    [ "$(sha "$f.gz")" = "$3" ] || { echo "$1 download hash mismatch"; exit 1; }
    gunzip -c "$f.gz" > "$f"; rm -f "$f.gz"
  fi
  [ "$(sha "$f")" = "$4" ] || { echo "$1 hash mismatch"; exit 1; }
}
fetch otel215 "$OTEL_URL" "$OTEL_GZ_SHA" "$OTEL_SHA"
fetch rec1155 "$REC_URL" "$REC_GZ_SHA" "$REC_SHA"

# ------------------------- per release: what its image ships, then the engine runs
: > results/library.tsv
VERSIONS=()
for r in "${RELEASES[@]}"; do
  ver="${r%% *}"; image="${r#* }"; VERSIONS+=("$ver")
  pulled=0
  if ! docker image inspect "$image" > /dev/null 2>&1; then docker pull -q "$image" > /dev/null; pulled=1; fi
  tmp="$(mktemp -d)"
  cid="$(docker create "$image")"
  docker cp -q "$cid:/etc/tenx/symbols" "$tmp/symbols"
  docker cp -q "$cid:/etc/tenx/config" "$tmp/config"
  docker rm "$cid" > /dev/null
  python3 - "$ver" "$tmp" "$HERE/results" <<'PY'
import hashlib, os, sys, tarfile
ver, tmp, res = sys.argv[1:]
for name in sorted(os.listdir(os.path.join(tmp, "symbols"))):
    with tarfile.open(os.path.join(tmp, "symbols", name)) as tf:
        for m in sorted(tf.getmembers(), key=lambda m: m.name):
            h = hashlib.sha256(tf.extractfile(m).read()).hexdigest()
            kind = m.name.replace(f"-{ver}", "").replace("tenx-", "")
            with open(os.path.join(res, "library.tsv"), "a") as f:
                f.write(f"{ver}\t{kind}\t{h}\n")
root = os.path.join(tmp, "config")
with open(os.path.join(res, f"config-{ver}.sha256"), "w") as f:
    for d, _, files in sorted(os.walk(root)):
        for fn in sorted(files):
            p = os.path.join(d, fn)
            f.write(f"{hashlib.sha256(open(p, 'rb').read()).hexdigest()}  {os.path.relpath(p, root)}\n")
PY
  rm -rf "$tmp"
  for cap in rec1155 otel215; do
    out="$CACHE/engine-$ver/$cap"
    if [ -f "$out/events.jsonl.gz" ]; then continue; fi
    say "engine $ver on $cap"
    bench/engine.sh "$image" "$CACHE/$cap.log" "$out"
    gzip -f "$out/events.jsonl"
  done
  if [ "${NS_PRUNE:-0}" = 1 ] && [ "$pulled" = 1 ]; then docker rmi "$image" > /dev/null; fi
done
python3 - "${VERSIONS[@]}" > results/config-diff.txt <<'PY'
import sys
vs = sys.argv[1:]
def load(v):
    return dict(reversed(l.rstrip("\n").split("  ", 1)) for l in open(f"results/config-{v}.sha256"))
for a, b in zip(vs, vs[1:]):
    A, B = load(a), load(b)
    print(f"# {a} -> {b}: files of the shipped config that differ")
    for p in sorted(set(A) | set(B)):
        if A.get(p) != B.get(p):
            print(("changed " if p in A and p in B else "added   " if p in B else "removed ") + p)
    print()
PY

python3 bench/compare.py "$CACHE" "${VERSIONS[@]}" > /dev/null
say "done: results/results.md"
