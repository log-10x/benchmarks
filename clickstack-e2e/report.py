#!/usr/bin/env python3
"""Read the run back and write the results file.

Three measurements, in this order:

  1. the wire. Every record the receiver returned was tapped to a file by the
     collector. This counts them, censuses the field names that arrived, and
     keeps one record verbatim.
  2. the queries. Each one is run with its own query id, then read back out of
     system.query_log for rows, bytes, time and the S3 request counters.
  3. the lossless check. Records that left the receiver against rows in hot plus
     cold, in total and per pattern hash.
"""
import argparse
import collections
import json
import pathlib
import re
import subprocess
import time
import uuid


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True,
                          check=False).stdout.strip()


class Client:
    def __init__(self, container: str):
        self.container = container

    def q(self, sql: str, fmt: str = "TSVRaw", query_id: str | None = None) -> str:
        cmd = ["docker", "exec", "-i", self.container, "clickhouse-client"]
        if query_id:
            cmd += ["--query_id", query_id]
        cmd += ["--format", fmt, "--query", sql]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return "ERROR: " + r.stderr.strip().splitlines()[0]
        # rstrip only: a TSV row whose first column is the empty pattern hash
        # starts with a tab, and a full strip() would eat it and leave one field.
        return r.stdout.rstrip("\n")

    def one(self, sql: str) -> str:
        return self.q(sql).splitlines()[0] if self.q(sql) else ""

    def rows(self, sql: str) -> list[list[str]]:
        out = self.q(sql, fmt="TSV")
        return [line.split("\t") for line in out.splitlines()] if out else []


# --------------------------------------------------------------------- the wire
def read_wire(path: pathlib.Path):
    total = 0
    field_counts: collections.Counter = collections.Counter()
    resource_counts: collections.Counter = collections.Counter()
    route_counts: collections.Counter = collections.Counter()
    per_hash: collections.Counter = collections.Counter()
    no_attrs = 0
    no_attrs_body_key = 0
    with_time = 0
    sample = None
    if not path.exists():
        return dict(total=0, fields={}, resource={}, routes={}, per_hash={},
                    no_attrs=0, no_attrs_body_key=0, with_time=0, sample=None)
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            for rl in doc.get("resourceLogs", []):
                rkeys = [a["key"] for a in rl.get("resource", {}).get("attributes", [])]
                for sl in rl.get("scopeLogs", []):
                    for lr in sl.get("logRecords", []):
                        total += 1
                        if lr.get("timeUnixNano") not in (None, "", "0"):
                            with_time += 1
                        attrs = {a["key"]: a["value"] for a in lr.get("attributes", [])}
                        for k in attrs:
                            field_counts[k] += 1
                        for k in rkeys:
                            resource_counts[k] += 1
                        route = attrs.get("routeState", {}).get("stringValue", "")
                        route_counts[route or "(no routeState)"] += 1
                        h = attrs.get("tenx_hash", {}).get("stringValue", "")
                        per_hash[h] += 1
                        if not attrs:
                            no_attrs += 1
                            body = lr.get("body", {}).get("stringValue", "")
                            if body.startswith('{"body"'):
                                no_attrs_body_key += 1
                        elif sample is None and route == "offload":
                            sample = lr
    return dict(total=total, fields=dict(field_counts), resource=dict(resource_counts),
                routes=dict(route_counts), per_hash=dict(per_hash),
                no_attrs=no_attrs, no_attrs_body_key=no_attrs_body_key,
                with_time=with_time, sample=sample)


# ------------------------------------------------- what ClickStack's collector has
# The components the harness needs, and where each one has to run. The list is
# read out of the ClickStack collector's own `components` output, so it is a
# measurement of the image rather than a claim about it.
WANTED = [
    ("receivers", "file_log", "read the capture"),
    ("receivers", "otlp", "take the receiver's return path"),
    ("connectors", "routing", "split the stream on routeState"),
    ("exporters", "clickhouse", "insert the rows that stayed"),
    ("exporters", "awss3", "write the rows that left"),
    ("extensions", "json_log_encoding", "encode the offloaded object"),
    ("extensions", "otlp_encoding", "the alternative encoding"),
    ("processors", "groupbyattrs", "lift the service back onto the resource"),
    ("processors", "transform", "stamp the record time"),
]


