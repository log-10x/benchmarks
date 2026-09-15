
# Verified against the patched engine, 2026-09-15

Both patches applied, built and rerun. The reproduction's own `analyze.py`
produced every number below from `out-patched/<variant>/wire/returned.json`.

| Part | What ran |
|---|---|
| engine | the JVM build of `log-10x/engine` `main` + `0001`, with `log-10x/pipeline-extensions` `main` + `0002`, as `run-cloud-<version>-all.jar` on `eclipse-temurin:23-jre` |
| collector | `otel/opentelemetry-collector-contrib:0.160.0`, the image the reproduction pinned |
| config, modules | `log-10x/config` and `log-10x/modules` at `main`, the pairing CI builds `main` against, with the same asserted edits `patch_config.py` makes |

The shipped `ghcr.io/log-10x/edge-10x` image is a native binary, so a patched
engine cannot be dropped into it and no image was published for this. The
topology is otherwise the run `repro.sh` performs: two containers on one
network, the engine listening on 4317, the return arriving on 24225, the
collector's file exporter writing every returned record with no processor in
between. `verify-patched.sh` is the runner.

## The 56 crafted lines, all four variants

| Measure | `resource` | `noresource` | `nodrop` | `withtime` |
|---|---:|---:|---:|---:|
| records returned | 55 | 55 | 55 | 55 |
| carrying attributes | 55 | 55 | 55 | 55 |
| carrying no attribute at all | 0 | 0 | 0 | 0 |
| carrying `routeState` | 55 | 55 | 55 | 55 |
| carrying `tenx_hash` | 55 | 55 | 55 | 55 |
| carrying `message_pattern` | 55 | 55 | 55 | 55 |
| `timeUnixNano` set | 55 | 55 | 55 | 55 |
| `timeUnixNano` zero or absent | 0 | 0 | 0 | 0 |
| `observedTimeUnixNano` set | 55 | 55 | 55 | 55 |
| a resource attribute present | 55 | 0 | 55 | 55 |
| `service.name` as a log attribute | 0 | 0 | 0 | 0 |
| attribute names nothing configured | 0 | 0 | 0 | 0 |

Read against the unpatched run in "The numbers" above:

- **D1 and D3 are gone.** Every record parses, in every variant, at every
  escape count from 0 to 40. No `taenx_resource_keys`, no `_tes`, no variant
  spelling of anything: the count of attribute names outside the configured set
  is zero across all four variants, where `resource` alone previously carried
  five of them. The `noise` block still comes back with 11 attributes, so the
  fix did not buy the clean sweep by suppressing a field.
- **The service is in one place.** `resource` now sets the OTLP resource on 55
  of 55 and writes `service.name` as a log attribute on none, where it was 15
  and 10. `noresource` sets no resource, which is what that variant asks for.
  This was never a quirk of the collector; a damaged `_tenx_resource_keys` was
  simply not readable by the appender.
- **D2 is gone.** 55 of 55 carry a `timeUnixNano` in every variant, `nodrop`
  included, where `nodrop` previously carried none. The no-record-time input is
  the interesting one: `_tenx_time` renders as 0, `_tenx_observed_time` carries
  the collector's observed time, and the appender now uses it. `withtime`,
  which sets a record time on the way in, still returns that time rather than
  the observed one.
- **The two fixes are independent and both are needed.** `nodrop` isolates D2
  (no drop configured, so the coordinates never matter) and it passes. The
  sweep isolates D1 and D3 and they pass with the drop in place.

## The 50,000 line slice

`clickstack-e2e/data/slice.log`, the slice the ClickStack harness ran, through
the same patched engine and the same collector.

| Measure | Original run, engine 1.1.74 | Patched engine |
|---|---:|---:|
| records returned | 37519 | 37540 |
| marked | 18083 | 37540 |
| unmarked | 19436 | 0 |
| carrying a `timeUnixNano` | 19436 | 37540 |
| carrying a resource attribute | not measured | 37540 |
| attribute names nothing configured | 8 spellings, 2133 records | 0 |

Every returned record carries `routeState`, so every one of them is routable:
the half of the sample that used to take the default path into the hot table
because it carried no mark is now zero. The 21 record difference in the total
is the multiline grouping landing a few continuation lines differently between
the two runs, not a change in what returns.

## Unit tests

| Repo | Test | Cases |
|---|---|---:|
| `log-10x/engine` | `ExtractDropRangeCoordinatesTest` | 9 |
| `log-10x/pipeline-extensions` | `OtlpLogsOutputAppenderTimestampsTest` | 7 |

Both are falsifiable against the file as it stood. The extractor test fails at
5 and 30 escape sequences without `0001`; 0, 1 and 2 pass either way, because
the character at the splice boundary repeats, which is the ambiguity the sweep
already measured. The appender test's zero cases fail without `0002`: the old
body returned true and stamped 0, measured by running it verbatim.

Suites of the touched modules, all green: engine `:tests` 308 tests,
`edge-extensions` 7, `cloud-extensions` 257 with 14 skipped (the skips are the
Azurite and live-service integration tests, unrelated).
