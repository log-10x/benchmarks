#!/usr/bin/env python3
"""
End-to-end Selenium test for the Log10x Query Console.

Submits a query via the console UI using the REST endpoint,
verifies the query ID is assigned, waits for pipeline completion,
and checks CloudWatch Logs for structured messages and performance times.

Usage:
    python3 test_e2e.py [--console-url http://localhost:8080] [--rest-url http://localhost:9080]
"""

import argparse
import json
import subprocess
import sys
import time
import uuid

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def aws_cli(args):
    """Run an AWS CLI command and return stdout."""
    result = subprocess.run(
        ["aws"] + args,
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"aws cli failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_cw_streams(log_group, query_id):
    """List CW log streams whose name starts with the given query ID."""
    raw = aws_cli([
        "logs", "describe-log-streams",
        "--log-group-name", log_group,
        "--log-stream-name-prefix", query_id,
        "--query", "logStreams[].logStreamName",
        "--output", "json"
    ])
    return json.loads(raw)


def get_cw_events(log_group, stream_name):
    """Return all events from a CW log stream as parsed JSON objects."""
    raw = aws_cli([
        "logs", "get-log-events",
        "--log-group-name", log_group,
        "--log-stream-name", stream_name,
        "--output", "json"
    ])
    data = json.loads(raw)
    events = []
    for ev in data.get("events", []):
        msg = ev.get("message", "")
        try:
            events.append(json.loads(msg))
        except json.JSONDecodeError:
            events.append({"raw": msg})
    return events


# ---------------------------------------------------------------------------
#  Test
# ---------------------------------------------------------------------------

def run_test(console_url, rest_url, headless=True):
    test_id = "e2e-" + uuid.uuid4().hex[:8]
    log_group = "/log10x/query"

    print(f"[TEST] Query name: {test_id}")
    print(f"[TEST] Console:    {console_url}")
    print(f"[TEST] REST:       {rest_url}")
    print()

    # -----------------------------------------------------------------------
    #  1. Launch browser and open console
    # -----------------------------------------------------------------------
    print("[1/6] Launching browser...")
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=opts)
    driver.get(console_url)
    time.sleep(4)
    print(f"       Page title: {driver.title}")

    # -----------------------------------------------------------------------
    #  2. Fill in the query form via JS (Monaco editors need special handling)
    # -----------------------------------------------------------------------
    print("[2/6] Filling query form...")

    # Switch to REST endpoint mode
    driver.execute_script("""
        if (typeof setSubmitMethod === 'function') setSubmitMethod('rest');
    """)
    time.sleep(0.3)

    # Set endpoint URL
    endpoint_input = driver.find_element(By.ID, "endpoint-url")
    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                          endpoint_input, rest_url + "/retriever/query")

    # Set query name
    name_input = driver.find_element(By.ID, "query-name")
    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                          name_input, test_id)

    # Set search expression in Monaco editor
    driver.execute_script("""
        var ed = monaco.editor.getEditors()[0];
        ed.setValue('includes(text, "Test")');
    """)

    # Set time range to "Last 5 min"
    driver.execute_script("""
        document.getElementById('time-range').value = '5m';
    """)

    # Open advanced section and set processing time to 5 minutes (300000ms)
    driver.execute_script("toggleAdvanced()")
    time.sleep(0.3)

    pt_input = driver.find_element(By.ID, "processing-time")
    driver.execute_script("arguments[0].value = '300000'; arguments[0].dispatchEvent(new Event('input'));", pt_input)

    # Take screenshot of filled form
    driver.save_screenshot("/tmp/e2e_form_filled.png")
    print("       Form filled. Screenshot: /tmp/e2e_form_filled.png")

    # -----------------------------------------------------------------------
    #  3. Submit the query
    # -----------------------------------------------------------------------
    print("[3/6] Submitting query...")
    submit_time = time.time()

    submit_btn = driver.find_element(By.ID, "btn-submit")
    submit_btn.click()
    time.sleep(2)

    # Check for toast or status update
    driver.save_screenshot("/tmp/e2e_after_submit.png")
    print("       Submitted. Screenshot: /tmp/e2e_after_submit.png")

    # Check the query log table for the submission
    log_content = driver.execute_script("""
        var rows = document.querySelectorAll('#query-log-body tr');
        var msgs = [];
        for (var r of rows) {
            var cells = r.querySelectorAll('td');
            if (cells.length >= 3) {
                msgs.push({
                    time: cells[0].textContent.trim(),
                    worker: cells[1].textContent.trim(),
                    message: cells[2].textContent.trim()
                });
            }
        }
        return msgs;
    """)
    print(f"       Query log entries: {len(log_content)}")
    for entry in log_content[:5]:
        print(f"         {entry['time']} | {entry['worker'][:20]} | {entry['message'][:80]}")

    # -----------------------------------------------------------------------
    #  4. Wait for pipeline to complete
    # -----------------------------------------------------------------------
    print("[4/6] Waiting for pipeline to process (up to 90s)...")
    poll_start = time.time()
    streams = []
    query_uuid = None

    # Snapshot the known query IDs before our submit
    try:
        pre_raw = aws_cli([
            "logs", "describe-log-streams",
            "--log-group-name", log_group,
            "--order-by", "LastEventTime",
            "--descending", "--limit", "20",
            "--output", "json"
        ])
        pre_data = json.loads(pre_raw)
        known_ids = set()
        for s in pre_data.get("logStreams", []):
            name = s.get("logStreamName", "")
            if "/" in name:
                known_ids.add(name.split("/")[0])
    except Exception:
        known_ids = set()

    while time.time() - poll_start < 90:
        try:
            recent = aws_cli([
                "logs", "describe-log-streams",
                "--log-group-name", log_group,
                "--order-by", "LastEventTime",
                "--descending", "--limit", "20",
                "--output", "json"
            ])
            recent_data = json.loads(recent)
            recent_streams = recent_data.get("logStreams", [])

            # Find NEW query IDs (not in the pre-submit snapshot)
            current_ids = set()
            for s in recent_streams:
                name = s.get("logStreamName", "")
                if "/" in name:
                    current_ids.add(name.split("/")[0])

            new_ids = current_ids - known_ids
            if new_ids:
                query_uuid = new_ids.pop()
                # Check if coordinator's "query complete" event exists
                qid_streams = [s["logStreamName"] for s in recent_streams
                               if s["logStreamName"].startswith(query_uuid + "/")]
                for sn in qid_streams:
                    events = get_cw_events(log_group, sn)
                    for ev in events:
                        if ev.get("message", "").startswith("query complete:"):
                            streams = qid_streams
                            break
                    if streams:
                        break
                if streams:
                    break
        except Exception as e:
            pass

        time.sleep(5)
        elapsed = int(time.time() - poll_start)
        print(f"       ...polling ({elapsed}s)")

    if not streams:
        print("  [FAIL] No CW log streams found for query after 90s")
        driver.save_screenshot("/tmp/e2e_timeout.png")
        driver.quit()
        return False

    print(f"       Query ID: {query_uuid}")
    print(f"       Found {len(streams)} CW log stream(s)")

    # -----------------------------------------------------------------------
    #  5. Read all CW log events and verify structure
    # -----------------------------------------------------------------------
    print("[5/6] Reading CloudWatch Logs events...")
    all_events = []
    all_streams = get_cw_streams(log_group, query_uuid)
    stream_names = all_streams if isinstance(all_streams, list) else []

    # Re-fetch properly
    stream_names_raw = aws_cli([
        "logs", "describe-log-streams",
        "--log-group-name", log_group,
        "--log-stream-name-prefix", query_uuid,
        "--query", "logStreams[].logStreamName",
        "--output", "json"
    ])
    stream_names = json.loads(stream_names_raw)

    coordinator_events = []
    worker_events = []
    perf_events = []

    for sn in stream_names:
        events = get_cw_events(log_group, sn)
        worker_id = sn.split("/")[1] if "/" in sn else "unknown"
        for ev in events:
            ev["_stream"] = sn
            ev["_worker"] = worker_id
            all_events.append(ev)

            level = ev.get("level", "")
            msg = ev.get("message", "")

            if "query started:" in msg:
                coordinator_events.append(ev)
            if level == "PERF":
                perf_events.append(ev)
            if "stream worker" in msg:
                worker_events.append(ev)

    print(f"       Total events: {len(all_events)}")
    print(f"       Streams: {len(stream_names)}")
    print()

    # Print all events nicely
    for ev in all_events:
        level = ev.get("level", "???")
        msg = ev.get("message", ev.get("raw", "???"))
        data = ev.get("data", {})
        worker = ev.get("_worker", "")[:16]
        data_str = f" data={json.dumps(data)}" if data else ""
        print(f"  [{level:5s}] [{worker}] {msg}{data_str}")

    # -----------------------------------------------------------------------
    #  6. Verify expected events
    # -----------------------------------------------------------------------
    print()
    print("[6/6] Verifying expected events...")
    errors = []

    # Check: at least one "query started" event
    started = [e for e in all_events if "query started:" in e.get("message", "")]
    if not started:
        errors.append("Missing 'query started' event")
    else:
        print(f"  [OK] Found {len(started)} 'query started' event(s)")
        # Verify it contains expected fields
        msg = started[0]["message"]
        if test_id in msg:
            print(f"  [OK] Query name '{test_id}' present in started message")
        if 'includes(text, "Test")' in msg or "includes(text," in msg:
            print(f"  [OK] Search expression present in started message")
        if "target=app" in msg:
            print(f"  [OK] Target 'app' present in started message")

    # Check: at least one "scan dispatched" event
    dispatched = [e for e in all_events if "scan dispatched:" in e.get("message", "")]
    if not dispatched:
        errors.append("Missing 'scan dispatched' event")
    else:
        print(f"  [OK] Found {len(dispatched)} 'scan dispatched' event(s)")

    # Check: at least one "query complete" with elapsed time
    completed = [e for e in all_events if "query complete:" in e.get("message", "")]
    if not completed:
        errors.append("Missing 'query complete' event")
    else:
        print(f"  [OK] Found {len(completed)} 'query complete' event(s)")
        for c in completed:
            elapsed = c.get("data", {}).get("elapsedMs")
            if elapsed is not None:
                print(f"  [OK] Performance data: elapsedMs={elapsed}")

    # Check: all events have valid level
    valid_levels = {"INFO", "DEBUG", "PERF", "ERROR"}
    for ev in all_events:
        level = ev.get("level")
        if level and level not in valid_levels:
            errors.append(f"Invalid log level: {level}")

    # Check: PERF events have 'data' field
    for ev in perf_events:
        if "data" not in ev and "query complete" in ev.get("message", ""):
            errors.append(f"PERF event missing 'data': {ev.get('message')}")

    # Summary
    print()
    if errors:
        print(f"  [FAIL] {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
    else:
        print(f"  [PASS] All checks passed!")
        print(f"         Query ID:      {query_uuid}")
        print(f"         CW Streams:    {len(stream_names)}")
        print(f"         Total Events:  {len(all_events)}")
        print(f"         PERF Events:   {len(perf_events)}")

    # Take final screenshot
    driver.save_screenshot("/tmp/e2e_final.png")
    print(f"\n  Screenshots: /tmp/e2e_form_filled.png, /tmp/e2e_after_submit.png, /tmp/e2e_final.png")

    # Print browser console errors
    logs = driver.get_log("browser")
    js_errors = [l for l in logs if l["level"] == "SEVERE" and "favicon" not in l["message"]]
    if js_errors:
        print(f"\n  Browser JS errors:")
        for l in js_errors:
            print(f"    {l['message'][:120]}")

    driver.quit()
    return len(errors) == 0


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E test for Log10x Query Console")
    parser.add_argument("--console-url", default="http://localhost:8080")
    parser.add_argument("--rest-url", default="http://localhost:9080")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    success = run_test(args.console_url, args.rest_url, headless=not args.headed)
    sys.exit(0 if success else 1)
