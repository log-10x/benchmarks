#!/usr/bin/env bash
#
# E21: what 10x in front of Splunk does to licence-metered volume.
#
# Two arms, the same capture, the same forwarder path, the same index settings.
# Arm one ships the raw file. Arm two ships the same file after the 10x Receiver
# has compacted it. Splunk's own licence meter is the measurement; the file sizes
# are reported beside it only so the two can be compared.
#
#   ./run.sh                  everything, then tear the containers down
#   KEEP=1 ./run.sh           leave the containers up afterwards
#   ./run.sh encode licence   run some stages only, in the order given
#
# Stages: data encode groundtruth splunk ingest kv expand licence report
#
# Needs Docker with about 10 GB of free disk (the Splunk image alone is 6.5 GB)
# and roughly two hours, most of which is waiting for a licence day to roll over.
# Nothing here touches a production Splunk: it stands up a throwaway container
# on the Splunk Enterprise download trial and destroys it.
#
# Environment:
#   E21_DATA_DIR    capture and engine output cache (default: <dir>/data)
#   E21_ENGINE      engine image (default: ghcr.io/log-10x/edge-10x:1.1.79)
#   E21_SPLUNK      Splunk image (default: splunk/splunk:latest)
#   E21_UF          forwarder image (default: splunk/universalforwarder:latest)
#   E21_MIN_LEAD    minutes the licence rollover must sit ahead of container
#                   start (default: 75). See "the licence day" below.
#   KEEP            1 to leave the containers up

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

DATA_DIR="${E21_DATA_DIR:-$HERE/data}"
ENGINE="${E21_ENGINE:-ghcr.io/log-10x/edge-10x:1.1.79}"
SPLUNK_IMAGE="${E21_SPLUNK:-splunk/splunk:latest}"
UF_IMAGE="${E21_UF:-splunk/universalforwarder:latest}"
MIN_LEAD="${E21_MIN_LEAD:-75}"
RESULTS="$HERE/results"
APP_REPO="${E21_APP_REPO:-https://github.com/log-10x/splunk-app.git}"

IDX=e21-idx
UF=e21-uf
NET=e21net
PASS='Chang3d!Bench21'

# The public capture. Both arms are built from this one file, so the two sides
# are the same source logs by construction rather than by assertion.
RELEASE="https://github.com/log-10x/config/releases/download/otel-sample-v2"
ASSET="otel-sample-200mb.log"
ASSET_GZ_SHA256="c118e55f1e431d9ff43fe1b3b62237d2fbd7c6e27821a8a9c4c57757786b0eb9"
ASSET_SHA256="aa79b9349a4123d88936fd064f5eccd9fd84f45a1fd03cff3f64c259715c2432"
ASSET_BYTES=215039161
ASSET_LINES=197430

say() { printf '\n=== %s\n' "$*"; }
die() { echo "$*" >&2; exit 1; }

# Splunk's CLI has to run as the splunk user; as root it cannot read its own
# pid file and fails with a wall of permission errors that look like a bug.
# docker exec can hang for minutes when the daemon is saturated, which it is
# while a 6.5 GB image is being extracted on the same host. Every call into a
# container gets a ceiling, so a stall fails a stage loudly instead of freezing
# it. Ten minutes is long enough for a slow splunk restart on a loaded box.
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"
dx()  { ${TIMEOUT_BIN:+$TIMEOUT_BIN 600} docker exec "$@"; }
sp()  { dx -u splunk "$IDX" /opt/splunk/bin/splunk "$@"; }
# -preview false matters: without it the export carries the scheduler's partial
# result batches too, and a row count comes back larger than the event count.
spq() { sp search "$1" -app tenx-for-splunk -auth "$PASS_ARG" -maxout 0 -preview false "${@:2}" 2>/dev/null; }

PASS_ARG="admin:$PASS"

mkdir -p "$DATA_DIR" "$RESULTS"
command -v docker >/dev/null 2>&1 || die "docker is required"

