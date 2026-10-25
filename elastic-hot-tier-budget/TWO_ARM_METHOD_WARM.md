# Elastic two-arm run, warm placement: method addendum (written before the run, 2026-10-25 01:53 UTC)

Amends `TWO_ARM_METHOD.md` with one change. Everything not named here is as in that method and as run on 2026-10-24 (`benchmarks/elastic-hot-tier-budget/results-two-arm`).

Question: with moved lines written to warm instead of hot, does arm A's hot store stay at S through the 2.5x step while arm B's still tracks load? In the first two-arm run every byte of arm A over S was moved lines waiting on hot for their mount.

## The one change
Arm A's tier_down index and arm B's overflow stream are placed on a warm node from creation and go to frozen from warm. The index template sets `index.routing.allocation.include._tier_preference: data_warm,data_hot` (arm A's `tenx-tierdown-tpl`, which arm B's `native-overflow-tpl` copies), rendered by the recipe's `tierDownPlacement: 'warm'` option, so each bootstrap index is created on warm. ILM policies, rollover ages, the 1-minute frozen `min_age` and the 100-second poll are unchanged. Arm A's kept stream (`tenx-app`) and arm B's normal stream (`native-app`) stay on the hot node.

Elastic's documentation for this, read 2026-10-25:
- Data tiers: "At the time of index creation, you can override the default setting by explicitly setting the preferred value in one of two ways: Using an index template. [...] Within the create index request body." and "You can override this setting after index creation by updating the index setting to the preferred value."
- Migrate action: "The migrate action is not allowed in the hot phase. The initial index allocation is performed automatically, and can be configured manually or via index templates." So the hot phase, where rollover runs, leaves the template's placement in place.
- Searchable snapshot action: "In the frozen phase, the action mounts a partially mounted index prefixed with `partial-` to the frozen tier." The force merge before it "occurs in the phase that the index is in prior to the searchable_snapshot action", here on warm.

The rig's indices are rollover aliases, not data streams; the same template setting governs both. For data streams the documented default is `data_hot`, overridden the same way.

## Layout
Each arm: one hot node (1 GB heap, 2 GB limit), and its frozen node also carrying `data_warm` (roles `data_warm,data_frozen`, 512 MB heap, 1200 MB limit, 128 MB shared cache). Six nodes at the first run's heap sizes (hot, warm, frozen per arm) set 9.5 GiB of container limits against the Docker VM's 7.65 GiB; the shared node keeps the first run's 7.1 GiB. Elastic documents a node in several tiers ("A node can belong to multiple tiers") and a frozen tier without dedicated nodes ("If you do not have a dedicated frozen tier, you must configure the `xpack.searchable.snapshot.shared_cache.size` setting"), while recommending dedicated frozen nodes for production.

## Meter
As before, plus each shard's node (`_cat/shards`): per stream, store on hot and on warm; per arm, the warm node's index store.

## Criteria (unchanged)
1. Arm A's hot store stays at or under 1.10 S in every reading from 20 minutes after the step to the end of the hold.
2. Arm B's hot store rises above 1.5x its pre-step level during the hold. If B also holds within 1.10 of its pre-step level, the run reports "no differentiator" and no Cloud deployment is bought.
3. Delivery: every line in each arm is on hot, warm or frozen. The check by sequence number is unchanged; "warm" is added only because the moved lines' newest index sits there when the run ends.

Hot store is the hot node's index store, as the hot-tier run reads it: log10x-mcp `readHotTierInputs` sums `indices.store.size_in_bytes` over nodes with the `data_hot` or `data` role only, so the warm node is outside S.

## Reported, not scored
- Warm store per arm (the warm node's index store, and the tier_down or overflow stream's store on warm) before the step, at the hot peak and the warm peak in the hold, and at the end of the hold.
- Readings that find a tier_down or overflow index on a hot node (expected none after setup).
- The kept stream's store, beside the hot node's.

**2026-10-25 02:08 UTC, before the run:** the hot-tier run counts in flight only what sits on hot. log10x-mcp `feat/elastic-tierdown-warm` at c1b456a (1.30.85, from main at d6fa2b1) reads the node of each tier_down index's shards (`_cat/shards` joined to the node roles); only tier_down indices with a shard on a `data_hot` or `data` node count in the hot split, and moved lines in flight count against S only while the tier_down write index sits on hot. The same commit adds the recipe option above. The rig runs that build (`MCP=/Users/talweiss/git/l1x-co/wt-mcp-warm`, commit in `build.json`). The run on main would have subtracted tier_down in flight from S wherever it sat, holding the kept stream below S by that amount.

## Not claimed
A measured Elastic Cloud bill; 300 nodes; compact; autoscaling; the cost of a warm tier (warm is not free, and the projection prices hot only).
