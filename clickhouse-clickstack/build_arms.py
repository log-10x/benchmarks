#!/usr/bin/env python3
"""Map the released OTel-demo capture into the ClickStack `otel_logs` schema, twice.

The capture is container stdout in a Fluentd envelope: one JSON record per line,
the container's message under `log`, its Kubernetes and Docker metadata around it.
ClickStack's schema wants typed columns and two attribute maps, so every field has
to be placed by hand. This script does that placement once and writes the same
mapping for every arm, so the only column that differs between arms is `Body`.

Three arms are written:

  native         one row per raw line, Body = that line's message.
                 197,430 rows. This is the baseline a collector produces.

  compact        one row per 10x compact event, Body = the compact event
                 (`~<templateHash>,<values>`). Fewer rows, because the engine
                 folds a multi-line event (a stack trace) into one event.

  native_folded  one row per 10x compact event, Body = the ORIGINAL text of that
                 same event, its lines joined by newline. Same row count and the
                 same attribute values as `compact`, so `compact` against
                 `native_folded` is the templating contribution alone, with the
                 row-count change held constant.

`native` against `compact` is the deployment-level comparison and carries both
effects. `native` against `native_folded` is the folding alone. The results file
reports all three; none of them is a ratio with a hidden row-count change in it.

Alignment
---------
A compact event covers K consecutive raw lines. K is recovered exactly from the
event's own template: the engine joins the folded lines with a newline, so the
template carries K-1 of them. The script checks two invariants on every record
and refuses to write anything if either fails:

  1. the reconstructed line count equals the number of lines in the capture;
  2. the envelope of each compact record (every field except `log`) is
     byte-identical to the envelope of the first raw line it covers.

Timestamp
---------
The Fluentd envelope carries no timestamp field; the time is inside the message
text. Rather than write a second timestamp parser, this script reads the one the
engine already produced: for a template with a timestamp slot, the compact event
carries that slot's value as an epoch integer. Scale is taken from the digit
count (10 seconds, 13 milliseconds, 16 microseconds, 19 nanoseconds) and the
result is rejected if it falls outside the capture window.

84.6% of compact events carry a usable timestamp. For the rest the last valid
timestamp seen for that container is carried forward, and before a container has
one, the earliest valid timestamp in the capture is used. Every raw line covered
by a compact event gets that event's timestamp, so `Timestamp` is identical
across all three arms and the ORDER BY sees the same data in each.
"""

import argparse
import datetime
import json
import pathlib
import re
import sys

SLOT = re.compile(r"\$\([^)]*\)|\$")

# The capture is from 2025-10-01. Anything outside this window is a slot the
# engine read as a timestamp that is not one (a lone letter, or a time-only
# format resolved against today's date), and is treated as absent.
WINDOW_LO_NS = 1_726_000_000 * 1_000_000_000  # 2024-09-11
WINDOW_HI_NS = 1_760_000_000 * 1_000_000_000  # 2025-10-09

SCALE_BY_DIGITS = {10: 1_000_000_000, 13: 1_000_000, 16: 1_000, 19: 1}


def epoch_ns(value: str):
    """Engine slot value to nanoseconds, or None if it is not a timestamp."""
    if not value or not value.isdigit():
        return None
    scale = SCALE_BY_DIGITS.get(len(value))
    if scale is None:
        return None
    ns = int(value) * scale
    return ns if WINDOW_LO_NS <= ns <= WINDOW_HI_NS else None


def as_datetime64(ns: int) -> str:
    """Nanoseconds to the literal DateTime64(9) accepts exactly.

    A bare integer in JSONEachRow is read as seconds with a fractional part and
    overflows, so the value is written as a UTC datetime string with nine
    fractional digits, which round-trips to the same nanosecond.
    """
    whole, fraction = divmod(int(ns), 1_000_000_000)
    stamp = datetime.datetime.fromtimestamp(whole, datetime.timezone.utc)
    return f"{stamp.strftime('%Y-%m-%d %H:%M:%S')}.{fraction:09d}"


def load_templates(path: pathlib.Path) -> dict:
    templates = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            template = record["template"]
            templates[record["templateHash"]] = {
                "text": template,
                "lines": template.count("\n") + 1,
                # index of the first `$(...)` slot, which is where the engine put
                # the timestamp it parsed out of the message
                "ts_slot": next(
                    (i for i, s in enumerate(SLOT.findall(template))
                     if s.startswith("$(")),
                    None,
                ),
            }
    return templates


def split_encoded(log: str):
    """`~<hash>,<v1>,<v2>...` to (hash, values). Returns (None, []) if not encoded."""
    if not log.startswith("~"):
        return None, []
    comma = log.find(",")
    if comma < 0:
        return log[1:], []
    return log[1:comma], log[comma + 1:].split(",")


def envelope(record: dict) -> str:
    """Every field except `log`, canonically serialised, for the alignment check."""
    return json.dumps({k: v for k, v in record.items() if k != "log"},
                      sort_keys=True, separators=(",", ":"))


