# Amazon OpenSearch Service: per-statement tier down to UltraWarm

A slice of records the engine had already marked was loaded into a live Amazon OpenSearch
Service domain with UltraWarm, as a forwarder would send it: kept records (routeState
`pass`) to the `tenx-app` alias, held records (routeState `offload`) to the `tenx-tierdown`
alias. An ISM policy rolled the tier-down index over and migrated it to warm. The kept index
was the control and stayed hot. The question was whether the stamped identity survives the
move, whether the hot nodes shed the bytes, and whether one Dashboards index pattern reads
kept and moved lines together.

Every figure below names the file and field it was read from. A figure the run did not produce
is written "not measured".

## The finding

**Identity survived the move. A term query on `tenx_hash` returned 400 of 400 held hashes
against the warm index, with `_source` identical to what was sent, right after the move and
again an hour later. One index pattern read both tiers: 600 documents, 400 warm and 200 hot.**

| | Before the move (19:04Z) | After the move (19:59Z) | An hour after (20:37Z) |
|---|---|---|---|
| `tenx-tierdown-000001` tier (`GET _hot` / `GET _warm`) | hot | warm | warm |
| Held hashes with exactly 1 hit, of 400 | 400 | 400 | 400 |
| Held `_source` identical to the bulk file, of 400 | 400 | 400 | 400 |
| `routeState` aggregation on the moved index | offload 400 | offload 400 | offload 400 |
| Kept hashes with exactly 1 hit on `tenx-app-000001` (hot control), of 200 | 200 | 200 | 200 |
| Index-pattern search, total hits | 600 | 600 | 600 |

Sources: `results/proof-before-move.json`, `results/proof-after-move.json`,
`results/proof-hour-after-move.json`, fields `held`, `kept`, `index_pattern`, `hot`, `warm`.
Every hash was sent once (`data/slice.json`), so one hit per hash is the full count.

## Hot store before and after

Same listing call on both sides: `_cat/shards?format=json&bytes=b&h=index,shard,prirep,state,docs,store,node`
(`results/raw/requests.jsonl`, tags `watch:1:shards` at 19:04:53Z and `listing:shards-final`
at 20:37Z). Node roles from `_cat/nodes` (`listing:nodes-after-move`): `dir` = hot data node,
`dr` = warm node, `mr` = dedicated master.

| Index | Before: node (role), store | After: node (role), store |
|---|---|---|
| `tenx-tierdown-000001` (400 held) | `50655aa3` (dir, hot), 156,282 b | `49ed5807` (dr, warm), 156,392 b |
| `tenx-app-000001` (200 kept, control) | `0453433c` (dir, hot), 104,903 b | `0453433c` (dir, hot), 105,013 b |
| `tenx-tierdown-000002` (successor after rollover) | did not exist | `50655aa3` (dir, hot), 208 b, 0 docs |

On the hot nodes, the tier-down slice went from 156,282 b to 0 b; one empty successor index of
208 b took its place. `_cat/shards` lists one copy of `tenx-tierdown-000001` after the move, on
the warm node. Both indices grew by 110 b between the two readings while their document counts
did not change; reported as read, cause not measured.

`_cat/indices` is not a tier measure here: it reported `tenx-tierdown-000001` at 156,392 b after
the move too, and the UltraWarm page says Dashboards and `_cat/indices` "still report UltraWarm
index size".

CloudWatch `FreeStorageSpace` per hot node (`results/raw/cloudwatch-free-storage-per-node.json`)
shows no visible step at the migration. The node that held the slice read 7,912.650 MB at 19:30Z
and 7,912.654 at 19:31Z, then drifted down to 7,912.389 by 19:45Z. The slice is 0.15 MB and the
metric moves more than that from other writes over the hour, so this metric does not resolve the
shed. The shard listing above is the measurement.

## Warm storage

`WarmStorageSpaceUtilization` Maximum (`results/raw/cloudwatch.json`, unit "Megabytes" from
CloudWatch; the metrics page describes it "in MiB"):

- 0.003506 from 19:02Z (the canary only, see below)
- 0.152653 from 19:31Z to the last reading at 20:36Z

0.152653 MiB is 160,068 b, which equals 156,392 b (`tenx-tierdown-000001`) plus 3,676 b
(`uw-canary`). The tier-down slice is about 0.000146 GiB of warm storage.
`WarmSearchableDocuments` Sum went from 1 to 401 in the 19:31Z minute.

## Time from load to warm

Times in UTC. The run's own minute-by-minute watcher has a gap from 19:17Z to 19:58Z, caused by
an SSO token that botocore could not refresh (`results/raw/events.jsonl`, `watch_error` and
`note`). The times in this table come from records the service kept for itself: ISM's managed
index history (`results/raw/ism-history.json`), the `cs-ultrawarm` snapshot list (tag
`snapshot:cs-ultrawarm`) and CloudWatch (`results/raw/cloudwatch.json`).

