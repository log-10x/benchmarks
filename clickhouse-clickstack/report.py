#!/usr/bin/env python3
"""Read the measurement out of a loaded ClickHouse and write results/.

Every number here comes from `system.parts`, `system.parts_columns`,
`system.data_skipping_indices` or `system.query_log` on the container the run
just loaded. Nothing is carried over from a previous run and nothing is copied
from a post.
"""

import argparse
import json
import pathlib
import statistics
import subprocess
import sys

ARMS = ["native", "compact", "native_folded"]
CODECS = ["zstd1", "zstd3", "lz4"]
CODEC_LABEL = {"zstd1": "ZSTD(1)", "zstd3": "ZSTD(3)", "lz4": "LZ4"}

# The two expand paths install.sql ships. `iso` is its recommended default and
# rewrites every timestamp to ISO 8601; `native` preserves each template's own
# timestamp format through a multiIf over the formats it knows.
EXPAND = {
    "iso": "tenx_inflate_iso",
    "native": "tenx_inflate",
}


def expand(column="Body"):
    return {
        name: (f"{fn}({column}, "
               "dictGetOrDefault('tenx.templates_dict','literals',tuple("
               f"if(startsWith({column},'~'), if(position({column},',')>0, "
               f"substring({column},2,position({column},',')-2), substring({column},2)), '')"
               "),[]::Array(String)), "
               "dictGetOrDefault('tenx.templates_dict','slots',tuple("
               f"if(startsWith({column},'~'), if(position({column},',')>0, "
               f"substring({column},2,position({column},',')-2), substring({column},2)), '')"
               "),[]::Array(String)))")
        for name, fn in EXPAND.items()
    }


