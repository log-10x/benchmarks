**Closed, and the answer is no.** The handoff is not durable. With the routing
collector killed mid-stream and restarted twenty seconds later, 65,269 of the
197,430 input lines were never stored and 16,828 deliveries arrived twice. With
the receiver killed instead, 84,762 were never stored and nothing arrived
twice.

Every input line carries its own number inside its body, so the reconciliation
is per line and not per batch: `extractAll(Body, 'tenxseq…')` over the Merge
table counts what was stored, whatever the receiver grouped or the collector
batched. Read the missing and duplicate rows of the table first; everything else
is context for them.

**The routing collector, killed and restarted.** The collector checkpoints its
file position in a `file_storage` extension, which is what a deployment would
configure, and the checkpoint is why this arm does not simply re-read the file
from the top. What it does instead is lose everything that was in flight and
deliver part of the rest twice. The file receiver reads far ahead of the route,
so by the time the container dies its checkpoint has already passed the lines
the engine and the exporters were still holding, and those lines come back from
nowhere.

**The receiver, killed and restarted.** Nothing is duplicated and more is lost.
The collector's OTLP exporter cannot deliver while the receiver is down, its
queue fills, and the records in it are gone; the receiver's own in-memory state
goes with the container.

Two things this arm pair does NOT say. It does not say what a crash costs when
the collector's checkpoint is also lost, which is the harsher case. And it does
not say anything about a half-written object: the object store here is MinIO on
the same host, and every object the run wrote was complete.

**One reading artifact, stated so the table is not misread.** The collector's
file exporter, which taps every record the receiver returned, is truncated when
the collector container restarts. In the collector arm the tap therefore holds
only what came back after the restart, which is why `records over, counted by
hash` is large there and means nothing: the wire is not a reference in that arm.
In the receiver arm the collector never restarts, the tap is intact, and hot
plus cold equals the tap exactly.

**What would close the gap the other way.** A persistent queue on both hops: the
collector's `file_storage` extension behind the exporter queues rather than the
file position alone, and a receiver that either acknowledges nothing until the
record is written or keeps its own spool. Neither is configured in the shipped
recipe today, and until one is, "every line kept" is a claim about the policy
and not about the route.
