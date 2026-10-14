#!/usr/bin/env python3
"""
Log10x Retriever Query Console

Submit queries to the Retriever via SQS and track progress via CloudWatch Logs.
Supports both CLI and a built-in web GUI with Monaco editor for expression authoring.

Usage:
  python3 console.py --serve                          # start web GUI on :8080
  python3 console.py --search 'severity_level=="ERROR"' --since 30m --bucket my-bucket --queue-url URL --follow

Documentation: https://doc.log10x.com/run/input/objectStorage/query/
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request
from urllib.error import URLError

boto3 = None
_boto3_checked = False

def _try_boto3():
    """Try to import boto3. Returns module or None (no sys.exit)."""
    global boto3, _boto3_checked
    if not _boto3_checked:
        _boto3_checked = True
        try:
            import boto3 as _b3
            boto3 = _b3
        except ImportError:
            boto3 = None
    return boto3

def _require_boto3():
    b3 = _try_boto3()
    if b3 is None:
        print("boto3 is required. Install with: pip3 install boto3", file=sys.stderr)
        sys.exit(1)
    return b3

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
DEFAULT_REGION = "us-east-1"
DEFAULT_TARGET = "app"
DEFAULT_OBJECT_STORAGE = "AWS"
DEFAULT_PROCESSING_TIME = "60000"   # 60s in ms
DEFAULT_RESULT_SIZE = "10485760"    # 10MB in bytes
DEFAULT_PORT = 8080
DEFAULT_CW_LOG_GROUP = "/log10x/query"
POLL_INTERVAL = 2  # seconds

DOC_BASE = "https://doc.log10x.com/run/input/objectStorage/query/"
DEFAULT_LOG_LEVELS = ["ERROR", "INFO", "PERF"]

SAMPLE_QUERIES = [
    {
        "name": "ERROR events (last 5 min)",
        "search": 'severity_level=="ERROR"',
        "since": "5m",
    },
    {
        "name": "ERROR/FATAL with POST",
        "search": '(severity_level=="ERROR" || severity_level=="FATAL") && includes(text, "POST")',
        "since": "30m",
    },
    {
        "name": "HTTP 500 errors",
        "search": 'http_code=="500"',
        "since": "1h",
    },
    {
        "name": "Country filter (US)",
        "search": 'country=="US"',
        "since": "30m",
    },
    {
        "name": "Kubernetes namespace",
        "search": 'k8s_namespace=="production"',
        "since": "1h",
    },
    {
        "name": "INFO level with keyword",
        "search": 'severity_level=="INFO" && includes(text, "request")',
        "since": "15m",
    },
    {
        "name": "All events (broad scan)",
        "search": "",
        "since": "5m",
    },
]

# Maps CLI flag name -> (QueryRequest JSON field, doc anchor, description)
FIELD_DOCS = {
    "name":             ("name",              "#queryname",                "logical name for the query"),
    "target":           ("target",            "#querytarget",             "app/service prefix to filter index objects"),
    "from":             ("from",              "#queryfrom",               "start of time range (epoch ms, inclusive)"),
    "to":               ("to",                "#queryto",                 "end of time range (epoch ms, exclusive)"),
    "search":           ("search",            "#querysearch",             "search expression (==, &&, ||, includes)"),
    "filters":          ("filters",           "#queryfilters",            "JavaScript filter expressions for in-memory filtering"),
    "object_storage":   ("objectStorageName", "#queryobjectstoragename",  "object storage provider"),
    "bucket":           ("readContainer",     "#queryreadcontainer",      "S3 bucket containing log files"),
    "index_bucket":     ("indexContainer",    "#queryindexcontainer",     "S3 bucket containing index objects"),
    "processing_time":  ("processingTime",    "#querylimitprocessingtime","max processing time"),
    "result_size":      ("resultSize",        "#querylimitresultsize",    "max result volume in bytes"),
}

# ---------------------------------------------------------------------------
# Parsing utilities
# ---------------------------------------------------------------------------

def parse_relative_time(since: str):
    """Parse '30s', '5m', '1h', '2d' into (from_epoch_ms, to_epoch_ms)."""
    m = re.match(r'^(\d+)(s|m|h|d)$', since)
    if not m:
        raise ValueError(f"Invalid --since format: '{since}'. Use: 30s, 5m, 1h, 2d")
    val, unit = int(m.group(1)), m.group(2)
    mult = {'s': 1000, 'm': 60_000, 'h': 3_600_000, 'd': 86_400_000}
    now_ms = int(time.time() * 1000)
    return (now_ms - val * mult[unit], now_ms)


def parse_size(s: str) -> str:
    """Parse '10MB', '1GB' into bytes string. Pass through if already numeric."""
    m = re.match(r'^(\d+)(B|KB|MB|GB)$', s, re.IGNORECASE)
    if not m:
        return s
    val, unit = int(m.group(1)), m.group(2).upper()
    mult = {'B': 1, 'KB': 1024, 'MB': 1_048_576, 'GB': 1_073_741_824}
    return str(val * mult[unit])


def parse_duration(s: str) -> str:
    """Parse '60s', '2m', '5m' into milliseconds string."""
    m = re.match(r'^(\d+)(s|m|h)$', s)
    if not m:
        return s
    val, unit = int(m.group(1)), m.group(2)
    mult = {'s': 1000, 'm': 60_000, 'h': 3_600_000}
    return str(val * mult[unit])


# ---------------------------------------------------------------------------
# QueryRequest builder
# ---------------------------------------------------------------------------

def build_query_request(
    name, target, from_ms, to_ms, search,
    bucket, index_bucket=None, filters=None,
    object_storage=DEFAULT_OBJECT_STORAGE,
    processing_time=DEFAULT_PROCESSING_TIME,
    result_size=DEFAULT_RESULT_SIZE,
    query_id=None,
    log_levels=None,
):
    """Build QueryRequest JSON matching the Java QueryRequest POJO."""
    req = {
        "name": name,
        "target": target,
        "from": str(from_ms),
        "to": str(to_ms),
        "search": search or "",
        "id": query_id or str(uuid.uuid4()),
        "filters": filters or [],
        "objectStorageName": object_storage,
        "readContainer": bucket,
        "indexContainer": index_bucket or bucket,
        "processingTime": processing_time,
        "resultSize": result_size,
    }
    if log_levels:
        req["logLevels"] = ",".join(log_levels) if isinstance(log_levels, list) else log_levels
    return req


# ---------------------------------------------------------------------------
# SQS submission
# ---------------------------------------------------------------------------

def submit_query(queue_url, query_request, region=DEFAULT_REGION):
    """Submit QueryRequest to SQS. Returns dict with queryId or error."""
    b3 = _require_boto3()
    from botocore.exceptions import ClientError, NoCredentialsError
    try:
        sqs = b3.client('sqs', region_name=region)
        resp = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(query_request),
        )
        return {
            "queryId": query_request["id"],
            "messageId": resp["MessageId"],
            "status": "submitted",
        }
    except NoCredentialsError:
        return {"error": "AWS credentials not configured. Run 'aws configure' or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY."}
    except ClientError as e:
        return {"error": f"SQS error: {e.response['Error']['Message']}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# REST endpoint submission
# ---------------------------------------------------------------------------

def submit_query_rest(endpoint_url, query_request):
    """Submit QueryRequest via REST endpoint. Returns dict with queryId or error."""
    import urllib.request
    import urllib.error
    try:
        url = endpoint_url.rstrip('/')
        if not url.endswith('/retriever/query'):
            url += '/retriever/query'
        data = json.dumps(query_request).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "queryId": query_request["id"],
                "status": "submitted",
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return {"error": f"REST error ({e.code}): {body[:200]}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# CloudWatch Logs polling
# ---------------------------------------------------------------------------

def _parse_event_message(raw):
    """Extract the message string from a raw CW event (may be JSON)."""
    try:
        parsed = json.loads(raw)
        return parsed.get('message', raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def _analyze_lifecycle(events):
    """Analyze query lifecycle from structured log events.

    The retriever has a two-tier architecture:
      1. Main coordinator logs "query started", dispatches sub-queries via SQS
         ("scan dispatched: N remote scan tasks"), then "query complete" (fast, ~3ms).
      2. Each sub-query is an independent worker that logs "query started",
         "scan dispatched: N local scan tasks", optionally "stream dispatch: M requests",
         then "query complete".
      3. Stream workers (dispatched by sub-queries) log "stream worker started/complete/error/skipped".

    The main coordinator's "query complete" fires after dispatch (~3ms), NOT when all
    work is done. We must wait for all sub-queries AND all stream workers to finish.

    Single-coordinator mode (no remote dispatch): the coordinator scans locally and
    may dispatch stream workers directly. Same as the old model.

    Special cases:
      - "query empty" (DEBUG): no matching templates/vars — terminal.
      - "query aborted" (ERROR): processing time or result size limit exceeded.
      - "scan error" (ERROR): scan worker failed.
    """
    # --- Phase 1: identify main coordinator ---
    # The main coordinator logs "scan dispatched: N remote scan tasks".
    # If no remote dispatch, fall back to first "query started" worker.
    main_id = None
    for e in events:
        msg = _parse_event_message(e['message'])
        if 'scan dispatched:' in msg and 'remote' in msg:
            main_id = e['workerId']
            break
    if main_id is None:
        for e in events:
            msg = _parse_event_message(e['message'])
            if 'query started' in msg:
                main_id = e['workerId']
                break

    # --- Phase 2: single pass over all events ---
    main_done = False
    query_empty = False
    has_error = False
    processing_time_ms = None
    remote_scan_count = None        # "scan dispatched: N remote scan tasks" (main coordinator)
    sub_query_ids = set()           # workers that logged "query started" (excluding main)
    sub_query_done = set()          # sub-queries that logged "query complete"
    stream_dispatch_total = 0       # sum of all "stream dispatch: N requests"
    stream_worker_ids = set()       # workers that logged stream worker events
    stream_worker_terminal = set()  # stream workers with terminal events

    for e in events:
        msg = _parse_event_message(e['message'])
        wid = e['workerId']

        if wid == main_id:
            # --- Main coordinator events ---
            if 'query started' in msg:
                m = re.search(r'processingTimeLimit=(\d+)ms', msg)
                if m:
                    processing_time_ms = int(m.group(1))
            if 'scan dispatched:' in msg and 'remote' in msg:
                m = re.search(r'scan dispatched:\s*(\d+)\s+remote', msg)
                if m:
                    remote_scan_count = int(m.group(1))
            if 'stream dispatch:' in msg:
                m = re.search(r'stream dispatch:\s*(\d+)\s+requests', msg)
                if m:
                    stream_dispatch_total += int(m.group(1))
            if 'query complete' in msg:
                main_done = True
            if 'query empty' in msg:
                query_empty = True
            if 'query aborted' in msg or 'query error' in msg:
                has_error = True
        else:
            # --- Non-coordinator events ---
            # Detect sub-queries (they log "query started")
            if 'query started' in msg:
                sub_query_ids.add(wid)

            if wid in sub_query_ids:
                # Sub-query events
                if 'query complete' in msg:
                    sub_query_done.add(wid)
                if 'stream dispatch:' in msg:
                    m = re.search(r'stream dispatch:\s*(\d+)\s+requests', msg)
                    if m:
                        stream_dispatch_total += int(m.group(1))
                if 'query aborted' in msg or 'query error' in msg or 'scan error' in msg:
                    has_error = True
            else:
                # Stream worker events (workers that never log "query started")
                if 'stream worker' in msg:
                    stream_worker_ids.add(wid)
                    if ('stream worker complete' in msg or
                        'stream worker error' in msg or
                        'stream worker skipped' in msg):
                        stream_worker_terminal.add(wid)
                if 'scan error' in msg:
                    has_error = True

    # --- Phase 3: determine status ---
    if not events:
        status = "pending"
    elif has_error:
        status = "error"
    elif query_empty:
        status = "complete"
    elif remote_scan_count is not None:
        # Two-tier mode: main coordinator dispatched sub-queries
        if not main_done:
            status = "running"
        elif len(sub_query_done) < remote_scan_count:
            status = "scanning"
        elif stream_dispatch_total > 0 and len(stream_worker_terminal) < stream_dispatch_total:
            status = "streaming"
        else:
            status = "complete"
    elif main_done:
        # Single-coordinator mode (no remote dispatch)
        if stream_dispatch_total > 0 and len(stream_worker_terminal) < stream_dispatch_total:
            status = "streaming"
        else:
            status = "complete"
    else:
        status = "running"

    return {
        "status": status,
        "progress": {
            "coordinatorDone": main_done,
            "dispatchedSubQueries": remote_scan_count,
            "completedSubQueries": len(sub_query_done),
            "dispatchedStreamWorkers": stream_dispatch_total if stream_dispatch_total > 0 else None,
            "completedStreamWorkers": len(stream_worker_terminal),
            "processingTimeMs": processing_time_ms,
        }
    }


def get_query_events(query_id, region=DEFAULT_REGION, log_group=DEFAULT_CW_LOG_GROUP):
    """Poll CloudWatch Logs for query events. Streams: {queryID}/{workerID}."""
    b3 = _require_boto3()
    from botocore.exceptions import ClientError
    logs_client = b3.client('logs', region_name=region)
    events = []

    try:
        # Paginate describe_log_streams to get ALL streams for this query
        streams = []
        paginator = logs_client.get_paginator('describe_log_streams')
        for page in paginator.paginate(
            logGroupName=log_group,
            logStreamNamePrefix=query_id,
        ):
            streams.extend(page.get('logStreams', []))

        if not streams:
            return {"events": [], "status": "pending", "streams": 0, "progress": {}}

        for stream in streams:
            sname = stream['logStreamName']
            worker = sname.split('/')[-1] if '/' in sname else sname

            # Paginate get_log_events to fetch ALL events from each stream
            kwargs = dict(
                logGroupName=log_group,
                logStreamName=sname,
                startFromHead=True,
            )
            while True:
                resp = logs_client.get_log_events(**kwargs)
                for ev in resp.get('events', []):
                    events.append({
                        'timestamp': ev['timestamp'],
                        'workerId': worker,
                        'message': ev['message'],
                    })
                token = resp.get('nextForwardToken')
                if token and token != kwargs.get('nextToken'):
                    kwargs['nextToken'] = token
                else:
                    break

        events.sort(key=lambda e: e['timestamp'])

        lifecycle = _analyze_lifecycle(events)

        print(f"[debug] get_query_events: query={query_id}, streams={len(streams)}, "
              f"events={len(events)}, status={lifecycle['status']}, "
              f"progress={lifecycle['progress']}")

        return {
            "events": events,
            "status": lifecycle["status"],
            "streams": len(streams),
            "progress": lifecycle["progress"],
        }

    except logs_client.exceptions.ResourceNotFoundException:
        return {"events": [], "status": "pending", "streams": 0, "progress": {}}
    except ClientError as e:
        return {"events": [], "status": "error", "error": str(e), "streams": 0, "progress": {}}


# ---------------------------------------------------------------------------
# HTTP server for web GUI
# ---------------------------------------------------------------------------

class QueryHandler(BaseHTTPRequestHandler):

    region = DEFAULT_REGION
    log_group = DEFAULT_CW_LOG_GROUP
    @classmethod
    def _load_html(cls):
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ('/', '/index.html'):
            html = self._load_html()
            self._send(200, html, 'text/html')

        elif path == '/api/status':
            self._handle_status()

        elif path == '/api/samples':
            self._json(200, SAMPLE_QUERIES)

        elif path == '/api/health':
            self._handle_health()

        elif path == '/favicon.ico':
            self._handle_favicon()

        elif path.startswith('/api/query/') and path.endswith('/events'):
            parts = path.split('/')
            if len(parts) >= 4:
                self._handle_events(parts[3])
            else:
                self._json(404, {"error": "Not found"})
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        if urlparse(self.path).path == '/api/query':
            self._handle_submit()
        else:
            self._json(404, {"error": "Not found"})

    def _handle_status(self):
        update = _update_info.get("remoteVersion") if _update_info else None
        try:
            b3 = _try_boto3()
            if b3 is None:
                resp = {
                    "status": "error",
                    "error": "boto3 not installed. Install with: pip3 install boto3",
                    "version": VERSION,
                }
                if update:
                    resp["updateAvailable"] = update
                self._json(200, resp)
                return
            sts = b3.client('sts', region_name=self.region)
            identity = sts.get_caller_identity()
            resp = {
                "status": "ok",
                "account": identity['Account'],
                "arn": identity['Arn'],
                "region": self.region,
                "logGroup": self.log_group,
                "version": VERSION,
            }
            if update:
                resp["updateAvailable"] = update
            self._json(200, resp)
        except Exception as e:
            resp = {
                "status": "error",
                "error": str(e),
                "version": VERSION,
            }
            if update:
                resp["updateAvailable"] = update
            self._json(200, resp)

    def _handle_health(self):
        qs = parse_qs(urlparse(self.path).query)
        url = qs.get('url', [None])[0]
        if not url:
            self._json(400, {"status": "error", "error": "url parameter required"})
            return
        try:
            parsed = urlparse(url)
            health_url = f"{parsed.scheme}://{parsed.netloc}/q/health/ready"
            req = Request(health_url, method='GET')
            resp = urlopen(req, timeout=5)
            self._json(200, {"status": "ok", "code": resp.status})
        except URLError as e:
            self._json(200, {"status": "error", "error": str(e.reason)})
        except Exception as e:
            self._json(200, {"status": "error", "error": str(e)})

    def _handle_favicon(self):
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', '..', '..', '..', 'comsite', 'log10x', 'images', 'favicon.ico')
        try:
            with open(ico_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/x-icon')
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._json(404, {"error": "favicon not found"})

    def _handle_submit(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))

        method = body.get('submitMethod', 'sqs')

        qr = build_query_request(
            name=body.get('name', 'web-query'),
            target=body.get('target', DEFAULT_TARGET),
            from_ms=int(body['from']),
            to_ms=int(body['to']),
            search=body.get('search', ''),
            bucket=body.get('bucket', ''),
            index_bucket=body.get('indexBucket'),
            object_storage=body.get('objectStorageName', DEFAULT_OBJECT_STORAGE),
            filters=body.get('filters', []),
            processing_time=body.get('processingTime', DEFAULT_PROCESSING_TIME),
            result_size=body.get('resultSize', DEFAULT_RESULT_SIZE),
            log_levels=body.get('logLevels', DEFAULT_LOG_LEVELS),
        )

        if body.get('dryRun'):
            self._json(200, {"dryRun": True, "payload": qr})
            return

        if method == 'rest':
            endpoint_url = body.get('endpointUrl', '').strip()
            if not endpoint_url:
                self._json(400, {"error": "Endpoint URL is required"})
                return
            result = submit_query_rest(endpoint_url, qr)
        else:
            queue_url = body.get('queueUrl', '').strip()
            if not queue_url:
                self._json(400, {"error": "SQS Queue URL is required"})
                return
            if _try_boto3() is None:
                self._json(500, {"error": "boto3 not installed. Install with: pip3 install boto3"})
                return
            region = body.get('region', self.region)
            result = submit_query(queue_url, qr, region)

        self._json(200 if 'queryId' in result else 500, result)

    def _handle_events(self, query_id):
        if _try_boto3() is None:
            self._json(500, {"error": "boto3 not installed"})
            return
        result = get_query_events(query_id, self.region, self.log_group)
        self._json(200, result)

    def _json(self, code, data):
        self._send(code, json.dumps(data), 'application/json')

    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, fmt, *args):
        pass  # silence request logging


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog='console.py',
        description='Log10x Retriever Query Console',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
query options reference:
  {DOC_BASE}

examples:
  # search for errors in the last 30 minutes and follow progress
  python3 console.py \\
    --search 'severity_level==\"ERROR\"' --since 30m \\
    --bucket my-bucket --queue-url URL --follow

  # dry run - print JSON payload without sending
  python3 console.py \\
    --search 'http_code==\"500\"' --since 1h \\
    --bucket my-bucket --dry-run

  # follow an existing query by ID (no submission)
  python3 console.py --query-id QUERY_UUID --log-group /tenx/retriever/query

  # start web GUI
  python3 console.py --serve
  python3 console.py --serve --port 9090
""",
    )

    mode = p.add_argument_group('mode')
    mode.add_argument('--serve', action='store_true',
        help='start web GUI (default: http://localhost:8080)')
    mode.add_argument('--port', type=int, default=DEFAULT_PORT,
        help=f'web GUI port (default: {DEFAULT_PORT})')

    criteria = p.add_argument_group(
        'query criteria',
        f'docs: {DOC_BASE}')
    criteria.add_argument('--search', type=str, metavar='EXPR',
        help=f'search expression (==, &&, ||, includes)  {DOC_BASE}#querysearch')
    criteria.add_argument('--filters', type=str, nargs='*', metavar='EXPR',
        help=f'JavaScript filter expressions  {DOC_BASE}#queryfilters')
    criteria.add_argument('--since', type=str, metavar='TIME',
        help=f'relative time range (30s, 5m, 1h, 2d)  {DOC_BASE}#queryfrom')
    criteria.add_argument('--from', dest='from_ms', type=int, metavar='EPOCH_MS',
        help=f'start time as epoch ms  {DOC_BASE}#queryfrom')
    criteria.add_argument('--to', dest='to_ms', type=int, metavar='EPOCH_MS',
        help=f'end time as epoch ms  {DOC_BASE}#queryto')
    criteria.add_argument('--target', type=str, default=DEFAULT_TARGET, metavar='PREFIX',
        help=f'app/service prefix (default: {DEFAULT_TARGET})  {DOC_BASE}#querytarget')
    criteria.add_argument('--name', type=str, metavar='NAME',
        help=f'query identifier  {DOC_BASE}#queryname')

    storage = p.add_argument_group('storage')
    storage.add_argument('--bucket', type=str, metavar='BUCKET',
        help=f'S3 bucket for log files  {DOC_BASE}#queryreadcontainer')
    storage.add_argument('--index-bucket', type=str, metavar='BUCKET',
        help=f'S3 bucket for index (default: same as --bucket)  {DOC_BASE}#queryindexcontainer')
    storage.add_argument('--object-storage', type=str, default=DEFAULT_OBJECT_STORAGE, metavar='NAME',
        help=f'storage provider (default: {DEFAULT_OBJECT_STORAGE})  {DOC_BASE}#queryobjectstoragename')

    limits = p.add_argument_group('limits')
    limits.add_argument('--processing-time', type=str, default='60s', metavar='DUR',
        help=f'max processing time (60s, 2m, 5m; default: 60s)  {DOC_BASE}#querylimitprocessingtime')
    limits.add_argument('--result-size', type=str, default='10MB', metavar='SIZE',
        help=f'max result volume (10MB, 1GB; default: 10MB)  {DOC_BASE}#querylimitresultsize')
    limits.add_argument('--log-levels', type=str, default='ERROR,INFO,PERF', metavar='LEVELS',
        help=f'comma-separated log levels to capture (default: ERROR,INFO,PERF)  {DOC_BASE}#queryloglevelss')

    infra = p.add_argument_group('infrastructure')
    infra.add_argument('--queue-url', type=str, metavar='URL',
        help='SQS queue URL (or env LOG10X_QUERY_QUEUE_URL)')
    infra.add_argument('--region', type=str, default=DEFAULT_REGION, metavar='REGION',
        help=f'AWS region (default: {DEFAULT_REGION})')
    infra.add_argument('--log-group', type=str, metavar='GROUP',
        help=f'CloudWatch Logs group for query events (or env TENX_QUERY_LOG_GROUP, default: {DEFAULT_CW_LOG_GROUP})')

    actions = p.add_argument_group('actions')
    actions.add_argument('--query-id', type=str, metavar='ID',
        help='follow an existing query by ID (skips submission, implies --follow)')
    actions.add_argument('--dry-run', action='store_true',
        help='print JSON payload without sending to SQS')
    actions.add_argument('--follow', action='store_true',
        help='block and poll CloudWatch Logs until query completes (Ctrl+C to stop)')
    actions.add_argument('--confirm', action='store_true',
        help='skip safety prompt for large time ranges (>24h)')

    p.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    return p


