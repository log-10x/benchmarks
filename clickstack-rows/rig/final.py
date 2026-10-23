#!/usr/bin/env python3
"""Criteria 3, 4, 5 and 7 of ROWS_RUN_METHOD.md, read while the containers are up.

  final.py <results-dir> <clickstack-container>   -> markdown on stdout

3. Hot plus cold equals the wire, per hash for the ten largest moved statements.
4. A count of each of those statements through the Merge table equals the local count.
5. Delivery: lines the pacers wrote (by `seq`) against records returned; returned
   records against the table plus the bucket.
7. The injected service (inventory) is held from its first window by the `*` row.
"""
import collections
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "clickstack-e2e"))
from report import read_wire  # noqa: E402


def ch(container: str, sql: str) -> str:
    r = subprocess.run(["docker", "exec", container, "clickhouse-client", "--query", sql], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else f"ERR {r.stderr.strip()[:160]}"


def num(container: str, sql: str) -> int:
    """A count, or -1 when the query fails (so one failure is visible and does not stop the scoring)."""
    v = ch(container, sql)
    try:
        return int(v or 0)
    except ValueError:
        return -1


def main() -> int:
    res, cs = sys.argv[1], sys.argv[2]
    wire = read_wire(pathlib.Path(res, "wire", "returned.json"))
    hot = num(cs, "SELECT count() FROM default.otel_logs")
    cold = num(cs, "SELECT count() FROM default.otel_logs_coldv")
    out = ["# Rows run, final criteria", ""]
    out.append(f"Wire: {wire['total']} returned, by route {json.dumps(wire['routes'], sort_keys=True)}. Hot {hot}, cold {cold}, hot plus cold {hot + cold}.")
    ok5b = hot + cold == wire["total"]
    out.append(f"\n## 5. Delivery: returned records in the table or the bucket: {'PASS' if ok5b else 'FAIL'} (totals; a loss and a duplicate cancel in it)")
    # lines written by the pacers: the highest seq per writer is in the feed; count non-blank lines of the feed
    feed = os.path.join(res, "data", "feed.log")
    try:
        with open(feed, "rb") as fh:
            written = sum(1 for l in fh if l.strip())
    except OSError:
        written = -1
    out.append(f"Lines the pacers wrote: {written}; records returned: {wire['total']}; {'PASS' if written == wire['total'] else 'FAIL'} on lines in equals records back (the Receiver folds multi-line events, so a difference is read against the fold count, not as loss).")

    # top ten moved statements by hash on the wire (route offload)
    per_hash_offload: collections.Counter = collections.Counter()
    with open(os.path.join(res, "wire", "returned.json")) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            for rl in doc.get("resourceLogs", []):
                for sl in rl.get("scopeLogs", []):
                    for lr in sl.get("logRecords", []):
                        attrs = {a["key"]: a["value"] for a in lr.get("attributes", [])}
                        if attrs.get("routeState", {}).get("stringValue") == "offload":
                            per_hash_offload[attrs.get("tenx_hash", {}).get("stringValue", "")] += 1
    top = [h for h, _ in per_hash_offload.most_common(10) if h]
    out.append("\n## 3 and 4. The ten largest moved statements: wire against hot plus cold, and the Merge table against the local count\n")
    out.append("| hash | wire total | hot | cold (S3 view) | hot + cold | merge table | 3 | 4 |\n|---|---:|---:|---:|---:|---:|---|---|")
    ok3 = ok4 = True
    for h in top:
        w = wire["per_hash"].get(h, 0)
        ht = num(cs, f"SELECT count() FROM default.otel_logs WHERE LogAttributes['tenx_hash'] = '{h}'")
        cd = num(cs, f"SELECT count() FROM default.otel_logs_coldv WHERE LogAttributes['tenx_hash'] = '{h}'")
        mg = num(cs, f"SELECT count() FROM default.otel_logs_all WHERE LogAttributes['tenx_hash'] = '{h}'")
        c3 = ht + cd == w
        c4 = mg == w
        ok3 &= c3
        ok4 &= c4
        out.append(f"| {h} | {w} | {ht} | {cd} | {ht + cd} | {mg} | {'ok' if c3 else 'MISS'} | {'ok' if c4 else 'MISS'} |")
    out.append(f"\nCriterion 3: {'PASS' if ok3 else 'FAIL'}. Criterion 4: {'PASS' if ok4 else 'FAIL'}.")

    # 7. inventory held from its first window by the * row: hot rows per 4-minute window against the star total
    out.append("\n## 7. The injected service\n")
    rows = ch(cs, "SELECT intDiv(toUnixTimestamp(ins), 240) * 240 AS w, count() FROM default.otel_logs WHERE ServiceName = 'inventory' GROUP BY w ORDER BY w FORMAT TSV")
    inv_cold = num(cs, "SELECT count() FROM default.otel_logs_coldv WHERE ServiceName = 'inventory'")
    out.append(f"inventory rows in the bucket: {inv_cold}. Hot rows per 4-minute window (the `*` total of the applied run in force bounds each; read it from that run's totals.csv):\n")
    out.append("| window | hot rows |\n|---|---:|")
    for l in rows.splitlines():
        if l and not l.startswith("ERR"):
            w, n = l.split("\t")
            out.append(f"| {w} | {n} |")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
