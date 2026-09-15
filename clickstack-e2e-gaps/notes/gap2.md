**Closed on the route, open on Parquet.** Vector carries the cold branch end to
end and the objects read back through the same tables. What this run did not
measure is Parquet, because the image was a year old and the probe asked for a
key that was never the right one.

What Vector does is the rest of it, and it does it without complaint: an
OpenTelemetry source takes the returned stream from the routing collector, a
`route` transform makes the offload decision on `routeState`, a `remap`
transform shapes each record into the body and attribute map the cold table
reads, and `aws_s3` writes objects with the service and the day in `key_prefix`.
The objects are read by the same S3 table and the same Merge table the harness
uses, with no change to either, and the same queries answer the same numbers.

**What the Parquet probe in this run is worth, which is nothing.** The run
pinned `timberio/vector:0.50.0-debian`, published 2025-09-23, and validated a
configuration that set `encoding.codec: parquet`. That key names the per event
serializer and has never taken a columnar codec. Vector writes Parquet on the
`aws_s3` sink through a separate option, `batch_encoding.codec`, added in
v0.55.0 on 2026-04-22 and carried by the official release binaries from v0.56.0
on 2026-06-03; upstream issue 1374 was closed on 2026-04-28, by pull requests
25156 and 25321. The pinned build predates all of that and refuses
`batch_encoding` as an unknown field. So the codec list the probe printed is the
list 0.50.0 carried, and this run measured nothing about Parquet in Vector.

**Where the missing codec claim still holds.** The OpenTelemetry Collector
contrib `awss3exporter` takes four marshalers, `otlp_json`, `otlp_proto`,
`sumo_ic` and `body`, and none of them writes Parquet. The request for one,
contrib issue 45103, was closed `not_planned` on 2026-05-10.

Two things about the run are worth reading off the table rather than the prose.
The object count is what a large batch buys: fifty objects for the whole cold
side, against one S3 GET each on a query that names only a time. And the Parquet
copy of exactly the same rows, written by ClickHouse rather than by Vector, is
three objects and 1.3 MiB against fifty objects and 165 MiB of JSON, and answers
every query identically. The text search reads 139,354 rows through the Parquet
copy against 157,083 through the JSON objects, and why is not settled here:
nothing in this run read `ParquetPrunedRowGroups` or `ParquetReadRowGroups` out
of `system.query_log`, and the query is a substring test that neither min/max
nor bloom statistics can prune.

Two footnotes on the run itself. Vector 0.50 has no `ndjson` codec: the newline
delimited JSON the S3 table reads is the `json` codec with newline framing. And
end to end acknowledgements on the OpenTelemetry source hold the gRPC response
until the S3 batch flushes, which pushes back through the collector and stalls
the entire route, hot side included; the first run of this script moved 1,425
records of 157,083 for that reason, and the config turns them off.