# --------------------------------------------------------------------- stages

stage_data() {
  say "public capture"
  local gz="$DATA_DIR/$ASSET.gz" plain="$DATA_DIR/base/$ASSET"
  mkdir -p "$DATA_DIR/base"
  [ -s "$gz" ] || curl -fsSL -o "$gz" "$RELEASE/$ASSET.gz"
  [ -s "$plain" ] || gunzip -c "$gz" > "$plain"
  local gz_sha plain_sha bytes lines
  gz_sha="$(shasum -a 256 "$gz" | cut -d' ' -f1)"
  plain_sha="$(shasum -a 256 "$plain" | cut -d' ' -f1)"
  bytes="$(wc -c < "$plain" | tr -d ' ')"
  lines="$(wc -l < "$plain" | tr -d ' ')"
  echo "$ASSET  $bytes bytes  $lines lines  sha256 $plain_sha"
  [ "$gz_sha" = "$ASSET_GZ_SHA256" ] && [ "$plain_sha" = "$ASSET_SHA256" ] \
    || die "the release asset does not match the sha256 this results table was measured on"
  [ "$bytes" = "$ASSET_BYTES" ] && [ "$lines" = "$ASSET_LINES" ] \
    || die "capture is $bytes bytes / $lines lines, expected $ASSET_BYTES / $ASSET_LINES"
}

# The engine's own config, with one line changed. varMaxRecurIndexes cannot be
# set from a config file here: the shipped engine config already sets it, and a
# second setting is rejected with "option 'varMaxRecurIndexes' (number) should be
# specified only once". So the file is taken out of the image, edited, mounted
# back, and the diff is asserted to be that one line and nothing else.
patch_engine_config() {
  local src="$1" out="$2"; shift 2
  docker run --rm --entrypoint sh "$ENGINE" -c "cat $src" > "$out.orig" 2>/dev/null
  [ -s "$out.orig" ] || die "could not read $src out of $ENGINE"
  cp "$out.orig" "$out"
  local pairs=0
  while [ "$#" -ge 2 ]; do
    sed "s|^$1\$|$2|" "$out" > "$out.tmp" && mv "$out.tmp" "$out"
    pairs=$((pairs + 1)); shift 2
  done
  local changed
  changed="$(diff "$out.orig" "$out" | grep -c '^[<>]' || true)"
  [ "$changed" = "$((2 * pairs))" ] \
    || die "patching $src changed $((changed / 2)) lines, expected exactly $pairs"
  rm -f "$out.orig"
}

