#!/usr/bin/env bash
#
# Gap 3: can the Retriever index and fetch from the cold layout this route
# writes?
#
# The Retriever's shipped deployment is a set of Quarkus services on AWS with
# four SQS queues and an S3 bucket, or a Lambda behind an S3 trigger. Neither
# fits in this harness, and neither is what the question is about. The question
# is whether the OBJECTS are indexable as written, so the run uses the third
# accessor the engine ships, `Local:com.log10x.ext.cloud.index.access.LocalIndexAccess`,
# which the settings file names for exactly this: the local file system, no
# queues, no cloud. Everything else is the shipped index and query pipeline.
#
# The objects are the ones a gap run wrote, copied out of the object store by
# `g_export_cold` (build/cold-export). Two shapes are indexed, so a failure can
# be attributed:
#
#   as written     the objects exactly as the collector's json encoding wrote
#                  them, one JSON array per object
#   as jsonl       the same records, one JSON object per line, written by this
#                  script. If this one indexes and the first does not, the
#                  finding is the container shape and not the Retriever.
#
# Then one query: one pattern hash, one time window, against the index it built.
#
#   ./gap3_retriever_fetch.sh
#
# Environment: as lib.sh, plus nothing else. Needs build/cold-export, which gap
# 2, 5 or 6 leaves behind.

set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

# Indexing is per object and the objects are megabytes each, so the run indexes
# the first OBJECT_LIMIT of them rather than all forty odd. What it answers is
# whether the layout is indexable and what a fetch costs, and neither needs the
# whole bucket.
OBJECT_LIMIT="${OBJECT_LIMIT:-2}"
OUT="$RESULTS/gap3.json"
EXPORT="$BUILD/cold-export"
WORK="$BUILD/retriever"

g_require
# This gap alone still needs the jar. The other five drive the receiver, which
# the published image is; this one drives the Retriever index and query
# pipelines directly, and those are entry points of the run-cloud build rather
# than of the receiver image.
: "${PATCHED_JAR:?gap 3 runs the Retriever pipelines: set PATCHED_JAR, TENX_CONFIG_TREE and TENX_MODULES_TREE}"
: "${TENX_CONFIG_TREE:?gap 3 needs a checkout of log-10x/config}"
: "${TENX_MODULES_TREE:?gap 3 needs a checkout of log-10x/modules}"
[ -d "$EXPORT" ] || { echo "no build/cold-export: run gap 2, 5 or 6 first" >&2; exit 1; }
g_images "$JRE_IMAGE"

rm -rf "$WORK"; mkdir -p "$WORK/asis" "$WORK/jsonl" "$WORK/index-asis" "$WORK/index-jsonl" "$WORK/out"
chmod -R 777 "$WORK"
cp -R "$EXPORT"/. "$WORK/asis"/

say "the layout, as the collector wrote it"
OBJECTS="$(cd "$WORK/asis" && find . -type f | sort | head -n "$OBJECT_LIMIT")"
OBJECTS_ALL="$(cd "$WORK/asis" && find . -type f | wc -l | tr -d " ")"
OBJECT_COUNT="$(printf '%s\n' "$OBJECTS" | grep -c . || true)"
FIRST_OBJECT="$(printf '%s\n' "$OBJECTS" | head -1 | sed 's#^\./##')"
echo "  $OBJECT_COUNT objects, first is $FIRST_OBJECT"
head -c 220 "$WORK/asis/$FIRST_OBJECT" | sed 's/^/  /'
echo

