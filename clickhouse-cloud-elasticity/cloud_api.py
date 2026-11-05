#!/usr/bin/env python3
"""ClickHouse Cloud API reads and the few writes this run needs.

The API key is read from SSM (profile l1x-admin) into this process's memory, or
from CHC_KEY_ID / CHC_KEY_SECRET when the caller exported them. It is never
printed or written. Every response is printed as JSON on stdout.

  cloud_api.py whoami
  cloud_api.py orgs
  cloud_api.py org
  cloud_api.py services
  cloud_api.py service <id>
  cloud_api.py profiles <region>
  cloud_api.py usage <from YYYY-MM-DD> <to YYYY-MM-DD>
  cloud_api.py credits
  cloud_api.py activities [from] [to]
  cloud_api.py prometheus <id> [filtered]
  cloud_api.py create <request.json>
  cloud_api.py patch <id> <path-suffix> <request.json>   # e.g. replicaScaling, state
  cloud_api.py delete <id>
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.clickhouse.cloud/v1"
SSM_ID = "/l1x/tooling/clickhouse-cloud-key-id"
SSM_SECRET = "/l1x/tooling/clickhouse-cloud-key-secret"


def ssm(name: str) -> str:
    out = subprocess.run(
        ["aws", "ssm", "get-parameter", "--profile", "l1x-admin", "--name", name,
         "--with-decryption", "--query", "Parameter.Value", "--output", "text"],
        capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"SSM read failed for {name} (SSO expired?)")
    return out.stdout.strip()


def auth() -> str:
    kid = os.environ.get("CHC_KEY_ID") or ssm(SSM_ID)
    sec = os.environ.get("CHC_KEY_SECRET") or ssm(SSM_SECRET)
    return "Basic " + base64.b64encode(f"{kid}:{sec}".encode()).decode()


_AUTH = None


def call(method: str, path: str, body=None, raw=False):
    global _AUTH
    _AUTH = _AUTH or auth()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", _AUTH)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode()
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        sys.stderr.write(f"HTTP {e.code} {method} {path}\n")
        try:
            return {"httpStatus": e.code, **json.loads(text)}
        except json.JSONDecodeError:
            return {"httpStatus": e.code, "text": text[:2000]}
    if raw:
        return text
    return json.loads(text) if text else {}


def org_id() -> str:
    oid = os.environ.get("CHC_ORG_ID")
    if oid:
        return oid
    orgs = call("GET", "/organizations")["result"]
    if len(orgs) != 1:
        sys.exit(f"{len(orgs)} organizations; set CHC_ORG_ID")
    return orgs[0]["id"]


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "whoami":
        out = call("GET", "/whoami")
    elif cmd == "orgs":
        out = call("GET", "/organizations")
    elif cmd == "org":
        out = call("GET", f"/organizations/{org_id()}")
    elif cmd == "services":
        out = call("GET", f"/organizations/{org_id()}/services")
    elif cmd == "service":
        out = call("GET", f"/organizations/{org_id()}/services/{args[0]}")
    elif cmd == "profiles":
        out = call("GET", f"/organizations/{org_id()}/serviceProfiles?region_id={args[0]}")
    elif cmd == "usage":
        out = call("GET", f"/organizations/{org_id()}/usageCost?from_date={args[0]}&to_date={args[1]}")
    elif cmd == "credits":
        out = call("GET", f"/organizations/{org_id()}/creditBalances")
    elif cmd == "activities":
        q = f"?from_date={args[0]}&to_date={args[1]}" if len(args) >= 2 else ""
        out = call("GET", f"/organizations/{org_id()}/activities{q}")
    elif cmd == "prometheus":
        q = "?filtered_metrics=true" if len(args) > 1 and args[1] == "filtered" else ""
        print(call("GET", f"/organizations/{org_id()}/services/{args[0]}/prometheus{q}", raw=True))
        return 0
    elif cmd == "create":
        # the service password comes back once; it goes to CHC_SECRET_FILE (mode 600), never stdout
        with open(args[0]) as fh:
            out = call("POST", f"/organizations/{org_id()}/services", json.load(fh))
        res = out.get("result", {})
        if "password" in res:
            path = os.environ["CHC_SECRET_FILE"]
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh:
                json.dump({"serviceId": res["service"]["id"], "user": "default", "password": res.pop("password"),
                           "endpoints": res["service"].get("endpoints")}, fh)
            res["password"] = f"<written to {path}>"
    elif cmd == "patch":
        with open(args[2]) as fh:
            out = call("PATCH", f"/organizations/{org_id()}/services/{args[0]}/{args[1]}", json.load(fh))
    elif cmd == "delete":
        out = call("DELETE", f"/organizations/{org_id()}/services/{args[0]}")
    else:
        sys.exit(__doc__)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