# ---------------------------------------------------------------------------
# CLI execution
# ---------------------------------------------------------------------------

def run_cli(args):
    log_group = args.log_group or os.environ.get('TENX_QUERY_LOG_GROUP') or DEFAULT_CW_LOG_GROUP
    queue_url = args.queue_url or os.environ.get('LOG10X_QUERY_QUEUE_URL')
    if not queue_url and not args.dry_run:
        print("error: --queue-url or LOG10X_QUERY_QUEUE_URL env var required", file=sys.stderr)
        sys.exit(1)

    # resolve time range
    if args.from_ms and args.to_ms:
        from_ms, to_ms = args.from_ms, args.to_ms
    elif args.since:
        from_ms, to_ms = parse_relative_time(args.since)
    else:
        print("error: --since or --from/--to required", file=sys.stderr)
        sys.exit(1)

    # safety check: warn on large time ranges
    range_ms = to_ms - from_ms
    range_hours = range_ms / 3_600_000
    if range_hours > 24 and not args.confirm and not args.dry_run:
        print(f"warning: time range spans {range_hours:.0f} hours — this may scan a large amount of data.", file=sys.stderr)
        if args.since:
            hint_val = int(re.match(r'^(\d+)', args.since).group(1))
            hint_unit = args.since[-1]
            if hint_unit == 'd' and hint_val > 1:
                print(f"  hint: did you mean --since {hint_val}h?", file=sys.stderr)
            elif hint_unit == 'h' and hint_val > 24:
                print(f"  hint: did you mean --since {min(hint_val, 24)}h?", file=sys.stderr)
        print("  add --confirm to proceed, or --dry-run to preview the payload", file=sys.stderr)
        sys.exit(1)

    if not args.bucket:
        print("error: --bucket required", file=sys.stderr)
        sys.exit(1)

    query_name = args.name or f"query-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    query_id = str(uuid.uuid4())

    log_levels = [l.strip().upper() for l in args.log_levels.split(',') if l.strip()]

    qr = build_query_request(
        name=query_name,
        target=args.target,
        from_ms=from_ms,
        to_ms=to_ms,
        search=args.search or '',
        bucket=args.bucket,
        index_bucket=args.index_bucket,
        object_storage=args.object_storage,
        filters=args.filters,
        processing_time=parse_duration(args.processing_time),
        result_size=parse_size(args.result_size),
        query_id=query_id,
        log_levels=log_levels,
    )

    # dry run
    if args.dry_run:
        print(json.dumps(qr, indent=2))
        return

    # submit
    from_dt = datetime.fromtimestamp(from_ms / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    to_dt = datetime.fromtimestamp(to_ms / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"Submitting query to {queue_url}")
    result = submit_query(queue_url, qr, args.region)

    if 'error' in result:
        print(f"error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"Query submitted.")
    print(f"  Query ID:   {result['queryId']}")
    print(f"  Time range: {from_dt} -> {to_dt}")
    if args.search:
        print(f"  Search:     {args.search}")

    # follow mode: block and poll
    if args.follow:
        _poll_events(query_id, args.region, log_group)


def follow_query(args):
    """Follow an existing query by ID — no submission, just poll CloudWatch Logs."""
    log_group = args.log_group or os.environ.get('TENX_QUERY_LOG_GROUP') or DEFAULT_CW_LOG_GROUP
    print(f"Following query {args.query_id}")
    _poll_events(args.query_id, args.region, log_group)


def _poll_events(query_id, region, log_group):
    """Poll CloudWatch Logs for query events until all work is done.

    Uses semantic lifecycle tracking: the coordinator's "query complete" only means
    dispatch is done — stream workers are async. We keep polling until all dispatched
    workers have reported back (or a safety timeout is reached).
    """
    print(f"\nPolling CloudWatch Logs ({log_group})... Ctrl+C to stop")
    print("-" * 70)
    seen = set()
    t0 = time.time()
    last_status = None
    try:
        while True:
            data = get_query_events(query_id, region, log_group)
            progress = data.get('progress', {})

            for ev in data['events']:
                key = (ev['timestamp'], ev['message'])
                if key not in seen:
                    seen.add(key)
                    ts = datetime.fromtimestamp(
                        ev['timestamp'] / 1000, timezone.utc
                    ).strftime('%H:%M:%S.') + f"{ev['timestamp'] % 1000:03d}"
                    worker = ev.get('workerId', '')
                    short_worker = worker[:8] if len(worker) > 8 else worker

                    # Parse structured JSON events
                    msg_text = ev['message']
                    level_tag = ""
                    perf_suffix = ""
                    try:
                        parsed = json.loads(msg_text)
                        level_tag = f"[{parsed.get('level', 'INFO'):>5s}] "
                        msg_text = parsed.get('message', msg_text)
                        data_obj = parsed.get('data')
                        if data_obj:
                            perf_parts = [f"{k}={v}" for k, v in data_obj.items()]
                            perf_suffix = "  (" + ", ".join(perf_parts) + ")"
                    except (json.JSONDecodeError, TypeError):
                        pass

                    print(f"[{ts}] [{short_worker}] {level_tag}{msg_text}{perf_suffix}")

            status = data['status']

            # Print phase transitions
            if status != last_status:
                if status == 'scanning':
                    total = progress.get('dispatchedSubQueries', '?')
                    done = progress.get('completedSubQueries', 0)
                    print(f"  ... scanning: {done}/{total} sub-queries complete")
                elif status == 'streaming':
                    total = progress.get('dispatchedStreamWorkers', '?')
                    done = progress.get('completedStreamWorkers', 0)
                    print(f"  ... streaming: {done}/{total} event streams complete")
            last_status = status

            if status in ('complete', 'error'):
                streams = data.get('streams', '?')
                sub_q = progress.get('completedSubQueries', 0)
                sw = progress.get('completedStreamWorkers', 0)
                elapsed = time.time() - t0
                print("-" * 70)
                parts = [f"{len(seen)} events", f"{streams} log streams"]
                if sub_q:
                    parts.append(f"{sub_q} sub-queries")
                if sw:
                    parts.append(f"{sw} event streams")
                print(f"Query {status}. {', '.join(parts)} in {elapsed:.1f}s")
                break

            # Safety timeout: use processingTime from the query if available,
            # otherwise default to 10 minutes after first events appear
            timeout_ms = progress.get('processingTimeMs') or 600000
            if data['events'] and (time.time() - t0) > (timeout_ms / 1000) + 30:
                streams = data.get('streams', '?')
                sub_q = progress.get('completedSubQueries', 0)
                total_sub = progress.get('dispatchedSubQueries', '?')
                print("-" * 70)
                print(f"Timeout. {len(seen)} events, {sub_q}/{total_sub} sub-queries, {streams} log streams")
                break

            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        elapsed = time.time() - t0
        print(f"\nStopped. {len(seen)} events in {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_update_info = None  # cached result: None = not checked, dict = result

def _check_for_update():
    """Check GitHub for a newer version. Fails silently on any error. Returns remote version or None."""
    global _update_info
    if _update_info is not None:
        return _update_info.get("remoteVersion")
    _update_info = {}
    try:
        url = "https://raw.githubusercontent.com/log-10x/modules/main/apps/retriever/console/console.py"
        req = Request(url, headers={"User-Agent": "log10x-console"})
        with urlopen(req, timeout=3) as resp:
            for line in resp:
                line = line.decode("utf-8", errors="ignore").strip()
                if line.startswith("VERSION"):
                    remote = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if remote != VERSION:
                        _update_info["remoteVersion"] = remote
                        print(f"\n  Update available: {VERSION} → {remote}")
                        print(f"  https://github.com/log-10x/modules/tree/main/apps/retriever/console\n")
                        return remote
                    return None
    except Exception:
        pass
    return None


def main():
    _check_for_update()
    parser = build_parser()
    args = parser.parse_args()

    if args.serve:
        QueryHandler.region = args.region
        QueryHandler.log_group = args.log_group or os.environ.get('TENX_QUERY_LOG_GROUP') or DEFAULT_CW_LOG_GROUP
        server = HTTPServer(('0.0.0.0', args.port), QueryHandler)
        print(f"Log10x Query Console running at http://localhost:{args.port}")
        print(f"Region: {args.region}")
        print(f"Log group: {QueryHandler.log_group}")
        print("Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
            server.shutdown()
    elif args.query_id:
        follow_query(args)
    else:
        if not args.search and not args.dry_run:
            parser.print_help()
            sys.exit(1)
        run_cli(args)


if __name__ == '__main__':
    main()
