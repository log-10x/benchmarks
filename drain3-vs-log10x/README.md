# log10x vs Drain3: pattern stability and lossless reduction

Does a log line keep the same pattern ID whatever order the lines arrive in, and can the original line be rebuilt byte for byte? This benchmark gives the same lines to log10x and to Drain3, the open-source template miner, on 16 public loghub datasets. log10x kept every ID stable on all 16 and rebuilt 99.98% of lines exactly, against 66.48% for Drain3. Drain3 found fewer templates, closer to the hand-labelled count.

## Result

Figures over the 16 loghub samples of 2,000 lines each.

| Measure | log10x | Drain3 |
|---|---:|---:|
| Same ID in both orders (worst) | 100% | 83.4% (Zookeeper) |
| Same ID alone and combined (worst) | 100% | 0.8% (Windows) |
| Lines rebuilt byte for byte (mean) | 99.98% | 66.48% |
| Datasets rebuilt byte for byte | 14 of 16 | 5 of 16 |
| Templates found | 4,367 | 1,761 |

The second row compares the ID a line gets when its half is read alone with its ID in the whole file. loghub's hand labels list 1,363 templates.

- Drain3's patterns depend on reading order. The same 2,000 Mac lines in two orders gave 37 templates found only in one order and 40 only in the other. log10x found the same set in both orders on every dataset.
- log10x missed exact rebuild on BGL (99.75%) and Thunderbird (99.9%). On the full BGL file of 4,747,963 lines it rebuilt 99.73%. Of the 12,648 lines that differ, 11,904 quote a date with a zone name and come back as the same instant written in another zone. The rest trace to two other defects listed in the record.

## How it was measured

Both tools read identical bytes, with line endings converted to LF. The 10x engine ran in Docker as a codec: one pass encodes, a second decodes, and the output is compared with the input. Drain3 ran with default settings and has no decoder, so the harness rebuilds each line from its template by token position, which joins tokens with single spaces. Drain3 therefore misses exactly the lines with a tab, a run of spaces or a leading or trailing space. For stability, each dataset is split into halves A and B, and both tools run on A, B, A+B and B+A.

## Limits

- The data is public research logs, plus one full BGL file.
- Storage size is out of scope. Compaction on the full loghub datasets is in [loghub-compaction](../loghub-compaction/).
- Every Mac and Windows line has whitespace that the token-position rebuild cannot restore, so Drain3 scores 0% there.
- For a short template list close to the hand labels, Drain3 is the better fit. log10x found more templates on 14 of 16 datasets, and 136,461 against Drain3's 842 on the full BGL file.

## Run it

```
pip install -r requirements.txt
python smoke_test.py      # Drain3 whitespace check, no Docker or data
cd bench                  # full rerun, needs the loghub setup
python bench.py && python stability.py all && python facts.py
```

A full rerun needs Docker, the engine image `log10x/pipeline-10x:1.1.136`, Drain3 0.9.11 and the loghub clone in [RECORD.md](RECORD.md#setup). Reference numbers are in [bench/facts.json](bench/facts.json).

[RECORD.md](RECORD.md) has the field definitions, setup, the full BGL run and what each script does.
