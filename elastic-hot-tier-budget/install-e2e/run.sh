#!/bin/bash
# E100/E101 install proof. Subcommands, in the order the README ran them:
#   render <hot_tier_gb>   render.mjs: the recipe (advise_retriever), the Receiver (advise_install),
#                          policy.yaml (setup_recurring, the local policy checkout as its config plane)
#   policy-init            a local bare repo as the policy remote: policy.yaml on main, the seed files
#                          from advise_install's ConfigMap under log10x/policy/ on log10x-policy
#   up                     Elasticsearch hot + warm/frozen, the snapshot volume owned by uid 1000,
#                          setup-es.mjs (licence, repository, the recipe), then Fluent Bit and the Receiver
#   feed start <speed> | stop   the OTel sample replay at 7 lines a second x speed (forward_send.py)
#   tick [--dry-run]       tenx-recur on policy.yaml against the cluster and the local policy repo
#   sync                   copy the four files from log10x-policy into the mounted policy dir, restart the Receiver
#   state                  aliases, indices, doc counts and shard nodes
#   down                   remove every e100 container and volume (docker compose -p e100 down -v)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export RIG_DIR=$HERE/../rig
export RESULTS=${RESULTS:-$HERE/results}
export RIG_DATA=$RESULTS/data
export MCP=${MCP:?log10x-mcp package}
export ENGINE_IMAGE=${ENGINE_IMAGE:-ghcr.io/log-10x/edge-10x:1.1.150}
POLICY=$RESULTS/policy-git
T=$RESULTS/timeline.jsonl
mkdir -p "$RESULTS" "$RIG_DATA"
mark() { echo "{\"event\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\",\"epoch\":$(date +%s)${2:+,$2}}" >> "$T"; }
compose() { docker compose -p e100 -f "$HERE/compose.yaml" -f "$RESULTS/compose.receiver.yaml" "$@"; }
es() { curl -s -m 30 "http://127.0.0.1:9200$1"; }
git_local() { git -c user.name='log10x hot-tier run (e100 rig)' -c user.email=install@log10x.com "$@"; }
case "${1:-}" in
  render)
    gb=${2:?hot_tier_gb}
    containers=$(python3 -c "import json;print(','.join(sorted({json.loads(l)['container_name'].lstrip('/') for l in open('$RESULTS/replay/source.jsonl')})))")
    node "$HERE/render.mjs" "$RESULTS" "$gb" "$POLICY/checkout" "$containers" > "$RESULTS/render.out"
    mark rendered "\"hot_tier_gb\":\"$gb\""
    ;;
  policy-init)
    rm -rf "$POLICY" && mkdir -p "$POLICY"
    git init -q --bare "$POLICY/origin.git"
    git clone -q "$POLICY/origin.git" "$POLICY/checkout" 2>/dev/null
    cd "$POLICY/checkout"
    git checkout -q -b main
    cp "$RESULTS/policy.yaml" policy.yaml && git add policy.yaml && git_local commit -q -m "policy.yaml from log10x_setup_recurring" && git push -q origin main
    git checkout -q -b log10x-policy
    mkdir -p log10x/policy
    python3 -c "
import json
d=json.load(open('$RESULTS/receiver.json'))['policy_configmap']['data']
for k,v in d.items(): open('log10x/policy/'+k,'w').write(v if v.endswith('\n') else v+'\n')"
    git add log10x/policy && git_local commit -q -m "seed: the policy files from log10x_advise_install" && git push -q origin log10x-policy
    git checkout -q main
    mark policy_init
    ;;
  up)
    compose up -d es-hot es-warm-frozen
    for i in $(seq 1 90); do [ "$( (es '/_cat/nodes?h=name' || true) | grep -c . || true)" = 2 ] && break; sleep 4; done
    docker run -d --name e100-chown -v e100_es-snapshots:/s alpine:latest chown 1000:0 /s >/dev/null
    docker wait e100-chown >/dev/null; docker rm -f -v e100-chown >/dev/null
    mark es_ready "\"version\":\"$(es / | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"]["number"])')\""
    node "$HERE/setup-es.mjs" "$RESULTS" | tee "$RESULTS/setup-es.out"
    mark es_setup_done
    compose up -d fluent-bit tenx
    for i in $(seq 1 120); do docker logs e100-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field' && break; sleep 3; done
    mark receiver_ready
    ;;
  feed)
    case "${2:-}" in
      start)
        docker run -d --name e100-feed --network e100_default -v "$RIG_DIR:/rig:ro" -v "$RESULTS/replay:/replay:ro" python:3.12-slim \
          python3 -u /rig/forward_send.py replay /replay/source.jsonl "${3:?speed}" fluent-bit 24224 "${4:-0}" >/dev/null
        mark feed_start "\"speed\":$3,\"lines_per_s\":$(python3 -c "print(7*$3)")" ;;
      stop) docker rm -f -v e100-feed >/dev/null 2>&1 || true; mark feed_stop ;;
    esac
    ;;
  tick)
    stamp=$(date -u +%Y%m%dT%H%M%SZ); out=$RESULTS/ticks/$stamp; mkdir -p "$out"
    set +e
    LOG10X_ES_URL=http://127.0.0.1:9200 LOG10X_GITOPS_REPO_PATH=$POLICY/checkout \
      GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=user.name GIT_CONFIG_VALUE_0='log10x hot-tier run (e100 rig)' GIT_CONFIG_KEY_1=user.email GIT_CONFIG_VALUE_1=install@log10x.com \
      node "$MCP/build/bin/tenx-recur.js" --policy "$RESULTS/policy.yaml" --verbose "${@:2}" > "$out/run.json" 2> "$out/report.txt"
    rc=$?; set -e
    echo "$rc" > "$out/exit"
    git -C "$POLICY/checkout" fetch -q origin '+refs/heads/log10x-policy:refs/remotes/origin/log10x-policy'
    git -C "$POLICY/checkout" log --format='%h %s' origin/log10x-policy > "$out/branch-log.txt"
    mark tick "\"dir\":\"ticks/$stamp\",\"exit\":$rc,\"dry_run\":$([ "${2:-}" = --dry-run ] && echo true || echo false)"
    echo "exit $rc ($out)"
    ;;
  sync)
    git -C "$POLICY/checkout" fetch -q origin '+refs/heads/log10x-policy:refs/remotes/origin/log10x-policy'
    for f in caps.csv actions.csv totals.csv; do git -C "$POLICY/checkout" show "origin/log10x-policy:log10x/policy/$f" > "$RESULTS/policy/$f"; done
    docker restart e100-tenx >/dev/null
    for i in $(seq 1 120); do docker logs --since 30s e100-tenx 2>&1 | grep -q -E 'Forward protocol server listening|Writing TenXObject field' && break; sleep 3; done
    mark policy_synced "\"commit\":\"$(git -C "$POLICY/checkout" rev-parse --short origin/log10x-policy)\""
    ;;
  state)
    es '/_cat/aliases/tenx-*?v&h=alias,index,is_write_index'
    es '/_cat/indices/*tenx-*?v&h=index,docs.count,store.size&s=index'
    es '/_cat/shards/*tenx-*?v&h=index,prirep,state,node&s=index'
    ;;
  down)
    docker rm -f -v e100-feed e100-chown >/dev/null 2>&1 || true
    docker logs e100-tenx > "$RESULTS/e100-tenx.log" 2>&1 || true
    docker logs e100-fluent-bit > "$RESULTS/e100-fluent-bit.log" 2>&1 || true
    compose down -v
    mark down
    ;;
  *) sed -n '2,15p' "$0"; exit 2;;
esac
