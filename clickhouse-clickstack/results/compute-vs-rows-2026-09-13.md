# Does ClickHouse compute scale with rows

Measured 2026-09-13 by `run_compute.sh`. Insert CPU from `system.query_log`, merge CPU from `system.part_log`, both ClickHouse's own user-plus-system time. Every arm holds the same original log text in the same ClickStack schema at ZSTD(1); the only thing that varies is which rows are present. Inserts arrive in batches of 5,000 rows, so an arm with half the data sends half the batches, and background merges run on their own and are measured rather than forced with one `OPTIMIZE FINAL`. Each arm is loaded 3 times after a discarded warm-up pass, and the fastest is kept.

## Why this and not more compression

ClickHouse Cloud bills compute per unit-hour and storage at $25.30 per **compressed** TB per month. At that rate a log estate of ordinary size carries tens of dollars of storage, so the storage line is not the bill and the 7% that compaction is worth on it cannot be either. Compute is the bill. This file asks whether the product can move it.

## The falsifier, stated before the run

If halving the rows does not roughly halve insert-plus-merge CPU, then compute on ClickHouse is not driven by row count, removing rows is not a compute lever, and the cost story for this destination is finished.

**Half the rows used 39% of the CPU. The claim HOLDS.**

## Compute per arm

| Arm | Rows | Rows vs full | Insert CPU s | Merge CPU s | Total CPU s | CPU vs full | CPU per 1k rows | Every pass | On disk |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `full` | 197,430 | 100% | 5.20 | 4.68 | 9.87 | 100% | 0.0500 | 9.87, 10.59, 17.27 | 7,870,644 |
| `sampled_75` | 148,147 | 75% | 3.04 | 3.22 | 6.27 | 63% | 0.0423 | 6.27, 7.23, 7.72 | 6,745,773 |
| `sampled_50` | 99,038 | 50% | 1.91 | 1.98 | 3.90 | 39% | 0.0393 | 3.90, 3.98, 4.19 | 4,828,292 |
| `sampled_25` | 49,499 | 25% | 1.16 | 0.55 | 1.70 | 17% | 0.0344 | 1.70, 1.83, 2.07 | 2,767,552 |
| `bypattern_75` | 143,832 | 73% | 3.92 | 4.30 | 8.22 | 83% | 0.0572 | 8.22, 8.29, 9.68 | 6,541,774 |
| `bypattern_50` | 97,367 | 49% | 1.69 | 1.74 | 3.43 | 35% | 0.0352 | 3.43, 3.56, 4.96 | 4,997,429 |
| `bypattern_25` | 47,147 | 24% | 0.90 | 0.58 | 1.48 | 15% | 0.0314 | 1.48, 1.60, 1.78 | 3,192,322 |

## What it says

**How compute moved with rows.** Across the uniform samples, 75% of the rows cost 63% of the CPU, 50% of the rows cost 39% of the CPU, 25% of the rows cost 17% of the CPU. The uniform sample keeps the content mix identical, so this is row count and nothing else.

CPU per thousand rows runs from 0.0314 s to 0.0572 s across every arm, a spread of 1.82x. A flat per-row cost would be a spread of 1. Per-row cost FALLS as the table shrinks, which rules out a fixed overhead as the explanation: a fixed cost would make half the rows cost more than half, not less. What falls is merge work, which grows faster than linearly with the parts that arrive.

At about 75% of the rows, dropping whole message types cost 83% of the CPU against 63% for the uniform sample, and 6,541,774 bytes against 6,745,773.
At about 50% of the rows, dropping whole message types cost 35% of the CPU against 39% for the uniform sample, and 4,997,429 bytes against 4,828,292.
At about 25% of the rows, dropping whole message types cost 15% of the CPU against 17% for the uniform sample, and 3,192,322 bytes against 2,767,552.

**Removing rows saves more than proportionally.** Half the rows cost 39% of the CPU and a quarter of the rows cost 17%, both below the row share. Merging is the reason: fewer parts arrive, they merge fewer times on the way up, and each merge rewrites less. A row never written is not paid for once, it is not paid for on every merge that would have carried it.

**Dropping whole message types and sampling uniformly cost about the same.** At half and at a quarter of the rows the two are within a couple of points of each other. The one arm that disagrees is `bypattern_75`, which cost more per row than its uniform twin across all three passes. The two message types it removed are the collector's debug exporter, whose lines are long and highly repetitive, so taking them out leaves a residue that is more varied per row and costs more to tokenise and compress. Worth knowing before assuming the largest pattern is always the cheapest one to remove.

**What this does not measure.** Query compute, which is the other half of a cluster's work. A production corpus, rather than a demo capture whose largest message type is the OpenTelemetry collector's debug exporter, a development default a real cluster would not run. And what share of rows an operator would actually agree to remove, which is a judgement about somebody's real logs and cannot be measured here.

## The message types in this capture

197,430 captured lines fall into 2,627 message types. The ten largest:

| Message type | Lines | Share |
|---|---:|---:|
| `-L3!]kPjVal` | 32,855 | 16.64% |
| `-M>+yzgY+*w` | 20,743 | 10.51% |
| `&$18^Az03e` | 18,480 | 9.36% |
| `-;;6#92RzlK` | 14,478 | 7.33% |
| `-+YpYe?G?Gd` | 13,507 | 6.84% |
| `7Pz[prIOZH` | 12,442 | 6.3% |
| `6tP;ALviMp` | 9,248 | 4.68% |
| `-.a7HKgM>82` | 6,936 | 3.51% |
| `-K<JNLEahM5` | 6,936 | 3.51% |
| `Hdk.1$@_cj` | 3,818 | 1.93% |

The ten largest types carry 70.6% of the lines. That concentration is what makes per-pattern removal a lever at all: a decision about ten things reaches most of the volume. Whether those particular ten should be removed is a question about somebody's real cluster.

## Arms

| Arm | Rows | Message types kept |
|---|---:|---:|
| `full` | 197,430 | 2,627 |
| `sampled_75` | 148,147 | 2,627 |
| `sampled_50` | 99,038 | 2,627 |
| `sampled_25` | 49,499 | 2,627 |
| `bypattern_75` | 143,832 | 2,625 |
| `bypattern_50` | 97,367 | 2,622 |
| `bypattern_25` | 47,147 | 2,614 |

