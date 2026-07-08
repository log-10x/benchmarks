#!/usr/bin/env python3
"""Independent re-verification of log10x losslessness: re-read files fresh,
compare original bytes vs decoded bytes (LF-normalized, trailing-NL stripped).
Also count the lines drain3 cannot reproduce byte-for-byte: any line whose
whitespace is not already single inter-token spaces (a collapsible run, a tab,
or leading/trailing space), which is exactly what its tokenizer discards."""
import os
SCRATCH = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS = ["Android","Apache","BGL","HDFS","HPC","Hadoop","HealthApp","Linux",
            "Mac","OpenSSH","OpenStack","Proxifier","Spark","Thunderbird","Windows","Zookeeper"]
allok = True
print(f"{'dataset':<12} {'orig_B':>8} {'recon_B':>8} {'exact':>6} {'ws_lines':>9}")
print("-"*48)
for ds in DATASETS:
    orig = open(os.path.join(SCRATCH,"loghub",ds,f"{ds}_2k.log"),"rb").read()
    recon= open(os.path.join(SCRATCH,"bench","out",ds,"log10x","decoded.log"),"rb").read()
    o = orig.replace(b"\r\n",b"\n").rstrip(b"\n")
    r = recon.replace(b"\r\n",b"\n").rstrip(b"\n")
    exact = (o == r)
    allok = allok and exact
    ws_lines = sum(1 for ln in o.split(b"\n") if b" ".join(ln.split()) != ln)
    print(f"{ds:<12} {len(o):>8} {len(r):>8} {str(exact):>6} {ws_lines:>9}")
print("-"*48)
print("ALL 16 BYTE-EXACT:", allok)