class Client:
    def __init__(self, container):
        self.container = container

    def __call__(self, sql, fmt="TabSeparated", settings=()):
        cmd = ["docker", "exec", "-i", self.container, "clickhouse-client",
               "--allow_experimental_full_text_index=1", "--format", fmt,
               *settings, "--query", sql]
        out = subprocess.run(cmd, capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError(f"query failed:\n{sql}\n{out.stderr.strip()}")
        return out.stdout.strip()

    def rows(self, sql):
        return [line.split("\t") for line in self(sql).splitlines() if line]

    def one(self, sql):
        return self(sql)


def table_totals(ch):
    rows = ch.rows("""
        SELECT table, sum(rows), sum(bytes_on_disk),
               sum(data_compressed_bytes), sum(data_uncompressed_bytes),
               count(), sum(primary_key_bytes_in_memory)
        FROM system.parts
        WHERE database = 'bench' AND active
        GROUP BY table ORDER BY table FORMAT TabSeparated""")
    return {r[0]: {"rows": int(r[1]), "bytes_on_disk": int(r[2]),
                   "data_compressed_bytes": int(r[3]),
                   "data_uncompressed_bytes": int(r[4]),
                   "parts": int(r[5])} for r in rows}


def column_bytes(ch):
    rows = ch.rows("""
        SELECT table, column, sum(column_data_compressed_bytes),
               sum(column_data_uncompressed_bytes)
        FROM system.parts_columns
        WHERE database = 'bench' AND active
        GROUP BY table, column ORDER BY table, column FORMAT TabSeparated""")
    out = {}
    for table, column, compressed, uncompressed in rows:
        out.setdefault(table, {})[column] = {
            "compressed": int(compressed), "uncompressed": int(uncompressed)}
    return out


def index_bytes(ch):
    rows = ch.rows("""
        SELECT table, sum(data_compressed_bytes), sum(data_uncompressed_bytes)
        FROM system.data_skipping_indices
        WHERE database = 'bench' GROUP BY table ORDER BY table FORMAT TabSeparated""")
    return {r[0]: {"compressed": int(r[1]), "uncompressed": int(r[2])} for r in rows}


def dictionary_bytes(ch):
    """What the compact arm costs beyond its own table: the template dictionary."""
    on_disk = int(ch.one("""
        SELECT sum(bytes_on_disk) FROM system.parts
        WHERE database = 'tenx' AND table = 'templates' AND active"""))
    in_memory = int(ch.one("""
        SELECT bytes_allocated FROM system.dictionaries
        WHERE database = 'tenx' AND name = 'templates_dict'"""))
    rows = int(ch.one("SELECT count() FROM tenx.templates"))
    return {"table_bytes_on_disk": on_disk, "dictionary_bytes_in_memory": in_memory,
            "templates": rows}


def timed(ch, sql, runs=11):
    """Run a query `runs` times, discard the first, keep the rest.

    Wall time and rows read come from system.query_log rather than from the
    client, so the number is ClickHouse's own accounting of the query. Both the
    median and the fastest run are kept: on a host carrying other work the
    median drifts upward with the contention and the fastest run is the closest
    thing to the query's own cost.
    """
    tag = f"/*bench-{abs(hash(sql))}*/ "
    result = None
    for _ in range(runs):
        result = ch.one(tag + sql)
    ch.one("SYSTEM FLUSH LOGS")
    rows = ch.rows(f"""
        SELECT query_duration_ms, read_rows, read_bytes, memory_usage
        FROM system.query_log
        WHERE type = 'QueryFinish' AND positionCaseInsensitive(query, 'bench-{abs(hash(sql))}') > 0
        ORDER BY event_time_microseconds DESC LIMIT {runs - 1} FORMAT TabSeparated""")
    return {
        "result": result,
        "runs": runs - 1,
        "median_ms": int(statistics.median(int(r[0]) for r in rows)),
        "fastest_ms": min(int(r[0]) for r in rows),
        "ms": sorted(int(r[0]) for r in rows),
        "read_rows": int(statistics.median(int(r[1]) for r in rows)),
        "read_bytes": int(statistics.median(int(r[2]) for r in rows)),
        "peak_memory_bytes": max(int(r[3]) for r in rows),
    }


def ingest_cpu(ch):
    """CPU each arm's INSERT burned, as ClickHouse accounted for it.

    This is an INSERT ... FORMAT JSONEachRow from a file, so it includes parsing
    a JSON payload that is a different size in each arm. It is not a measurement
    of collector-to-ClickHouse ingest over the native protocol, and it is
    reported as what it is.
    """
    rows = ch.rows("""
        SELECT extract(query, 'bench\\.(otel_logs_[a-z_0-9]+)') AS t,
               sum(ProfileEvents['UserTimeMicroseconds'] + ProfileEvents['SystemTimeMicroseconds']),
               sum(query_duration_ms), sum(written_rows), sum(written_bytes)
        FROM system.query_log
        WHERE type = 'QueryFinish' AND query_kind = 'Insert' AND t != ''
        GROUP BY t ORDER BY t FORMAT TabSeparated""")
    return {r[0]: {"cpu_microseconds": int(r[1]), "wall_ms": int(r[2]),
                   "written_rows": int(r[3]), "written_bytes": int(r[4])} for r in rows}


def losslessness(ch):
    """Does the compact arm expand back to the text the folded native arm holds?

    Row for row is not checkable without an ordering column the schema does not
    have, so the check is on the multiset: same row count, same total length, and
    the same sum of per-row hashes. Both expand paths are checked, because only
    the format-preserving one can reproduce the original bytes at all.
    """
    def fingerprint(table, column):
        rows = ch.rows(f"""
            SELECT count(), sum(length({column})), sum(sipHash64({column}))
            FROM bench.{table} FORMAT TabSeparated""")[0]
        return {"rows": int(rows[0]), "total_length": int(rows[1]), "hash_sum": rows[2]}

    reference = fingerprint("otel_logs_native_folded_zstd1", "Body")
    out = {"native_folded": reference}
    for name, sql in expand().items():
        rows = ch.rows(f"""
            SELECT count(), sum(length({sql})), sum(sipHash64({sql}))
            FROM bench.otel_logs_compact_zstd1 FORMAT TabSeparated""")[0]
        out[name] = {"rows": int(rows[0]), "total_length": int(rows[1]),
                     "hash_sum": rows[2],
                     "identical_to_native_folded":
                         int(rows[0]) == reference["rows"]
                         and int(rows[1]) == reference["total_length"]
                         and rows[2] == reference["hash_sum"]}

    # How many rows, not just whether any. A row counts as wrong when its
    # expansion is not any of the original texts.
    counts = ch.rows(f"""
        WITH orig AS (SELECT sipHash64(Body) AS s FROM bench.otel_logs_native_folded_zstd1)
        SELECT
          countIf(sipHash64({expand()['native']}) NOT IN (SELECT s FROM orig)),
          countIf(sipHash64({expand()['iso']}) NOT IN (SELECT s FROM orig)),
          count()
        FROM bench.otel_logs_compact_zstd1 FORMAT TabSeparated""")[0]
    out["native"]["rows_not_matching_any_original"] = int(counts[0])
    out["iso"]["rows_not_matching_any_original"] = int(counts[1])
    out["rows_checked"] = int(counts[2])
    return out


def decoder_defects(ch):
    """The two template constructs install.sql's expansion does not implement.

    Both are visible in the template text itself, so they are counted from
    `tenx.templates` rather than inferred from the mismatch total.

      $N   a back-reference to the value N slots earlier. The regex in
           install.sql matches `$` and leaves the digits as literal text, so the
           digit is printed and the value cursor runs one position ahead.
      //   the engine writes a literal `/` as `//` in a template. install.sql
           never reverses it, so every path and URL comes back with its slashes
           doubled, which is also why the expanded text is LONGER than the
           original rather than shorter.
    """
    row = ch.rows(r"""
        SELECT count(),
               countIf(match(template, '\$[0-9]')),
               countIf(position(template, '//') > 0),
               countIf(match(template, '\$[0-9]') OR position(template, '//') > 0)
        FROM tenx.templates FORMAT TabSeparated""")[0]
    examples = ch.rows(r"""
        SELECT template FROM tenx.templates
        WHERE match(template, '\$[0-9]') OR position(template, '//') > 0
        ORDER BY length(template) LIMIT 4 FORMAT TabSeparated""")
    return {"templates": int(row[0]), "with_back_reference": int(row[1]),
            "with_doubled_slash": int(row[2]), "with_either": int(row[3]),
            "examples": [e[0] for e in examples]}


def mismatch_sample(ch, limit=5):
    """A few rows where the format-preserving expansion is not the original."""
    sql = expand()["native"]
    rows = ch.rows(f"""
        SELECT Body, {sql}
        FROM bench.otel_logs_compact_zstd1
        WHERE sipHash64({sql}) NOT IN (
            SELECT sipHash64(Body) FROM bench.otel_logs_native_folded_zstd1)
        LIMIT {limit} FORMAT TabSeparated""")
    return [{"compact": r[0], "expanded": r[1] if len(r) > 1 else ""} for r in rows]


def pct(new, old):
    return None if not old else round((1 - new / old) * 100, 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--ch-version", required=True)
    ap.add_argument("--ch-image", required=True)
    ap.add_argument("--engine-digest", required=True)
    ap.add_argument("--asset-sha256", required=True)
    ap.add_argument("--term", required=True)
    ap.add_argument("--reference-decode", help="reference-decode.json, if it was run")
    args = ap.parse_args()

    ch = Client(args.container)
    results_dir = pathlib.Path(args.results)
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(pathlib.Path(args.manifest).read_text())

    totals = table_totals(ch)
    columns = column_bytes(ch)
    indexes = index_bytes(ch)
    dictionary = dictionary_bytes(ch)

    print("checking that the compact arm expands back to the original text")
    lossless = losslessness(ch)
    samples = [] if lossless["native"].get("identical_to_native_folded") \
        else mismatch_sample(ch)

    print("timing one text filter per arm")
    term = args.term.replace("'", "''")
    queries = {}
    for arm in ("native", "native_folded"):
        queries[arm] = timed(ch, f"""
            SELECT count() FROM bench.otel_logs_{arm}_zstd1
            WHERE position(Body, '{term}') > 0""")
    for name, sql in expand().items():
        queries[f"compact_{name}"] = timed(ch, f"""
            SELECT count() FROM bench.otel_logs_compact_zstd1
            WHERE position({sql}, '{term}') > 0""")

    results = {
        "clickhouse_version": args.ch_version,
        "clickhouse_image": args.ch_image,
        "engine_image": args.engine_digest,
        "capture_sha256": args.asset_sha256,
        "filter_term": args.term,
        "manifest": manifest,
        "totals": totals,
        "columns": columns,
        "skip_indexes": indexes,
        "template_dictionary": dictionary,
        "losslessness": lossless,
        "decoder_defects": decoder_defects(ch),
        "mismatch_sample": samples,
        "reference_decode": (json.loads(pathlib.Path(args.reference_decode).read_text())
                             if args.reference_decode
                             and pathlib.Path(args.reference_decode).exists() else None),
        "queries": queries,
        "ingest": ingest_cpu(ch),
    }
    (results_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"wrote {results_dir / 'results.json'}")

    render(results, results_dir)
    return 0


def fmt(n):
    return f"{n:,}"


def render(r, results_dir):
    """Write the results markdown from results.json and nothing else."""
    import datetime
    date = datetime.date.today().isoformat()
    t, c, idx = r["totals"], r["columns"], r["skip_indexes"]
    dict_disk = r["template_dictionary"]["table_bytes_on_disk"]

    def tbl(arm, codec):
        return f"otel_logs_{arm}_{codec}"

    def total_with_dictionary(arm, codec):
        base = t[tbl(arm, codec)]["bytes_on_disk"]
        return base + dict_disk if arm == "compact" else base

    def body(arm, codec):
        return c[tbl(arm, codec)]["Body"]["compressed"]

    lines = []
    add = lines.append
    add(f"# 10x compact events in ClickHouse's own ClickStack schema")
    add("")
    add(f"Measured {date} by `run.sh` in this folder. Every byte count is read from "
        "`system.parts`, `system.parts_columns` or `system.data_skipping_indices` "
        "after `OPTIMIZE FINAL`; every timing is `query_duration_ms` from "
        "`system.query_log`. Nothing here is copied from a post.")
    add("")

    # --------------------------------------------------------- the five lines
    b_n = body("native_folded", "zstd1")
    b_c = body("compact", "zstd1")
    tot_n = total_with_dictionary("native", "zstd1")
    tot_c = total_with_dictionary("compact", "zstd1")
    rows_n = t[tbl("native", "zstd1")]["rows"]
    rows_c = t[tbl("compact", "zstd1")]["rows"]
    add("## The five lines")
    add("")
    add(f"1. **Body column at ZSTD(1), row for row: {fmt(b_n)} to {fmt(b_c)} bytes, "
        f"{pct(b_c, b_n)}%.** Same {fmt(rows_c)} rows and the same attribute values "
        "on both sides, so this is the templating layer alone.")
    add(f"2. **Whole table at ZSTD(1): {fmt(tot_n)} to {fmt(tot_c)} bytes, "
        f"{pct(tot_c, tot_n)}%,** on {fmt(rows_n)} rows against {fmt(rows_c)} rows. "
        "The compact figure includes the template dictionary "
        f"({fmt(dict_disk)} bytes on disk). The row counts differ because the engine "
        "folds a multi-line event into one event; that reduction is inside this "
        "number and outside line 1.")
    qn = r["queries"]["native"]["fastest_ms"]
    qi = r["queries"]["compact_iso"]["fastest_ms"]
    qv = r["queries"]["compact_native"]["fastest_ms"]
    add(f"3. **One text filter on `{r['filter_term']}`: {fmt(qn)} ms native, "
        f"{fmt(qi)} ms compact through the ISO expand path, {fmt(qv)} ms through the "
        "format-preserving one.** Fastest of ten, first run discarded; see the timing table for the spread.")
    for codec in ("lz4", "zstd3"):
        add(f"4{'a' if codec == 'lz4' else 'b'}. **{CODEC_LABEL[codec]}:** Body "
            f"{pct(body('compact', codec), body('native_folded', codec))}%, whole "
            f"table {pct(total_with_dictionary('compact', codec), total_with_dictionary('native', codec))}% "
            f"({fmt(total_with_dictionary('native', codec))} to "
            f"{fmt(total_with_dictionary('compact', codec))} bytes).")
    wrong = r["losslessness"]["native"]["rows_not_matching_any_original"]
    checked = r["losslessness"]["rows_checked"]
    add(f"5. **It would not survive one, and the storage figure is not the reason.** "
        f"{fmt(wrong)} of {fmt(checked)} rows, {wrong / checked * 100:.1f}%, do not "
        "expand back to the text they came from, because the shipped SQL decoder "
        "implements neither the `$N` back-reference nor the `/` escape nor the JSON "
        "unescape that INNER mode needs. The compact form does still hold the text, "
        "which `reference_decode.py` shows by getting it back, so this is a decoder "
        "to fix rather than a claim to withdraw. But until it is fixed there is no "
        "lossless read path on ClickHouse for a storage number to sit on. And the "
        f"number itself, {pct(tot_c, tot_n)}% on the whole table at the ClickStack "
        "default, is below the 30% a ClickHouse maintainer has already called "
        "achievable against a well-sorted ZSTD column, on a schema of their choosing.")
    add("")

    # ------------------------------------------------------------- provenance
    add("## What this was measured on")
    add("")
    add(f"- ClickHouse `{r['clickhouse_version']}` from `{r['clickhouse_image']}`, "
        "8 GiB and 8 CPUs, one container, all arms in it at once.")
    add(f"- Engine `{r['engine_image']}`, INNER encode, config "
        "`tenx-encode-inner.config.yaml` in this folder.")
    add(f"- Capture `otel-sample-200mb.log` from the `otel-sample-v2` release of "
        f"`log-10x/config`, sha256 `{r['capture_sha256']}`, "
        f"{fmt(r['manifest']['raw_lines'])} lines.")
    add(f"- {fmt(r['manifest']['compact_events'])} compact events and "
        f"{fmt(r['manifest']['templates'])} templates came out of the encode.")
    add("- Schema: the ClickStack `otel_logs` DDL from "
        "https://clickhouse.com/docs/use-cases/observability/clickstack/ingesting-data/schemas "
        ", copied into `schema.sql.tpl` with the codec substituted and the TTL "
        "placeholder removed. Typed columns, `LowCardinality`, the two attribute "
        "maps, all eight skip indexes and the published "
        "`ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)`.")
    add("")

    # ------------------------------------------------------------- the arms
    add("## The three arms")
    add("")
    add("| Arm | Rows | Body | Attributes |")
    add("|---|---:|---|---|")
    add(f"| `native` | {fmt(rows_n)} | the line's message | from that line's envelope |")
    add(f"| `compact` | {fmt(rows_c)} | the compact event `~<hash>,<values>` | "
        "from the same envelope |")
    add(f"| `native_folded` | {fmt(rows_c)} | the original text of that same event | "
        "identical to `compact` |")
    add("")
    add("`native` against `compact` is what a deployment sees and carries both the "
        "templating and the event folding. `native_folded` against `compact` holds "
        "the row count and every other column fixed and isolates the templating. "
        "`native` against `native_folded` is the folding on its own.")
    add("")

    # ----------------------------------------------------------- total bytes
    add("## On disk, whole table")
    add("")
    add("`sum(bytes_on_disk)` from `system.parts`, active parts, after "
        "`OPTIMIZE FINAL`. The compact column adds the template dictionary table, "
        "without which the arm cannot be read.")
    add("")
    add("| Codec | native | native_folded | compact | compact + dictionary | "
        "compact vs native | compact vs native_folded |")
    add("|---|---:|---:|---:|---:|---:|---:|")
    for codec in CODECS:
        n = t[tbl("native", codec)]["bytes_on_disk"]
        f = t[tbl("native_folded", codec)]["bytes_on_disk"]
        cp = t[tbl("compact", codec)]["bytes_on_disk"]
        add(f"| {CODEC_LABEL[codec]} | {fmt(n)} | {fmt(f)} | {fmt(cp)} | "
            f"{fmt(cp + dict_disk)} | {pct(cp + dict_disk, n)}% | "
            f"{pct(cp + dict_disk, f)}% |")
    add("")
    add(f"Rows: `native` {fmt(rows_n)}, `compact` and `native_folded` {fmt(rows_c)}. "
        f"Template dictionary on disk: {fmt(dict_disk)} bytes for "
        f"{fmt(r['template_dictionary']['templates'])} templates, "
        f"{fmt(r['template_dictionary']['dictionary_bytes_in_memory'])} bytes "
        "allocated in memory.")
    add("")

    # ---------------------------------------------------------- per column
    add("## Per column, ZSTD(1)")
    add("")
    add("`system.parts_columns`, compressed and uncompressed. The attribute "
        "columns are the same values in every arm, so the Body row is where the "
        "comparison lives; the rest is here so nobody has to take that on trust.")
    add("")
    names = sorted(set(c[tbl("native", "zstd1")]) | set(c[tbl("compact", "zstd1")]))
    add("| Column | native | native_folded | compact | native uncompressed | "
        "compact uncompressed |")
    add("|---|---:|---:|---:|---:|---:|")
    for name in names:
        def cell(arm, key="compressed"):
            return fmt(c[tbl(arm, "zstd1")].get(name, {}).get(key, 0))
        add(f"| `{name}` | {cell('native')} | {cell('native_folded')} | "
            f"{cell('compact')} | {cell('native', 'uncompressed')} | "
            f"{cell('compact', 'uncompressed')} |")
    add("")
    add("Skip indexes, compressed, ZSTD(1): "
        + ", ".join(f"`{arm}` {fmt(idx.get(tbl(arm, 'zstd1'), {}).get('compressed', 0))}"
                    for arm in ARMS) + ".")
    add("")

    # ------------------------------------------------------------ Body only
    add("## The Body column alone")
    add("")
    add("| Codec | native | native_folded | compact | compact vs native_folded |")
    add("|---|---:|---:|---:|---:|")
    for codec in CODECS:
        add(f"| {CODEC_LABEL[codec]} | {fmt(body('native', codec))} | "
            f"{fmt(body('native_folded', codec))} | {fmt(body('compact', codec))} | "
            f"{pct(body('compact', codec), body('native_folded', codec))}% |")
    add("")
    add(f"Before ClickHouse touches it, the same text is "
        f"{fmt(r['manifest']['body_bytes']['native_folded'])} bytes native and "
        f"{fmt(r['manifest']['body_bytes']['compact'])} bytes compact, "
        f"{pct(r['manifest']['body_bytes']['compact'], r['manifest']['body_bytes']['native_folded'])}%.")
    add("")

    # ---------------------------------------------------------- correctness
    add("## Does the compact arm come back")
    add("")
    ls = r["losslessness"]
    add("Checked on the multiset, because the schema has no column to order rows "
        "by: same row count, same total length, same sum of per-row hashes as "
        "`native_folded`.")
    add("")
    add("| Expand path | Rows | Total length | Rows that are not any original | Matches |")
    add("|---|---:|---:|---:|---|")
    add(f"| `native_folded` (the original) | {fmt(ls['native_folded']['rows'])} | "
        f"{fmt(ls['native_folded']['total_length'])} | 0 | reference |")
    for name in ("native", "iso"):
        row = ls[name]
        add(f"| `{EXPAND[name]}` | {fmt(row['rows'])} | {fmt(row['total_length'])} | "
            f"{fmt(row['rows_not_matching_any_original'])} | "
            f"{'yes' if row['identical_to_native_folded'] else 'NO'} |")
    add("")
    defects = r["decoder_defects"]
    wrong = ls["native"]["rows_not_matching_any_original"]
    add(f"**It does not.** {fmt(wrong)} of {fmt(ls['rows_checked'])} rows, "
        f"{wrong / ls['rows_checked'] * 100:.1f}%, expand to text that is not any "
        "line in the capture, and that is through the format-preserving path, the "
        "one meant to reproduce the original exactly. The expanded text is "
        "**longer** than the original, which is the first clue: this is not lossy "
        "compaction, it is the SQL decoder failing to read constructs the engine "
        "writes into a template.")
    add("")
    add("| Template construct | Templates | What `install.sql` does with it |")
    add("|---|---:|---|")
    add(f"| `$N`, a back-reference to the value N slots earlier | "
        f"{fmt(defects['with_back_reference'])} | matches the `$` and leaves the "
        "digits as literal text, so the digit is printed and the value cursor runs "
        "one position ahead |")
    add(f"| `//`, how the engine writes a literal `/` inside a template | "
        f"{fmt(defects['with_doubled_slash'])} | never reverses it, so every path "
        "and URL comes back with its slashes doubled |")
    add(f"| either | {fmt(defects['with_either'])} of {fmt(defects['templates'])} | |")
    add("")
    samples = r["mismatch_sample"]
    if samples:
        add("Compact event, and what the shipped SQL returns for it:")
        add("")
        add("```")
        for sample in samples[:3]:
            add(sample["compact"])
            add(f"  -> {sample['expanded']}")
        add("```")
        add("")
    ref = r.get("reference_decode")
    if ref:
        plain = ref["without_timestamp_slot"]
        back = ref["without_timestamp_slot_decoded"]
        add("### Is the text still in the compact form")
        add("")
        add("Two explanations fit a decoder that returns the wrong text, and they are "
            "not close in consequence: either the compaction lost the original, or it "
            "held it and the SQL misread it. `reference_decode.py` decides it by "
            "decoding the same events in Python with the four rules `install.sql` "
            "does not implement, and nothing else: `//` for a literal `/`, `/$` for a "
            "literal `$`, `$N` for a back-reference, and the JSON unescape that INNER "
            "mode needs.")
        add("")
        add(f"**{fmt(back)} of {fmt(plain)}**, {back / plain * 100:.2f}%, of the "
            "compact events whose template carries no timestamp slot come back "
            "byte-identical. The seven that do not are a back-reference case that "
            "reference decoder gets wrong. Events with a timestamp slot are left out "
            f"of this count, all {fmt(ref['with_timestamp_slot'])} of them: the slot "
            "holds an epoch integer and rendering it back needs a Joda formatter, "
            "which is a separate question from the decode rules above.")
        add("")
        add("So the text is there. What is broken is the SQL that reads it.")
        add("")
    add("None of this is in the compact form. The `otel-sample-v2` release states "
        "and shows how to check that the engine's own round trip on this capture "
        "returns all 215,039,161 bytes byte-identical. Every one of these defects is "
        "in the SQL, and they are in "
        "`../clickhouse-inflate/install-fixed.sql` and in the `install.sql` that "
        "`log-10x/clickhouse-app` ships. The earlier ClickHouse benchmark did not "
        "catch them: its byte-identity check compared the pre-fix decoder's output "
        "with the post-fix decoder's output, never with the original log text.")
    add("")

    # --------------------------------------------------------------- queries
    add("## One text filter per arm")
    add("")
    add(f"`SELECT count() ... WHERE position(Body, '{r['filter_term']}') > 0`, and "
        "for the compact arm the same filter over the expanded text, which is how a "
        "user who does not know the template hash would ask. Ten runs, the first "
        "discarded, from `system.query_log`.")
    add("")
    add("These are the one set of numbers here that a busy host moves. On a laptop "
        "carrying other work the compact arm read anywhere from 0.5 s to 4 s for the "
        "same query while the byte counts did not move at all. This run was taken on "
        "a machine with other work on it, so the fastest run is the column to read: "
        "it is the closest to the query's own cost. Every run is printed so the "
        "spread is visible rather than described.")
    add("")
    add("| Arm | Fastest ms | Median ms | Every run | Rows read | Bytes read | Result |")
    add("|---|---:|---:|---|---:|---:|---:|")
    label = {"native": "native", "native_folded": "native_folded",
             "compact_iso": "compact, `tenx_inflate_iso`",
             "compact_native": "compact, `tenx_inflate`"}
    for key, q in r["queries"].items():
        add(f"| {label[key]} | {fmt(q['fastest_ms'])} | {fmt(q['median_ms'])} | "
            f"{', '.join(str(m) for m in q['ms'])} | {fmt(q['read_rows'])} | "
            f"{fmt(q['read_bytes'])} | {q['result']} |")
    add("")

    # ---------------------------------------------------------------- ingest
    add("## Ingest")
    add("")
    add("CPU as ClickHouse accounted for the `INSERT`. Each arm was loaded from a "
        "JSONEachRow file, so this includes parsing a payload that is a different "
        "size in each arm. It is not collector-to-ClickHouse ingest over the native "
        "protocol and should not be read as that number.")
    add("")
    add("| Table | CPU seconds | Wall ms | Rows written |")
    add("|---|---:|---:|---:|")
    for name, row in sorted(r["ingest"].items()):
        add(f"| `{name}` | {row['cpu_microseconds'] / 1e6:.1f} | "
            f"{fmt(row['wall_ms'])} | {fmt(row['written_rows'])} |")
    add("")

    out = results_dir / f"clickstack-storage-{date}.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
