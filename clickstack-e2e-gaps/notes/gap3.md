**Half closed, and the half that is open is named.** The layout is indexable as
written. A value-level fetch from it was not completed here, and the reason is
the Retriever's topology rather than the objects.

The objects the collector wrote, one JSON array per object with the body and a
flat attribute map per record, went through the shipped index pipeline with the
`Local` accessor and came out with a byte-range index, a reverse index, a
template file and bloom filter objects under `tenx/app/{b,r,t}/` and
`app/<bucket>/<byte range>/`. The same records written one per line indexed the
same way. Neither shape needed a change to the objects, so the container shape
is not a barrier: the indexer reads the array and it reads the lines.

The query is where it stops. Two things had to be changed in the shipped query
config before it would even start, both asserted in `patch_retriever_config.py`
and both reported here rather than worked around:

- `search` may not be blank. A query by type alone, with the hash in `filters`
  and nothing in `search`, is refused at construction with "search cannot be
  blank", so the run passes a word from the type's own pattern text.
- The scan slice, `scanFunction.parallel.timeslice`, is one minute in the
  shipped file, and the coordinator reads it to decide between running each
  slice itself and posting it to a worker. With a window wider than a slice
  every slice is posted to `http://localhost:8080/pipeline`, and a single
  container has nothing listening there. Set to zero, the scan runs in the
  coordinator's own thread pool and the query completes.

With the scan local and a type that is in the indexed objects, the query runs to
completion in the time the table records, the scan matches byte ranges, and then
the fetch of those byte ranges is posted to the stream worker endpoint, which is
the same address. Three connection failures, no results object, no rows returned.
The Retriever's read path is a coordinator plus scan workers plus stream workers;
what a single container can do is index and scan, not fetch.

**What it would take to close the other half.** The deployed shape, or the
Lambda flavour: a query handler and a stream worker reachable at the scan and
stream URLs, which is what `terraform-aws-tenx-retriever-lambda` stands up. That
is a deployment, not a change to the layout, and nothing in this run suggests
the layout is what would fail.

Two smaller facts from the run, both of which a deployment would have to size
for: indexing is per object and the objects here are megabytes, and the first
run of this script indexed one 9 MB object in about six minutes with the
progress gauge on. This run sets `quiet` and indexes two objects per shape
rather than all forty three, because what is being answered is whether the
layout is indexable, not what a bucket's worth costs.
