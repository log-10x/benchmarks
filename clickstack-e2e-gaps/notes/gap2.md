**Closed, and the answer to the first question is no.** Vector's shipped build
does not carry a parquet codec. Its own binary lists what it will take, and
parquet is not in the list. The research note that said Vector "writes Parquet
natively" is wrong, and any surface that rests on it needs correcting.

What Vector does do is the rest of it, and it does it without complaint: an
OpenTelemetry source takes the returned stream from the routing collector, a
`route` transform makes the offload decision on `routeState`, a `remap`
transform shapes each record into the body and attribute map the cold table
reads, and `aws_s3` writes objects with the service and the day in `key_prefix`.
The objects are read by the same S3 table and the same Merge table the harness
uses, with no change to either, and the same queries answer the same numbers.

Two things about the run are worth reading off the table rather than the prose.
The object count is what a large batch buys: fifty objects for the whole cold
side, against one S3 GET each on a query that names only a time. And the
Parquet copy of exactly the same rows, written by ClickHouse because Vector
cannot write it, is three objects and 1.3 MiB against fifty objects and 165 MiB
of JSON, answers every query identically, and reads fewer rows on the text
search because Parquet row groups are skipped on statistics that JSON has no
equivalent of. That is the shape of what a parquet codec at the collector would
be worth; it is not a measurement of Vector.

Two footnotes on the run itself. Vector 0.50 has no `ndjson` codec either: the
newline delimited JSON the S3 table reads is the `json` codec with newline
framing. And end to end acknowledgements on the OpenTelemetry source hold the
gRPC response until the S3 batch flushes, which pushes back through the
collector and stalls the entire route, hot side included; the first run of this
script moved 1,425 records of 157,083 for that reason, and the config turns them
off.
