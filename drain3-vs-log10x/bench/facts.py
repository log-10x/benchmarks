#!/usr/bin/env python3
"""Consolidate all benchmark results into one canonical facts.json + facts.md.
Single source of truth for the blog draft AND the fact-check workflow."""
import json, os, re, glob

SCRATCH = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGHUB  = os.path.join(SCRATCH, "loghub")
BENCH   = os.path.join(SCRATCH, "bench")
DATASETS = ["Android","Apache","BGL","HDFS","HPC","Hadoop","HealthApp","Linux",
            "Mac","OpenSSH","OpenStack","Proxifier","Spark","Thunderbird","Windows","Zookeeper"]

def gt(ds):
    p=os.path.join(LOGHUB,ds,f"{ds}_2k.log_templates.csv")
    return sum(1 for _ in open(p,encoding="utf-8",errors="replace"))-1 if os.path.exists(p) else None

def wsinfo(ds):
    o=open(os.path.join(LOGHUB,ds,f"{ds}_2k.log"),"rb").read().replace(b"\r\n",b"\n").rstrip(b"\n")
    lines=o.split(b"\n")
    # a line drain3 cannot reproduce byte-for-byte == one whose whitespace is not
    # already single inter-token spaces: a collapsible run, a tab, or leading/
    # trailing space. Token-aligned reconstruction rebuilds every token but joins
    # them with single spaces, so this count equals drain3's loss exactly.
    ws_lines=sum(1 for l in lines if b" ".join(l.split()) != l)
    return dict(n_lines=len(lines), ws_lines=ws_lines)

res=json.load(open(os.path.join(BENCH,"results.json")))
facts={"datasets":{}, "versions":{"drain3":"0.9.11","engine":"1.1.5","image":"log10x/pipeline-10x:1.1.5",
        "loghub":"logpai/loghub 2k samples (16 datasets)"}}

agg=dict(lx_loss=[],d3_loss=[],lx_tmpl=0,d3_tmpl=0,gt_tmpl=0,
         lx_exact=0,d3_100=0,lx_stable_order=0,lx_stable_ctx=0,d3_min_order=100.0,d3_min_ctx=100.0)
for ds in DATASETS:
    d=res.get(ds,{}); lx=d.get("log10x",{}); d3=d.get("drain3-default",{}); d3m=d.get("drain3-masked",{})
    w=wsinfo(ds)
    stab=None
    sp=os.path.join(BENCH,"stability",f"stability_{ds}.json")
    if os.path.exists(sp): stab=json.load(open(sp))
    entry=dict(
        gt=gt(ds), n_lines=w["n_lines"], ws_lines=w["ws_lines"],
        lx=dict(templates=lx.get("n_templates"), lossless=lx.get("lossless_pct"),
                exact=lx.get("lossless_exact"), engine_ms=lx.get("engine_ms")),
        d3=dict(templates=d3.get("n_templates"), lossless=d3.get("lossless_pct"),
                time_ms=d3.get("time_ms")),
        d3_masked=dict(templates=d3m.get("n_templates"), lossless=d3m.get("lossless_pct")),
    )
    if stab:
        L,D=stab["log10x"],stab["drain3"]
        entry["stability"]=dict(
            log10x=dict(order_pct=round(100*L["order"]/L["both"],1),
                        ctxA_pct=round(100*L["ctxA"]/1000,1), ctxB_pct=round(100*L["ctxB"]/1000,1),
                        set_stable=L["setstable"]),
            drain3=dict(order_pct=round(100*D["order"]/D["both"],1),
                        ctxA_pct=round(100*D["ctxA"]/1000,1), ctxB_pct=round(100*D["ctxB"]/1000,1),
                        set_stable=D["setstable"]))
        agg["lx_stable_order"]+=1 if L["order"]==L["both"] else 0
        agg["lx_stable_ctx"]+=1 if (L["ctxA"]==1000 and L["ctxB"]==1000) else 0
        agg["d3_min_order"]=min(agg["d3_min_order"], 100*D["order"]/D["both"])
        agg["d3_min_ctx"]=min(agg["d3_min_ctx"], 100*D["ctxA"]/1000, 100*D["ctxB"]/1000)
    facts["datasets"][ds]=entry
    agg["lx_loss"].append(lx.get("lossless_pct",0)); agg["d3_loss"].append(d3.get("lossless_pct",0))
    agg["lx_tmpl"]+=lx.get("n_templates",0); agg["d3_tmpl"]+=d3.get("n_templates",0); agg["gt_tmpl"]+=gt(ds) or 0
    agg["lx_exact"]+=1 if lx.get("lossless_exact") else 0
    agg["d3_100"]+=1 if d3.get("lossless_pct")==100.0 else 0

n=len(DATASETS)
n_stab=sum(1 for ds in DATASETS if "stability" in facts["datasets"][ds])
facts["aggregate"]=dict(
    n_datasets=n, n_stability_datasets=n_stab,
    lx_lossless_mean=round(sum(agg["lx_loss"])/n,2), lx_byte_exact=f"{agg['lx_exact']}/{n}",
    d3_lossless_mean=round(sum(agg["d3_loss"])/n,2), d3_fully_lossless=f"{agg['d3_100']}/{n}",
    d3_near_total_loss=[ds for ds in DATASETS if res[ds]["drain3-default"]["lossless_pct"]<50],
    gt_templates=agg["gt_tmpl"], lx_templates=agg["lx_tmpl"], d3_templates=agg["d3_tmpl"],
    lx_more_templates_than_d3=sum(1 for ds in DATASETS
        if res[ds]["log10x"]["n_templates"]>res[ds]["drain3-default"]["n_templates"]),
    lx_stability_perfect_order=f"{agg['lx_stable_order']}/{n_stab}",
    lx_stability_perfect_ctx=f"{agg['lx_stable_ctx']}/{n_stab}",
    d3_worst_order_pct=round(agg["d3_min_order"],1), d3_worst_ctx_pct=round(agg["d3_min_ctx"],1),
)
json.dump(facts, open(os.path.join(BENCH,"facts.json"),"w"), indent=2)
print(json.dumps(facts["aggregate"], indent=2))
print("\nwrote facts.json")