stage_encode() {
  say "engine image"
  docker image inspect "$ENGINE" >/dev/null 2>&1 || docker pull "$ENGINE"
  ENGINE_DIGEST="$(docker image inspect "$ENGINE" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "$ENGINE")"
  echo "$ENGINE_DIGEST"

  say "engine config patches"
  # varMaxRecurIndexes: 0. The Splunk app does not decode back-referenced
  # templates and reconstructs the wrong text on one, silently, so the Receiver
  # feeding it must not produce any.
  patch_engine_config /etc/tenx/config/pipelines/run/template/config.yaml \
    "$HERE/conf/engine-template-norecur.yaml" "  maxRecurIndexes: 10" "  maxRecurIndexes: 0"
  # The engine logs every line it has no symbol pattern for, at INFO, to stdout.
  # On this capture that is most of the run's wall clock and 20x its log volume.
  # Root logger to warn; it changes no output byte.
  patch_engine_config /etc/tenx/config/log4j2.yaml \
    "$HERE/conf/engine-log4j2-quiet.yaml" "      level: info" "      level: warn"
  # timestampZone: UTC. A timestamp with no zone marker of its own is only a time
  # once something decides which zone it was written in, and the engine's default
  # is the clock of the host it runs on. That choice is not recorded in the
  # compact event, so nothing downstream can recover it. Pinning it here is what
  # makes the arm reproducible on a host that is not on UTC, and it is the
  # setting the Splunk app requires for the same reason.
  patch_engine_config /etc/tenx/config/pipelines/run/transform/timestamp/config.yaml \
    "$HERE/conf/engine-timestamp-control.yaml" "  zone: null" "  zone: UTC"
  # maxPerObject: 1. The engine's default records every timestamp it finds in an
  # event as its own slot; the Splunk app stores one timestamp format per
  # template and reconstructs one. On the E21 capture 23 templates carried two
  # or more, and they were every one of the 5,892 events still wrong after the
  # app's own timestamp fixes. With one slot per event the first timestamp keeps
  # its slot and any later one becomes an ordinary variable whose literal text
  # round-trips as it is. The zone is pinned here as well.
  patch_engine_config /etc/tenx/config/pipelines/run/transform/timestamp/config.yaml \
    "$HERE/conf/engine-timestamp-splunk.yaml" \
    "  zone: null" "  zone: UTC" "  maxPerObject: 0" "  maxPerObject: 1"
  docker run --rm --entrypoint sh "$ENGINE" -c "cat /etc/tenx/config/pipelines/run/template/config.yaml" \
    > "$HERE/conf/engine-template-shipped.yaml" 2>/dev/null

  probe_parse_zone
  encode_arm norecur "$HERE/conf/engine-template-norecur.yaml" \
    "$HERE/conf/engine-timestamp-splunk.yaml" "$DATA_DIR/compact"

  say "falsifier: one timestamp slot per template"
  python3 template_stats.py --templates "$DATA_DIR/compact/templates.json" --max-slots 1

  # The control arm is the engine's own defaults for both settings the Splunk
  # app requires, so the gap between the arms is what those requirements cost,
  # measured rather than claimed. The zone is pinned on it too; that moves no
  # byte. It is not ingested.
  encode_arm shipped "$HERE/conf/engine-template-shipped.yaml" \
    "$HERE/conf/engine-timestamp-control.yaml" "$DATA_DIR/compact_default"

  say "round trip: decode the compact form and compare to the capture"
  cat "$DATA_DIR/compact/templates.json" "$DATA_DIR/compact/encoded.log" > "$DATA_DIR/compact/compact.log"
  docker run --rm -e INPUT_FILE=/out/compact.log -e OUTPUT_DIR=/out \
    -v "$DATA_DIR/compact":/out \
    -v "$HERE/tenx-decode.config.yaml":/cfg/dec.yaml:ro \
    -v "$HERE/conf/engine-log4j2-quiet.yaml":/etc/tenx/config/log4j2.yaml:ro \
    "$ENGINE" @/cfg/dec.yaml > "$DATA_DIR/compact/decode.stdout" 2>&1
  if cmp -s "$DATA_DIR/base/$ASSET" "$DATA_DIR/compact/decoded.log"; then
    ROUNDTRIP=BYTE-IDENTICAL
  else
    ROUNDTRIP=DIFFERS
  fi
  echo "round trip: $ROUNDTRIP"
  echo "$ROUNDTRIP" > "$DATA_DIR/roundtrip.txt"
  # The decode and the concatenation are each the size of the capture again.
  rm -f "$DATA_DIR/compact/decoded.log" "$DATA_DIR/compact/compact.log" \
        "$DATA_DIR/compact_default/encoded.log"
  [ "$ROUNDTRIP" = "BYTE-IDENTICAL" ] || die "the compact form does not decode back to the capture"
}