# The same records, one per line. `body` and `logAttributes` are kept exactly as
# they are in the object; only the container changes.
python3 - "$WORK/asis" "$WORK/jsonl" > "$WORK/jsonl.log" <<'PY'
import json, pathlib, sys
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
records = lines = 0
for p in sorted(src.rglob("*")):
    if not p.is_file():
        continue
    out = dst / p.relative_to(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = p.read_text()
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        doc = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(doc, dict):
        doc = [doc]
    with out.open("w") as fh:
        for rec in doc:
            fh.write(json.dumps(rec) + "\n")
            records += 1
    lines += 1
print(f"{lines} objects, {records} records")
PY
sed 's/^/  /' "$WORK/jsonl.log"

# ------------------------------------------------------ the engine config tree
say "the retriever config, pointed at the local file system"
rm -rf "$WORK/tenx-config" "$WORK/modules"
rsync -a --exclude '.git' "$TENX_CONFIG_TREE/" "$WORK/tenx-config/"
rsync -a --exclude '.git' "$TENX_MODULES_TREE/" "$WORK/modules/"
python3 "$GAPS_HERE/patch_retriever_config.py" --config-dir "$WORK/tenx-config"

if [ ! -d "$BUILD/symbols" ] || [ -z "$(ls -A "$BUILD/symbols" 2>/dev/null)" ]; then
  mkdir -p "$BUILD/symbols"
  docker rm -f csg-symbols-tmp >/dev/null 2>&1 || true
  docker create --name csg-symbols-tmp "$EDGE_IMAGE" >/dev/null
  docker cp csg-symbols-tmp:/etc/tenx/symbols/. "$BUILD/symbols/" >/dev/null
  docker rm csg-symbols-tmp >/dev/null
fi

retriever() {  # app, read dir, index dir, object, extra env...
  local app="$1" readdir="$2" indexdir="$3" object="$4"; shift 4
  docker run --rm --name csg-retriever --memory 2g --cpus 2 \
    -v "$PATCHED_JAR":/app/run-cloud.jar:ro \
    -v "$WORK/tenx-config":/etc/tenx/config:ro \
    -v "$WORK/modules":/opt/tenx/modules:ro \
    -v "$BUILD/symbols":/etc/tenx/symbols:ro \
    -v "$readdir":/cold \
    -v "$indexdir":/index \
    -e TENX_CONFIG=/etc/tenx/config \
    -e TENX_MODULES=/opt/tenx/modules \
    -e TENX_SYMBOLS_PATH=/etc/tenx/symbols \
    -e TENX_LOG_APPENDER=tenxConsoleAppender \
    -e TENX_STREAMER_INPUT_BUCKET=/cold \
    -e TENX_STREAMER_INDEX_BUCKET=/index \
    -e INDEX_READ_OBJECT="$object" \
    -e quiet=true \
    "$@" \
    -w /tmp "$JRE_IMAGE" \
    java -Xmx1500m -Dfile.encoding=UTF-8 -classpath /app/run-cloud.jar \
      com.log10x.ext.cloud.run.RunCloud "@$app" 2>&1
}

index_shape() {  # label, read dir, index dir
  local label="$1" readdir="$2" indexdir="$3" rc=0 n=0
  say "index the objects, $label"
  : > "$WORK/out/index-$label.log"
  while IFS= read -r object; do
    [ -n "$object" ] || continue
    object="${object#./}"
    set +e
    retriever apps/retriever/index "$readdir" "$indexdir" "$object" >> "$WORK/out/index-$label.log" 2>&1
    rc=$?
    set -e
    n=$((n + 1))
    [ "$rc" = "0" ] || break
  done <<< "$OBJECTS"
  local artifacts
  artifacts="$(find "$indexdir" -type f 2>/dev/null | wc -l | tr -d ' ')"
  echo "  $label: $n objects attempted, exit $rc, $artifacts index artifacts"
  printf '%s %s %s\n' "$n" "$rc" "$artifacts" > "$WORK/out/index-$label.stat"
}

index_shape asis "$WORK/asis" "$WORK/index-asis"
index_shape jsonl "$WORK/jsonl" "$WORK/index-jsonl"

# --------------------------------------------------------------- one query
QUERY_LABEL=none
QUERY_MS=0
QUERY_RC=1
# The type to fetch has to be one of the types in the objects that were indexed,
# not one from the whole export: the index holds what it was given.
printf '%s\n' "$OBJECTS" > "$WORK/out/indexed.txt"
HASH="$(python3 - "$WORK/asis" "$WORK/out/indexed.txt" <<'PY'
import collections, json, pathlib, sys
src = pathlib.Path(sys.argv[1])
c = collections.Counter()
for line in open(sys.argv[2]):
    name = line.strip().lstrip("./")
    if not name:
        continue
    p = src / name
    if not p.is_file():
        continue
    try:
        doc = json.loads(p.read_text())
    except json.JSONDecodeError:
        continue
    if isinstance(doc, dict):
        doc = [doc]
    for rec in doc:
        h = (rec.get("logAttributes") or {}).get("tenx_hash", "")
        if h:
            c[h] += 1
print(c.most_common(1)[0][0] if c else "")
PY
)"
SEARCH_WORD="$(python3 - "$WORK/asis" "$HASH" "$WORK/out/indexed.txt" <<'PY'
import json, pathlib, sys
src, h = pathlib.Path(sys.argv[1]), sys.argv[2]
for line in open(sys.argv[3]):
    name = line.strip().lstrip("./")
    if not name:
        continue
    p = src / name
    if not p.is_file():
        continue
    try:
        doc = json.loads(p.read_text())
    except json.JSONDecodeError:
        continue
    if isinstance(doc, dict):
        doc = [doc]
    for rec in doc:
        attrs = rec.get("logAttributes") or {}
        if attrs.get("tenx_hash") == h:
            words = [w for w in (attrs.get("message_pattern") or "").split("_") if len(w) >= 6]
            print(words[0] if words else "")
            sys.exit(0)
