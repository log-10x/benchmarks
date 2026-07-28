#!/usr/bin/env python3
"""Fetch the public sample data this benchmark runs on.

Nothing is vendored into this repository. The three assets below are published
GitHub release files. They are downloaded once on first use and cached under
`data/` in their gzipped form. Readers open the `.gz` directly, so the 215 MB
plain-text expansion never lands on disk.

Override the cache location with the PIB_DATA_DIR environment variable.

    python bench/data.py            # fetch everything, print sizes
    python bench/data.py --check    # report what is cached, fetch nothing
    python bench/data.py --stats    # provenance: sha256 of each asset, line count,
                                    # and the share of file bytes the application
                                    # message accounts for
"""

import argparse
import collections
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

# First ISO-8601 timestamp in a message, used only to report the window the
# sample covers. Lexical order is chronological for this format, so min and max
# need no parsing.
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def _seconds_between(first: str, last: str):
    fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        a = datetime.datetime.strptime(first.replace(" ", "T"), fmt)
        b = datetime.datetime.strptime(last.replace(" ", "T"), fmt)
    except ValueError:
        return None
    return (b - a).total_seconds() or None

RELEASE_BASE = "https://github.com/log-10x/config/releases/download/otel-sample-v1"

ASSETS = {
    # asset name                    what it holds
    "otel-sample-200mb.log": "raw Fluentd/Kubernetes JSON records, 197,430 lines",
    "otel-sample-templates.json": "engine templates, JSONL, 2,896 records",
    "otel-sample-encoded.log": "engine-encoded events, 159,454 records",
}

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = pathlib.Path(os.environ.get("PIB_DATA_DIR", str(REPO_ROOT / "data")))


def asset_path(name: str) -> pathlib.Path:
    return DATA_DIR / (name + ".gz")


def ensure(name: str, quiet: bool = False) -> pathlib.Path:
    """Return the local path to `<name>.gz`, downloading it once if absent."""
    if name not in ASSETS:
        raise KeyError(f"unknown asset {name!r}; known: {sorted(ASSETS)}")
    dest = asset_path(name)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{RELEASE_BASE}/{name}.gz"
    tmp = dest.with_suffix(dest.suffix + ".part")
    if not quiet:
        print(f"downloading {url}", file=sys.stderr, flush=True)
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:
        total = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            total += len(chunk)
    tmp.replace(dest)
    if not quiet:
        print(f"  cached {dest} ({total:,} bytes)", file=sys.stderr, flush=True)
    return dest


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_log_messages(path: pathlib.Path, limit: int = None):
    """Yield the application message from each record of the sample file.

    Every record is a Fluentd/Kubernetes envelope with the same key set. The
    application message sits in `log`; the rest is envelope. Feeding whole lines
    to a template miner measures envelope clustering, so the benchmark uses the
    extracted message. `python bench/data.py --stats` measures the byte share.
    """
    n = 0
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if limit is not None and n >= limit:
                return
            try:
                yield json.loads(line).get("log", "") or ""
            except Exception:
                yield ""
            n += 1


def stats() -> int:
    """Provenance record: what was downloaded, and the shape of the raw asset.

    Written so every figure the scripts lean on has a script that produced it,
    including the share of file bytes the application message accounts for.
    """
    print("asset provenance")
    print(f"source {RELEASE_BASE}")
    for name in ASSETS:
        p = ensure(name, quiet=True)
        print(f"  {name + '.gz':<32} {p.stat().st_size:>10,} bytes  sha256 {sha256(p)}")

    raw = ensure("otel-sample-200mb.log", quiet=True)
    n_lines = n_bad = 0
    total_bytes = msg_bytes = 0
    stamps = []
    containers = collections.Counter()
    with gzip.open(raw, "rt", errors="replace") as f:
        for line in f:
            n_lines += 1
            total_bytes += len(line.encode("utf-8"))
            try:
                rec = json.loads(line)
                m = rec.get("log", "") or ""
                k = rec.get("kubernetes") or {}
                containers[k.get("container_name") or "<none>"] += 1
            except Exception:
                n_bad += 1
                m = ""
            msg_bytes += len(m.encode("utf-8"))
            t = TIMESTAMP_RE.search(m)
            if t:
                stamps.append(t.group(0).replace(" ", "T"))
    print()
    print("raw asset, as text")
    print(f"  lines                              {n_lines:>13,}")
    print(f"  records that failed to parse       {n_bad:>13,}")
    print(f"  bytes                              {total_bytes:>13,}")
    print(f"  bytes in the application message   {msg_bytes:>13,}")
    print(f"  message share of file bytes        {100.0 * msg_bytes / total_bytes:>12.1f}%")
    print(f"  distinct Kubernetes containers     {len(containers):>13,}")
    print(f"  busiest container                  {containers.most_common(1)[0][0]:>13}"
          f"  {containers.most_common(1)[0][1]:,} lines"
          f"  ({100.0 * containers.most_common(1)[0][1] / n_lines:.1f}%)")
    print()
    print("scale, so a reader can calibrate what \"seen once\" means here")
    if stamps:
        stamps.sort()
        lo = stamps[len(stamps) // 100]
        hi = stamps[-1 - len(stamps) // 100]
        span = _seconds_between(lo, hi)
        print(f"  lines carrying an ISO timestamp    {len(stamps):>13,}")
        print(f"  earliest timestamp quoted anywhere {stamps[0]:>13}")
        print(f"  latest timestamp quoted anywhere   {stamps[-1]:>13}")
        print(f"  1st percentile                     {lo:>13}")
        print(f"  99th percentile                    {hi:>13}")
        if span:
            print(f"  window, 1st to 99th percentile     {span / 3600.0:>12.1f} hours")
            print(f"  mean rate over that window         {n_lines / span:>12.1f} lines/sec")
    print()
    print("A handful of messages quote dates from outside the capture, build stamps and")
    print("the like, which is why the window is taken between percentiles rather than")
    print("between the extremes. This is one small demo cluster over a few hours, not a")
    print("log platform. A shape that occurs once here is a different population from a")
    print("shape that occurs once at a hundred thousand lines a second, and the frequency")
    print("strata in results/identity.md should be read against this scale.")
    print()
    print("The message is the `log` field of each Fluentd/Kubernetes record. The rest")
    print("is envelope, identical in shape on every line, so a miner fed whole lines")
    print("spends most of its similarity budget on the envelope. Every script here")
    print("feeds the extracted message.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report cache state, fetch nothing")
    ap.add_argument("--sha256", action="store_true", help="print sha256 of each cached asset")
    ap.add_argument("--stats", action="store_true",
                    help="provenance record: hashes, line count, message byte share")
    args = ap.parse_args()

    if args.stats:
        return stats()

    for name, desc in ASSETS.items():
        p = asset_path(name)
        if args.check:
            state = f"{p.stat().st_size:,} bytes" if p.exists() else "MISSING"
            print(f"{name:<30} {state:>16}  {desc}")
            continue
        p = ensure(name)
        line = f"{name:<30} {p.stat().st_size:>12,} bytes  {desc}"
        if args.sha256:
            line += f"\n  sha256 {sha256(p)}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