# Falsifier for the zone pinning, named before the run: encode one timestamp that
# carries no zone and one that ends in Z, on a container whose clock is not UTC,
# and require that both come out as the UTC epoch. If a future engine stops
# honouring timestampZone, this fails here rather than moving a figure quietly.
probe_parse_zone() {
  say "falsifier: timestampZone pins the parse zone"
  local dir="$DATA_DIR/zone_probe"
  rm -rf "$dir"; mkdir -p "$dir/out"
  printf '2025-10-02 06:35:34,498 INFO zoneless\n2025-10-02T06:35:34.498Z INFO zoned\n' > "$dir/in.log"
  docker run --rm -e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out -e TZ=America/New_York \
    -v "$dir/out":/out -v "$dir/in.log":/in/events.log:ro \
    -v "$HERE/tenx-encode-splunk.config.yaml":/cfg/enc.yaml:ro \
    -v "$HERE/conf/engine-template-norecur.yaml":/etc/tenx/config/pipelines/run/template/config.yaml:ro \
    -v "$HERE/conf/engine-timestamp-splunk.yaml":/etc/tenx/config/pipelines/run/transform/timestamp/config.yaml:ro \
    -v "$HERE/conf/engine-log4j2-quiet.yaml":/etc/tenx/config/log4j2.yaml:ro \
    "$ENGINE" @/cfg/enc.yaml > "$dir/encode.stdout" 2>&1
  local n
  n="$(grep -c ',1759386934498' "$dir/out/encoded.log" 2>/dev/null || echo 0)"
  echo "  epochs equal to the UTC reading of 2025-10-02 06:35:34.498: $n of 2"
  [ "$n" = "2" ] || die "timestampZone did not pin the parse zone: a host on America/New_York read the zoneless timestamp differently, so this arm is not reproducible off a UTC host"
}

encode_arm() {
  local label="$1" template="$2" tsconf="$3" out="$4"
  say "encode ($label)"
  rm -rf "$out"; mkdir -p "$out"
  docker run --rm -e INPUT_FILE=/in/events.log -e OUTPUT_DIR=/out \
    -v "$out":/out \
    -v "$DATA_DIR/base/$ASSET":/in/events.log:ro \
    -v "$HERE/tenx-encode-splunk.config.yaml":/cfg/enc.yaml:ro \
    -v "$template":/etc/tenx/config/pipelines/run/template/config.yaml:ro \
    -v "$tsconf":/etc/tenx/config/pipelines/run/transform/timestamp/config.yaml:ro \
    -v "$HERE/conf/engine-log4j2-quiet.yaml":/etc/tenx/config/log4j2.yaml:ro \
    "$ENGINE" @/cfg/enc.yaml > "$out/encode.stdout" 2>&1
  [ -s "$out/encoded.log" ] || { tail -20 "$out/encode.stdout"; die "encode ($label) produced nothing"; }
  echo "encoded.log    $(wc -c < "$out/encoded.log" | tr -d ' ') bytes, $(wc -l < "$out/encoded.log" | tr -d ' ') records"
  echo "templates.json $(wc -c < "$out/templates.json" | tr -d ' ') bytes, $(wc -l < "$out/templates.json" | tr -d ' ') templates"
}

stage_groundtruth() {
  say "ground truth for the expansion check"
  python3 build_groundtruth.py \
    --raw "$DATA_DIR/base/$ASSET" \
    --encoded "$DATA_DIR/compact/encoded.log" \
    --templates "$DATA_DIR/compact/templates.json" \
    --out "$DATA_DIR/groundtruth.json"

  say "where the gap is smallest"
  python3 worst_slice.py \
    --raw "$DATA_DIR/base/$ASSET" \
    --encoded "$DATA_DIR/compact/encoded.log" \
    --templates "$DATA_DIR/compact/templates.json" \
    --out "$RESULTS/worst_slice.json"
}