print("")
PY
)"
echo "  the pattern hash to fetch: ${HASH:-none found}, search term: ${SEARCH_WORD:-none}"

for shape in jsonl asis; do
  read -r _ rc artifacts < "$WORK/out/index-$shape.stat"
  if [ "$rc" = "0" ] && [ "$artifacts" -gt 0 ]; then
    say "query the $shape index for one pattern hash"
    START="$(python3 -c 'import time; print(int(time.time() * 1000))')"
    set +e
    retriever apps/retriever/query "$WORK/$shape" "$WORK/index-$shape" "" \
      -e QUERY_FILTER="tenx_hash == \"$HASH\"" \
      -e QUERY_SEARCH="includes(message, \"$SEARCH_WORD\")" > "$WORK/out/query-$shape.log" 2>&1
    QUERY_RC=$?
    set -e
    END="$(python3 -c 'import time; print(int(time.time() * 1000))')"
    QUERY_MS=$((END - START))
    QUERY_LABEL="$shape"
    echo "  exit $QUERY_RC in $QUERY_MS ms"
    tail -5 "$WORK/out/query-$shape.log" | sed 's/^/  /'
    break
  fi
done

python3 - "$OUT" "$WORK" "$FIRST_OBJECT" "$OBJECT_COUNT" "${HASH:-}" "$QUERY_LABEL" "$QUERY_MS" "$QUERY_RC" "$OBJECTS_ALL" "${SEARCH_WORD:-}" <<'PY'
import json, pathlib, sys
out, work, first, count, h, qlabel, qms, qrc, all_objects, search = sys.argv[1:11]
work = pathlib.Path(work)
def stat(label):
    p = work / "out" / f"index-{label}.stat"
    if not p.exists():
        return {}
    n, rc, artifacts = p.read_text().split()
    log = (work / "out" / f"index-{label}.log")
    text = log.read_text() if log.exists() else ""
    return {"objects_attempted": int(n), "exit_code": int(rc),
            "index_artifacts": int(artifacts), "log_tail": text[-1500:]}
export_meta = work.parent / "cold-export.json"
qlog = work / "out" / f"query-{qlabel}.log"
json.dump({
 "gap": 3,
 "cold_export": json.loads(export_meta.read_text()) if export_meta.exists() else None,
 "objects_indexed": int(count), "objects_in_export": int(all_objects), "first_object": first,
 "first_object_head": (work / "asis" / first).read_text()[:400],
 "index_as_written": stat("asis"),
 "index_as_jsonl": stat("jsonl"),
 "hash_probed": h,
 "query_shape": qlabel, "query_ms": int(qms), "query_exit": int(qrc),
 "query_search": search,
 "query_log_tail": qlog.read_text()[-2000:] if qlog.exists() else "",
}, open(out, "w"), indent=1)
print("wrote", out)
PY

say "done"
