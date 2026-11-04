#!/usr/bin/env python3
"""Watch the tier-down index from bulk load to warm, one round a minute.

Each round, through osreq (results/raw/requests.jsonl), tag watch:<n>:
  _cat/indices (one listing call for every index: store size per index),
  _cat/shards (which node holds each shard), GET _hot, GET _warm,
  _plugins/_ism/explain/tenx-*, _ultrawarm/migration/_status?v,
  _ultrawarm/migration/tenx-tierdown-000001/_status.
A summary line per round goes to results/raw/watch.jsonl. Events (first time each):
  rollover_seen       tenx-tierdown-000002 exists / explain shows rolled_over
  ism_state_warm      explain shows tenx-tierdown-000001 in state warm
  ism_warm_migration  explain shows action warm_migration (its start_time kept)
  migration_state:<S> each distinct _status state of the index
  in_warm             GET _warm lists tenx-tierdown-000001
Stops two rounds after in_warm, or after 3 h (event watch_timeout).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osreq  # noqa: E402

RAW = os.path.join(osreq.HERE, "results", "raw")
IDX = "tenx-tierdown-000001"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


seen = set()


def event(name, **kw):
    if name in seen:
        return
    seen.add(name)
    line = {"t": now(), "event": name, **kw}
    with open(os.path.join(RAW, "events.jsonl"), "a") as fh:
        fh.write(json.dumps(line) + "\n")
    print(json.dumps(line), flush=True)


def main() -> int:
    t0 = time.time()
    n = 0
    after = None
    mstate = None
    while True:
        n += 1
        tag = f"watch:{n}"
        try:
            _, ind = osreq.request("GET", "_cat/indices?format=json&bytes=b&h=index,health,pri,rep,docs.count,store.size,pri.store.size", tag=tag + ":indices")
            _, shards = osreq.request("GET", "_cat/shards?format=json&bytes=b&h=index,shard,prirep,state,docs,store,node", tag=tag + ":shards")
            _, hot = osreq.request("GET", "_hot", tag=tag + ":hot")
            _, warm = osreq.request("GET", "_warm", tag=tag + ":warm")
            _, ex = osreq.request("GET", "_plugins/_ism/explain/tenx-*", tag=tag + ":explain")
            _, allm = osreq.request("GET", "_ultrawarm/migration/_status?v", tag=tag + ":migrations")
            ms, mig = osreq.request("GET", f"_ultrawarm/migration/{IDX}/_status", tag=tag + ":migration")
            tenx = {i["index"]: {k: i[k] for k in ("docs.count", "store.size", "pri.store.size")} for i in ind if i["index"].startswith("tenx-")}
            e = ex.get(IDX, {}) if isinstance(ex, dict) else {}
            state = (e.get("state") or {}).get("name")
            action = (e.get("action") or {}).get("name")
            mstate = (mig.get("migration_status") or {}).get("state") if ms == 200 and isinstance(mig, dict) else None
            in_hot = isinstance(hot, dict) and IDX in hot
            in_warm = isinstance(warm, dict) and IDX in warm
            summary = {"t": now(), "round": n, "tenx": tenx, "ism_state": state, "ism_action": action,
                       "ism_action_start": (e.get("action") or {}).get("start_time"),
                       "rolled_over": (e.get("info") or {}).get("message"), "migration_state": mstate,
                       "in_hot": in_hot, "in_warm": in_warm,
                       "nodes": {s["index"]: s["node"] for s in shards if s["index"].startswith("tenx-")}}
            with open(os.path.join(RAW, "watch.jsonl"), "a") as fh:
                fh.write(json.dumps(summary) + "\n")
            print(json.dumps(summary), flush=True)
            if "tenx-tierdown-000002" in tenx or e.get("rolled_over"):
                event("rollover_seen", info=e.get("info"))
            if state == "warm":
                event("ism_state_warm", state_start=(e.get("state") or {}).get("start_time"))
            if action == "warm_migration":
                event("ism_warm_migration", action_start=(e.get("action") or {}).get("start_time"), info=e.get("info"))
            if mstate:
                event(f"migration_state:{mstate}")
            if in_warm:
                event("in_warm", store=tenx.get(IDX))
                after = n if after is None else after
            if after is not None and n >= after + 2:
                return 0
        except Exception as exc:  # a failed reading is kept as read
            with open(os.path.join(RAW, "events.jsonl"), "a") as fh:
                fh.write(json.dumps({"t": now(), "event": "watch_error", "error": repr(exc)[:300]}) + "\n")
            print("watch_error", repr(exc)[:300], flush=True)
        if time.time() - t0 > 3 * 3600:
            event("watch_timeout")
            return 3
        time.sleep(60 if mstate is None else 15)


if __name__ == "__main__":
    raise SystemExit(main())
