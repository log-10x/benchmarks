**Closed on the queries and on the alert's creation, open on the alert's own
evaluation.** Two of the three questions change their answer when rows leave the
hot table. The Merge table and the counts table both give the answer the hot
table gave before the offload, to the row. HyperDX's API accepts an alert over
each of the three surfaces, the Merge table included, which is the surface an
alert has to point at if it is to keep firing.

Read the question table by column. The hot table before the offload and the
Merge table after it agree exactly: the type that was counted 36,395 times
before is counted 36,395 times after, through hot plus cold. The hot table after
the offload answers 3,688 for the same question, and it does not fail or warn
while doing it, which is the whole problem. The counts table answers the
count-shaped questions at a fraction of the rows read and with no object-store
request at all.

**Q3 is weaker than intended, and here is why.** The word for the text search was
supposed to be one that lives only in offloaded rows. No word of the twenty
biggest offloaded types is absent from the hot table, because the cap keeps the
first occurrences of every type and offloads the overflow: a capped type is on
both sides by construction. The run reports that in `word_only_cold`, and the
word it fell back to lives on both sides, so Q3 measures the drift rather than a
clean disappearance. A type that first appears after its window's cap is already
spent would give the clean case; finding one is a search over the census, not a
property of the policy.

**Nothing was lost and nothing was stored twice in this run, and that is not a
property of the route.** Hot plus cold equals what the receiver returned, on both
feeds, and every stored row is a distinct `(Timestamp, Body)` pair. An earlier
run of this same script on this same host stored 207,384 rows for 157,126
distinct pairs: fifty thousand copies, with no restart and no policy change, from
a retry on an insert that had already committed. The duplicates table is in the
results because the check is cheap and the failure is invisible to the lossless
check the end to end harness performs. One caveat on its cold column: a cold
row's timestamp is reconstructed from `TimestampSec`, so two identical messages
inside one second are indistinguishable there and the cold repeats are an
artifact of second resolution, not evidence of duplication.

**The alert.** A webhook, three sources, three saved searches and three alerts,
all created over the API, all 200. Two API facts worth keeping: an alert is
refused without `channel.webhookId`, and a webhook is refused if its URL resolves
to a private or reserved address. Whether each alert would fire is computed from
the count its surface returns against a threshold of half the before count, and
the table says which: the hot table stops firing after the offload, the Merge
table and the counts table do not. That computation is not HyperDX's own
evaluation loop. An alert evaluates the window its interval names, and by the
time a five minute loop runs, a replayed capture's rows are older than the
window. That is the open half of this gap and it needs a live feed, not a replay.
