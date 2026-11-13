# Pattern identity benchmark

Does a log line get the same pattern name in two places, and keep it over time? Sampling and suppression rules key on that name. Two Drain3 instances, each mining one half of the same stream, gave a line whose shape occurs 2 to 10 times the same template 0.6022 of the time. Two 10x engine instances fed the same halves gave the same pattern name to 299,997 of 300,000 probe lines.

A Drain3 template is the running intersection of every line in its cluster, so the template changes when a sibling line arrives. In one process, the same bytes replayed after two siblings got a new template, and Drain3 reported no cluster change. The 10x engine takes names from a compiled symbol library instead of mining them.

## Result

Share of probe lines both instances named the same, mean of 10 trials.

| Shape occurs in stream | Probes per trial | Drain3 template | Drain3 cluster_id | Engine pattern hash |
|---|---:|---:|---:|---:|
| once | 136 | 0.9859 | 0.0007 | 1.0000 |
| 2 to 10 times | 204 | 0.6022 | 0.0005 | 1.0000 |
| 11 to 100 times | 589 | 0.9118 | 0.0051 | 1.0000 |
| 101 to 1,000 times | 916 | 0.9788 | 0.0070 | 1.0000 |
| over 1,000 times | 28,152 | 1.0000 | 0.0646 | 1.0000 |
| all probes | 30,000 | 0.9949 | 0.0609 | 1.0000 |

A line seen once agrees because neither Drain3 instance can generalize from one example. The divergence starts when Drain3 generalizes, and the all-probes row hides it because shapes seen over 1,000 times are 94% of probes.

- Fed the same 60,000 lines in two orders, two Drain3 runs agreed on the template 0.9860 of the time and on `cluster_id`, an arrival counter, 0.0001.
- The 3 engine probes that differed were indented lines joined to each half's last event, and the two halves ended differently.
- A second engine identifier, the template hash, differed on 44 probes of one Grafana statement, because for those events it depends on what the instance read before.

## How it was measured

The data is 197,430 Fluentd/Kubernetes lines from the OpenTelemetry demo ([otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1)), covering 10.3 hours. Each trial splits the stream into random disjoint halves, like two forwarders that never share state, and after its half each instance names the same 30,000 probe lines. Both ingest every probe, so their states converge, which on net favors Drain3. Drain3 0.9.11 runs its strongest tested configuration against engine 1.1.142, and the fork drain3-improved 0.10.0 gave identical numbers.

## Limits

- The data is one small demo cluster, and the magnitudes belong to this stream.
- A central miner, such as a SIEM that mines at query time, has no second instance to disagree, but the replay result still applies. Drain3 needs no build step and is the right default when the emitting code is out of reach.
- The demo's source is in the engine's default symbol library. On invented words the engine returned an all-variable template named by a hash.
- Of the engine's templates here, 82.8% carry deployment values such as image tags, and agreement across redeploys is unmeasured.

## Run it

```
cd pattern-identity
./run.sh                 # full run, writes every artifact under results/
PIB_QUICK=1 ./run.sh     # identity experiment at 60,000 lines and 3 trials
```

The script needs Python 3.13 and downloads the sample. The Drain3 split takes about 19 minutes, and the engine split takes about 35 and needs Docker.

[RECORD.md](RECORD.md) has every experiment and the tests that could prove log10x wrong, two of which fired against it.
