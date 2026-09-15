#!/usr/bin/env python3
"""Time a list of queries against the ClickStack container and write the numbers.

Every row is measured the way ../clickstack-e2e/report.py measures one: the
filesystem, mark and uncompressed caches dropped first, the count-from-files
cache off, then the query run under its own query id and read back out of
`system.query_log` for rows, bytes, duration and the S3 request counters. The
same query is then run once more, warm, and its duration and GET count kept.

  measure.py --container <name> --spec queries.json --out out.json

`queries.json` is a list of {"name": ..., "sql": ...}. The answer each query
returned is kept beside its cost, because a table of costs with no answers
cannot show which answers changed.
"""
import argparse
import json
import pathlib
import subprocess
import time
import uuid


def run(container: str, sql: str, fmt: str = "TSVRaw", query_id: str | None = None) -> str:
    cmd = ["docker", "exec", "-i", container, "clickhouse-client"]
    if query_id:
        cmd += ["--query_id", query_id]
    cmd += ["--format", fmt, "--query", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        first = r.stderr.strip().splitlines()
        return "ERROR: " + (first[0] if first else "unknown")
    return r.stdout.rstrip("\n")


def measure(container: str, name: str, sql: str, drop_cache: bool = True) -> dict:
    sql_run = sql + " SETTINGS use_cache_for_count_from_files = 0"
    if drop_cache:
        for cache in ("FILESYSTEM CACHE", "MARK CACHE", "UNCOMPRESSED CACHE"):
            run(container, f"SYSTEM DROP {cache}")
    qid = str(uuid.uuid4())
    t0 = time.time()
    answer = run(container, sql_run, query_id=qid)
    wall_ms = int((time.time() - t0) * 1000)
    qid2 = str(uuid.uuid4())
    run(container, sql_run, query_id=qid2)
    run(container, "SYSTEM FLUSH LOGS")
    cols = ("read_rows", "read_bytes", "query_duration_ms",
            "ProfileEvents['S3GetObject']", "ProfileEvents['S3ListObjects']",
            "ProfileEvents['S3ReadRequestsCount']",
            "ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']",
            # The Parquet reader's own accounting. Zero on every query that
            # reads no Parquet, and zero is also what a missing key returns, so
            # a run that cares about these checks `system.events` for the names.
            "ProfileEvents['ParquetPrunedRowGroups']",
            "ProfileEvents['ParquetReadRowGroups']",
            "ProfileEvents['ParquetPrunedPages']",
            "ProfileEvents['ParquetReadPages']")
    select = ", ".join(f"toString({c})" for c in cols)
    row = run(container, f"SELECT {select} FROM system.query_log WHERE query_id = '{qid}' "
                         "AND type = 'QueryFinish' LIMIT 1", fmt="TSV").split("\t")
    row = row if len(row) == len(cols) else [""] * len(cols)
    warm = run(container, "SELECT toString(query_duration_ms), "
                          "toString(ProfileEvents['S3GetObject']) FROM system.query_log "
                          f"WHERE query_id = '{qid2}' AND type = 'QueryFinish' LIMIT 1",
               fmt="TSV").split("\t")
    warm = warm if len(warm) == 2 else ["", ""]
    return dict(name=name, sql=" ".join(sql.split()),
                answer=answer.replace("\n", " | ")[:200],
                read_rows=row[0], read_bytes=row[1], ms=row[2],
                s3_get=row[3], s3_list=row[4], s3_reads=row[5], cpu_us=row[6],
                pq_pruned_row_groups=row[7], pq_read_row_groups=row[8],
                pq_pruned_pages=row[9], pq_read_pages=row[10],
                ms_warm=warm[0], s3_get_warm=warm[1], wall_ms=wall_ms)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-drop-cache", action="store_true")
    args = ap.parse_args()
    spec = json.loads(pathlib.Path(args.spec).read_text())
    rows = [measure(args.container, q["name"], q["sql"], not args.no_drop_cache) for q in spec]
    pathlib.Path(args.out).write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(f"  {r['name']}: answer {r['answer'][:40]}, rows {r['read_rows']}, "
              f"GET {r['s3_get']}, LIST {r['s3_list']}, {r['ms']} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
