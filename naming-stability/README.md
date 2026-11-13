# Naming stability across releases

When the 10x engine moves to its next release, do the same log events keep the same pattern names? Across releases 1.1.140, 1.1.141 and 1.1.142, on two captures of the OpenTelemetry demo, no event changed its pattern name, its pattern hash or its template hash.

Each event gets a pattern name, a pattern hash (`tenx_hash`, the hash of the name) and a template hash. Each release ran with the configuration and symbol library its own image ships.

## Result

| Capture | Releases | Events | Events changed | Patterns renamed |
|---|---|---:|---:|---:|
| rec1155 | 1.1.140 to 1.1.141 | 41,573 | 0 | 0 of 582 |
| rec1155 | 1.1.141 to 1.1.142 | 41,573 | 0 | 0 of 582 |
| otel215 | 1.1.140 to 1.1.141 | 157,228 | 0 | 0 of 2,687 |
| otel215 | 1.1.141 to 1.1.142 | 157,228 | 0 | 0 of 2,687 |

Each pair of releases cut each capture into the same events, so events were compared one for one. An event counts as changed when any of its three names or hashes differs.

- The three images carry the same 1.1.89 symbol library. In the shipped configuration, 18 files differ between 1.1.140 and 1.1.141 and none between 1.1.141 and 1.1.142.
- In 1.1.141, a line opening with the ANSI dim code starts its own event. Neither capture has such a line, so that change had nothing to act on here.
- The intent benchmark reports fewer patterns for the same 1.1.142 image (2,277 on otel215, 406 on rec1155) because it counts only the events it has source labels for.

## How it was measured

The two captures are the ones the [intent benchmark](../intent) uses, each checked by SHA-256. Each release's engine image was pinned by digest and run on each capture as a file, writing every event's pattern name, both hashes and its text. A script compared consecutive releases event by event. A pattern of the earlier release counts as renamed when any of its events carries another name in the later one. The runs were made on 2026-10-15.

## Limits

- Both captures come from one application, the OpenTelemetry demo (versions 2.2.0 and 2.1.3). Another application, or the ANSI-colored lines that 1.1.141 regroups, can rename where these do not.
- The engine read each capture as a file. The 1.1.142 release notes describe a flush timer change on the forwarder input, which is not measured here.
- Only three releases are compared. Names did change between two earlier ones: on otel215 the intent benchmark counts 6,944 merged events for 1.1.132 and 13 for 1.1.133.
- A library change is not measured, since all three images carry the same one. The page makes no promise about future releases.

## Run it

From this directory:

```
python3 bench/compare.py --render | diff - results/results.md   # check the table against compare.json
NS_PRUNE=1 ./run.sh                                         # full rerun: downloads both captures, pulls the three images
```

The full rerun needs Docker, curl and Python 3, and took one to three minutes per release on an Intel macOS laptop, plus the image pulls.

The complete record is in [RECORD.md](RECORD.md): the changes each release's notes list, how the pattern counts reconcile with the intent benchmark, the full method and the files.
