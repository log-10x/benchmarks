"""
A stand-in for Datadog's series intake: accepts the engine's metric posts on any path and
appends each body, decompressed, to /data/posts.jsonl. Nothing is forwarded.
"""
import gzip, json, os, sys, zlib
from http.server import BaseHTTPRequestHandler, HTTPServer
OUT = "/data/posts.jsonl"
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        enc = (self.headers.get("Content-Encoding") or "").lower()
        try:
            if enc == "gzip": body = gzip.decompress(body)
            elif enc == "deflate": body = zlib.decompress(body)
        except Exception: pass
        with open(OUT, "a") as f:
            f.write(json.dumps({"path": self.path, "body": body.decode("utf-8", "replace")}) + "\n")
        self.send_response(202); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
    def log_message(self, *a): pass
HTTPServer(("0.0.0.0", 8080), H).serve_forever()