# The licence day.
#
# RolloverSummary is written when the licence day ends, at midnight in the
# licence manager's own local time, and a partial day is not a result. A run
# started at nine in the morning would otherwise wait fifteen hours. So the
# container is given a whole-hour timezone chosen to put its next local midnight
# a stated distance ahead of container start, long enough that the whole ingest
# is inside one licence day with room to spare. Local midnight always lands on a
# UTC hour boundary, so the reachable leads are (60 - current UTC minute) plus
# whole hours; the smallest one at least MIN_LEAD ahead wins.
choose_tz() {
  python3 - "$MIN_LEAD" <<'PY'
import datetime, sys
lead_min = int(sys.argv[1])
now = datetime.datetime.now(datetime.timezone.utc)
base = (60 - now.minute) % 60 or 60
lead = base
while lead < lead_min:
    lead += 60
# local midnight lands lead minutes from now; solve for the whole-hour offset
target = now + datetime.timedelta(minutes=lead)
offset = -target.hour if target.hour else 0
offset = ((offset + 11) % 24) - 11
# POSIX inverts the sign: Etc/GMT+1 is UTC-1
name = "UTC" if offset == 0 else ("Etc/GMT%+d" % -offset)
print(f"{name} {lead}")
PY
}

stage_splunk() {
  say "Splunk"
  docker image inspect "$SPLUNK_IMAGE" >/dev/null 2>&1 || docker pull "$SPLUNK_IMAGE"
  docker image inspect "$UF_IMAGE" >/dev/null 2>&1 || docker pull "$UF_IMAGE"
  docker network create "$NET" >/dev/null 2>&1 || true
  docker rm -f "$IDX" "$UF" >/dev/null 2>&1 || true

  read -r TZSEL LEAD <<<"$(choose_tz)"
  echo "container timezone $TZSEL; licence day rolls over in about $LEAD minutes"
  echo "$TZSEL" > "$DATA_DIR/tz.txt"

  docker run -d --name "$IDX" --network "$NET" --hostname "$IDX" \
    -e SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com \
    -e SPLUNK_START_ARGS=--accept-license \
    -e SPLUNK_PASSWORD="$PASS" -e TZ="$TZSEL" \
    -p 8000:8000 "$SPLUNK_IMAGE" >/dev/null
  docker run -d --name "$UF" --network "$NET" --hostname "$UF" \
    -e SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com \
    -e SPLUNK_START_ARGS=--accept-license \
    -e SPLUNK_PASSWORD="$PASS" -e TZ="$TZSEL" \
    -v "$DATA_DIR/base":/data/base:ro \
    -v "$DATA_DIR/compact":/data/compact:ro \
    "$UF_IMAGE" >/dev/null

  echo "waiting for splunkd"
  until dx -u splunk "$IDX" /opt/splunk/bin/splunk status 2>/dev/null \
        | grep -q "splunkd is running"; do sleep 15; done
  sp version | head -1

  say "indexer configuration and the 10x app"
  for f in indexes.conf inputs.conf props.conf; do
    docker cp "$HERE/conf/indexer/$f" "$IDX:/opt/splunk/etc/system/local/$f"
  done
  local app="$DATA_DIR/app"
  rm -rf "$app"; mkdir -p "$app"
  if [ -d "${E21_APP_DIR:-}" ]; then
    cp -R "$E21_APP_DIR/tenx-for-splunk" "$app/tenx-for-splunk"
    # The results file names the app commit that produced the expansion figure.
    # A local checkout has to record its own HEAD, and say so when it is dirty;
    # without this the run reports whatever commit the last clone left behind,
    # which is a different app from the one it just measured.
    if (cd "$E21_APP_DIR" && git rev-parse HEAD >/dev/null 2>&1); then
      ( cd "$E21_APP_DIR"
        sha="$(git rev-parse HEAD)"
        git diff --quiet && git diff --cached --quiet || sha="$sha (working tree modified)"
        echo "$sha" ) > "$DATA_DIR/app_sha.txt"
    else
      echo "local directory $E21_APP_DIR, not a git checkout" > "$DATA_DIR/app_sha.txt"
    fi
  else
    git clone --depth 1 "$APP_REPO" "$app/src" >/dev/null 2>&1
    cp -R "$app/src/tenx-for-splunk" "$app/tenx-for-splunk"
    (cd "$app/src" && git rev-parse HEAD) > "$DATA_DIR/app_sha.txt"
  fi
  find "$app/tenx-for-splunk" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  mkdir -p "$app/tenx-for-splunk/local"
  cp "$HERE/conf/tenx_config.conf" "$app/tenx-for-splunk/local/tenx_config.conf"
  docker cp "$app/tenx-for-splunk" "$IDX:/opt/splunk/etc/apps/tenx-for-splunk"
  dx -u root "$IDX" chown -R splunk:splunk \
    /opt/splunk/etc/apps/tenx-for-splunk /opt/splunk/etc/system/local
  sp restart >/dev/null
  until dx -u splunk "$IDX" /opt/splunk/bin/splunk status 2>/dev/null \
        | grep -q "splunkd is running"; do sleep 10; done
}

