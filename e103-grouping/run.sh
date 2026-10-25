#!/bin/bash
# E103 grouping rig. Fluent Bit and the Receiver as the elastic-hot-tier-budget rig starts them, without
# Elasticsearch: the returned records go to a file. Subcommands:
#   all                 check no other rig is running, up, send, wait for the returned records, score, clean
#   up                  network e103, Fluent Bit (e103-fluent-bit), the Receiver (e103-tenx)
#   send [cases] [n]    send.py in a container (e103-send) on the network, waits for it to finish
#   drain               waits until every sent line is back or nothing new arrives for 20 s (at most 180 s)
#   score               score.py on the results dir (exit 1 on any cross-container record, missing or duplicate)
#   logs                saves the Receiver and Fluent Bit logs and Fluent Bit's counters to the results dir
#   clean               docker rm -f -v of every e103-* container, removes the e103 network
#   extract <dir>       copies the image's bundled config and modules to <dir>/config and <dir>/modules
# Environment:
#   E103_IMAGE          engine image (default: ghcr.io/log-10x/edge-10x:1.1.150, pinned by digest)
#   E103_CONFIG_DIR     host directory mounted read-only over the image's config (/etc/tenx/config)
#   E103_MODULES_DIR    host directory mounted read-only over the image's modules (/opt/tenx-edge/lib/app/modules)
#   E103_LABEL          results subdirectory name (default: shipped-1.1.150, or override when a dir is set)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RIG=$(cd "$HERE/../elastic-hot-tier-budget/rig" && pwd)
IMAGE=${E103_IMAGE:-ghcr.io/log-10x/edge-10x:1.1.150@sha256:3e755bbc14780a27e643e09b76dfd7ec9616cab67833f70daf9420eff646d350}
FB_IMAGE=fluent/fluent-bit:4.2
PY_IMAGE=python:3.12-slim
NET=e103
if [ -n "${E103_CONFIG_DIR:-}${E103_MODULES_DIR:-}" ]; then LABEL=${E103_LABEL:-override}; else LABEL=${E103_LABEL:-shipped-1.1.150}; fi
RES=$HERE/results/$LABEL
DATA=$RES/data
# the Receiver's arguments and environment, as gen-receiver-values.mjs renders them for the hot-tier run
# (results-two-arm*/values/compose.receiver.yaml); GH_* (the policy branch) is left out: nothing is held
ARGS=(@run/input/forwarder/fluentbit @apps/receiver symbolMessageHashField tenx_hash outputEncodeField
      'fullText("tenx_hash","routeState","message_pattern","severity_level","utf8Size")')
ENVS=(-e TENX_AIRGAPPED=true -e TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit)

foreign() { docker ps --format '{{.Names}}' | grep -v '^e103-' || true; }

