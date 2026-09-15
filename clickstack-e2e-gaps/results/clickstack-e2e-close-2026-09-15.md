# ClickStack end to end: closing the gaps, 2026-09-15

A second pass over `clickstack-e2e-gaps`, written after a record check found one
published claim false and four questions the first pass never put. Every number
here comes from a run on this host on 2026-09-15, and every run is named with the
command that produced it.

`clickstack-e2e-gaps-2026-09-15.md` holds the first pass and is unchanged in its
numbers. Where this file contradicts it, this file is the later measurement and
says so in its own section.

## The images that ran

Every image is pinned by tag and digest in `lib.sh`. These are the digests these
runs used.

| Image | Digest |
|---|---|
| `ghcr.io/log-10x/edge-10x:1.1.79` | `sha256:14357d8d570cb36ba6ca254802a1b8eedb11d8acf6916a936893f8e3babb41f4` |
| `clickhouse/clickstack-all-in-one:2.38.0` | `sha256:7b3bd9eec4e61aded56f705af7ddb2e8e49c54098d21aaaa7de6fde4d7c1f267` |
| `otel/opentelemetry-collector-contrib:0.160.0` | `sha256:799dc6cf12c96192af37b5bdba804da8c10b3bc563b43cb90c3f3c58d9572ad6` |
| `timberio/vector:0.58.0-debian` | `sha256:1c1ea358c617ea0b23003d5af87f7a678b30f8f7096437e680380c47fc13d2d9` |
| `quay.io/minio/minio:latest` | `sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` |
| `quay.io/minio/mc:latest` | `sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727` |
| `eclipse-temurin:23-jre` | `sha256:4972459272d4050ab14700677ac7a7511194f1d9ed333b95e886c3c8c80dedae` |

ClickHouse inside the ClickStack image reports `26.5.7.64`.

## Step 1: the runs no longer need a private build

**Closed.** The first pass ran the receiver as a run-cloud shadow jar on a JRE
image, because the shipped `edge-10x` image was then a native binary carrying
three OpenTelemetry return path defects. Both fixes shipped in 1.1.79, so
`g_engine_up` now runs the published image by default and `PATCHED_JAR` survives
as an optional override for anyone reproducing the first pass or testing an
unpublished build. Five of the six gap scripts need no jar, no engine checkout
and no private repository. Gap 3 still does, because it drives the Retriever
index and query pipelines rather than the receiver, and its own guard says so.

The smoke run below is gap 1 over a short feed on three days rather than thirty,
which is enough to prove the route end to end on the image: the receiver starts,
the harness's asserted config edits apply to the image's own config tree, records
come back marked, the collector writes objects, and the queries answer with their
object-store counters intact.

```
LINES=20000 DAYS=3 CSE_DATA_DIR=<repo>/clickstack-e2e/data ./gap1_multiday_pruning.sh
```

| Measure | Smoke on the image |
|---|---:|
| lines fed | 20,000 |
| records the receiver returned | 13,161 |
| rows in the hot table | 7,251 |
| rows in the objects | 5,910 |
| objects the run wrote | 9 |
| objects after replication across 3 days | 18 |
| bytes after replication | 762KiB |

| Query | Answer | Rows read | S3 GET | S3 LIST | ms |
|---|---|---:|---:|---:|---:|
| hot only, last hour, count | 7,251 | 6,253 | 0 | 0 | 50 |
| merge, service and one day, both in the path | 4,568 | 10,812 | 2 | 1 | 79 |
| merge, service, no day predicate | 15,039 | 19,948 | 6 | 1 | 204 |
| merge, time only, the shape HyperDX sends | 13,161 | 24,981 | 18 | 1 | 303 |
| merge, time plus `day >= today() - 1` | 13,161 | 19,071 | 12 | 1 | 127 |
| merge, text search for 'snapshot', no other filter | 1,338 | 24,981 | 18 | 1 | 423 |
| merge, text search for 'snapshot', one day | 203 | 13,161 | 6 | 1 | 276 |
| merge, one pattern hash, no time filter | 6,196 | 24,981 | 18 | 1 | 1,797 |
| merge, one pattern hash and one day | 1,953 | 13,161 | 6 | 1 | 243 |
| cold only, one day, count | 5,910 | 5,910 | 6 | 1 | 130 |

Read this table as a proof that the image path runs, not as a pruning
measurement: the committed pruning figures are gap 1's own, over the whole
capture and thirty days, in `clickstack-e2e-gaps-2026-09-15.md`. The shape holds
at this size too, at one GET per object and one LIST for the whole matched key
set.

The smoke's own `gap1.json` is not committed. `results/gap1.json` remains the
full-capture run.
