# Pattern identity benchmark

One benchmark in the [log10x benchmarks](../) repository. Everything it needs is in this
directory: the scripts under `bench/`, the pinned dependencies, `run.sh`, and the artifacts
under `results/` that each script wrote.

## The question

Does a log line keep the same name over time, and does it get the same name in two different places?

A pattern name is the key that sampling rules, suppression, dedup keys, cost attribution and new-pattern detection are built on. A template miner produces that name by mining the stream in front of it, so the name is a function of what that process happened to see and when. This benchmark measures what that costs, on public data, states what result would prove the log10x position wrong, and runs those tests instead of asserting them. Two of the pre-registered tests fired against log10x, and both stand as concessions on this page, in the sections where they were tested.

The Drain-side experiments run against one public sample: 197,430 Fluentd/Kubernetes lines from the OpenTelemetry demo, published at [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1). Measured scale, from `results/data_provenance.txt`: 10.3 hours between the 1st and 99th percentile timestamp, about 5.3 lines per second, 36 Kubernetes containers, the busiest of them 47.5% of the lines. That is one small demo cluster over about ten hours, not a log platform, and a shape that occurs once at 5 lines per second is a different population from a shape that occurs once at 100,000. The engine-side coverage experiments additionally use two public LogHub log sets from Zenodo and a pinned engine Docker image whose digest is recorded in the artifact. Every measured number on this page is printed by a script in this directory; the wall-clock estimates under Reproduce are not, and the ledger expectations are external, recorded six weeks earlier as disclosed in section 4.

## What Drain does well

Drain3 is the incumbent for a reason, and the concessions come first.

- **Its templates are stable under reordering.** The same 60,000 lines fed in natural order and shuffled produce template strings that agree 0.9860 of the time (`bench/identifier.py`). The published stability result reproduces here and stands.
- **It works from the stream alone.** There is no build step, no compiler pass, and no dependency on the emitting source. Pointed at an unfamiliar stream it produces useful templates immediately, which makes it the right default when the emitting code is out of reach.
- **Two instances that never exchanged state give a rare line the same name.** Through the production path, `add_log_message`, a line seen once is named identically by both instances 0.9859 of the time (`bench/identity.py`, strong arm). This was a pre-registered falsifier and it fired against log10x. The mechanism is in the Drain3 source: neither instance can generalize a shape it has one example of, so both mint the line's own literal text, and the two strings are equal. An earlier revision of this benchmark reported 0.0 for that row by probing with the read-only `match()` API, whose misses are a coverage property of a lookup call; that number described the probe, not the miner, and the corrected design below replaces it.
- **On frequent shapes it converges.** For shapes occurring over 1,000 times, two independent instances agree 1.0000 of the time, through either path.
- **Centralized query-time mining is out of scope of the split result.** The major SIEM platforms that mine patterns do it in one central pass at query time, over whatever the query returns, so no second instance exists to disagree. The two-forwarder experiment below indicts per-node mining and any design that persists a mined name, not those products as they ship today. Section 1 is the part that reaches a central miner, because a name moving inside one process needs only that one process.
- **Two claims made against it fail on this data, and the scripts say so.** Drain does not shatter stack frames into a long cluster tail here: 4,658 frame lines collapse to 25 shapes. And an exception count turned out to be expressible in Drain's output on this file, through clusters that fire exactly once per burst and never outside one, so that claim is withdrawn in `results/multiline.txt` where it was tested.

The templates are good. What this benchmark measures is the identity attached to them.

## 1. A name moves inside one process

This is the exhibit everything else depends on. It needs no split, no fleet, and no download, it runs in under a second, and `run.sh` runs it first.

One Drain3 instance, one cluster, four lines from the public sample: a Grafana provisioning line arrives and is named, two sibling outputs of the same statement arrive, and the first line is presented again byte for byte.

```
step 1  logger=provisioning.datasources t=<TS> level=info msg="inserting datasource from configuration" name=Jaeger uid=webstore-traces
step 4  logger=provisioning.datasources t=<TS> level=info msg="inserting datasource from configuration" <*> <*>
```

