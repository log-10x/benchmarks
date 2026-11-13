# Intent: does each pattern hold one logging statement?

A log platform groups repeated lines and shows a count beside each group. A cap, a sample rate or a route set on a group acts on every statement inside it. Against labels naming the source line behind the events of three captures, the 10x engine put 0.01% to 0.21% of events in another statement's group, fewer than [Drain3](https://github.com/logpai/Drain3) in every configuration. Drain3 with masking split fewer events and produced fewer patterns on two captures.

## Events grouped with a different statement

otel215 and rec1155 are OpenTelemetry demo captures.

| Tool | otel215 | rec1155 | ZooKeeper |
|---|---:|---:|---:|
| 10x engine | 0.01% (13) | 0.15% (63) | 0.21% (153) |
| Drain3, example-config masking | 0.05% (83) | 1.78% (734) | 0.75% (555) |
| Drain3, typed-token masking | 0.06% (99) | 1.81% (749) | 0.55% (412) |
| Drain3, factory defaults | 0.15% (239) | 3.34% (1,381) | 1.12% (831) |

Drain3's merges on otel215 pair statements that differ in one word, such as Grafana's "starting to provision dashboards" and "finished to provision dashboards". Fed one record at a time, as it normally runs, Drain3 with example-config masking merges 4.48% of otel215's events, 6,930 of them because the cart service's .NET logger prints this header above its three statements:

```
info: cart.cartstore.ValkeyCartStore[0]
```

The engine names that event from its message line.

## Split events and pattern counts

A split event sits outside its statement's most frequent pattern, which costs that statement an extra rule. With example-config masking, Drain3 splits 3.47% of otel215's events against the engine's 4.59% and 0.32% of ZooKeeper's against 1.21%. On rec1155 the engine splits fewer, 9.95% against 10.37%. Drain3 produces 865 patterns for otel215's labeled events against 2,277, and 58 for ZooKeeper's against 97. Two Grafana migration statements make 1,331 of the engine's, one per migration id.

## How the events were labeled

The labels cover 99.58% of otel215's 157,228 events, 99.42% of rec1155's 41,573 and all 74,380 lines of LogHub's ZooKeeper log, come from source code alone, and were frozen before any tool's output was read. Engine 1.1.142 ran as shipped, and Drain3 0.9.11 was given the engine's events with the settings of [pattern-identity](../pattern-identity) or its factory defaults. The scorer gives each pattern to the statement with most of its events and counts the rest as merged.

## Scope of the test

- No capture is a clean out-of-sample test. The engine's rule for naming a multi-line event was built with both demo captures in view, and 2,000 ZooKeeper lines were in view during development.
- Log10x wrote the labels, each naming a source line in `labels/`.
- The engine's symbol library lists the source behind 145,612 of otel215's 156,563 labeled events and none of ZooKeeper's. Outside it on otel215, the engine merges 0.13% of events against Drain3's 0.86%, and Drain3 groups more of them one statement to one pattern, 65.49% against 62.89%.
- The captures come from two applications, and three statements of the collector's debug exporter wrote 85,739 of otel215's events.

## Run it

```
python3 intent/bench/summarize.py   # print the result tables from the committed scores
cd intent && ./run.sh                # full rerun
```

A full rerun needs Docker, curl and Python 3 and takes about 55 minutes on an Intel laptop.

[RECORD.md](RECORD.md) has every score table and the Drain3 settings, and [METHOD.md](METHOD.md) explains how each label was made.
