#!/usr/bin/env python3
"""Create an alert in HyperDX proper, over its API, on the count of one type.

Every request is made from inside the ClickStack container against its own API
on port 8000, with the session cookie the harness already holds, and every step
records the HTTP status and the first part of the response body. Nothing here
asserts: if the API refuses a shape, the refusal is the result.

Three alerts are attempted, all with the same threshold and interval, each over
its own saved search and source:

  before  the copy of the hot table as it was with nothing offloaded
  after   the hot table after the offload
  merge   the Merge table over hot plus cold

Whether an alert would fire is NOT read from HyperDX's own evaluation loop. An
alert evaluates the window its interval names, and by the time the loop runs,
the replayed capture's rows are older than any interval short enough to wait
for. The firing condition is therefore evaluated against the count each surface
returns over the run's own window, and this file says so where it reports it.

  hyperdx_alert.py --container <name> --hash <tenx_hash> --out alert.json
"""
import argparse
import json
import pathlib
import subprocess


def api(container: str, method: str, path: str, body: dict | None = None) -> dict:
    cmd = ["docker", "exec", container, "curl", "-s", "-o", "/tmp/resp.json",
           "-w", "%{http_code}", "-b", "/tmp/ck.txt", "-X", method,
           f"http://localhost:8000{path}"]
    if body is not None:
        blob = json.dumps(body)
        subprocess.run(["docker", "exec", "-i", container, "sh", "-c",
                        "cat > /tmp/body.json"], input=blob, text=True, check=False)
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@/tmp/body.json"]
    code = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    raw = subprocess.run(["docker", "exec", container, "cat", "/tmp/resp.json"],
                         capture_output=True, text=True).stdout
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    return {"method": method, "path": path, "status": code,
            "body": (raw[:600] if parsed is None else None), "json": parsed}


