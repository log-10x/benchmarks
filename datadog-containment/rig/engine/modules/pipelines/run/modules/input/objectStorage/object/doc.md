---
icon: octicons/filter-24
hidden: true
---

Fetch specified byte range(s) from an object storage container (e.g., AWS S3 bucket) to transform 
into TenXObjects on which to perform a set of [actions](https://doc.log10x.com/run/input/objectStorage/query/#queryactions).

End-users do not commonly configure fetch object directly but instead use [queries](https://doc.log10x.com/run/input/objectStorage/query/) to scan through a target container for matching byte ranges to fetch.

The query coordinator dispatches each stream worker with bootstrap args carrying its slice bounds ([`queryObjectSliceFrom`](#queryobjectslicefrom), [`queryObjectSliceTo`](#queryobjectsliceto)) and output-mode flags ([`queryObjectWriteResults`](#queryobjectwriteresults), [`queryObjectWriteSummaries`](#queryobjectwritesummaries)). Slice bounds are encoded into output S3 keys: events at `qr/{queryId}/{sliceFrom}_{sliceTo}/{worker}.jsonl`, summaries at `qrs/{queryId}/{sliceFrom}_{sliceTo}/{worker}.jsonl`.

