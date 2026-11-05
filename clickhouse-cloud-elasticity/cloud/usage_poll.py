#!/usr/bin/env python3
"""Record the Cloud API's billing figures on a fixed cadence.

usageCost reports per day, so an arm's dollars come from the difference between
readings taken at its start and end (allowing for the endpoint's lag). Every --every
seconds this appends one line: the service's computeCHC and totalCHC for today and
yesterday (UTC), and the credit balance's amountSpent.

  usage_poll.py --service <id> --out results/raw/usage.jsonl [--every 600]
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cloud_api  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=float, default=600)
    args = ap.parse_args()
    oid = cloud_api.org_id()
    while True:
        rec = {"t": round(time.time(), 1)}
        try:
            today = dt.datetime.now(dt.timezone.utc).date()
            frm, to = today - dt.timedelta(days=1), today + dt.timedelta(days=1)
            u = cloud_api.call("GET", f"/organizations/{oid}/usageCost?from_date={frm}&to_date={to}")["result"]
            rec["days"] = {c["date"]: {"computeCHC": c["metrics"].get("computeCHC"), "totalCHC": c.get("totalCHC")}
                           for c in u.get("costs", []) if c.get("entityId") == args.service}
            rec["grandTotalCHC"] = u.get("grandTotalCHC")
            c = cloud_api.call("GET", f"/organizations/{oid}/creditBalances")["result"]
            rec["amountSpent"] = sum(b.get("amountSpent", 0) for b in c.get("balances", []))
        except Exception as e:
            rec["error"] = repr(e)[:300]
        with open(args.out, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
