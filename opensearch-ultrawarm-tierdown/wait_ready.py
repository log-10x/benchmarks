#!/usr/bin/env python3
"""Wait for the domain to go Active, then for UltraWarm to be usable, keeping every poll.

Phase A, every 60 s: describe-domain to results/raw/status-polls.jsonl. Active is
the first poll with Processing false and an Endpoint; event domain_active.
Gives up 90 min after the create call (event active_timeout, exit 2).

Phase B, every 60 s: GET _cat/nodes, GET _cat/nodeattrs, GET _warm, and a
canary migration (index uw-canary, one doc, outside the tenx-* patterns):
POST _ultrawarm/migration/uw-canary/_warm until accepted, then its _status.
Each reading goes through osreq (results/raw/requests.jsonl). One event the first
time each happens: warm_nodes_listed (a node with box_type warm in nodeattrs),
warm_api_ok (GET _warm 200), warm_migration_accepted, warm_usable (uw-canary
listed by GET _warm). Gives up 6 h after Active (event warm_timeout, exit 3).
"""
import calendar
import json
import os
import sys
import time

import boto3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osreq  # noqa: E402

RAW = os.path.join(osreq.HERE, "results", "raw")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def event(name, **kw):
    line = {"t": now(), "event": name, **kw}
    with open(os.path.join(RAW, "events.jsonl"), "a") as fh:
        fh.write(json.dumps(line) + "\n")
    print(json.dumps(line), flush=True)


def phase_a(created):
    es = osreq.session_().client("opensearch", region_name=osreq.REGION)
    while True:
        t = now()
        d = es.describe_domain(DomainName=osreq.DOMAIN)["DomainStatus"]
        with open(os.path.join(RAW, "status-polls.jsonl"), "a") as fh:
            fh.write(json.dumps({"t": t, "status": d}, default=str) + "\n")
        if not d.get("Processing") and d.get("Endpoint"):
            with open(os.path.join(osreq.HERE, "results", "domain.json"), "w") as fh:
                json.dump({"DomainStatus": d}, fh, indent=1, default=str)
            event("domain_active", endpoint_set=True, processing_status=d.get("DomainProcessingStatus"))
            return time.time()
        if time.time() - created > 90 * 60:
            event("active_timeout", processing=d.get("Processing"), processing_status=d.get("DomainProcessingStatus"))
            sys.exit(2)
        time.sleep(60)


def phase_b(active):
    seen = set()

    def first(name, **kw):
        if name not in seen:
            seen.add(name)
            event(name, **kw)

    canary = False
    accepted = False
    while True:
        try:
            s, nodes = osreq.request("GET", "_cat/nodes?format=json&h=name,node.role,ip", tag="wait:nodes")
            if s == 200 and "first_api_200" not in seen:
                first("first_api_200", nodes=len(nodes))
            s, attrs = osreq.request("GET", "_cat/nodeattrs?format=json", tag="wait:nodeattrs")
            if s == 200 and any(a.get("attr") == "box_type" and a.get("value") == "warm" for a in attrs):
                first("warm_nodes_listed", warm=sum(1 for a in attrs if a.get("attr") == "box_type" and a.get("value") == "warm"))
            s, warm = osreq.request("GET", "_warm", tag="wait:warm")
            if s == 200:
                first("warm_api_ok")
            if not canary:
                s1, _ = osreq.request("PUT", "uw-canary", json.dumps({"settings": {"number_of_shards": 1, "number_of_replicas": 0}}).encode(), tag="wait:canary-create")
                s2, _ = osreq.request("PUT", "uw-canary/_doc/1?refresh=true", json.dumps({"@timestamp": now(), "canary": True}).encode(), tag="wait:canary-doc")
                canary = s1 in (200, 400) and s2 in (200, 201)
            if canary and not accepted:
                s, _ = osreq.request("POST", "_ultrawarm/migration/uw-canary/_warm", tag="wait:canary-migrate")
                if s == 200:
                    accepted = True
                    first("warm_migration_accepted")
            if accepted:
                osreq.request("GET", "_ultrawarm/migration/uw-canary/_status", tag="wait:canary-status")
                s, warm = osreq.request("GET", "_warm", tag="wait:warm-after")
                if s == 200 and isinstance(warm, dict) and "uw-canary" in warm:
                    first("warm_usable", hours_after_active=round((time.time() - active) / 3600, 3))
                    return
        except Exception as e:  # a reading that fails is kept as read
            event("poll_error", error=repr(e)[:300])
        if time.time() - active > 6 * 3600:
            event("warm_timeout", seen=sorted(seen))
            sys.exit(3)
        time.sleep(60)


def main() -> int:
    created = None
    with open(os.path.join(RAW, "events.jsonl")) as fh:
        for line in fh:
            e = json.loads(line)
            if e["event"] == "create_domain_call":
                created = calendar.timegm(time.strptime(e["t"], "%Y-%m-%dT%H:%M:%SZ"))
    active = phase_a(created)
    phase_b(active)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