The bytes are identical. The name is not. Step 2 reports `cluster_template_changed`, so the rename is visible to a caller processing the sibling. Step 4, the replay of the original bytes, reports `change_type='none'`, so a pipeline that keys on the template, or on a hash of it, writes a second name for the first line while being told the cluster held steady. Both facts are asserted against drain3 0.9.11, and the script refuses to run under `python -O` so the asserts stay live (`bench/replay.py`, `results/replay.txt`).

This applies to every deployment, including one central miner with a single model. Anything that persists a mined name across time inherits it: a sampling rule, a suppression rule, a dedup key, a cost attribution, a new-pattern panel that now has a new pattern to report. Hand-written alerts on fields are untouched; alerts keyed on a mined pattern id are not. This is also why the singleton agreement conceded above is narrower than it sounds: the name both instances agree on is the pre-generalization literal, the exact string this exhibit shows moving the moment a sibling arrives.

## 2. Two instances, the production path

Two Drain3 instances each receive one random half of the same stream, disjoint, which models two forwarders that never exchange state. The same probe sequence is then fed to both through `add_log_message` itself, in the same order, exactly as if two nodes with different histories started seeing the same traffic. Every probe gets an answer from both sides, because the production path mints a cluster on first sight; there is no coverage term and no `None` anywhere in this table. Full file, 10 trials, 30,000 probes per trial, seed pinned (`bench/identity.py`, `results/identity.md`).

The probe pass itself is shared traffic, so the two states converge as it proceeds, which works in Drain's favour on net. The divergence reported is what survives that convergence.