up() {
  [ -z "$(foreign)" ] || { echo "other containers are running, not starting:"; foreign; exit 3; }
  mkdir -p "$DATA"
  rm -f "$DATA"/*.jsonl
  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
  docker run -d --name e103-fluent-bit --network "$NET" --network-alias fluent-bit --memory 300m \
    -v "$HERE/fluent-bit:/fluent-bit/etc/rig:ro" -v "$DATA:/data" \
    "$FB_IMAGE" /fluent-bit/bin/fluent-bit -c /fluent-bit/etc/rig/fluent-bit.conf >/dev/null
  MOUNTS=()
  [ -z "${E103_CONFIG_DIR:-}" ] || MOUNTS+=(-v "$(cd "$E103_CONFIG_DIR" && pwd):/etc/tenx/config:ro")
  [ -z "${E103_MODULES_DIR:-}" ] || MOUNTS+=(-v "$(cd "$E103_MODULES_DIR" && pwd):/opt/tenx-edge/lib/app/modules:ro")
  docker run -d --name e103-tenx --network "$NET" --network-alias tenx --cpus 0.5 --memory 512m --tmpfs /tmp \
    "${ENVS[@]}" ${MOUNTS[@]+"${MOUNTS[@]}"} "$IMAGE" "${ARGS[@]}" >/dev/null
  for _ in $(seq 1 60); do
    docker logs e103-tenx 2>&1 | grep -q 'Forward protocol server listening' && break
    [ "$(docker inspect -f '{{.State.Running}}' e103-tenx)" = true ] || break
    sleep 2
  done
  docker logs e103-tenx 2>&1 | grep -q 'Forward protocol server listening' || { echo "the Receiver did not start"; docker logs --tail 30 e103-tenx; exit 1; }
  sleep 3
  commit() { git -C "$1" rev-parse HEAD 2>/dev/null || echo "not a git checkout"; }
  python3 - "$RES/run.json" "$IMAGE" "$(docker inspect -f '{{.Image}}' e103-tenx)" "${E103_CONFIG_DIR:-}" "${E103_MODULES_DIR:-}" \
    "$( [ -n "${E103_CONFIG_DIR:-}" ] && commit "$E103_CONFIG_DIR")" "$( [ -n "${E103_MODULES_DIR:-}" ] && commit "$E103_MODULES_DIR")" \
    "$(docker inspect -f '{{.Image}}' e103-fluent-bit)" "${ARGS[@]}" <<'EOF'
import json, sys, time
out, image, image_id, cdir, mdir, ccommit, mcommit, fb_id, *args = sys.argv[1:]
json.dump({'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'image': image, 'image_id': image_id,
           'args': args, 'env': ['TENX_AIRGAPPED=true', 'TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit'], 'cpus': 0.5, 'memory': '512m',
           'config_dir': cdir or None, 'config_commit': ccommit or None, 'modules_dir': mdir or None, 'modules_commit': mcommit or None,
           'fluent_bit_image': 'fluent/fluent-bit:4.2', 'fluent_bit_image_id': fb_id}, open(out, 'w'), indent=1)
EOF
  echo "up: $LABEL"
}

send() {
  docker rm -f -v e103-send >/dev/null 2>&1 || true
  docker run -d --name e103-send --network "$NET" -v "$HERE:/e103:ro" -v "$RIG:/rig:ro" -v "$DATA:/out" \
    "$PY_IMAGE" python3 -u /e103/send.py fluent-bit 24224 /out/sent.jsonl "${1:-abcde}" "${2:-500}" >/dev/null
  docker wait e103-send >/dev/null
  docker logs e103-send > "$RES/send.log" 2>&1
  docker rm -f -v e103-send >/dev/null
  cat "$RES/send.log"
}

drain() {
  python3 - "$DATA" <<'EOF'
import json, os, re, sys, time
d = sys.argv[1]
want = sum(1 for _ in open(os.path.join(d, 'sent.jsonl')))
tok = re.compile(r'e103id\W{1,3}(\d+)')
def back():
    p = os.path.join(d, 'returned.jsonl')
    return len(tok.findall(open(p).read())) if os.path.exists(p) else 0
t0 = last_t = time.time(); last = -1
while time.time() - t0 < 180:
    n = back()
    if n != last:
        last, last_t = n, time.time()
    if n >= want or time.time() - last_t > 20:
        break
    time.sleep(3)
print(json.dumps({'sent_lines': want, 'returned_tokens': last, 'waited_s': round(time.time() - t0)}))
EOF
}

logs() {
  docker logs e103-tenx > "$RES/tenx.log" 2>&1 || true
  docker logs e103-fluent-bit > "$RES/fluent-bit.log" 2>&1 || true
  docker rm -f -v e103-fbmetrics >/dev/null 2>&1 || true
  docker run -d --name e103-fbmetrics --network "$NET" "$PY_IMAGE" python3 -c \
    "import urllib.request; print(urllib.request.urlopen('http://fluent-bit:2020/api/v1/metrics').read().decode())" >/dev/null
  docker wait e103-fbmetrics >/dev/null; docker logs e103-fbmetrics > "$RES/fluent-bit-metrics.json" 2>&1 || true
  docker rm -f -v e103-fbmetrics >/dev/null 2>&1 || true
}

clean() {
  for c in $(docker ps -a --format '{{.Names}}' | grep '^e103-' || true); do docker rm -f -v "$c" >/dev/null; done
  docker network rm "$NET" >/dev/null 2>&1 || true
}

case "${1:-}" in
  up) up ;;
  send) send "${2:-abcde}" "${3:-500}" ;;
  drain) drain ;;
  score) python3 "$HERE/score.py" "$DATA" ;;
  logs) logs ;;
  clean) clean ;;
  extract)
    dir=${2:?target dir}; mkdir -p "$dir"
    docker rm -f e103-extract >/dev/null 2>&1 || true
    docker create --name e103-extract "$IMAGE" >/dev/null
    docker cp e103-extract:/etc/tenx/config "$dir/config" >/dev/null
    docker cp e103-extract:/opt/tenx-edge/lib/app/modules "$dir/modules" >/dev/null
    docker rm -f -v e103-extract >/dev/null
    echo "$dir/config $dir/modules" ;;
  all)
    trap clean EXIT
    up; send "${2:-abcde}" "${3:-500}"; drain; logs
    set +e; python3 "$HERE/score.py" "$DATA" | tee "$RES/score.md"; rc=${PIPESTATUS[0]}; set -e
    gzip -f "$DATA"/*.jsonl
    exit $rc ;;
  *) sed -n '2,18p' "$0"; exit 2 ;;
esac
