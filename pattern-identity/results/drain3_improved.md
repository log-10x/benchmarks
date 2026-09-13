# The same experiments against the maintained fork, drain3-improved 0.10.0

Every Drain-side experiment in this benchmark was rerun against
[drain3-improved](https://github.com/jpodivin/Drain3-improved) 0.10.0, the maintained fork,
with the same seed, the same configuration and the same input. The upstream artifacts in this
directory were produced by drain3 0.9.11.

**Every measured number is identical.** Not close: identical, to the last digit, including the
per-trial counts in the raw JSON.

## How it was run

Upstream `drain3` and the fork `drain3-improved` install the same import name, `drain3`, so a
second virtualenv with the fork installed is all the difference:

```sh
python3 -m venv .venv-fork
.venv-fork/bin/pip install drain3-improved==0.10.0
.venv-fork/bin/python bench/replay.py     > results/replay_drain3_improved.txt
.venv-fork/bin/python bench/identifier.py > results/identifier_drain3_improved.txt
.venv-fork/bin/python bench/multiline.py --full-line > results/multiline_drain3_improved.txt
.venv-fork/bin/python bench/identity.py \
  --out-md   results/identity_drain3_improved.md \
  --out-json results/identity_drain3_improved_raw.json
```

No flag, no threshold and no seed was changed. `bench/drainver.py` exists because
`importlib.metadata.version("drain3")` raises under the fork, whose distribution is named
`drain3-improved`; every artifact now records which distribution produced it.

`bench/engine_side.py` and `bench/coverage.py` do not import drain3 and were not rerun.

## What came back

| Artifact | Fork artifact | Difference from the upstream run |
|---|---|---|
| `replay.txt` | `replay_drain3_improved.txt` | the version line only |
| `identifier.txt` | `identifier_drain3_improved.txt` | the version line only |
| `multiline.txt` | `multiline_drain3_improved.txt` | **none, byte for byte** |
| `identity.md` | `identity_drain3_improved.md` | the version line only |
| `identity_raw.json` | `identity_drain3_improved_raw.json` | the `env` block only |

The raw JSON comparison is the strict one: strip `env.drain3_version` and
`env.drain3_distribution` and the two files are equal objects, so all thirty trials across
three arms produced the same counts in the same strata.

### The table both versions produce

Production path, `strong` arm, 10 trials, 30,000 probes per trial:

| line frequency | probes/trial | template agreement | cluster_id agreement |
|---|---:|---:|---:|
| seen once | 136 | 0.9859 | 0.0007 |
| 2 to 10 | 204 | 0.6022 | 0.0005 |
| 11 to 100 | 589 | 0.9118 | 0.0051 |
| 101 to 1,000 | 916 | 0.9788 | 0.0070 |
| over 1,000 | 28,152 | 1.0000 | 0.0646 |
| all events | 30,000 | 0.9949 | 0.0609 |

### The exhibits both versions produce

- The replay asserts hold. A Grafana provisioning line is named on first sight, two siblings
  arrive, and the same bytes replayed come back under a different template while
  `change_type` reports `none`. Both sha256 values in `replay_drain3_improved.txt` match the
  upstream artifact.
- `identifier.py`: template agreement 0.9860 against `cluster_id` agreement 0.0001 across two
  arrival orders, and 0.9848 against 0.0000 under `max_clusters=500`.
- `multiline.py` reproduces byte for byte, including the withdrawn exception-count claim.

## Why this is worth recording rather than skipping

The fork exists because upstream went quiet
([logpai/Drain3#120](https://github.com/logpai/Drain3/issues/120), 2026-04-28), and it has
moved: masking and snapshot-timing changes shipped in August 2026. A reader of this benchmark
is entitled to ask whether the identity results are a property of an unmaintained release. On
this data, at this configuration, they are not. The mechanism is unchanged in the fork's own
source: `create_template` still returns the running intersection of the two token sequences
and writes it back, `tree_search` still partitions on token count at the first level, and
`match()` still documents "Match shall be perfect (sim_th=1.0)" with
`full_search_strategy="never"` as its default.

## What this does not say

- **Not a claim about every fork release.** 0.10.0, on this stream, at this configuration. A
  later release that changes `create_template` or the identifier would move these numbers, and
  a version bump is a rerun gate here exactly as it is for upstream.
- **Not a defect report against the fork.** The fork reproduces upstream's behaviour on these
  exhibits, which is what a fork maintaining compatibility should do.
- **Not a claim about the Go implementations.** The OpenTelemetry Collector's drain processor
  and Loki's pattern ingester are separate implementations and are not measured here.

## Configuration, for the record

Both runs: depth 6, sim_th 0.6, max_children 20, max_clusters 2,000,
`parametrize_numeric_tokens=True`, message capped at 1,024 characters, seed 100, Python
3.13.11. These are not the library's factory values, which in 0.10.0 are depth 4, sim_th 0.4,
max_children 100 and no cluster cap (`drain3/template_miner_config.py`). On this data the
settings used raise agreement rather than lowering it.
