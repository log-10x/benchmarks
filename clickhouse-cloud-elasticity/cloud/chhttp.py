"""A keep-alive HTTPS client for the service's HTTP interface.

Credentials come from the secret file the create step wrote (CHC_SECRET_FILE,
default ~/git/l1x-co/.claude-tmp/chce-secrets/service.json); nothing is printed.

A connection is reopened once it is max_age seconds old (CHC_CONN_MAX_AGE, default
30), so the load balancer places each new connection on the replicas serving at
that moment. A kept-alive connection stays on its replica, and after a scale event
that is the old replica until it is removed.
"""
import base64
import http.client
import json
import os
import ssl
import time
import urllib.parse

SECRET = os.environ.get("CHC_SECRET_FILE", os.path.expanduser("~/git/l1x-co/.claude-tmp/chce-secrets/service.json"))


class CH:
    def __init__(self, timeout=600, max_age=None):
        s = json.load(open(SECRET))
        self.host = [e["host"] for e in s["endpoints"] if e["protocol"] == "https"][0]
        self.auth = "Basic " + base64.b64encode(f"{s['user']}:{s['password']}".encode()).decode()
        self.timeout = timeout
        self.max_age = float(max_age if max_age is not None else os.environ.get("CHC_CONN_MAX_AGE", 30))
        self.conn = None
        self.born = 0.0

    def _connect(self):
        self.conn = http.client.HTTPSConnection(self.host, 8443, timeout=self.timeout, context=ssl.create_default_context())
        self.born = time.time()

    def query(self, sql, settings=None, retries=2):
        """Run one statement; returns (body text, summary header dict). Raises on a server error."""
        params = {"default_format": "TabSeparated"}
        params.update({k: str(v) for k, v in (settings or {}).items()})
        path = "/?" + urllib.parse.urlencode(params)
        last = None
        for attempt in range(retries + 1):
            try:
                if self.conn is not None and time.time() - self.born > self.max_age:
                    self.conn.close()
                    self.conn = None
                if self.conn is None:
                    self._connect()
                self.conn.request("POST", path, body=sql.encode(), headers={"Authorization": self.auth})
                r = self.conn.getresponse()
                body = r.read().decode(errors="replace")
                summary = json.loads(r.getheader("X-ClickHouse-Summary") or "{}")
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}: {body[:500]}")
                return body, summary
            except (http.client.HTTPException, OSError) as e:
                last = e
                self.conn = None
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"connection failed: {last!r}")
