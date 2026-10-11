# Shared shell for the accounting benchmarks. Sourced by each folder's run.sh.
#
# Expects: IMAGE (engine image, pinned by digest), LIB (this directory), MCP_VERSION,
# MCP_DIR (where log10x-mcp is installed), MCP_HOME (an empty HOME for the server), and
# optionally MCP_TARBALL, a local `npm pack` of log10x-mcp to install instead of the
# published version.

say() { printf '\n=== %s\n' "$*"; }
die() { echo "$*" >&2; exit 1; }

# The public capture, the same asset the other benchmarks run on.
RELEASE="https://github.com/log-10x/config/releases/download/otel-sample-v1"
ASSET="otel-sample-200mb.log"
ASSET_GZ_SHA256="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
ASSET_BYTES=215039161
ASSET_LINES=197430

sha256() { shasum -a 256 "$1" | awk '{print $1}'; }

fetch_capture() {
  local dir="$1"
  mkdir -p "$dir"
  if [ -f "$dir/$ASSET" ] && [ "$(sha256 "$dir/$ASSET")" = "$ASSET_SHA256" ]; then
    echo "$dir/$ASSET present, sha256 matches"
    return
  fi
  echo "downloading $RELEASE/$ASSET.gz"
  curl -fsSL "$RELEASE/$ASSET.gz" -o "$dir/$ASSET.gz"
  [ "$(sha256 "$dir/$ASSET.gz")" = "$ASSET_GZ_SHA256" ] || die "gzipped asset sha256 does not match"
  gunzip -kf "$dir/$ASSET.gz"
  [ "$(sha256 "$dir/$ASSET")" = "$ASSET_SHA256" ] || die "expanded asset sha256 does not match"
  [ "$(wc -c < "$dir/$ASSET" | tr -d ' ')" = "$ASSET_BYTES" ] || die "asset byte count differs"
  [ "$(wc -l < "$dir/$ASSET" | tr -d ' ')" = "$ASSET_LINES" ] || die "asset line count differs"
}

pull_engine() {
  docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull "$IMAGE"
  IMAGE_DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
  echo "$IMAGE_DIGEST"
}

install_mcp() {
  mkdir -p "$MCP_DIR" "$MCP_HOME"
  [ -f "$MCP_DIR/package.json" ] || printf '{ "name": "accounting-plan", "private": true }\n' > "$MCP_DIR/package.json"
  local spec="log10x-mcp@$MCP_VERSION"
  [ -n "${MCP_TARBALL:-}" ] && spec="$(cd "$(dirname "$MCP_TARBALL")" && pwd)/$(basename "$MCP_TARBALL")"
  if [ ! -f "$MCP_DIR/node_modules/log10x-mcp/package.json" ] ||
     [ "$(node -p "require('$MCP_DIR/node_modules/log10x-mcp/package.json').version")" != "$MCP_VERSION" ]; then
    (cd "$MCP_DIR" && npm install --silent --no-audit --no-fund "$spec")
  fi
  cp "$LIB/plan.mjs" "$MCP_DIR/plan.mjs"
  echo "log10x-mcp $(node -p "require('$MCP_DIR/node_modules/log10x-mcp/package.json').version")"
}

# plan <siem> <target> <out.json> [key=value ...]
# The server boots in POC mode under an empty HOME, so no account on this machine changes
# what it does, and runs the pinned engine image for its own pattern extraction.
plan() {
  local siem="$1" target="$2" out="$3"; shift 3
  (cd "$MCP_DIR" && HOME="$MCP_HOME" LOG10X_MCP_FORCE_MODE=poc LOG10X_TENX_MODE=docker \
     LOG10X_RUNTIME_IMAGE="$IMAGE" CAPTURE="$CAPTURE" SPAN="$WINDOW" \
     node plan.mjs "$siem" "$target" "$out" "$@")
}

# replay <capture> <out_dir> [<caps.csv> <actions.csv>]
# The regulator's warm-up is the only setting passed on the command line: a replay has no
# warm-up period to wait out. Everything else is the image's shipped configuration.
replay() {
  local capture="$1" out="$2" caps="${3:-}" actions="${4:-}"
  rm -rf "$out"; mkdir -p "$out"
  local envs=(-e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out)
  local vols=(-v "$capture":/in/events.log:ro -v "$out":/out -v "$LIB/replay.config.yaml":/cfg/replay.yaml:ro)
  if [ -n "$caps" ]; then
    mkdir -p "$out/policy"
    cp "$caps" "$out/policy/caps.csv"
    cp "$actions" "$out/policy/actions.csv"
    envs+=(-e CAP_LOOKUP_FILE=/policy/caps.csv -e ACTION_LOOKUP_FILE=/policy/actions.csv)
    vols+=(-v "$out/policy":/policy:ro)
  fi
  local t0=$SECONDS
  docker run --rm "${envs[@]}" "${vols[@]}" "$IMAGE" @/cfg/replay.yaml rateReceiverWarmupMs 0 \
    > "$out/engine.log" 2>&1 || { tail -20 "$out/engine.log"; die "engine run failed"; }
  local secs=$((SECONDS - t0))
  echo "$secs" > "$out/seconds.txt"
  [ -s "$out/routed.jsonl" ] || die "the replay wrote no events"
  # The regulator counts bytes per pattern per 240 s window. The whole capture has to land
  # inside one window for the cap arithmetic in policy.py to hold.
  [ "$secs" -lt 240 ] || die "replay took $secs s, longer than one 240 s regulator window"
  echo "replayed $(wc -l < "$out/routed.jsonl" | tr -d ' ') events in $secs s"
}