def sql_count(container: str, sql: str) -> int:
    out = subprocess.run(["docker", "exec", "-i", container, "clickhouse-client",
                          "--format", "TSVRaw", "--query", sql],
                         capture_output=True, text=True)
    try:
        return int(out.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--hash", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", default="5m")
    args = ap.parse_args()
    c = args.container
    steps = []
    result = {"steps": steps}

    # The counts the alert's condition is judged against, over the run's window.
    counts = {
        "before, hot table": sql_count(c, f"SELECT count() FROM gaps.hot_before "
                                          f"WHERE LogAttributes['tenx_hash'] = '{args.hash}'"),
        "after, hot table": sql_count(c, f"SELECT count() FROM default.otel_logs "
                                         f"WHERE LogAttributes['tenx_hash'] = '{args.hash}'"),
        "after, merge table": sql_count(c, f"SELECT count() FROM default.otel_logs_all "
                                           f"WHERE LogAttributes['tenx_hash'] = '{args.hash}'"),
        "after, counts table": sql_count(c, f"SELECT sum(cnt) FROM default.counts_by_type "
                                            f"WHERE tenx_hash = '{args.hash}'"),
    }
    threshold = max(1, counts["before, hot table"] // 2)
    result["counts"] = counts
    result["threshold"] = threshold
    result["threshold_rule"] = ("fires when the count of the type is above half what it was "
                                "before the offload")
    result["would_fire"] = {k: (v > threshold) for k, v in counts.items()}

    # The connection every source hangs off.
    conns = api(c, "GET", "/connections")
    steps.append(conns)
    conn_id = ""
    if isinstance(conns.get("json"), list) and conns["json"]:
        conn_id = conns["json"][0].get("_id", "") or conns["json"][0].get("id", "")
    elif isinstance(conns.get("json"), dict):
        data = conns["json"].get("data") or []
        conn_id = (data[0].get("_id") or data[0].get("id")) if data else ""
    result["connection_id"] = conn_id

    def make_source(name: str, table: str) -> str:
        body = {"kind": "log", "name": name, "connection": conn_id,
                "from": {"databaseName": "default" if "." not in table else table.split(".")[0],
                         "tableName": table.split(".")[-1]},
                "timestampValueExpression": "Timestamp",
                "displayedTimestampValueExpression": "Timestamp",
                "implicitColumnExpression": "Body",
                "serviceNameExpression": "ServiceName",
                "bodyExpression": "Body",
                "eventAttributesExpression": "LogAttributes",
                "defaultTableSelectExpression": "Timestamp,ServiceName,Body"}
        r = api(c, "POST", "/sources", body)
        steps.append(r)
        j = r.get("json")
        j = j if isinstance(j, dict) else {}
        return j.get("_id") or j.get("id") or ""

    # An alert needs a notification channel, and the channel needs a webhook that
    # exists: without `channel.webhookId` the API refuses the alert with a zod
    # error naming that field. The URL has to resolve to a public address, which
    # the API checks and refuses otherwise, so this one points at a documentation
    # domain. Nothing is ever delivered to it: what is being measured is whether
    # the API takes the alert.
    hook = api(c, "POST", "/webhooks",
               {"name": "gap5 sink", "service": "generic",
                "url": "https://example.com/gap5-sink",
                "description": "gap 5, never delivered"})
    steps.append(hook)
    hj = hook.get("json")
    hj = hj if isinstance(hj, dict) else {}
    webhook_id = hj.get("_id") or hj.get("id") or (hj.get("data") or {}).get("_id") or ""
    if not webhook_id:
        listing = api(c, "GET", "/webhooks?service=generic")
        steps.append(listing)
        lj = listing.get("json")
        rows = lj.get("data") if isinstance(lj, dict) else (lj if isinstance(lj, list) else [])
        for row in rows or []:
            if isinstance(row, dict) and row.get("name") == "gap5 sink":
                webhook_id = row.get("_id") or row.get("id") or ""
                break
    result["webhook_status"] = hook["status"]
    result["webhook_id"] = webhook_id

    surfaces = {
        "before": ("Gap5 before, hot only", "gaps.hot_before"),
        "after": ("Gap5 after, hot only", "default.otel_logs"),
        "merge": ("Gap5 after, hot plus cold", "default.otel_logs_all"),
    }
    result["alerts"] = {}
    where = f"LogAttributes['tenx_hash'] = '{args.hash}'"
    for key, (name, table) in surfaces.items():
        entry = {"table": table}
        source_id = make_source(name, table)
        entry["source_id"] = source_id
        if not source_id:
            entry["stopped_at"] = "source"
            result["alerts"][key] = entry
            continue
        search = api(c, "POST", "/saved-search",
                     {"name": f"gap5 {key} count of one type", "select": "",
                      "where": where, "whereLanguage": "sql", "source": source_id,
                      "orderBy": "", "tags": []})
        steps.append(search)
        entry["saved_search_status"] = search["status"]
        j = search.get("json")
        j = j if isinstance(j, dict) else {}
        search_id = j.get("_id") or j.get("id") or ""
        entry["saved_search_id"] = search_id
        if not search_id:
            entry["stopped_at"] = "saved-search"
            entry["saved_search_error"] = search.get("body") or json.dumps(j)[:400]
            result["alerts"][key] = entry
            continue
        alert_body = {"source": "saved_search", "savedSearchId": search_id,
                      "interval": args.interval, "threshold": threshold,
                      "thresholdType": "above",
                      "name": f"gap5 {key}: count of one offloaded type",
                      "channel": {"type": "webhook", "webhookId": webhook_id}}
        alert = api(c, "POST", "/alerts", alert_body)
        steps.append(alert)
        entry["alert_status"] = alert["status"]
        aj = alert.get("json")
        aj = aj if isinstance(aj, dict) else {}
        entry["alert_id"] = aj.get("_id") or aj.get("id") or ""
        if not entry["alert_id"]:
            entry["alert_error"] = (alert.get("body")
                                    or json.dumps(alert.get("json"))[:400])
        result["alerts"][key] = entry

    listing = api(c, "GET", "/alerts")
    steps.append(listing)
    result["alerts_listed"] = len((listing.get("json") or {}).get("data", [])) \
        if isinstance(listing.get("json"), dict) else None

    pathlib.Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print("  counts:", counts)
    for k, v in result["alerts"].items():
        print(f"  {k}: source {v.get('source_id','')[:8]} saved-search "
              f"{v.get('saved_search_status','-')} alert {v.get('alert_status','-')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
