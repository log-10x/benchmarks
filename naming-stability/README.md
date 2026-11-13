# Naming stability across releases

The 10x engine gives each log event a pattern name, a pattern hash (`tenx_hash`, the hash of the name) and a template hash, and a per-pattern budget, a routing rule or a cost report keys on the pattern. Three consecutive engine releases, 1.1.140, 1.1.141 and 1.1.142, ran over two captures of the OpenTelemetry demo. Across 157,228 events in one capture and 41,573 in the other, no event changed its pattern name, pattern hash or template hash between releases.

10x gives each line an ID taken from the fixed words the code prints, leaving out every value that is not a word in its library. Nodes running the same pinned library and engine version agree on it. All three images carry the same 1.1.89 library, so this test keeps the library and changes the engine and its shipped configuration.

## Names the three releases gave the same events

| Capture | Releases | Events | Events changed | Patterns renamed |
|---|---|---:|---:|---:|
| rec1155 | 1.1.140 to 1.1.141 | 41,573 | 0 | 0 of 582 |
| rec1155 | 1.1.141 to 1.1.142 | 41,573 | 0 | 0 of 582 |
| otel215 | 1.1.140 to 1.1.141 | 157,228 | 0 | 0 of 2,687 |
| otel215 | 1.1.141 to 1.1.142 | 157,228 | 0 | 0 of 2,687 |

Each pair of releases cut each capture into the same events, so events were compared one for one. A pattern counts as renamed when any of its events carries another name in the later release.

- The 1.1.141 release notes say the engine is unchanged, and 18 files of the shipped configuration differ, among them the group, template and rate modules. In 1.1.142 no configuration file differs, and its notes list two engine changes.
- In 1.1.141 a line opening with the ANSI dim code starts its own event, and neither capture has such a line.

## How each release was run

The captures are otel215 from the [otel-sample-v1](https://github.com/log-10x/config/releases/tag/otel-sample-v1) release and rec1155 from this repository's [intent-data-v1](https://github.com/log-10x/benchmarks/releases/tag/intent-data-v1) release, both checked by SHA-256. Each release's image, pinned by digest, read each capture as a file and wrote every event's pattern name, both hashes and its text. A script compared consecutive releases event by event. The runs were made on 2026-10-15.

## Applications, inputs, releases and libraries outside this test

- Both captures come from one application, the OpenTelemetry demo (versions 2.2.0 and 2.1.3). Another application, or the ANSI-colored lines that 1.1.141 regroups, can change names where these did not.
- The 1.1.142 release notes describe a flush timer change on the forwarder input, and no forwarder run is measured here.
- Releases before 1.1.140 are not compared, and names did change between two of them: on otel215 the [intent benchmark](../intent) counts 6,944 merged events for 1.1.132 and 13 for 1.1.133.
- A library change is not measured, and a new library is where names built from library words would move. These results promise nothing about later releases.

## Run it

```
cd naming-stability
python3 bench/compare.py --render | diff - results/results.md   # check the table against compare.json
NS_PRUNE=1 ./run.sh                                             # full rerun: downloads both captures, pulls the three images
```

The check needs only Python. The full rerun needs Docker, curl and Python 3, and took one to three minutes per release on an Intel macOS laptop, plus the image pulls.

[RECORD.md](RECORD.md) has the changes each release's notes list, how the pattern counts reconcile with the intent benchmark, the full method and the files.
