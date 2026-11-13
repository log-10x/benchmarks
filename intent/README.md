# Intent: does each pattern hold one logging statement?

A cap or sample rate set on a log pattern is only safe when the pattern stands for one logging statement. This benchmark labels each event with the source line that wrote it and counts how often a tool puts two statements in one pattern. On three captures the 10x engine merged 0.01% to 0.21% of events, fewer than Drain3 in every configuration. Drain3 with masking split fewer events and produced fewer patterns on one of two demo captures and on ZooKeeper.

A merged event shares its pattern with a different statement, so a cap on that pattern acts on both. A split event sits outside its statement's main pattern, and that pattern can still be capped on its own.

## Result

Share of events merged with another statement. otel215 and rec1155 are two OpenTelemetry demo captures.

| Tool | otel215 | rec1155 | ZooKeeper |
|---|---:|---:|---:|
| 10x engine | 0.01% (13) | 0.15% (63) | 0.21% (153) |
| Drain3, example-config masking | 0.05% (83) | 1.78% (734) | 0.75% (555) |
| Drain3, typed-token masking | 0.06% (99) | 1.81% (749) | 0.55% (412) |
| Drain3, factory defaults | 0.15% (239) | 3.34% (1,381) | 1.12% (831) |

Drain3's merges on otel215 pair statements that differ in one word, such as Grafana's "starting to provision dashboards" and "finished to provision dashboards".

- Drain3 splits 3.47% of otel215's events against the engine's 4.59%, and with masking 0.32% of ZooKeeper's against 1.21%. The engine splits fewer on rec1155.
- Drain3 produces 865 patterns on otel215 against 2,277, and 58 on ZooKeeper against 97. Two Grafana statements make 1,331 of the engine's, one pattern per migration id.
- Fed one record at a time, as it normally runs, Drain3 merges 4.48% of otel215's events, because every cart service message starts with the same .NET header line.

## How it was measured

otel215 has 157,228 events from Fluentd, rec1155 has 41,573 from Fluent Bit, and ZooKeeper is LogHub's 74,380-line log from 84 statements. Each event was labeled from source code alone with the file and line that wrote it, and the labels were frozen before any tool's output was read. They cover 99.58% of otel215, 99.42% of rec1155 and all of ZooKeeper. The engine (release 1.1.142) ran as shipped, Drain3 0.9.11 was given the same events, and `bench/score.py` scored both against the labels.

## Limits

- No capture is a clean out-of-sample test. Both demo captures and 2,000 ZooKeeper lines were in view during the engine's rule work.
- Log10x wrote the labels, and each names a source line in `labels/` that can be checked.
- The engine's built-in library lists the source behind 145,612 of otel215's 156,563 labeled events and none of ZooKeeper's. On otel215 statements outside it, the engine merges 0.13% of events against Drain3's 0.86%.
- Only two applications are covered, and the collector's debug exporter wrote 85,739 of otel215's 157,228 events.

## Run it

```
python3 intent/bench/summarize.py   # print the result tables from the committed scores
cd intent && ./run.sh                # full rerun
```

A full rerun needs Docker, curl and Python 3 and takes about 55 minutes on an Intel laptop.

[RECORD.md](RECORD.md) has the full score tables, the Drain3 settings and the image digests, and [METHOD.md](METHOD.md) explains how each label was made.
