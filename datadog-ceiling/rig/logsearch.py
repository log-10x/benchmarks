#!/usr/bin/env python3
"""Count logs matching a query in one index (or the flex tier) over the last N minutes, by an attribute.
Run under rig/ddenv.sh.  logsearch.py <query> <index|flex> [minutes] [attribute]"""
import json, os, sys, urllib.request, urllib.error
from collections import Counter
q, idx = sys.argv[1], sys.argv[2]
mins = sys.argv[3] if len(sys.argv) > 3 else '60'
attr = sys.argv[4] if len(sys.argv) > 4 else 'routeState'
f = {"query": q, "from": f"now-{mins}m", "to": "now"}
if idx == 'flex':
    f["storage_tier"] = "flex"
else:
    f["indexes"] = [idx]
hdr = {"Content-Type": "application/json", "DD-API-KEY": os.environ["DD_API_KEY"], "DD-APPLICATION-KEY": os.environ["DD_APP_KEY"]}
req = urllib.request.Request("https://" + os.environ["DD_API_HOST"] + "/api/v2/logs/events/search",
                             data=json.dumps({"filter": f, "page": {"limit": 1000}}).encode(), headers=hdr)
try:
    d = json.load(urllib.request.urlopen(req))
except urllib.error.HTTPError as e:
    print(idx, "HTTP", e.code, e.read()[:300].decode()); sys.exit(1)
rows = d.get("data", [])
print(json.dumps({"index": idx, "count": len(rows), "by_" + attr: dict(Counter(r["attributes"]["attributes"].get(attr) for r in rows))}))
