# log10x vs Drain3 — lossless log-reduction benchmark

Reproducible harness behind the Log10x blog post *"The pattern ID you can plot: stability
and losslessness measured on 16 real datasets"*.

It feeds the **same raw log lines** to both tools and measures three things across the 16
[loghub](https://github.com/logpai/loghub) 2k datasets (~32,000 lines):

1. **Losslessness** — can you reconstruct the exact original bytes from the reduced form?
2. **Pattern stability** — does a line get the same pattern ID regardless of file / order?
3. **Representation size** — bytes (raw + gzip) of each tool's reduced form.

Reference results are committed in [`bench/facts.json`](bench/facts.json) (canonical roll-up)
and [`bench/results.json`](bench/results.json) (per-dataset). Rerunning should reproduce them.

## Prerequisites

- **Python 3.9+** with Drain3 pinned: `pip install -r requirements.txt` (Drain3 0.9.11).
- **Docker**, to run the log10x engine image `log10x/pipeline-10x:latest` (engine 1.1.4).
  No API key is needed — local file I/O runs under the image's built-in limited license.
- The 16 loghub datasets (see Setup).

## Setup

Clone loghub into this folder and normalize line endings to LF (loghub's committed files
are CRLF; both tools must see identical bytes):

```bash
cd drain3-vs-log10x
git clone --depth 1 https://github.com/logpai/loghub.git
python - <<'PY'
import glob
for f in glob.glob("loghub/*/*_2k.log"):
    d = open(f, "rb").read()
    open(f, "wb").write(d.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
PY
```

Paths are resolved relative to this folder (the parent of `bench/`). To point the scripts
at data elsewhere, set `BENCH_DIR=/path/to/base` (expects `loghub/` and writes `bench/out/`
under it).

## Run

```bash
cd bench
python bench.py       # runs Drain3 (default+masked) and log10x on all 16 -> results.json
python stability.py   # A / B / A+B / B+A pattern-stability test (per dataset)
python facts.py       # consolidate -> facts.json (the canonical numbers)
python analyze.py     # print the aggregate comparison table
```

Independent verification (recompute from primary files, not from the summary JSON):

```bash
python verify_lossless.py   # fresh byte-exact recheck of log10x + whitespace-run counts
python rederive.py          # recompute every aggregate from raw + outputs + a fresh Drain3
```

## Full-dataset run (optional)

The 2k samples measure losslessness and stability; `bench/bigfile.py` measures how the
fixed template-dictionary cost amortizes at full scale, on one big loghub dataset,
streaming and memory-bounded. The full datasets are hosted on
[Zenodo (record 8196385)](https://zenodo.org/records/8196385):

```bash
cd drain3-vs-log10x
mkdir -p bigfile && cd bigfile
curl -L -o BGL.zip "https://zenodo.org/records/8196385/files/BGL.zip?download=1"   # ~57 MB zip
unzip BGL.zip        # -> BGL.log (743,185,031 bytes, 4,747,963 lines, LF endings)
cd ../bench
python bigfile.py BGL ../bigfile/BGL.log
```

Reference results for BGL (measured 2026-07-07, engine 1.1.4, Drain3 0.9.11):

- log10x: **4,747,963/4,747,963 lines lossless (100.000%)**, whole file byte-identical;
  127,532 cold templates; representation (templates + encoded) **65% of the raw text**,
  template dictionary **5.0%** of the representation (vs 30% on the 2k sample); engine
  wall ~260 s.
- Drain3: 842 templates; 100% lossless on the sampled first 200,000 lines (BGL has no
  whitespace runs); mine ~194 s + match/extract ~478 s.

## What each script does

| script | role |
|---|---|
| `bench.py` | drives Drain3 (mine + reconstruct via bolted-on parameter store) and log10x (docker) on every dataset; writes `results.json` and the per-dataset log10x output tree under `bench/out/` |
| `stability.py` | splits a dataset in half and runs both tools on A, B, A+B, B+A; measures order- and context-invariance of pattern IDs (uses `tenx-stability.config.yaml`, grouping disabled for 1:1 line↔event) |
| `facts.py` | rolls `results.json` + stability outputs into `facts.json` |
| `analyze.py` | prints the aggregate table |
| `verify_lossless.py` | independent byte-exact reconstruction check + per-dataset whitespace-run counts |
| `rederive.py` | independent aggregate recomputation from raw files + log10x outputs + a fresh Drain3 run |
| `bigfile.py` | full-dataset run (streaming): losslessness on every line + template-dictionary amortization + timings on a big loghub dataset |
| `smoke_test.py` | self-contained check (no Docker/loghub) of the Drain3 whitespace-collapse mechanism; run in CI |

## The log10x pipeline configs

- `tenx-verify.config.yaml` — encode a log file to `templates.json` + `encoded.log`, and
  write the `text` reconstruction (`reconstructed.log`) in the same pass.
- `tenx-decode.config.yaml` — decode-only: read a compact file (`cat templates.json
  encoded.log`) and expand the encoded records back to the original text.
- `tenx-stability.config.yaml` — encode with multi-line grouping disabled (1:1 line↔event),
  used for the stability test.

`results-artifact.html` is a self-contained visual summary of the results.

## Versions

Drain3 0.9.11 · log10x engine 1.1.4 (`log10x/pipeline-10x:latest`) · loghub 2k samples.