stage_ingest() {
  say "forwarder configuration, then ingest"
  for f in outputs.conf inputs.conf props.conf limits.conf; do
    docker cp "$HERE/conf/uf/$f" "$UF:/opt/splunkforwarder/etc/system/local/$f"
  done
  dx -u root "$UF" chown -R splunk:splunk /opt/splunkforwarder/etc/system/local
  dx -u splunk "$UF" /opt/splunkforwarder/bin/splunk restart >/dev/null

  local want_enc want_tpl
  want_enc="$(wc -l < "$DATA_DIR/compact/encoded.log" | tr -d ' ')"
  want_tpl="$(wc -l < "$DATA_DIR/compact/templates.json" | tr -d ' ')"
  echo "waiting for $ASSET_LINES / $want_enc / $want_tpl events"
  local deadline=$((SECONDS + 1800))
  while :; do
    local got
    got="$(spq 'index=tenx_base OR index=tenx_enc OR index=tenx_dml | stats count by index' \
           -earliest_time -2h -latest_time now | tr -s ' ')"
    echo "$got" | tail -4
    if echo "$got" | grep -q "tenx_base $ASSET_LINES" \
       && echo "$got" | grep -q "tenx_enc $want_enc" \
       && echo "$got" | grep -q "tenx_dml $want_tpl"; then break; fi
    [ "$SECONDS" -lt "$deadline" ] || die "ingest did not reach the expected counts"
    sleep 20
  done
  echo "ingest complete"
}

stage_kv() {
  say "the app's Consume KV alert filling the KV store"
  local want deadline
  want="$(wc -l < "$DATA_DIR/compact/templates.json" | tr -d ' ')"
  deadline=$((SECONDS + 1800))
  until spq '| inputlookup tenx-dml-lookup | stats count' | tail -1 | grep -qE "^ *$want\$"; do
    spq '| inputlookup tenx-dml-lookup | stats count' | tail -1
    [ "$SECONDS" -lt "$deadline" ] || die "the KV store did not reach $want templates"
    sleep 20
  done
  echo "KV store holds $want templates"
}

# Every compact event, expanded by the app's own inflate macro, against the text
# that went in. Run twice: once with the search head in UTC and once in the
# instance's own timezone, because the macro renders a timestamp in the viewer's
# timezone rather than the timestamp's, so the answer depends on who is looking.
stage_expand() {
  local tzsel; tzsel="$(cat "$DATA_DIR/tz.txt")"
  for view in UTC "$tzsel"; do
    say "expansion check, search head in $view"
    sp _internal call /services/authentication/users/admin -post:tz "$view" -auth "$PASS_ARG" >/dev/null 2>&1
    local out="$RESULTS/expansion.json"
    [ "$view" = "UTC" ] || out="$RESULTS/expansion_local_tz.json"
    spq 'index=tenx_enc | eval tenx_compact=_raw | `tenx-inflate` | table tenx_compact, _raw' -output json \
      | python3 verify_expansion.py --groundtruth "$DATA_DIR/groundtruth.json" --out "$out"
  done
  sp _internal call /services/authentication/users/admin -post:tz UTC -auth "$PASS_ARG" >/dev/null 2>&1
}

