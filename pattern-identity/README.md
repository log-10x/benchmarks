# Pattern identity benchmark

A saved search or an alert points at a log pattern group by its stored text. Drain3, the open-source implementation of the Drain algorithm, rewrites that text as new lines arrive. Two copies fed random halves of one log set disagree on the stored text for many repeated shapes, and two 10x engine instances fed the same halves gave the same pattern name to 299,997 of 300,000 probe lines.

Drain decides which words in a log line stay the same and which change by comparing each new line against the text it already stored for that group. Every spot where the two lines differ is blanked out. The 10x engine's compiler takes the source, or the binaries and container images the application ships as, and links the message text and names into a symbol library that is settled before the first log line arrives.

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

A reference pass over the same stream resolved it into 1,481 distinct shapes, 921 of them seen once. On those same test log lines the two copies rarely pick the same group number.

- Three consecutive Grafana provisioning log lines were fed to one copy (0.9.11) in order, then the first one again, and the text stored for that group changed between the first call and the fourth. On the fourth call the tool reports `change_type='none'`, and the group number held across all four calls too.
- An alert check looks a log line up rather than feeding it in, and asked that way a log line seen once almost never has a group in one of the two copies.

## How it was measured

The log set is the public [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1) capture of the OpenTelemetry demo. The log set's 197,430 lines were shuffled, then split down the middle, one random half to each copy, so neither saw the other's. The benchmark calls that random split the friendliest division available to Drain. After its half each instance names the same 30,000 probe lines. Drain3 0.9.11 runs its strongest tested configuration against engine 1.1.142.

## Limits

- The price is running that compiler over the code that prints the logs, which watching traffic never asks for.
- When no word in a line is in the library, 10x gives the line a pattern from its shape: `template_` followed by a hash of its punctuation and of where its values sit.

## Run it

```
cd pattern-identity
./run.sh                 # full run, writes every artifact under results/
PIB_QUICK=1 ./run.sh     # identity experiment at 60,000 lines and 3 trials
```

The script needs Python 3.13 and downloads the sample. The Drain3 split takes about 19 minutes, and the engine split takes about 35 and needs Docker.

[RECORD.md](RECORD.md) has every experiment and the tests that could prove log10x wrong, two of which fired against it.

The same measurement, with more context: https://www.log10x.com/blog/drain-pattern-groups-change/
