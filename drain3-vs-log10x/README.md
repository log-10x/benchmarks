# log10x vs Drain3: pattern stability and lossless reduction

A saved search or an alert points at a log pattern group by its stored text. Drain3, the open-source implementation of the Drain algorithm, rewrites that text as new lines arrive. On 16 public loghub samples of 2,000 lines, read in two orders and in halves, the 10x engine gave each line one pattern ID throughout, and Drain3 gave as few as 83.4% of lines the same template in both orders. The engine rebuilt 99.98% of lines byte for byte and Drain3 66.48%, and every line Drain3 missed differs only in its spacing.

Drain compares each new line against the text it already stored for that group, and every spot where the two differ is blanked out.

## Pattern IDs and rebuilt lines on 16 samples

| Measure | 10x engine | Drain3 |
|---|---:|---:|
| Same ID in both orders (worst) | 100% | 83.4% (Zookeeper) |
| Same ID alone and combined (worst) | 100% | 0.8% (Windows) |
| Lines rebuilt byte for byte (mean) | 99.98% | 66.48% |
| Samples rebuilt byte for byte | 14 of 16 | 5 of 16 |
| Templates, all 16 samples | 4,367 | 1,761 |

The second row compares a line's ID in its half alone and in the whole file. Drain3's ID is its matched template text, since its cluster numbers are per-run counters, and the engine's is a content-addressed template hash.

- The same 2,000 Mac lines in two orders gave Drain3 37 templates only in one order and 40 only in the other. The engine's sets matched on every sample.
- Drain3 rebuilt the BGL and Thunderbird samples in full, where the engine rebuilt 99.75% and 99.9%, and 99.73% of the full BGL file's 4,747,963 lines. Of the 12,648 misses, 11,904 quote a date with a zone name and come back as the same instant in another zone. The decoder skips 737 lines of 13 templates with hashes of eight characters or fewer, and one template whose encoded records end early accounts for 7.
- The 1,363 templates in loghub's hand labels are closer to Drain3's count than to the engine's. On the full BGL file the engine found 136,461 templates against Drain3's 842, and loading them made decode slow. For a short template list, Drain3 is the better fit.

## How the lines were split, reordered and rebuilt

Both tools read identical bytes with LF line endings, and run each sample's first half A and second half B as A, B, A+B and B+A. The engine's decode output is compared with its input. The harness rebuilds each Drain3 line from its matched template by token position with single spaces, which loses every tab, run of spaces and leading or trailing space.

## Scope of the test

- The data is public research logs from loghub.
- Drain3 ran with default settings, and a run with number, hex and IP masking is kept per sample in the facts file.
- Storage size is out of scope, and [loghub-compaction](../loghub-compaction/) measures compact size.

## Rerunning the comparison

```
cd drain3-vs-log10x
pip install -r requirements.txt
python smoke_test.py      # Drain3 whitespace check, no Docker or data
cd bench                  # full rerun, needs the loghub setup
python bench.py && python stability.py all && python facts.py
```

A full rerun needs Docker, the engine image `log10x/pipeline-10x:1.1.136` and the loghub clone in [RECORD.md](RECORD.md#setup). Reference numbers are in [bench/facts.json](bench/facts.json).

[RECORD.md](RECORD.md) has the field definitions, setup, the full BGL run and what each script does.