**Drain3 at its strongest honest configuration** (`strong`: drain3's own `examples/drain3.ini` masking block, `FilePersistence` carried across a mid-stream restart, fallback lookup):

| line frequency | probes/trial | template agreement | stdev | cluster_id agreement |
|---|---:|---:|---:|---:|
| seen once | 136 | 0.9859 | 0.0085 | 0.0007 |
| 2 to 10 | 204 | **0.6022** | 0.0243 | 0.0005 |
| 11 to 100 | 589 | 0.9118 | 0.0158 | 0.0051 |
| 101 to 1,000 | 916 | 0.9788 | 0.0045 | 0.0070 |
| over 1,000 | 28,152 | 1.0000 | 0.0000 | 0.0646 |
| all events | 30,000 | 0.9949 | 0.0003 | **0.0609** |

Reading it, conceded row first:

- **Lines seen once agree, and the falsifier fired.** 0.9859, mechanism above, concession recorded in section "What would prove log10x wrong". The claim that a locally mined name is local to the process that mined it is withdrawn for lines seen once.
- **The divergence sits exactly where generalization begins.** At 2-to-10 the two instances give the same line two different names 0.3978 of the time, and at 11-to-100 still 0.0882. `create_template` wildcards the positions where that instance's own siblings happened to vary, so two instances with different histories settle on different intersections of the same statement's outputs. A fleet-wide statement that fires a handful of times per node lands in these strata on each node that mines it independently; the two instances here measure one such pair.
- **The integer never travels.** `cluster_id` agrees 0.0609 over all probes, and 0.0005 in the 2-to-10 stratum, because it is an arrival counter. Hashing the template string is the correct repair for the integer, and the hash column would equal the template column exactly: equal strings hash equal, divergent strings hash divergent. Hashing inherits the divergence.
- **The aggregate carries almost none of this.** The strong reference pass finds 1,481 distinct shapes, 921 of them occurring exactly once, yet the all-events row sits at 0.9949 because the over-1,000 stratum is 94% of probed events. The tail is where the divergence is, and the aggregate is not where the tail is visible.

`baseline` (typed-token masking, memory only) lands within a few points of `strong` in every stratum: 0.6500 at 2-to-10, 0.9036 at 11-to-100. Neither masking style, nor persistence, nor lookup strategy moves the tail materially; the split does.

**Buying agreement.** The `shared` arm chains the two instances through one snapshot, so B warm-starts from A's final state. That moves 2-to-10 agreement from 0.6022 to 0.8114 and cluster_id agreement over all events from 0.0609 to 0.9970. Agreement is purchasable, and its price is one shared model that both sides read and write in sequence, which is an architecture rather than a setting.

### Query-time lookup, reported separately

The read-only `match()` API answers a different question: not "what would this node name the line" but "does a name already exist here to resolve a query against". drain3 0.9.11 requires a similarity of 1.0 on that path, and an instance that never ingested the shape returns `None`. That is **coverage**, and this benchmark reports it under that word, never as disagreement. Strong arm: coverage at "seen once" is 0.0000, meaning the name exists in exactly one place in the fleet and nothing elsewhere can resolve it; coverage at 2-to-10 is 0.5307. Among probes both instances can already answer, the names still differ 0.2146 at 2-to-10 and 0.0924 at 11-to-100, the same generalization divergence as the primary table, seen from the lookup side. Full tables in `results/identity.md`.

## 3. The identifier

A separate experiment separates the template from the integer Drain returns with it, inside one process. Same 60,000 lines, two arrival orders: the template string agrees 0.9860, the integer `cluster_id` agrees 0.0001, and under cap pressure at `max_clusters=500` the split widens to 0.9848 against 0.0000 (`bench/identifier.py`). `cluster_id` is `self.clusters_counter += 1`, which is arrival rank and nothing else. Drain's own examples print it and dashboards key on it.

## 4. Coverage on the engine side

The engine assigns names from a compiled symbol library rather than from the stream, so the fair comparison is not a half-split: a content hash of a template drawn from a pinned library comes out identical in two places by construction, and a 1.0 from such a run would restate the construction. The engine question is coverage, and it splits into two parts, one circular and one not.

**The circular part is fenced off.** The published templates asset is the dictionary the encoding run wrote for its own output: `bench/engine_side.py` measures that every one of its 2,896 templates is referenced and every reference resolves, and reports that as a consistency gate, not evidence. Reading a resolve rate between two co-generated artifacts as library coverage is unsupported, and this page does not do it.

**The non-circular part runs the engine** (`bench/coverage.py`, `results/coverage.md`, pinned image digest recorded in the artifact; the script skips cleanly on machines without Docker):

- **Invented vocabulary.** Lines whose content words were made up for this benchmark, fed beside ordinary lines. The words cannot sit in any symbol library, because they did not exist until this test was written, which is what closes the "the templates file is definitionally complete for its own encoding run" loophole. The ordinary line comes back as `$(yyyy-MM-dd HH:mm:ss) INFO Connection established to database` with the readable pattern name `INFO_Connection_established_to_database`. The invented line comes back as `$(yyyy-MM-dd HH:mm:ss) $ $ $ $ $` with an EMPTY pattern name: unknown tokens become variables, the coverage failure is visible in the artifact itself, and at no point does the engine hand back a confident wrong name. All three occurrences carry the identical template hash, and a second, independent engine run reproduces it byte for byte.
- **Unfamiliar streams.** Two public LogHub log sets the symbol library was never built for, downloaded from Zenodo record 3227177: Proxifier, a Windows consumer application, encodes to 4,257 events under 574 templates with a median of 31 literal words per template and zero pure-variable templates; the Apache error log encodes to 52,004 events under 370 templates, median 20 literal words, zero pure-variable. Both counts reproduce the compaction ledger's figures recorded six weeks earlier, exactly, and the script fails loudly on any mismatch.
- **Caution.** The `encoded.log` the analysis app writes carries `pattern=` and `patternHash=` fields for tooling; it is the analysis artifact, and no storage-reduction figure may be computed from it. None appears in this benchmark.

**What the published artifacts show about granularity**, from `bench/engine_side.py`: 2,896 names for 159,454 events, 91.4% of them used exactly once, so name assignment does not wait for repetition. On the message body, 2,884 of 2,896 templates carry alphanumeric literal text at a median of 15 tokens, 12 do not, and anchoring does not degrade with rarity (used-once median 15 against over-1,000 median 19.5, ratio 0.77 against a floor of 0.50). One finding cuts against log10x and stays: 82.8% of templates carry deployment values welded into envelope literals, image tags and pod-name fragments, so a redeploy changes those names. That is the same identity property this benchmark scores Drain on, and cross-deployment engine agreement is unmeasured here.

## 5. The mechanism

The Drain-side results follow from four short code paths in `drain3/drain.py`, checkable in about ninety seconds against the pinned drain3 0.9.11.

- `add_log_message`: an unmatched line creates a cluster immediately, on first sight, holding the full literal tokens. There is no minimum-support threshold. This is why the production path agrees on rare shapes, and why the agreed name is the raw line.
- `create_template(seq1, seq2)` returns `[token2 if token1 == token2 else param_str ...]` and writes the result back. A cluster template is the running intersection of every line that ever matched it, so it only loses literal tokens, and it loses them whenever a sibling arrives. Sibling arrival order is a property of the stream, which is why two streams settle on different intersections.
- `tree_search` partitions on token count at the first level. Two outputs of one source statement with different token counts can never share a cluster, whatever `depth` and `sim_th` are set to.
- `match()` requires a similarity of 1.0 and defaults to `full_search_strategy="never"`. It is a lookup, not a naming call, which is why this benchmark reports its misses as coverage.

The same intersection mechanism is specified in the ICWS 2017 paper, so this is Drain working as designed, not a bug in drain3.

## What would prove log10x wrong

Each falsifier names a quantity that a rerun could move past a threshold fixed in the source before the run. They point in both directions: some fire against log10x, and two already have.

- **Two independent instances give a line seen once the same name through the production path.** `bench/identity.py`, strong arm, threshold 0.50. Observed **0.9859. TRIGGERED.** The claim that a locally mined name is local to the process that mined it is withdrawn for lines seen once. What survives is narrower: the agreed name is the pre-generalization literal that section 1 shows moving, and the divergence begins one sibling later.
- **The 2-to-10 divergence disappears.** Threshold: production-path template disagreement below 0.02 at 2-to-10, strong arm. Observed 0.3978, not triggered. The check reruns at any similarity threshold via `--sim-th`; a sim_th at which it passes while the reference pass still resolves the stream into at least half the distinct shapes found at sim_th 0.6 retires the divergence claim outright. The script scores that shape-count guard itself: a non-default `--sim-th` run measures the sim_th 0.6 shape count on the same lines, and a pass that merely coarsened the stream does not retire the claim.
- **The integer survives the split.** Threshold: cluster_id agreement at or above 0.50 over all probes, strong arm. Observed 0.0609, not triggered; at 2-to-10 it is 0.0005.
- **Where both instances hold a name at lookup time, they agree.** Threshold: disagreement below 0.02 at 11-to-100, strong arm. Observed 0.0924, not triggered.
- **Byte-identical input keeps its name inside one process.** `bench/replay.py` asserts the template moves and that the replay reports no cluster change; a drain3 release that makes the name hold fails the asserts and collapses the exhibit.
- **Drain's templates drift under reordering.** `bench/identifier.py` asserts template agreement above 0.95 at the 60,000-line reference run; below it, the stability concession at the top of this page is wrong and log10x has no business repeating it. The twin assert fires the other way: cluster_id agreement above 0.01 retires the arrival-rank claim.
- **An invented-vocabulary line ever yields two different template hashes**, across occurrences or across independent engine runs. `bench/coverage.py` checks it on every run; one mismatch retires the engine determinism claim.
- **An invented-vocabulary line comes back with a non-empty pattern name.** Same script; one occurrence retires the claim that engine coverage failures are visible rather than mislabelled.
- **A LogHub rerun stops reproducing the ledger counts**, or mints a material share of pure-variable templates. Observed zero pure-variable templates out of 574 and 370, and exact count reproduction; a mismatch fails the script.
- **Engine names degrade toward wildcards as shapes get rarer.** `bench/engine_side.py`, used-once median against over-1,000 median, floor 0.50. Observed 0.77, not triggered.
- **An exception count is not expressible in Drain's output.** `bench/multiline.py`. Fired against log10x on this file: proxy clusters exist for every burst and three of them unioned count all 2,316. The claim is withdrawn in `results/multiline.txt`, and what remains is narrower: the header-to-frames link is not a field in Drain's output, and the proxy holds only while each header shape stays exclusive to its exception.

## Fixed by the design, not tested by it

- **Production-path agreement for lines seen once is high mechanically.** Neither instance can generalize a shape it has one example of, so both mint the line's own literal text. The concession above is genuine, and this is its mechanism.
- **Lookup coverage for lines seen once is near zero by construction.** The shape occurs in one line, the line lands in one half, and `match()` requires a similarity of 1.0. It is a coverage property of a lookup API and is scored as coverage everywhere on this page.
- **The shared arm's seen-once coverage lands near one half by construction.** A shape seen once is in A's side or B's side with equal probability, and only A's side reaches B through the snapshot. Observed 0.5053, which is the sanity check passing.

## Where this applies

The split result applies where two or more processes mine independently and their names are expected to line up: multi-region or multi-cluster pipelines each mining locally, stream processors sharded on a key other than the pattern, edge agents clustering locally for sampling, and any design that ships a locally mined name upstream or persists it. Where one central miner holds the only model, at ingest or at query time, there is no second opinion and section 2 does not apply. Section 1 does apply there, because a name moving inside one process needs only that one process, and it reaches anything that persists a mined name across time.

A random half-split is also the friendliest division available: both instances draw statistically identical samples of one stream. Production splits follow placement, so each node sees different source statements, which is harsher than anything measured here.

## How this relates to log-parser accuracy benchmarks

Parser evaluations in the literature (LogHub/LogPAI, and the GA, PA, FGA and FTA metrics) measure single-run accuracy against human-labelled templates, so they need labelled ground truth and they score one miner at a time. No standard metric exists for cross-instance identity. Self-agreement is the instrument used here precisely because it needs no ground truth: shapes come from Drain's own full-stream reference pass and agreement is measured between two Drain instances, so no log10x notion of a pattern enters the Drain side of the measurement anywhere.

## Prior art, and what is not claimed

- Lossless template-plus-values storage is not novel. Prior art: CLP/YScope, US10484506B2.
- Template extraction from log text is not novel. Prior art: Drain, Spell, IPLoM.
- Compile-time message identity is not novel. Prior art: NanoLog, ETW event manifests.
- Engine-side identifiers are not unconditionally stable. They hold relative to a pinned symbol library, a pinned engine version, and that library's coverage of the emitting statement. Section 4 adds a measured fourth condition: 82.8% of templates on the published artifact carry deployment values in envelope literals, so a redeploy moves those names.
- Cross-instance agreement for the engine is not claimed as measured. The order-invariance of a content hash over a pinned library is true by construction and is therefore offered as no evidence of anything.
- Immediate naming of unfamiliar streams is not claimed as an engine advantage. Drain3 does the same with less machinery. The measured difference is the failure shape: an empty pattern under a deterministic hash, against a literal template that moves when siblings arrive.
- The split result is not claimed against centrally mining query-time products. It binds per-node mining and persisted mined names.

## Reproduce

```sh
./run.sh
```

That builds a virtualenv, installs the pinned dependencies (drain3==0.9.11 on Python 3.13), runs the replay first, then downloads the public release assets if absent, records their sha256 and line counts to `results/data_provenance.txt`, and runs the remaining experiments cheapest first, writing every artifact under `results/`. Measured on an Intel macOS laptop: replay under 1s, engine_side about 5s, identifier about 25s, multiline about 65s, coverage about 2 minutes with the Docker image present (it skips cleanly without), identity about 19 minutes. `PIB_QUICK=1 ./run.sh` runs the identity experiment at 60,000 lines and 3 trials. `PIB_PYTHON`, `PIB_VENV` and `PIB_DATA_DIR` override the interpreter, the virtualenv location and the download cache. The otel-sample assets are cached gzipped and read in place; the LogHub sets cache under `data/` as well.

Runs are deterministic and no artifact records a wall-clock time, so `git diff --exit-code results/` after a rerun is a usable gate. Timings go to stderr.

| script | question | artifact |
|---|---|---|
| `bench/replay.py` | one process: does a line keep its name when siblings arrive later | `results/replay.txt` |
| `bench/identity.py` | two instances, split halves, same probe sequence through the production path: template and identifier agreement by frequency, plus query-time lookup coverage | `results/identity.md`, `results/identity_raw.json` |
| `bench/identifier.py` | two arrival orders: does the template travel, does the integer travel | `results/identifier.txt` |
| `bench/multiline.py` | a stack trace is one event to a reader: how many names does each side give it | `results/multiline.txt` |
| `bench/engine_side.py` | how finely does the engine name this stream, and how much source text does each name pin down | `results/engine_side.md` |
| `bench/coverage.py` | what the engine does with vocabulary its library never held | `results/coverage.md`, `results/coverage_raw.json` |

## Known limits

Stated in the terms the reviewers of this benchmark used, because an objection published by the author is a caveat and the same objection found by a reader is a refutation.

- **The divergence bands come from one dataset family.** Every frequency-stratified number in section 2 is measured on one OpenTelemetry demo stream. The LogHub sets exercise only the engine coverage exhibit, not the split. The mechanism is source-verified and order-driven, so the direction should transfer; the magnitudes are properties of this stream.
- **The probe pass shares traffic between the instances.** Both ingest every probe, so their states converge during the measurement, and the reported divergence understates, in expectation, what a fleet with no shared traffic would see. The direction is net rather than guaranteed per probe: a probe that matches different clusters in the two instances wildcards one side's template only, so a later probe of a different shape can flip from agree to differ because of the shared ingest.
- **The seen-once stratum has no operational counterpart.** A shape that occurs exactly once in the whole stream is processed by exactly one forwarder and receives exactly one name. The row is reported because the falsifier on it fired against log10x and because the mechanism is instructive, not because a fleet behaves that way.
- **The half-split indicts an architecture many platforms do not run.** A deployment that mines centrally against one model has no cross-instance problem, and a reader running one correctly concludes that section 2 does not apply to them. Section 1 still does.
- **The engine artifacts are vendor-produced.** The coverage experiments run a pinned vendor-built Docker image, digest recorded in `results/coverage.md`, and this benchmark does not build the engine from source. The otel-sample templates asset is the encoding run's own output dictionary, which is why its resolve rate is a gate and not evidence, and whether that symbol library was compiled with sight of the otel stream is not disclosed in the release. The invented-vocabulary probe exists because it cannot be answered by anything compiled with sight of anything.
- **The encoded artifact is for analysis.** `encoded.log` carries `pattern=` and `patternHash=` fields for tooling. No storage-reduction figure may be computed from it, and none appears here.
- **Part of the engine's template identity is deployment-specific.** 82.8% of templates on the published artifact carry environment values in envelope literals, so a redeployment with a new image tag or pod hash changes some names. Cross-deployment engine agreement is unmeasured, and this is a concrete reason it could be below 1.0.
- **This sample is a weak surface for multi-line claims.** 2,311 of 2,316 exception bursts come from one container emitting one error shape, so the burst statistics describe one shape repeated, and `results/multiline.txt` says so in its scope note.
- **drain3 is pinned at 0.9.11 and a version bump is a re-run gate, not a routine update.** `bench/replay.py` and `bench/identifier.py` assert current library behaviour, and both refuse to run under `python -O` so the asserts stay live.