def attributes(record: dict):
    """Place the Fluentd envelope into ClickStack's typed column and its two maps.

    OpenTelemetry semantic-convention names are used wherever one exists, because
    that is what the ClickStack schema materialises (`__hdx_materialized_k8s.*`
    reads `ResourceAttributes['k8s.container.name']` and so on).

    `tenx_tag` is dropped: this project injects it, it is not part of what a
    cluster produces, and it is 13.59% of the capture's bytes. Dropping it in
    every arm keeps it out of both sides of the comparison.

    `stream` is a per-record property, so it goes to LogAttributes; everything
    identifying the container it came from is a resource and goes to
    ResourceAttributes.
    """
    kubernetes = record.get("kubernetes") or {}
    docker = record.get("docker") or {}
    labels = kubernetes.get("labels") or {}

    resource = {
        "k8s.container.name": kubernetes.get("container_name", ""),
        "k8s.namespace.name": kubernetes.get("namespace_name", ""),
        "k8s.pod.name": kubernetes.get("pod_name", ""),
        "k8s.pod.uid": kubernetes.get("pod_id", ""),
        "k8s.pod.ip": kubernetes.get("pod_ip", ""),
        "k8s.node.name": kubernetes.get("host", ""),
        "container.id": docker.get("container_id", ""),
        "container.image.name": kubernetes.get("container_image", ""),
        "container.image.id": kubernetes.get("container_image_id", ""),
    }
    for key, value in labels.items():
        resource["k8s.pod.label." + key] = value
    resource = {k: v for k, v in resource.items() if v != ""}

    log_attributes = {}
    if record.get("stream"):
        log_attributes["log.iostream"] = record["stream"]

    return kubernetes.get("container_name", ""), resource, log_attributes


def row(timestamp_ns, record, body):
    """One JSONEachRow row. Columns absent from the capture are left empty.

    The capture has no severity, no trace id, no span id and no scope: a Fluentd
    tail of container stdout carries none of them. They are written empty in
    every arm rather than invented, so they contribute the same bytes on both
    sides.
    """
    service, resource, log_attributes = attributes(record)
    return {
        "Timestamp": as_datetime64(timestamp_ns),
        "TraceId": "",
        "SpanId": "",
        "TraceFlags": 0,
        "SeverityText": "",
        "SeverityNumber": 0,
        "ServiceName": service,
        "Body": body,
        "ResourceSchemaUrl": "",
        "ResourceAttributes": resource,
        "ScopeSchemaUrl": "",
        "ScopeName": "",
        "ScopeVersion": "",
        "ScopeAttributes": {},
        "LogAttributes": log_attributes,
        "EventName": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", required=True, help="otel-sample-200mb.log")
    parser.add_argument("--encoded", required=True, help="INNER encoded.log")
    parser.add_argument("--templates", required=True, help="INNER templates.json")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = load_templates(pathlib.Path(args.templates))

    raw = [json.loads(line) for line in open(args.raw, encoding="utf-8")]
    encoded = [json.loads(line) for line in open(args.encoded, encoding="utf-8")]

    # ---- pass 1: fold sizes, alignment check, and the timestamp per event ----
    spans, stamps = [], []
    cursor = 0
    with_timestamp = 0
    for record in encoded:
        template_hash, values = split_encoded(record.get("log", ""))
        template = templates.get(template_hash) if template_hash else None
        lines = template["lines"] if template else 1

        if envelope(record) != envelope(raw[cursor]):
            print(f"alignment broke at compact record {len(spans)}, raw line {cursor}: "
                  "the envelope of the compact record is not the envelope of the raw "
                  "line it should cover", file=sys.stderr)
            return 1

        stamp = None
        if template and template["ts_slot"] is not None:
            slot = template["ts_slot"]
            if slot < len(values):
                stamp = epoch_ns(values[slot])
        if stamp is not None:
            with_timestamp += 1
        spans.append((cursor, lines))
        stamps.append(stamp)
        cursor += lines

    if cursor != len(raw):
        print(f"reconstructed {cursor} raw lines from the compact events, but the "
              f"capture has {len(raw)}", file=sys.stderr)
        return 1

    # ---- fill the gaps: carry forward per container, seed with the earliest ----
    earliest = min((s for s in stamps if s is not None), default=0)
    last_per_service = {}
    for i, record in enumerate(encoded):
        service = (record.get("kubernetes") or {}).get("container_name", "")
        if stamps[i] is None:
            stamps[i] = last_per_service.get(service, earliest)
        else:
            last_per_service[service] = stamps[i]

    # ------------------------------- write ----------------------------------
    counts = {"native": 0, "compact": 0, "native_folded": 0}
    files = {name: open(out_dir / f"{name}.jsonl", "w", encoding="utf-8")
             for name in counts}
    for i, record in enumerate(encoded):
        start, lines = spans[i]
        stamp = stamps[i]

        files["compact"].write(json.dumps(row(stamp, record, record["log"])) + "\n")
        counts["compact"] += 1

        original = "\n".join(raw[j].get("log") or "" for j in range(start, start + lines))
        files["native_folded"].write(json.dumps(row(stamp, record, original)) + "\n")
        counts["native_folded"] += 1

        for j in range(start, start + lines):
            files["native"].write(
                json.dumps(row(stamp, raw[j], raw[j].get("log") or "")) + "\n")
            counts["native"] += 1
    for handle in files.values():
        handle.close()

    manifest = {
        "raw_lines": len(raw),
        "compact_events": len(encoded),
        "templates": len(templates),
        "rows": counts,
        "compact_events_with_a_parsed_timestamp": with_timestamp,
        "compact_events_timestamp_carried_forward": len(encoded) - with_timestamp,
        "earliest_timestamp_ns": earliest,
        "latest_timestamp_ns": max(stamps),
        "body_bytes": {
            name: sum(len(json.loads(line)["Body"].encode())
                      for line in open(out_dir / f"{name}.jsonl", encoding="utf-8"))
            for name in counts
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
