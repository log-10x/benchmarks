**Closed, and the answer on this capture is no.** The per-type policy does not
beat a competent collector-only policy on hot compute. It beats it on what a
query can ask, and that is a different claim.

Three arms, the whole capture each time, on a ClickHouse whose `query_log` and
`part_log` were truncated before each: no offload, a collector-only policy by
service and severity, and the per-type cap with the overflow offloaded. The
collector-only policy is the one a competent engineer writes after reading a
census once: parse a severity out of the line, send the two chattiest services'
INFO and DEBUG to the object store, leave everything else alone. The two
chattiest services were read off the first arm's own hot table.

Insert plus merge CPU: the collector-only arm is the cheapest of the three. It
keeps more rows than the per-type arm and still costs less to insert and merge,
and the reason is in the bytes column rather than the rows column. The receiver
groups a multi-line event into one record, so the per-type arm's rows are fewer
and bigger, and ClickStack's text index is built over `Body`. Fewer, larger rows
is not automatically less work on a table whose cost is dominated by indexing
the text.

That grouping is also why the arms do not hold the same number of records at
all: the collector-only arm stores one record per input line, 197,430 of them,
and the two arms with the receiver in the path store about 157,000. Any
comparison of row counts across those arms is a comparison of two different
units, and the table says so.

What the per-type arm buys is the question the collector-only arm cannot answer.
`Q2`, the count of one message type, is asked by hash. In the collector-only arm
there is no hash on any row, hot or cold, so the question is not answered
wrongly, it cannot be put. `Q1` and `Q3` are answered by all three arms, and the
hot table's answers differ from the Merge table's in both offload arms, in the
direction the offload moved the rows.

**What this does not say.** Nothing about money: there is no Cloud autoscaler
here, no bill and no compute term, and the CPU seconds are ClickHouse's own
accounting on one container on one host. Merge CPU in particular is noisy: it
depends on which parts the scheduler happened to merge inside the arm's window,
and the per-type arm's merge figure is larger than the no-offload arm's despite
a quarter of the rows. A claim about compute on a customer estate needs that
estate's own `system.query_log`, not this.

**One thing to fix before this is rerun.** The three arms ran as three separate
invocations, on three fresh stacks, because an unrelated process on the host
removed the containers twice mid-run. Each arm's numbers are internally
consistent and come from its own truncated logs; a single uninterrupted run of
all three on one stack would be better and is what the script does by default.