| UTC | What | Source |
|---|---|---|
| 19:04:03 | `tenx-tierdown-000001` created | ISM explain `index_creation_date` |
| 19:04:23 | bulk load returned, 600 items, `errors: false` | `results/raw/bulk-response.json`, event `bulk_loaded` |
| 19:16:24 | ISM first runs on the index: policy initialized, state `hot` | ISM history `state.start_time` |
| 19:19:21 | rollover attempted and completed (`min_doc_count` 400 met); `tenx-tierdown-000002` created 19:19:23 | ISM history `action.start_time`; explain |
| 19:26:24 | "Transitioning to warm" | ISM history `history_timestamp` |
| 19:30:51 | state `warm`, action `warm_migration` starts; the call to start the migration completes | ISM history `action.start_time` |
| 19:30:53.8 to 19:30:54.6 | `cs-ultrawarm` snapshot of the index, 800 ms | `_snapshot/cs-ultrawarm/_all` |
| 19:30 to 19:31 minute | force merge 320 ms, snapshot stage 2,932 ms, processing 7,147 ms, success latency including queue 8,458 ms; success count 1; failure count 0 | CloudWatch `HotToWarmMigration*` |
| 19:31 minute | warm storage steps to 0.152653 MiB; warm searchable docs 401 | CloudWatch |
| 19:36:29 | ISM's next run sees the migration complete: "Successfully completed Warm migration" | ISM history `step.start_time` of `wait_for_warm_migration` |
| 19:42:04 | policy completed | ISM history, last row |

Read as lags a buyer would see:

- **Load to first ISM run:** 12 min 21 s after index creation. ISM had to initialize the policy
  before it could check rollover.
- **ISM run cadence:** successive runs on this index at 19:16:24, 19:19:21, 19:26:24, 19:30:51,
  19:36:29, 19:42:04. The gaps are 2.9, 7.1, 4.5, 5.6 and 5.6 min. The ISM page says the job
  "runs every 5 to 8 minutes". The 2.9 and 4.5 min gaps are shorter than that; reported as read.
- **Rollover to ISM picking the index up for migration:** 19:19:21 to 19:30:51, 11 min 30 s,
  across two ISM runs (the transition, then the action).
- **The migration itself:** 7.1 s processing (CloudWatch `HotToWarmMigrationProcessingLatency`),
  8.5 s including queue. It was done in the 19:31 minute. ISM recorded it complete at 19:36:29,
  its next run, 5 min 38 s after the start.
- **Bulk load to bytes in warm:** 19:04:23 to the 19:31 minute, about 27 min. To ISM's own
  completion record: 32 min 06 s.

The rollover threshold was a document count (400), so the index rolled at the first ISM run
after the policy was in place. A production policy would roll on size or age; that adds its
own wait before the 11.5 min pickup and the seconds of migration measured here.

## Index pattern

The pattern was created through the OpenSearch Dashboards saved-objects API,
`POST /_dashboards/api/saved_objects/index-pattern/tenx-all` with `osd-xsrf: true`
(tag `pattern:create`). Read back (tag `pattern:read`), it stores title
`tenx-app-*,tenx-tierdown-*`, `timeFieldName` `@timestamp`, and `migrationVersion`
`index-pattern 7.6.0`.

Three reads ran after the move (`results/proof-after-move.json` and
`results/proof-hour-after-move.json`, field `index_pattern`):

- **`_search` on the title the saved object stores.** 600 hits on 3 shards, 3 successful:
  `tenx-tierdown-000001` 400, all `offload`, and `tenx-app-000001` 200, all `pass`. The third
  shard is the empty `tenx-tierdown-000002`.
- **Dashboards' own search route.** `POST /_dashboards/internal/search/opensearch` with the title
  as index returned 600, split the same way. This route is internal to Dashboards and is not in
  the public API docs; reported as read.
- **`GET /_dashboards/api/index_patterns/_fields_for_wildcard`.** It returned 200 with 14 fields
  across both indices, `tenx_hash` and `routeState` among them. In the before-move run this call
  returned 400 because the harness passed `meta_fields=_source` in a form the route rejected. The
  parameter was dropped and the after-move runs returned 200.

## Dollars

- **By published rates.** The rates come from the AWS Price List API for us-east-1 on demand,
  read 2026-11-04: m7g.medium.search $0.068/h, ultrawarm1.medium.search $0.238/h,
  gp3 $0.122/GB-month, warm managed storage $0.024/GB-month. The pricing page's own examples
  agree on the UltraWarm rate and the storage rate. The domain ran from the create call at
  18:48:19Z to the delete call at 20:37:58Z, 1.8275 h.
  - 5 × m7g.medium plus 2 × ultrawarm1.medium at $0.816/h comes to $1.491.
  - 20 GB of gp3 comes to $0.006.
  - About 160 KB of warm storage comes to under $0.0001.
  - **The total is $1.50.** If the service bills partial hours as whole hours (not stated for
    these types), it is $1.64.
- **By the vendor's usage endpoint.** Not measured at write time. Cost Explorer
  `get-cost-and-usage` for 2026-11-04, filtered to Amazon OpenSearch Service and grouped by usage
  type, returned $0 with `Estimated: true` at 20:00:44Z (`results/raw/cost-explorer-1.json`).
  The day's charges had not posted.

