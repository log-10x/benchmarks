#!/usr/bin/env python3
"""Point the shipped Retriever index and query configs at the local file system.

Six edits, each asserted, in the style of ../clickstack-e2e/patch_engine_config.py:
a change in the shipped text fails here rather than producing a run that indexed
nothing and said nothing.

  index  objectStorageName AWS -> Local, the accessor the settings file names for
         the local file system; the SQS invocation arguments removed, since there
         is no queue here; the object to index taken from an environment variable
         so one container run indexes one object.
  query  the same accessor; the time window widened to the run's own window; the
         search expression and the filter list taken from environment variables,
         so the query is "one pattern hash, one time window" and nothing else;
         the results writer turned on, so what the query read is visible.
"""
import argparse
import pathlib
import sys

INDEX = ("pipelines", "run", "input", "objectStorage", "index", "config.yaml")
QUERY = ("pipelines", "run", "input", "objectStorage", "query", "config.yaml")

EDITS = {
    INDEX: [
        ("  - objectStorageName: AWS", "  - objectStorageName: Local",
         "index accessor set to the local file system"),
        ("    objectStorageArgs: [invoke, sqs]", "    objectStorageArgs: []",
         "index SQS invocation removed"),
        ('      object: ""  # (REQUIRED)',
         '      object: $=TenXEnv.get("INDEX_READ_OBJECT", "")  # (REQUIRED)',
         "index object taken from the environment"),
    ],
    QUERY: [
        ("    objectStorageName: AWS", "    objectStorageName: Local",
         "query accessor set to the local file system"),
        ('    from: now("-5m")   # (REQUIRED)', '    from: now("-24h")   # (REQUIRED)',
         "query window widened to a day"),
        ('    search: (severity_level == "ERROR") || (severity_level == "FATAL")',
         '    search: $=TenXEnv.get("QUERY_SEARCH", "")',
         "query search expression taken from the environment"),
        ("    writeResults: false", "    writeResults: true",
         "query results writer turned on"),
        ("    filters: $?queryFilters",
         '    filters:\n      - $=TenXEnv.get("QUERY_FILTER", "")',
         "query filter taken from the environment"),
        ("    objectStorageArgs: [invoke, sqs]", "    objectStorageArgs: []",
         "query SQS invocation removed"),
        ('        timeslice: parseDuration("1m")', "        timeslice: 0",
         "scan slices run in the coordinator's own thread pool"),
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-dir", required=True)
    args = ap.parse_args()
    root = pathlib.Path(args.config_dir)
    for parts, edits in EDITS.items():
        path = root.joinpath(*parts)
        if not path.exists():
            sys.exit(f"patch failed: {path} is not in the config tree")
        text = path.read_text()
        for old, new, what in edits:
            if old not in text:
                sys.exit(f"patch failed, {what}: the shipped text is not in {path}")
            text = text.replace(old, new, 1)
            print(f"  patched {what}")
        path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
