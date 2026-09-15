**Closed.** A day predicate prunes to that day's objects and a time-only
predicate opens every object in the bucket, at one S3 GET per object either way.

The run wrote its own cold objects, and those objects were then replicated
across thirty day partitions with their timestamps shifted by whole days, the
way `../../clickhouse-clickstack/run_scale.sh` replicates rows. Two things about
the replicated objects are not what the collector wrote, and both are here
rather than in a footnote: they are gzipped, because thirty uncompressed copies
of the cold side of the full capture does not fit on the host this ran on, and
ClickHouse wrote them, because shifting the day is what the replication is for.
The object count, the request count and which objects a predicate opens are
unaffected by either.

Read the GET column against the object counts. One day holds six objects and
two of them belong to the service asked for. The service and day query opens
exactly those two. The service alone opens sixty, which is that service's two
objects on each of thirty days. Every query that names only a time opens all
one hundred and eighty, because the day in the path is the only thing that can
exclude an object before it is opened, and `Timestamp` lives inside the file.
Adding `day >= today() - 1` to the same time-only query takes it from one
hundred and eighty GETs and 7,449 ms to twelve and 468 ms.

The pattern hash behaves the same way: named alone it opens every object,
because the hash is a column inside the file and not a path segment. A query
that names a type and a day pays six.

What this does not say: nothing about a real estate's day mix, because every day
here is a replica of one day's cold rows; nothing about Parquet row-group
skipping, because these objects are JSON; and nothing about the upload-day trap,
because ClickHouse synthesized these day partitions from the timestamp column.
The collector's own S3 exporter takes the `day=` segment from the clock at
upload time rather than from the record: `awss3exporter/internal/upload/writer.go`
line 84 reads `now := clock.Now(ctx)` and line 95 passes that `now` to `Build`.
On a steady feed the two agree. After a backfill or a replay they do not, and a
`day >=` predicate then drops rows that sit inside the time window. No query in
this run exercises that, because no object here carries a path day the collector
chose.