## The canary, kept apart

`uw-canary` is a one-document index outside the `tenx-*` patterns. It was used only to time when
UltraWarm first accepted and finished a migration on the new domain. It is not part of the tenx
figures above, except where its 3,676 b sit inside the warm storage total, as noted.

- 18:48:19: create-domain call
- 19:02:02: first poll with `Processing: false` and an endpoint, while `DomainProcessingStatus`
  still read `Creating`
- 19:02:38: `DomainProcessingStatus` reads `Active`, 14 min 19 s after the create call
- 19:02:07: `GET _warm` answers 200
- 19:02:12: migration accepted
- 19:03:22: listed in `_warm` and searchable

So UltraWarm took a first migration 44 s after the domain read Active. The UltraWarm page says it
"might not be available to use for several hours" after the domain is Active. This is one reading
on one domain (`results/raw/events.jsonl`, `results/raw/status-polls.jsonl`).

## Setup

- **Domain.** `tenx-uw-tierdown`, us-east-1, OpenSearch 2.19.0 (Lucene 9.12.1, from `GET /`),
  the latest 2.x the service offered (`list-versions` also offered 3.1 to 3.7). It ran in one AZ
  with no standby.
  - 3 dedicated masters and 2 data nodes, all m7g.medium.search, the cheapest non-T type that
    `list-instance-type-details` showed with warm enabled and the master role.
  - 10 GiB of gp3 per data node, the minimum.
  - 2 ultrawarm1.medium.search warm nodes.
  - Encryption at rest and node to node, with HTTPS enforced.
  - Fine-grained access control off. The access policy allowed `es:ESHttp*` for one IAM role from
    one /32. The runner IP, the AWS account ID and the SSO role name are redacted to `<runner-ip>`,
    `<account-id>` and `<sso-role>` in the committed files.
  - Create request: `results/raw/create-request.json`; response:
    `results/raw/create-response.json`.
- **Templates.** `plan/tenx-tierdown-tpl.json` and `plan/tenx-app-tpl.json`: one shard, zero
  replicas, `tenx_hash` and `routeState` mapped as keyword, `@timestamp` as date. These are the
  same mappings as the Elastic frozen-tier recipe.
  - The index templates carry only `plugins.index_state_management.rollover_alias`. The ISM page
    says "You can no longer use index templates to apply ISM policies to newly created indexes",
    so each policy attaches itself through its `ism_template` field.
- **ISM.**
  - `plan/ism-tenx-tier-down.json`: state `hot` with `rollover` {`min_doc_count`: 400}, then state
    `warm` with `warm_migration` {} and retry 5 at 10 min.
  - `plan/ism-tenx-keep.json`: state `hot` with `rollover` {`min_index_age`: 1d} and no
    transition. That condition was still unmet at the last explain, 50.5 min into its 1 d (tag
    `check:explain-after-gap`).
  - The ISM page names the action: "OpenSearch Service supports three unique ISM operations,
    `warm_migration`, `cold_migration`, and `cold_delete`".
- **Data.** 400 held and 200 kept records come from the records engine 1.1.153 returned in the
  ClickHouse Cloud elasticity run, under the 10-24 policy: 112,205 pass and 59,602 offload over
  3,032 hashes. The engine was not run again.
  - `build_slice.py` keeps the first record of each hash, so every hash is sent once.
  - It skips the 171 hashes that appear under both states in that file, so each hash names one
    side only.
  - Message bytes: 58,260 held and 22,849 kept (`data/slice.json`). Bulk file:
    `data/bulk.ndjson`.
- **Harness.**
  - `osreq.py` signs each request with SigV4 and appends every response, in full, to
    `results/raw/requests.jsonl`.
  - `wait_ready.py` polls readiness, `watch_move.py` watches the move, and `proof.py` runs the
    searches.
  - Two 403 responses from a signing bug early in the run echoed the signed request, including
    the session token. Their bodies were cut to the first sentence before commit.

## What was not shown

- No query load. Searches were single requests; warm search latency under load was not measured.
- No production mix or volume. The data is 600 documents, about 260 KB on disk.
- One AZ, no replicas on hot, no Multi-AZ with Standby.
- No self-managed OpenSearch. UltraWarm and `warm_migration` are Amazon OpenSearch Service
  features.
- No cold storage. The UltraWarm page says cold indexes cannot be read until migrated back to
  warm.
- No size- or age-based rollover for the tier-down slice; see the note under the timing table.
- Cost Explorer dollars: not measured at write time.

## Domain deleted

`delete-domain` was called at 20:37:58Z and returned `Deleted: true`,
`DomainProcessingStatus: Deleting` (`results/raw/delete-response.json`).
From 20:51:40Z, `describe-domain` returns `ResourceNotFoundException: Domain not found:
tenx-uw-tierdown` and `list-domain-names` returns an empty list (event `domain_gone`).
Dollars by rates run to the delete call. If billing ran until the domain was gone, add 13.7 min
at $0.816/h, $0.19.
