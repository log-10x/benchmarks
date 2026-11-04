#!/usr/bin/env python3
"""One SigV4-signed request to the domain, its reading kept.

Every call appends one line to results/raw/requests.jsonl: UTC time, method,
path, status, elapsed seconds and the full response body. The body is printed.

  osreq.py METHOD PATH [BODY_FILE|-] [--ndjson] [--dashboards] [--tag TAG]

PATH is relative to the domain endpoint (`_cat/indices?format=json`). With
--dashboards it is sent under /_dashboards/ with osd-xsrf: true. The endpoint
comes from `aws opensearch describe-domain` once and is cached in results/domain.json.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

HERE = os.path.dirname(os.path.abspath(__file__))
DOMAIN = "tenx-uw-tierdown"
REGION = "us-east-1"
PROFILE = "l1x-admin"


def endpoint(session):
    cache = os.path.join(HERE, "results", "domain.json")
    if os.path.exists(cache):
        ep = json.load(open(cache)).get("DomainStatus", {}).get("Endpoint")
        if ep:
            return ep
    d = session.client("opensearch", region_name=REGION).describe_domain(DomainName=DOMAIN)
    with open(cache, "w") as fh:
        json.dump(d, fh, indent=1, default=str)
    return d["DomainStatus"]["Endpoint"]


def session_():
    # Exported role credentials in the environment win; else the SSO profile.
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return boto3.Session(region_name=REGION)
    return boto3.Session(profile_name=PROFILE)


def request(method, path, body=None, ndjson=False, dashboards=False, tag=None):
    session = session_()
    path_only, _, query = path.lstrip("/").partition("?")
    # Percent-encode the query the way SigV4 canonicalises it (a raw comma fails the signature).
    query = urllib.parse.urlencode(urllib.parse.parse_qsl(query, keep_blank_values=True), quote_via=urllib.parse.quote)
    url = f"https://{endpoint(session)}/{'_dashboards/' if dashboards else ''}{path_only}{'?' + query if query else ''}"
    headers = {"Content-Type": "application/x-ndjson" if ndjson else "application/json"}
    if dashboards:
        headers["osd-xsrf"] = "true"
    req = AWSRequest(method=method, url=url, data=body, headers=headers)
    SigV4Auth(session.get_credentials(), "es", REGION).add_auth(req)
    r = urllib.request.Request(url, data=body, method=method, headers=dict(req.headers.items()))
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            status, text = resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode()
    elapsed = round(time.time() - t0, 3)
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = text
    line = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "tag": tag, "method": method,
            "path": path, "dashboards": dashboards, "status": status, "elapsed_s": elapsed, "body": parsed}
    with open(os.path.join(HERE, "results", "raw", "requests.jsonl"), "a") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return status, parsed


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    tag = flags[flags.index("--tag") + 1] if "--tag" in flags else None
    if tag in args:
        args.remove(tag)
    method, path = args[0], args[1]
    body = None
    if len(args) > 2:
        body = sys.stdin.buffer.read() if args[2] == "-" else open(args[2], "rb").read()
    status, parsed = request(method, path, body, "--ndjson" in flags, "--dashboards" in flags, tag)
    print(status)
    print(parsed if isinstance(parsed, str) else json.dumps(parsed, indent=1, ensure_ascii=False))
    return 0 if status < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