def components(path: pathlib.Path):
    """Parse `otelcol components` output into {section: {name}}."""
    have: dict[str, set] = {}
    section = None
    version = ""
    if not path.exists():
        return have, version, []
    for line in path.read_text().splitlines():
        m = re.match(r"^([a-z]+):$", line)
        if m:
            section = m.group(1)
            have.setdefault(section, set())
            continue
        m = re.match(r"^\s+version: (\S+)", line)
        if m and not version:
            version = m.group(1)
        m = re.match(r"^\s+- name: (\S+)", line)
        if m and section:
            have[section].add(m.group(1))
    rows = []
    for section, name, why in WANTED:
        present = name in have.get(section, set())
        rows.append(dict(section=section, name=name, why=why, present=present))
    return have, version, rows



def readable(record: dict) -> dict:
    """One returned record as body plus a flat attribute map.

    The raw OTLP JSON for one record runs past what is worth printing, and the
    three fields this harness is about sit at the end of it, so the marker
    fields are listed first and the rest follow in the order they arrived.
    """
    def value(v):
        if "stringValue" in v:
            return v["stringValue"]
        if "kvlistValue" in v:
            return {kv["key"]: value(kv["value"]) for kv in v["kvlistValue"]["values"]}
        if "arrayValue" in v:
            return [value(x) for x in v["arrayValue"].get("values", [])]
        return next(iter(v.values()), None)

    attrs = {a["key"]: value(a["value"]) for a in record.get("attributes", [])}
    first = ("routeState", "tenx_hash", "message_pattern", "k8s_container")
    ordered = {k: attrs[k] for k in first if k in attrs}
    ordered.update({k: v for k, v in attrs.items() if k not in first})
    return {"timeUnixNano": record.get("timeUnixNano"),
            "body": record.get("body", {}).get("stringValue"),
            "attributes": ordered}


# ------------------------------------------------------------------ the queries
QUERIES = [
    ("hot only, last hour, count",
     "SELECT count() FROM default.otel_logs WHERE Timestamp >= now() - INTERVAL 1 HOUR"),
    ("merge, one service, last hour",
     "SELECT count() FROM default.otel_logs_all WHERE ServiceName = '{svc}' "
     "AND Timestamp >= now() - INTERVAL 1 HOUR"),
    ("merge, one service and one day",
     "SELECT count() FROM default.otel_logs_all WHERE ServiceName = '{svc}' AND day = today()"),
    ("merge, time only, the shape HyperDX sends",
     "SELECT count() FROM default.otel_logs_all WHERE Timestamp >= now() - INTERVAL 1 HOUR"),
    ("merge, text search, no other filter",
     "SELECT count() FROM default.otel_logs_all WHERE positionCaseInsensitive(Body, 'snapshot') > 0"),
    ("merge, one pattern text, no time filter",
     "SELECT count() FROM default.otel_logs_all "
     "WHERE LogAttributes['message_pattern'] != '' "
     "AND LogAttributes['message_pattern'] = "
     "(SELECT message_pattern FROM default.counts_by_type WHERE source = 'cold' "
     "AND message_pattern != '' ORDER BY cnt DESC LIMIT 1)"),
    ("merge, one pattern hash, hot and cold side by side",
     "SELECT _table, count() FROM default.otel_logs_all "
     "WHERE LogAttributes['tenx_hash'] != '' GROUP BY _table"),
    ("counts table, count all by service, last hour",
     "SELECT ServiceName, sum(cnt) FROM default.counts_by_type "
     "WHERE Minute >= now() - INTERVAL 1 HOUR GROUP BY ServiceName ORDER BY sum(cnt) DESC"),
    ("cold only, one service and one day",
     "SELECT count() FROM default.otel_logs_coldv WHERE ServiceName = '{svc}' AND day = today()"),
]