stage_licence() {
  say "waiting for the licence day to roll over"
  local deadline=$((SECONDS + 9000))
  until dx -u splunk "$IDX" sh -c \
        'grep -c "type=RolloverSummary" /opt/splunk/var/log/splunk/license_usage.log' 2>/dev/null \
        | grep -qvE '^0$'; do
    echo "  container clock $(dx "$IDX" date)"
    [ "$SECONDS" -lt "$deadline" ] || die "no RolloverSummary was written"
    sleep 120
  done
  echo "rollover written at $(dx "$IDX" date)"
  # RolloverSummary is written at the boundary; give splunkd a moment to index it
  sleep 60

  local host pool
  host="$(spq 'index=_internal source=*license_usage.log type=RolloverSummary | head 1 | table host' \
          -earliest_time -2d -latest_time now | tail -1 | tr -d ' ')"
  pool="$(spq 'index=_internal source=*license_usage.log type=RolloverSummary | head 1 | table pool' \
          -earliest_time -2d -latest_time now | tail -1 | tr -d ' ')"
  echo "licence manager host $host, pool $pool"

  dx -u splunk "$IDX" sh -c \
    'grep "type=RolloverSummary" /opt/splunk/var/log/splunk/license_usage.log' \
    > "$RESULTS/license_usage_rollover.log" 2>/dev/null
  echo "kept $(wc -l < "$RESULTS/license_usage_rollover.log" | tr -d ' ') RolloverSummary lines verbatim"

  run_search() {
    local name="$1" spl="$2" early="$3"
    spq "$spl" -earliest_time "$early" -latest_time now | tee "$RESULTS/$name.txt"
    spq "$spl" -earliest_time "$early" -latest_time now -output json > "$RESULTS/$name.json"
  }

  say "rollover by index (the query the ask names)"
  run_search rollover_by_index "$(cat conf/searches/rollover_by_index.spl)" -2d

  say "Monitoring Console, Historic License Usage, split by Index"
  run_search mc_by_index \
    "$(sed "s/HOSTNAME/$host/; s/POOL/$pool/" conf/searches/mc_historic_by_index.spl)" -30d@d

  say "per-minute Usage records by index and sourcetype, for the sourcetype split"
  run_search usage_by_index_sourcetype "$(cat conf/searches/usage_by_index_sourcetype.spl)" -2d

  say "Monitoring Console, Historic License Usage, no split"
  run_search mc_no_split \
    "$(sed "s/HOSTNAME/$host/; s/POOL/$pool/" conf/searches/mc_historic_no_split.spl)" -30d@d
}

stage_report() {
  say "report"
  # Resolve the digest here too, so that running `./run.sh report` on its own
  # still records which image built the compact form rather than a moving tag.
  ENGINE_DIGEST="${ENGINE_DIGEST:-$(docker image inspect "$ENGINE" \
    --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "$ENGINE")}"
  python3 report.py --dir "$HERE" --data "$DATA_DIR" --results "$RESULTS" \
    --engine "$ENGINE_DIGEST" \
    --splunk-version "$(sp version 2>/dev/null | head -1)"
  cat "$RESULTS/results.md"
}

teardown() {
  if [ "${KEEP:-0}" = "1" ]; then
    echo "KEEP=1: $IDX and $UF left up on network $NET"
  else
    docker rm -f "$IDX" "$UF" >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
  fi
}

ALL=(data encode groundtruth splunk ingest kv expand licence report)
STAGES=("$@")
[ "${#STAGES[@]}" -gt 0 ] || STAGES=("${ALL[@]}")
trap teardown EXIT
for s in "${STAGES[@]}"; do
  case " ${ALL[*]} " in *" $s "*) "stage_$s" ;; *) die "unknown stage $s" ;; esac
done
say "done. artifacts in $RESULTS"
