#!/usr/bin/env python3
"""The searches that decide the run, against whatever tier the indices are on now.

  proof.py <label>        writes results/proof-<label>.json

1. One term query per tenx_hash sent, in a single _msearch: held hashes against
   tenx-tierdown-000001, kept hashes against tenx-app-000001. Hit count per hash,
   and the returned _source compared field by field to the document in data/bulk.ndjson.
2. routeState terms aggregation on each of the two indices.
3. The index pattern: read the saved object tenx-all, then _search on the exact
   title it stores (size 0, aggregations by _index and routeState); the Dashboards
   fields-for-wildcard route on that title; Dashboards' internal search route
   with the title as index. The last two are reported as read.
4. GET _hot and GET _warm, so the result says which tier the searches hit.
"""
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osreq  # noqa: E402

HELD_IDX, KEPT_IDX = "tenx-tierdown-000001", "tenx-app-000001"


def main() -> int:
    label = sys.argv[1]
    tag = f"proof:{label}"
    docs = {}
    with open(os.path.join(osreq.HERE, "data", "bulk.ndjson")) as fh:
        lines = fh.read().splitlines()
    for meta, doc in zip(lines[0::2], lines[1::2]):
        d = json.loads(doc)
        docs[d["tenx_hash"]] = d
    held = [h for h, d in docs.items() if d["routeState"] == "offload"]
    kept = [h for h, d in docs.items() if d["routeState"] == "pass"]

    out = {"label": label}
    _, out["hot"] = osreq.request("GET", "_hot", tag=tag + ":hot")
    _, out["warm"] = osreq.request("GET", "_warm", tag=tag + ":warm")
    out["hot"], out["warm"] = sorted(out["hot"]), sorted(out["warm"])

    for name, idx, hashes in (("held", HELD_IDX, held), ("kept", KEPT_IDX, kept)):
        body = "".join(json.dumps({"index": idx}) + "\n" + json.dumps({"query": {"term": {"tenx_hash": h}}, "size": 2, "track_total_hits": True}) + "\n" for h in hashes)
        s, r = osreq.request("POST", "_msearch", body.encode(), ndjson=True, tag=f"{tag}:msearch-{name}")
        per = []
        for h, resp in zip(hashes, r.get("responses", [])):
            hits = resp.get("hits", {})
            total = (hits.get("total") or {}).get("value")
            src = hits["hits"][0]["_source"] if hits.get("hits") else None
            per.append({"tenx_hash": h, "hits": total, "source_intact": src == docs[h], "error": resp.get("error")})
        out[name] = {
            "index": idx, "status": s, "queries": len(hashes), "responses": len(r.get("responses", [])),
            "hashes_with_exactly_1_hit": sum(1 for p in per if p["hits"] == 1),
            "hashes_with_0_hits": sum(1 for p in per if p["hits"] == 0),
            "source_intact": sum(1 for p in per if p["source_intact"]),
            "errors": sum(1 for p in per if p["error"]),
            "per_hash": per,
        }
        agg = {"size": 0, "track_total_hits": True, "aggs": {"routeState": {"terms": {"field": "routeState"}}}}
        _, a = osreq.request("POST", f"{idx}/_search", json.dumps(agg).encode(), tag=f"{tag}:agg-{name}")
        out[name]["routeState_agg"] = {"total": a.get("hits", {}).get("total"), "buckets": a.get("aggregations", {}).get("routeState", {}).get("buckets")}

    s, so = osreq.request("GET", "api/saved_objects/index-pattern/tenx-all", dashboards=True, tag=tag + ":pattern-read")
    title = so["attributes"]["title"]
    q = {"size": 0, "track_total_hits": True, "aggs": {"index": {"terms": {"field": "_index"}, "aggs": {"routeState": {"terms": {"field": "routeState"}}}}}}
    s2, r2 = osreq.request("POST", f"{urllib.parse.quote(title, safe='*,')}/_search", json.dumps(q).encode(), tag=tag + ":pattern-search")
    s3, r3 = osreq.request("GET", "api/index_patterns/_fields_for_wildcard?" + urllib.parse.urlencode({"pattern": title}), dashboards=True, tag=tag + ":pattern-fields")
    ib = {"params": {"index": title, "body": q}}
    s4, r4 = osreq.request("POST", "internal/search/opensearch", json.dumps(ib).encode(), dashboards=True, tag=tag + ":pattern-internal-search")
    out["index_pattern"] = {
        "saved_object": {"status": s, "id": so.get("id"), "attributes": so.get("attributes")},
        "search_on_title": {"status": s2, "total": (r2.get("hits") or {}).get("total"), "by_index": (r2.get("aggregations") or {}).get("index", {}).get("buckets"), "shards": r2.get("_shards")},
        "fields_for_wildcard": {"status": s3, "fields": sorted(f.get("name") for f in r3.get("fields", [])) if isinstance(r3, dict) else r3},
        "dashboards_internal_search": {"status": s4, "total": ((r4.get("rawResponse") or {}).get("hits") or {}).get("total") if isinstance(r4, dict) else None,
                                       "by_index": (((r4.get("rawResponse") or {}).get("aggregations") or {}).get("index") or {}).get("buckets") if isinstance(r4, dict) else None,
                                       "raw_if_error": r4 if s4 >= 400 else None},
    }
    with open(os.path.join(osreq.HERE, "results", f"proof-{label}.json"), "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    brief = {k: {kk: vv for kk, vv in v.items() if kk != "per_hash"} if isinstance(v, dict) else v for k, v in out.items()}
    print(json.dumps(brief, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
