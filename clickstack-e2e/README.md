# clickstack-e2e

The whole ClickHouse route, end to end, in containers, in one command: a
released log capture read by an OpenTelemetry Collector, regulated by the 10x
receiver, split by the mark the receiver puts on each record, and read back out
of ClickHouse as one table over the rows that stayed and the rows that left.

Everything a ClickHouse surface claims should be traceable to a run of this
harness. The numbers live in `results/`, not in this file.

## Run it

```bash
./run.sh              # everything
KEEP=1 ./run.sh       # leave the containers up afterwards
LINES=20000 ./run.sh  # feed a smaller slice of the capture
```

Needs Docker with about 8 GB of memory, a few GB of free disk, and roughly
fifteen minutes. The capture is fetched into `data/` on the first run and its
sha256 is checked on every run. Every container is torn down at the end unless
`KEEP=1`.

The run writes `results/clickstack-e2e-<date>.md` and `results/results.json`.

## The shape

```
  slice of the released capture
            |
            |  filelog receiver, JSON envelope parsed, `log` value as the body
            v
  collector  --OTLP-->  10x receiver  --OTLP-->  collector
                        (cap + action)              |
                                                    |  routing connector on routeState
                                          +---------+---------+
                                          |                   |
                                   routeState=offload      everything else
                                          |                   |
                                    awss3 exporter        ClickStack's own
                                    -> MinIO, the         OTLP endpoint
                                       service and the       |
                                       day in the path       v
                                          |            ClickStack's ClickHouse
                                          v            exporter -> otel_logs
                                    S3 engine table
                                          |
                                          +--> Merge table over both <--+
```

The receiver reads two files: `conf/caps.csv` gives a byte cap per service, and
`conf/actions.csv` gives that service's disposition for the excess. Both must
exist and neither may be empty, and a service with no row in the cap file is not
regulated at all, which is what makes an uncapped service a control.

## What a run proves

- That the marks the regulator puts on a record survive an OTLP round trip
  through the receiver and arrive on the returned record as attributes a
  collector can route on. The results file lists every field that arrived and
  keeps one returned record verbatim.
- That a stock routing connector splits the returned stream on that mark, that
  the marked slice lands in an object store with the service and the day in the
  object path, and that the rest is inserted by ClickStack's own exporter into
  ClickStack's own table.
- That ClickHouse reads the offloaded objects in place through an S3 engine
  table, and reads them together with the hot table through a Merge table, with
  `_table` naming which side each row came from.
- That a counts-per-type table answers a dashboard question over both sides
  after the split.
- What each query shape costs over the Merge table, in rows read, object-store
  requests and time, against the same query over the hot table alone.
- That every record the receiver returned is in hot plus cold exactly once,
  counted in total and per pattern hash.

## What a run does not prove

- Nothing about ClickHouse Cloud. There is no compute term, no bill and no
  autoscaler here; the run measures requests and rows, not money.
- Nothing about alerts. No alert is defined, fired or compared.
- Nothing about a real estate's query mix. The query list is written here, not
  taken from a customer's `system.query_log`.
- Nothing about multi-day pruning. The objects are written during the run, so
  they carry one day in the path. Pruning across many days and many objects was
  measured separately, in the research note behind this harness.
- Nothing about the Retriever. Value-level fetch-back is a different door and
  is not exercised.
- Nothing about scale. The default slice is a few tens of thousands of records,
  enough to exercise every hop and too small to say anything about throughput.

## Files

| File | What it is |
|---|---|
| `run.sh` | the whole run: containers, feed, schema, measurement, teardown |
| `conf/router.yaml` | the collector config, both pipelines, as it ran |
| `conf/caps.csv`, `conf/actions.csv` | the per-service policy the receiver loads |
| `conf/schema_hot.sql` | the counts table and its view, created before any data flows |
| `conf/schema_cold.sql` | the S3 engine table, the rename view, the Merge table |
| `patch_engine_config.py` | the edits the harness makes to the engine's shipped config, each asserted |
| `report.py` | the wire census, the timed queries, the lossless check, the results file |
| `results/` | committed results of the last run |

`patch_engine_config.py` is the file to read first if a run comes back with no
marks on the wire: it names the four edits and fails loudly if the shipped
config has moved under it.
