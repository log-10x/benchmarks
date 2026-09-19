# The searches the licence numbers come from

`mc_historic_by_index.spl` and `mc_historic_no_split.spl` are the Monitoring
Console's own Historic License Usage searches, lifted out of the instance rather
than paraphrased: the panel's `$base_search$` and `$usage_search$` macros from
`splunk_monitoring_console/default/macros.conf`, expanded with the tokens the
view's Split By input sets, with `HOSTNAME` and `POOL` filled in at run time.
The one thing dropped from each is the stack or pool size overlay macro, which
adds the quota as a second series and no usage figure.

Note which source each one reads, because it is the reason there are two.

- **No split** reads `type="RolloverSummary"`, the daily rollup.
- **Split by Index** reads `type="Usage"`, the per-minute records, binned to a
  day. So does Split by Source, by Host and by Source Type.

That is not an inconsistency in the console. On Splunk 10.4.3 the rollup is a
single line per licence pool carrying the day's total, `b=`, with no `idx`,
`st`, `s` or `h` on it at all. There is no per-index figure in it to read. The
console splits from `Usage` because that is where the breakdown lives.

`rollover_by_index.spl` is the query the engineering ask names,
`type=RolloverSummary` broken down by index. It is kept, and the run keeps its
empty output, because the empty result is the finding: a reader who is told to
get per-arm GB/day out of the daily rollup will get nothing back, and needs to
know why before concluding the run failed.

`usage_by_index_sourcetype.spl` is where the per-arm split in the results file
comes from. The run checks it against the rollup: the per-index bytes must sum
to the rollup's own daily total, to the byte, and `report.py --check` fails if
they ever stop agreeing.