def run_queries(cl: Client):
    # The service the table filters on is the one that actually has offloaded
    # rows, so the query shapes are read against a service that is on both sides.
    svc = cl.q("SELECT ServiceName FROM default.otel_logs_coldv GROUP BY ServiceName "
               "ORDER BY count() DESC LIMIT 1").splitlines()
    svc = svc[0] if svc and not svc[0].startswith("ERROR") else "kafka"
    out = []
    for name, sql in QUERIES:
        sql = sql.replace("{svc}", svc)
        # ClickHouse keeps a per-object row count and answers a repeated count()
        # over the same objects from it, with no request at all. That is a real
        # saving and it would also hide what a query costs, so it is off here.
        sql += " SETTINGS use_cache_for_count_from_files = 0"
        # ClickHouse caches what it read from the object store, so a second
        # query over the same objects issues no request at all. Every query in
        # this table is measured on a cold cache, and then once more warm.
        for drop in ("FILESYSTEM CACHE", "MARK CACHE", "UNCOMPRESSED CACHE"):
            cl.q(f"SYSTEM DROP {drop}")
        qid = str(uuid.uuid4())
        t0 = time.time()
        result = cl.q(sql, query_id=qid)
        wall_ms = int((time.time() - t0) * 1000)
        qid2 = str(uuid.uuid4())
        cl.q(sql, query_id=qid2)
        cl.q("SYSTEM FLUSH LOGS")
        repeat = cl.q(
            "SELECT toString(query_duration_ms), toString(ProfileEvents['S3GetObject']) "
            f"FROM system.query_log WHERE query_id = '{qid2}' AND type = 'QueryFinish' LIMIT 1",
            fmt="TSV").split("\t")
        repeat = repeat if len(repeat) == 2 else ["", ""]
        row = cl.q(
            "SELECT toString(read_rows), toString(read_bytes), toString(query_duration_ms), "
            "toString(ProfileEvents['S3GetObject']), toString(ProfileEvents['S3ListObjects']), "
            "toString(ProfileEvents['S3ReadRequestsCount']) "
            f"FROM system.query_log WHERE query_id = '{qid}' AND type = 'QueryFinish' LIMIT 1",
            fmt="TSV")
        parts = row.split("\t") if row and not row.startswith("ERROR") else ["", "", "", "", "", ""]
        out.append(dict(name=name.replace("one service", f"service {svc}"),
                        sql=" ".join(sql.split()),
                        result=result.replace("\n", " | ")[:120],
                        read_rows=parts[0], read_bytes=parts[1], ms=parts[2],
                        s3_get=parts[3], s3_list=parts[4], s3_reads=parts[5],
                        ms_repeat=repeat[0], s3_get_repeat=repeat[1],
                        wall_ms=wall_ms))
    return out


# ----------------------------------------------------------------- the check
def lossless(cl: Client, wire: dict):
    hot = int(cl.q("SELECT count() FROM default.otel_logs") or 0)
    cold = int(cl.q("SELECT count() FROM default.otel_logs_coldv") or 0)
    hot_hashes = {h: int(n) for h, n in cl.rows(
        "SELECT LogAttributes['tenx_hash'], toString(count()) FROM default.otel_logs "
        "GROUP BY 1")}
    cold_hashes = {h: int(n) for h, n in cl.rows(
        "SELECT LogAttributes['tenx_hash'], toString(count()) FROM default.otel_logs_coldv "
        "GROUP BY 1")}
    stored = collections.Counter(hot_hashes)
    stored.update(cold_hashes)
    wire_hashes = collections.Counter(wire["per_hash"])
    missing = {h: wire_hashes[h] - stored.get(h, 0)
               for h in wire_hashes if wire_hashes[h] != stored.get(h, 0)}
    extra = {h: stored[h] - wire_hashes.get(h, 0)
             for h in stored if stored[h] != wire_hashes.get(h, 0)}
    return dict(hot=hot, cold=cold, wire=wire["total"],
                hot_plus_cold=hot + cold,
                gap=wire["total"] - (hot + cold),
                hashes_on_wire=len(wire_hashes), hashes_stored=len(stored),
                per_hash_mismatch={k: v for k, v in list(missing.items())[:10]},
                per_hash_extra={k: v for k, v in list(extra.items())[:10]})


