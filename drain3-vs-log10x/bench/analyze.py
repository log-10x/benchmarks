#!/usr/bin/env python3
"""Aggregate + present the log10x-vs-drain3 benchmark results."""
import json, os, csv

SCRATCH = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGHUB  = os.path.join(SCRATCH, "loghub")
RESULTS = os.path.join(SCRATCH, "bench", "results.json")
DATASETS = ["Android","Apache","BGL","HDFS","HPC","Hadoop","HealthApp","Linux",
            "Mac","OpenSSH","OpenStack","Proxifier","Spark","Thunderbird","Windows","Zookeeper"]

def gt_templates(ds):
    p = os.path.join(LOGHUB, ds, f"{ds}_2k.log_templates.csv")
    if not os.path.exists(p): return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f) - 1  # minus header

res = json.load(open(RESULTS))

print("="*118)
print("TEMPLATE COUNTS                          |  LOSSLESS RECONSTRUCTION %        |  REPR SIZE (gzip, bytes)")
print(f"{'dataset':<12} {'gt':>4} {'lx':>5} {'d3':>5} {'d3m':>5}  |  {'lx':>6} {'d3':>7} {'d3m':>7}  |  {'orig':>7} {'lx':>7} {'d3':>7}")
print("-"*118)

agg = {"lx_loss":[], "d3_loss":[], "d3m_loss":[], "d3_lossless_datasets":0, "lx_lossless_datasets":0,
       "lx_tmpl":[], "d3_tmpl":[], "gt_tmpl":[], "orig_gz":0, "lx_gz":0, "d3_gz":0,
       "orig_bytes":0, "lx_enc":0}
for ds in DATASETS:
    d = res.get(ds, {})
    lx = d.get("log10x",{}); d3 = d.get("drain3-default",{}); d3m = d.get("drain3-masked",{})
    gt = gt_templates(ds)
    print(f"{ds:<12} {gt:>4} {lx.get('n_templates',0):>5} {d3.get('n_templates',0):>5} {d3m.get('n_templates',0):>5}  |  "
          f"{lx.get('lossless_pct',0):>6} {d3.get('lossless_pct',0):>7} {d3m.get('lossless_pct',0):>7}  |  "
          f"{lx.get('orig_gzip',0):>7} {lx.get('repr_gzip',0):>7} {d3.get('repr_gzip',0):>7}")
    agg["lx_loss"].append(lx.get('lossless_pct',0)); agg["d3_loss"].append(d3.get('lossless_pct',0))
    agg["d3m_loss"].append(d3m.get('lossless_pct',0))
    agg["lx_lossless_datasets"] += 1 if lx.get('lossless_pct',0)==100.0 else 0
    agg["d3_lossless_datasets"] += 1 if d3.get('lossless_pct',0)==100.0 else 0
    agg["lx_tmpl"].append(lx.get('n_templates',0)); agg["d3_tmpl"].append(d3.get('n_templates',0))
    agg["gt_tmpl"].append(gt)
    agg["orig_gz"]+=lx.get('orig_gzip',0); agg["lx_gz"]+=lx.get('repr_gzip',0); agg["d3_gz"]+=d3.get('repr_gzip',0)
    agg["orig_bytes"]+=lx.get('orig_bytes',0); agg["lx_enc"]+=lx.get('encoded_bytes',0)

n=len(DATASETS)
print("="*118)
print("\nAGGREGATE (16 datasets, ~32k lines total):")
print(f"  log10x lossless:      mean {sum(agg['lx_loss'])/n:.2f}%   | 100%-exact on {agg['lx_lossless_datasets']}/16 datasets")
print(f"  drain3 lossless:      mean {sum(agg['d3_loss'])/n:.2f}%   | 100%-exact on {agg['d3_lossless_datasets']}/16 datasets  (best-effort param store)")
print(f"  drain3 <100% on:      {n-agg['d3_lossless_datasets']}/16 datasets")
print(f"  drain3 near-total loss (<50%): {sum(1 for x in agg['d3_loss'] if x<50)} datasets: " +
      ", ".join(ds for ds,x in zip(DATASETS,agg['d3_loss']) if x<50))
print()
print(f"  templates total:      ground-truth {sum(agg['gt_tmpl'])}   log10x {sum(agg['lx_tmpl'])}   drain3 {sum(agg['d3_tmpl'])}")
print(f"  log10x makes MORE templates than drain3 on {sum(1 for a,b in zip(agg['lx_tmpl'],agg['d3_tmpl']) if a>b)}/16 datasets")
print()
print(f"  total original bytes: {agg['orig_bytes']:,}")
print(f"  gzip(original):       {agg['orig_gz']:,}")
print(f"  log10x repr gzip:     {agg['lx_gz']:,}   ({agg['lx_gz']/agg['orig_gz']*100:.1f}% of gzip(orig))")
print(f"  drain3 repr gzip:     {agg['d3_gz']:,}   ({agg['d3_gz']/agg['orig_gz']*100:.1f}% of gzip(orig))  [but lossy on {n-agg['d3_lossless_datasets']}/16]")
print(f"  log10x raw encoded:   {agg['lx_enc']:,}   ({agg['lx_enc']/agg['orig_bytes']*100:.1f}% of raw original, uncompressed)")
