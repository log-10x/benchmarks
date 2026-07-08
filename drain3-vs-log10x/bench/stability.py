#!/usr/bin/env python3
"""
Pattern STABILITY test: run each tool on 4 files -- A, B, A+B, B+A -- and
check whether a given log line is assigned the SAME pattern regardless of
which file it lands in or the order of lines.

A = first half of a dataset, B = second half (disjoint concrete lines, but
recurring message TYPES appear in both halves -> stresses order/history).

log10x pattern id  = content-addressed template hash (from ~<hash>,... encoded line)
drain3  pattern id = the final mined template string (cluster ids are per-run
                     counters, meaningless across files, so we compare templates)
"""
import subprocess, os, sys, re, json

SCRATCH = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGHUB  = os.path.join(SCRATCH, "loghub")
CFG     = os.path.join(SCRATCH, "tenx-stability.config.yaml")  # no grouping -> 1:1 line/event
IMAGE   = "log10x/pipeline-10x:latest"
WORK    = os.path.join(SCRATCH, "bench", "stability")

def read_lines(path):
    d = open(path, "rb").read().decode("utf-8","replace")
    ls = d.split("\n")
    if ls and ls[-1] == "": ls = ls[:-1]
    return ls

def write_lines(path, lines):
    with open(path, "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8","replace"))

# ---- log10x: per-line template hash ----
def log10x_hashes(name, infile):
    outdir = os.path.join(WORK, name, "log10x"); os.makedirs(outdir, exist_ok=True)
    for fn in ("encoded.log","templates.json","reconstructed.log"):
        p=os.path.join(outdir,fn)
        if os.path.exists(p): os.remove(p)
    args = ["docker","run","--rm",
        "-e", "OUTPUT_DIR=/out",
        "-e", "INPUT_FILE=/in/events.log",
        "-v", f"{outdir}:/out",
        "-v", f"{CFG}:/cfg/tenx-stability.config.yaml:ro",
        "-v", f"{infile}:/in/events.log:ro",
        IMAGE, "@/cfg/tenx-stability.config.yaml"]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("  docker fail", name, r.stderr[-800:]); return None
    enc = read_lines(os.path.join(outdir,"encoded.log"))
    hashes = [ln[1:].split(",",1)[0] for ln in enc]  # ~<hash>,...
    ntmpl = len([l for l in read_lines(os.path.join(outdir,"templates.json")) if l.strip()])
    return hashes, ntmpl

# ---- drain3: per-line final mined template ----
def drain3_templates(lines):
    from drain3 import TemplateMiner
    tm = TemplateMiner()
    for ln in lines: tm.add_log_message(ln)
    out = []
    for ln in lines:
        m = tm.match(ln)
        out.append(m.get_template() if m else "<NO-MATCH>")
    ntmpl = len(list(tm.drain.clusters))
    return out, ntmpl

# ----------------------------------------------------------------------------
def main(ds="HDFS"):
    os.makedirs(WORK, exist_ok=True)
    lines = read_lines(os.path.join(LOGHUB, ds, f"{ds}_2k.log"))
    half = len(lines)//2
    A, B = lines[:half], lines[half:]
    files = {"A": A, "B": B, "AB": A+B, "BA": B+A}
    paths = {}
    for k,v in files.items():
        p = os.path.join(WORK, f"{k}.log"); write_lines(p, v); paths[k]=p

    print(f"dataset={ds}  |A|={len(A)} |B|={len(B)} |AB|={len(A)+len(B)}\n")

    # ---- log10x ----
    lx = {}; lx_ntmpl={}
    for k in files:
        res = log10x_hashes(k, paths[k])
        if res is None: return
        lx[k], lx_ntmpl[k] = res
        assert len(lx[k]) == len(files[k]), f"log10x {k}: {len(lx[k])} hashes vs {len(files[k])} lines"
    # map concrete line -> hash, per file
    lx_map = {k: dict(zip(files[k], lx[k])) for k in files}

    # ---- drain3 ----
    d3 = {}; d3_ntmpl={}
    for k in files:
        t, n = drain3_templates(files[k]); d3[k]=t; d3_ntmpl[k]=n
    d3_map = {k: dict(zip(files[k], d3[k])) for k in files}

    def stability_report(tool, mp, ntmpl):
        # order invariance: for each concrete line present in both AB and BA,
        # is its pattern id identical?
        both = set(mp["AB"]) & set(mp["BA"])
        order_same = sum(1 for ln in both if mp["AB"][ln]==mp["BA"][ln])
        # context invariance: A-lines: pattern in A-alone == pattern in AB?
        ctxA = sum(1 for ln in files["A"] if mp["A"].get(ln)==mp["AB"].get(ln))
        ctxB = sum(1 for ln in files["B"] if mp["B"].get(ln)==mp["BA"].get(ln))
        # distinct pattern-id SET stability across the 4 files
        setAB, setBA = set(mp["AB"].values()), set(mp["BA"].values())
        print(f"== {tool} ==")
        print(f"  distinct patterns:   A={ntmpl['A']}  B={ntmpl['B']}  AB={ntmpl['AB']}  BA={ntmpl['BA']}")
        print(f"  pattern SET(AB)==SET(BA):   {setAB==setBA}   (|AB\\BA|={len(setAB-setBA)}, |BA\\AB|={len(setBA-setAB)})")
        print(f"  ORDER-invariant lines (AB vs BA): {order_same}/{len(both)}  ({100.0*order_same/len(both):.1f}%)")
        print(f"  CONTEXT-invariant  A vs AB:       {ctxA}/{len(files['A'])}  ({100.0*ctxA/len(files['A']):.1f}%)")
        print(f"  CONTEXT-invariant  B vs BA:       {ctxB}/{len(files['B'])}  ({100.0*ctxB/len(files['B']):.1f}%)")
        print()
        return dict(order=order_same, both=len(both), ctxA=ctxA, ctxB=ctxB,
                    setstable=(setAB==setBA), ntmpl=ntmpl)

    r_lx = stability_report("log10x", lx_map, lx_ntmpl)
    r_d3 = stability_report("drain3", d3_map, d3_ntmpl)
    json.dump({"dataset":ds,"log10x":r_lx,"drain3":r_d3},
              open(os.path.join(WORK, f"stability_{ds}.json"),"w"), indent=2)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "HDFS")