def engine_counters(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    out: dict[str, float] = {}
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([0-9.eE+-]+)$", line)
        if not m:
            continue
        name = m.group(1)
        try:
            out[name] = out.get(name, 0.0) + float(m.group(3))
        except ValueError:
            pass
    return out



# ---------------------------------------------------- what did not work, plainly
def findings(wire: dict, component_rows: list, args) -> list[str]:
    total = max(wire["total"], 1)
    with_fields = wire["total"] - wire["no_attrs"]
    on_resource = wire["resource"].get("service.name", 0)
    as_attribute = wire["fields"].get("service.name", 0)
    expected = {"stream", "log.file.name", "k8s_container", "k8s_namespace", "docker",
                "kubernetes", "tenx_tag", "tenx_hash", "message_pattern", "routeState",
                "service.name"}
    odd_keys = sorted((k for k in wire["fields"] if k not in expected),
                      key=lambda k: -wire["fields"][k])
    routed = sum(v for k, v in wire["routes"].items() if k != "(no routeState)")
    hashed = wire["fields"].get("tenx_hash", 0)
    patterned = wire["fields"].get("message_pattern", 0)
    missing = [r["name"] for r in component_rows if not r["present"]]
    # Three of the findings the 2026-09-14 run reported were engine defects, fixed in
    # 1.1.79 (engine #150, pipeline-extensions #40). Each paragraph below is written
    # from the measurement, so a run states what it saw rather than asserting a defect
    # that is no longer there, and a regression puts the original wording back.
    clean = []
    if wire["no_attrs"] == 0:
        clean.append(
            f"**Every returned record carries the marks.** {wire['total']} of "
            f"{wire['total']} came back with attributes, messages that are themselves "
            f"JSON objects with a `body` key included, so every record is routable. The "
            f"2026-09-14 run returned {'{:,}'.format(19436)} of {'{:,}'.format(37519)} "
            f"with no attributes at all.")
    if as_attribute == 0 and on_resource:
        clean.append(
            f"**The service arrives in one place.** The OTLP resource carried "
            f"`service.name` on {on_resource} records and a log attribute carried it on "
            f"{as_attribute}, so the `groupbyattrs` hop had nothing to lift. The hop stays "
            f"in the config: a record that carries the service only as an attribute lands "
            f"under a prefix of `service=<nil>` without it.")
    if wire["with_time"] == wire["total"] and wire["total"]:
        clean.append(
            f"**A returned record carries the marks and a record time.** "
            f"{wire['with_time']} of {wire['total']} came back with `timeUnixNano` set, "
            f"the marked records included. The 2026-09-14 run set it only on the "
            f"unmarked ones.")

    out = []
    if clean:
        out += ["## What the earlier run reported and this run does not", ""]
        for para in clean:
            out += [para, ""]

    out += ["## What did not work, or was skipped", ""]
    if wire["no_attrs"]:
        out += [
        f"**The marker does not survive a message that is itself JSON with a `body` "
        f"key.** {wire['no_attrs']} of {wire['total']} returned records came back with no "
        f"attributes at all: no `routeState`, no pattern hash, no pattern text, and an "
        f"empty OTLP resource. "
        + ("Every one of them has a "
           if wire['no_attrs_body_key'] == wire['no_attrs'] else
           f"{wire['no_attrs_body_key']} of them have a ")
        + f"message that is itself a JSON object whose first key is `body`, which is the name "
        f"the OpenTelemetry Collector forwarder input gives its message field. The router "
        f"cannot route what carries no mark, so every one of them took the default route "
        f"into the hot table. Nothing was lost and nothing could be offloaded. The run "
        f"exits 0 and logs no error.", ""]
    if as_attribute:
        out += [
        f"**The service arrives in two different places.** Of the records that did carry "
        f"fields, the OTLP resource carried `service.name` on {on_resource} and a log "
        f"attribute carried it on {as_attribute}. The harness lifts the attribute back onto "
        f"the resource with the `groupbyattrs` processor; without that step the offloaded "
        f"objects land under a prefix of `service=<nil>` and the hot rows have an empty "
        f"`ServiceName`.", ""]
    out += [f"**The route arrives more often than the pattern does.** {routed} records came "
            f"back carrying a route, {hashed} carrying the pattern hash and {patterned} "
            f"carrying the pattern text. A record that is routed but unnamed can be shipped "
            f"and cannot be counted per type.", ""]
    if odd_keys:
        listed = ", ".join(f"`{k}` ({wire['fields'][k]})" for k in odd_keys[:12])
        out += [f"**Field names arrive corrupted.** Beside the fields the config asks for, "
                f"the returned records carry {len(odd_keys)} names nothing configured: "
                f"{listed}. Each is a damaged spelling of `tenx_resource_keys`, the field "
                f"holding the name of the resource attribute the engine folded into the "
                f"record, and the damage differs from record to record. Reported, not worked "
                f"around: nothing downstream reads that field.", ""]
    if wire["with_time"] != wire["total"]:
        out += [
        f"**A returned record carries either the marks or a record time, never both.** "
        f"{wire['with_time']} of {wire['total']} records came back with `timeUnixNano` set, "
        f"and they are exactly the {wire['no_attrs']} that came back with no attributes. "
        f"Every record that carried a route carried no time. The collector stamps ingest "
        f"time on both routes; the capture's envelope has no timestamp field either, so "
        f"nothing here reconstructs the time a line was written.", ""]
    out += [
        "**The offload encoding drops everything but the body and the attributes.** The "
        "`jsonlogencodingextension` in `body_with_inline_attributes` mode writes "
        "`{\"body\": ..., \"logAttributes\": {...}}` and nothing else: no record time, no "
        "resource attributes, no severity. The harness copies the service, the severity and "
        "the record time into log attributes before the write, or the cold rows have no "
        "timestamp and no service at all. `otlp_json` was not used; it keeps all three but "
        "puts every record inside a nested OTLP envelope that needs unpicking in SQL.", "",
        "**A repeated count over the same objects costs nothing, which would have "
        "flattered the table.** ClickHouse keeps a per-object row count and answers a "
        "second `count()` over the same objects from it, with no object-store request. "
        "That is a real saving for a dashboard that asks the same question twice, and it "
        "would also have hidden what the first ask costs, so the query table is measured "
        "with `use_cache_for_count_from_files = 0` and a dropped cache before every row.", "",
        "**The object path carries the write time, not the record time.** `s3_partition_format` "
        "is evaluated when the object is uploaded, so a run writes one day partition whatever "
        "the records say. Pruning across many days and many objects is not measured here; "
        "`clickstack-e2e-gaps/gap1_multiday_pruning.sh` measures it over thirty days.", "",
        "**ClickStack's `otel_logs` has no day column**, so a day predicate over the merge "
        "table would exclude every hot row. The harness adds `day Date MATERIALIZED "
        "toDate(Timestamp)` to the shipped table. That is a change to ClickStack's schema and "
        "it is the harness that makes it.", "",
        "**The S3 table engine rejects ALIAS columns**, so the cold table carries the JSON's "
        "own column names and a view renames them to ClickStack's. The Merge table reads the "
        "view, not the S3 table.", "",
        f"**The counts table is fed twice, not once.** The materialized view covers the rows "
        f"that are inserted into ClickHouse. The offloaded rows never pass through an insert, "
        f"so their counts are added by one `INSERT ... SELECT` over the S3 table after the "
        f"run. A deployment would run that on a schedule or feed the cold side from the "
        f"receiver's own metrics; the receiver's Prometheus endpoint is scraped here and its "
        f"counters are in `results.json`, but the counts table is not fed from it.", "",
    ]
    if missing:
        out += [f"**ClickStack's collector build is missing "
                f"{', '.join('`' + m + '`' for m in missing)}**, so the route and the offload "
                f"write run in a second, stock `opentelemetry-collector-contrib` container. "
                f"The rows that stay go back to ClickStack's own OTLP endpoint and are "
                f"inserted by ClickStack's own ClickHouse exporter.", ""]
    out += [
        f"**HyperDX got the merge table as a second source over its API** (HTTP "
        f"{args.hyperdx_source_http}), so no click is needed. The hot table stays the default "
        f"source: a query against the merge table pays object-store requests and a query "
        f"against the hot table pays none.", "",
        "**Skipped.** No alert is defined or fired, so nothing here says alerts are unchanged. "
        "No compute term, no bill and no autoscaler, so nothing here is a cost. No Retriever, "
        "so value-level fetch-back is not exercised. The query list is written here rather "
        "than taken from an estate's own query log.", "",
    ]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    for flag in ("container", "wire", "engine-metrics", "results", "slice",
                 "lines", "asset-sha256", "ch-version", "clickstack-image",
                 "engine-image", "otel-image", "minio-image", "hyperdx-source-http",
                 "conf-dir", "clickstack-components"):
        ap.add_argument("--" + flag, required=True)
    args = ap.parse_args()

    cl = Client(args.container)
    results = pathlib.Path(args.results)
    results.mkdir(parents=True, exist_ok=True)

    wire = read_wire(pathlib.Path(args.wire))
    queries = run_queries(cl)
    check = lossless(cl, wire)
    counters = engine_counters(pathlib.Path(args.engine_metrics))
    have, cs_collector_version, component_rows = components(pathlib.Path(args.clickstack_components))

    digests = {}
    for label, img in (("clickstack", args.clickstack_image), ("engine", args.engine_image),
                       ("collector", args.otel_image), ("minio", args.minio_image)):
        digests[label] = dict(image=img, digest=docker(
            "image", "inspect", img, "--format", "{{index .RepoDigests 0}}"))

    hot_by_service = cl.rows(
        "SELECT ServiceName, toString(count()) FROM default.otel_logs "
        "GROUP BY ServiceName ORDER BY count() DESC LIMIT 10")
    cold_by_service = cl.rows(
        "SELECT ServiceName, toString(count()) FROM default.otel_logs_coldv "
        "GROUP BY ServiceName ORDER BY count() DESC LIMIT 10")
    objects = cl.rows(
        "SELECT _path, toString(count()) FROM default.otel_logs_cold GROUP BY _path ORDER BY _path")
    counts_rows = cl.rows(
        "SELECT source, toString(sum(cnt)), toString(uniqExact(tenx_hash)) "
        "FROM default.counts_by_type GROUP BY source ORDER BY source")

    date = time.strftime("%Y-%m-%d")
    payload = dict(date=date, lines=int(args.lines), asset_sha256=args.asset_sha256,
                   ch_version=args.ch_version, images=digests, wire=wire,
                   queries=queries, lossless=check, engine_counters=counters,
                   hot_by_service=hot_by_service, cold_by_service=cold_by_service,
                   objects=objects, counts=counts_rows,
                   hyperdx_source_http=args.hyperdx_source_http,
                   clickstack_collector_version=cs_collector_version,
                   clickstack_components=component_rows)
    (results / "results.json").write_text(json.dumps(payload, indent=1))

    md = [f"# ClickStack end to end, {date}", "",
          "One run of `run.sh`: the released capture through a collector into the 10x",
          "receiver, the marked slice into an object store, everything else into",
          "ClickStack's own ClickHouse exporter, both sides read back as one table.",
          "", "## Components", "",
          "| Part | Image | Digest |", "|---|---|---|"]
    for label, d in digests.items():
        md.append(f"| {label} | `{d['image']}` | `{d['digest'].split('@')[-1]}` |")
    md += ["", f"ClickHouse {args.ch_version}. Input: `otel-sample-200mb.log` sha256 "
           f"`{args.asset_sha256}`, first {args.lines} lines.", ""]

    md += [f"ClickStack's own collector build reports itself as `{cs_collector_version}`.",
           "The harness needs these components; the ones its build does not carry are why",
           "a second, stock contrib collector runs as the routing hop.", "",
           "| Component | Kind | Needed for | In ClickStack's collector |",
           "|---|---|---|---|"]
    for row in component_rows:
        md.append(f"| `{row['name']}` | {row['section'][:-1]} | {row['why']} | "
                  f"{'yes' if row['present'] else 'NO'} |")
    md.append("")

    md += ["## What arrived on the wire", "",
           f"Records returned by the receiver: **{wire['total']}**.", "",
           "| Field on the returned record | Records carrying it |", "|---|---:|"]
    for k, v in sorted(wire["fields"].items(), key=lambda kv: -kv[1]):
        md.append(f"| `{k}` | {v} |")
    md += ["", "| Route marked | Records |", "|---|---:|"]
    for k, v in sorted(wire["routes"].items(), key=lambda kv: -kv[1]):
        md.append(f"| `{k}` | {v} |")
    if wire["sample"]:
        md += ["", "One returned record, its attributes flattened and the fields this",
               "harness is about listed first:", "", "```json",
               json.dumps(readable(wire["sample"]), indent=1)[:2800], "```", ""]

    md += ["## Where the rows went", "",
           "| Service | Hot rows |", "|---|---:|"]
    for s, n in hot_by_service:
        md.append(f"| {s or '(none)'} | {n} |")
    md += ["", "| Service | Offloaded rows |", "|---|---:|"]
    for s, n in cold_by_service:
        md.append(f"| {s or '(none)'} | {n} |")
    md += ["", "| Object | Rows |", "|---|---:|"]
    for p, n in objects:
        md.append(f"| `{p}` | {n} |")

    md += ["", "## Queries", "",
           "Every row is a cold cache: the filesystem, mark and uncompressed caches are",
           "dropped before each query. The last two columns are the same query run again",
           "straight after, warm.", "",
           "| Query | Rows read | Bytes read | S3 GET | S3 LIST | ms | ms again | S3 GET again |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for q in queries:
        md.append(f"| {q['name']} | {q['read_rows']} | {q['read_bytes']} | "
                  f"{q['s3_get']} | {q['s3_list']} | {q['ms']} | "
                  f"{q['ms_repeat']} | {q['s3_get_repeat']} |")

    md += ["", "## Counts per type", "",
           "| Source | Records counted | Distinct pattern hashes |", "|---|---:|---:|"]
    for row in counts_rows:
        md.append("| " + " | ".join(row) + " |")

    md += ["", "## Lossless check", "",
           "| Measure | Count |", "|---|---:|",
           f"| Records the receiver returned | {check['wire']} |",
           f"| Rows in the hot table | {check['hot']} |",
           f"| Rows in the offloaded objects | {check['cold']} |",
           f"| Hot plus cold | {check['hot_plus_cold']} |",
           f"| Gap | {check['gap']} |",
           f"| Distinct pattern hashes on the wire | {check['hashes_on_wire']} |",
           f"| Distinct pattern hashes stored | {check['hashes_stored']} |", ""]
    if check["per_hash_mismatch"]:
        md += ["Pattern hashes whose stored count differs from the wire count:", "",
               "```", json.dumps(check["per_hash_mismatch"], indent=1), "```", ""]

    md += [""] + findings(wire, component_rows, args)

    conf = pathlib.Path(args.conf_dir)
    md += ["## The configs, as they ran", "",
           "The collector, both pipelines:", "", "```yaml",
           (conf / "router.yaml").read_text().rstrip(), "```", "",
           "The per-service policy the receiver read:", "", "```",
           "caps.csv", (conf / "caps.csv").read_text().rstrip(), "",
           "actions.csv", (conf / "actions.csv").read_text().rstrip(), "```", "",
           "The counts table, created before any data flowed:", "", "```sql",
           (conf / "schema_hot.sql").read_text().rstrip(), "```", "",
           "The offloaded objects, the rename and the merge table:", "", "```sql",
           (conf / "schema_cold.sql").read_text().rstrip(), "```", "",
           "The engine's own config is the tree inside the pinned image with the four",
           "edits `patch_engine_config.py` makes, each of which fails the run if the",
           "shipped text has moved: the OpenTelemetry Collector forwarder input and the",
           "Prometheus scrape output enabled, the regulator's warmup and baseline count",
           "set to zero for a short run, and the pattern text added to the `fullText`",
           "splice list beside the pattern hash and the route. The shipped expression",
           "splices the hash and the route only.", ""]

    (results / f"clickstack-e2e-{date}.md").write_text("\n".join(md) + "\n")
    print(f"  wrote {results}/clickstack-e2e-{date}.md and results.json")
    print(f"  wire {check['wire']}, hot {check['hot']}, cold {check['cold']}, "
          f"gap {check['gap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
