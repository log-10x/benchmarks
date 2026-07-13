#!/usr/bin/env python3
"""Independent re-derivation of the draft's aggregate claims, computed ONLY from
primary sources (raw loghub files + log10x output files + a fresh Drain3 run) —
NOT from bench.py / results.json / facts.json. Catches computation-layer bugs."""
import os, glob, gzip, io
from drain3 import TemplateMiner

SCRATCH = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGHUB, OUT = os.path.join(SCRATCH,"loghub"), os.path.join(SCRATCH,"bench","out")
DATASETS = ["Android","Apache","BGL","HDFS","HPC","Hadoop","HealthApp","Linux",
            "Mac","OpenSSH","OpenStack","Proxifier","Spark","Thunderbird","Windows","Zookeeper"]
US="\x1f"

def gz(b):
    if isinstance(b,str): b=b.encode("utf-8","replace")
    buf=io.BytesIO()
    with gzip.GzipFile(fileobj=buf,mode="wb",compresslevel=6,mtime=0) as g: g.write(b)
    return len(buf.getvalue())
def lines(p):
    d=open(p,"rb").read().replace(b"\r\n",b"\n").decode("utf-8","replace").split("\n")
    return d[:-1] if d and d[-1]=="" else d
def align(t,l):
    # fair drain3 reconstruction: Drain clusters are length-homogeneous and <*> is
    # a whole token, so recover each variable by position. Joining with single
    # spaces means a collapsed whitespace run is the only thing lost.
    tt,lt=t.split(),l.split()
    if len(tt)!=len(lt): return None,None
    pv=[lt[i] for i in range(len(tt)) if tt[i]=="<*>"]
    return " ".join(lt[i] if tt[i]=="<*>" else tt[i] for i in range(len(tt))), pv

tot=dict(orig=0,orig_gz=0,lxT=0,d3T=0,gt=0,lx_gz=0,d3_gz=0,lx_enc=0,lx_exact=0,d3_100=0)
print(f"{'dataset':<12} {'lxT':>5} {'d3T':>5} {'gt':>4} {'d3loss':>7} {'lxExact':>7}")
for ds in DATASETS:
    raw=lines(os.path.join(LOGHUB,ds,f"{ds}_2k.log"))
    orig_txt="\n".join(raw); orig_b=sum(len(l.encode('utf-8','replace'))+1 for l in raw)
    # ground truth templates
    gtp=os.path.join(LOGHUB,ds,f"{ds}_2k.log_templates.csv")
    gt=sum(1 for _ in open(gtp,encoding="utf-8",errors="replace"))-1
    # log10x outputs (primary files)
    od=os.path.join(OUT,ds,"log10x")
    tj=open(os.path.join(od,"templates.json"),encoding="utf-8",errors="replace").read()
    enc=open(os.path.join(od,"encoded.log"),encoding="utf-8",errors="replace").read()
    rec=open(os.path.join(od,"decoded.log"),"rb").read().replace(b"\r\n",b"\n").decode("utf-8","replace")
    lxT=sum(1 for l in tj.split("\n") if l.strip())
    lx_exact=(orig_txt.rstrip("\n")==rec.rstrip("\n"))
    # fresh drain3
    tm=TemplateMiner()
    for l in raw: tm.add_log_message(l)
    d3T=len(list(tm.drain.clusters))
    d3rows=[]; d3ok=0
    for l in raw:
        m=tm.match(l)
        if m:
            recon,pv=align(m.get_template(),l)
            if recon is not None:
                if recon==l: d3ok+=1
                d3rows.append(str(m.cluster_id)+US+US.join(pv)); continue
        d3rows.append("MISS"+US+l)
    d3loss=100*d3ok/len(raw)
    d3tmpl="\n".join(sorted({c.get_template() for c in tm.drain.clusters}))
    # sizes
    lx_gz=gz(tj)+gz(enc); d3_gz=gz(d3tmpl)+gz("\n".join(d3rows))
    tot["orig"]+=orig_b; tot["orig_gz"]+=gz(orig_txt); tot["lxT"]+=lxT; tot["d3T"]+=d3T; tot["gt"]+=gt
    tot["lx_gz"]+=lx_gz; tot["d3_gz"]+=d3_gz; tot["lx_enc"]+=len(enc.encode("utf-8","replace"))
    tot["lx_exact"]+= 1 if lx_exact else 0; tot["d3_100"]+= 1 if abs(d3loss-100)<0.001 else 0
    print(f"{ds:<12} {lxT:>5} {d3T:>5} {gt:>4} {d3loss:>6.2f}% {str(lx_exact):>7}")

print("\n== INDEPENDENT AGGREGATE (from raw + log10x files + fresh drain3) ==")
print(f"  templates: log10x={tot['lxT']}  drain3={tot['d3T']}  ground-truth={tot['gt']}   [draft: 3509 / 1761 / 1363]")
print(f"  log10x byte-exact datasets: {tot['lx_exact']}/16   drain3 fully-lossless: {tot['d3_100']}/16   [draft: 16/16, 5/16]")
print("  (representation size is out of scope for this benchmark — stability + reversibility only)")
