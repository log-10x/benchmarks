#!/usr/bin/env python3
"""
log10x vs drain3 — lossless log-reduction benchmark on loghub 2k datasets.

Head-to-head: feed BOTH tools the identical raw 2k log lines, then measure
  * losslessness  — can the exact original bytes be reconstructed?
  * template count — how many message types each induces
  * representation size — bytes (raw + gzip) of the tool's lossless artifact
  * time           — engine/library processing time

Usage:
  python bench.py normalize
  python bench.py drain3   [DATASET ...]
  python bench.py log10x   [DATASET ...]
  python bench.py report
  python bench.py all
"""
import subprocess, os, glob, json, time, gzip, sys, re, io

SCRATCH = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGHUB  = os.path.join(SCRATCH, "loghub")
CFG     = os.path.join(SCRATCH, "tenx-verify.config.yaml")
IMAGE   = "log10x/pipeline-10x:latest"
BENCH   = os.path.join(SCRATCH, "bench")
OUTROOT = os.path.join(BENCH, "out")
RESULTS = os.path.join(BENCH, "results.json")

DATASETS = ["Android","Apache","BGL","HDFS","HPC","Hadoop","HealthApp","Linux",
            "Mac","OpenSSH","OpenStack","Proxifier","Spark","Thunderbird",
            "Windows","Zookeeper"]

US = "\x1f"  # unit separator for param joins

# ----------------------------------------------------------------------------

def logpath(ds):  return os.path.join(LOGHUB, ds, f"{ds}_2k.log")

def read_lines(path):
    data = open(path, "rb").read()
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines

def gz_len(b):
    if isinstance(b, str): b = b.encode("utf-8", "replace")
    buf = io.BytesIO();
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as g:
        g.write(b)
    return len(buf.getvalue())

def load_results():
    if os.path.exists(RESULTS):
        return json.load(open(RESULTS))
    return {}

def save_results(r):
    json.dump(r, open(RESULTS, "w"), indent=2)

# ----------------------------------------------------------------------------

def normalize():
    n = 0
    for f in glob.glob(os.path.join(LOGHUB, "*", "*_2k.log")):
        d = open(f, "rb").read()
        nd = d.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if nd != d:
            open(f, "wb").write(nd); n += 1
    print(f"normalized {n} files to LF")

# ----------------------------------------------------------------------------

def run_drain3(ds, config="default"):
    from drain3 import TemplateMiner
    from drain3.template_miner_config import TemplateMinerConfig
    lines = read_lines(logpath(ds))
    orig_bytes = sum(len(l.encode("utf-8","replace"))+1 for l in lines)

    cfg = TemplateMinerConfig()
    if config == "masked":
        # production-style masking (numbers, hex, ips) — recommended drain3 usage
        cfg.masking_instructions = []  # filled below via API-agnostic regex list
        from drain3.masking import MaskingInstruction
        for rx, name in [
            (r"((?<=[^A-Za-z0-9])|^)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})((?=[^A-Za-z0-9])|$)", "IP"),
            (r"((?<=[^A-Za-z0-9])|^)([0-9a-fA-F]{2,}(?::[0-9a-fA-F]{2,})+)((?=[^A-Za-z0-9])|$)", "HEX"),
            (r"((?<=[^A-Za-z0-9])|^)(\d+)((?=[^A-Za-z0-9])|$)", "NUM"),
        ]:
            cfg.masking_instructions.append(MaskingInstruction(rx, name))
    cfg.profiling_enabled = False

    miner = TemplateMiner(config=cfg)

    # placeholder pattern for reconstruction: default drain uses only <*>;
    # masked config also emits <IP>/<HEX>/<NUM>.
    ph_re = re.compile(r"<\*>" if config == "default" else r"<\*>|<IP>|<HEX>|<NUM>")

    # pass 1: build clusters
    t0 = time.time()
    for ln in lines:
        miner.add_log_message(ln)
    t_mine = time.time() - t0

    clusters = list(miner.drain.clusters)
    n_templates = len(clusters)
    templates = sorted({c.get_template() for c in clusters})

    # pass 2: assign + extract params + reconstruct against FINAL templates
    t0 = time.time()
    enc_rows = []       # per-line "clusterid<US>param<US>param"
    lossless_lines = 0
    unmatched = 0
    for ln in lines:
        m = miner.match(ln)
        if m is None:
            unmatched += 1
            enc_rows.append("MISS" + US + ln)  # would have to store raw line
            continue
        tmpl = m.get_template()
        params = miner.extract_parameters(tmpl, ln, exact_matching=True)
        if params is None:
            unmatched += 1
            enc_rows.append("MISS" + US + ln)
            continue
        pvals = [p.value for p in params]
        recon = _fill(tmpl, pvals, ph_re)
        if recon == ln:
            lossless_lines += 1
        enc_rows.append(str(m.cluster_id) + US + US.join(pvals))
    t_match = time.time() - t0

    templates_blob = "\n".join(f"{i}\t{t}" for i, t in enumerate(templates))
    encoded_blob = "\n".join(enc_rows)

    return {
        "tool": f"drain3-{config}",
        "n_lines": len(lines),
        "orig_bytes": orig_bytes,
        "orig_gzip": gz_len("\n".join(lines)),
        "n_templates": n_templates,
        "lossless_lines": lossless_lines,
        "lossless_pct": round(100.0*lossless_lines/len(lines), 3),
        "unmatched": unmatched,
        "templates_bytes": len(templates_blob.encode("utf-8","replace")),
        "encoded_bytes": len(encoded_blob.encode("utf-8","replace")),
        "repr_bytes": len(templates_blob.encode("utf-8","replace")) + len(encoded_blob.encode("utf-8","replace")),
        "repr_gzip": gz_len(templates_blob) + gz_len(encoded_blob),
        "time_ms": round((t_mine + t_match)*1000, 1),
        "time_mine_ms": round(t_mine*1000, 1),
    }

def _fill(template, params, ph_re):
    # split template into literal segments separated by placeholder tokens,
    # then interleave the extracted param values back in order.
    parts = ph_re.split(template)
    if len(parts) - 1 != len(params):
        return None
    out = []
    for i, seg in enumerate(parts):
        out.append(seg)
        if i < len(params):
            out.append(params[i])
    return "".join(out)

# ----------------------------------------------------------------------------

def run_log10x(ds):
    log = logpath(ds)
    outdir = os.path.join(OUTROOT, ds, "log10x")
    os.makedirs(outdir, exist_ok=True)
    # clean previous
    for fn in ("templates.json","encoded.log","reconstructed.log"):
        p = os.path.join(outdir, fn)
        if os.path.exists(p): os.remove(p)

    args = ["docker","run","--rm",
        "-e", f"LOG10X_MCP_RUNTIME_NAME={ds}",
        "-e", "LOG10X_MCP_OUTPUT_DIR=/mcp/output",
        "-e", "LOG10X_MCP_INPUT_PATH=/mcp/input/events.log",
        "-v", f"{outdir}:/mcp/output",
        "-v", f"{CFG}:/mcp/config/tenx-verify.config.yaml:ro",
        "-v", f"{log}:/mcp/input/events.log:ro",
        IMAGE, "@/mcp/config/tenx-verify.config.yaml"]
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    wall = time.time() - t0
    if r.returncode != 0:
        print(f"  !! {ds} docker exit {r.returncode}\n{r.stderr[-1500:]}")
        return {"tool":"log10x","error":r.returncode,"stderr":r.stderr[-1500:]}

    m = re.search(r"completed in:\s*(\d+)ms", r.stderr + r.stdout)
    engine_ms = int(m.group(1)) if m else None

    lines = read_lines(logpath(ds))
    orig_text = "\n".join(lines)
    orig_bytes = sum(len(l.encode("utf-8","replace"))+1 for l in lines)

    templates_raw = open(os.path.join(outdir,"templates.json"), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(outdir,"templates.json")) else ""
    encoded_raw   = open(os.path.join(outdir,"encoded.log"), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(outdir,"encoded.log")) else ""
    recon_path = os.path.join(outdir,"reconstructed.log")
    recon_raw  = open(recon_path, "rb").read().decode("utf-8","replace") if os.path.exists(recon_path) else ""

    n_templates = sum(1 for ln in templates_raw.split("\n") if ln.strip())

    # losslessness: full-blob compare (grouping-agnostic)
    recon_lines = recon_raw.split("\n")
    if recon_lines and recon_lines[-1] == "": recon_lines = recon_lines[:-1]
    recon_text = "\n".join(recon_lines)
    lossless_exact = (orig_text == recon_text)
    # per-line match count (when counts align)
    lossless_lines = 0
    if len(recon_lines) == len(lines):
        lossless_lines = sum(1 for a,b in zip(lines, recon_lines) if a==b)
    else:
        # counts differ (multi-line grouping) — fall back to blob equality
        lossless_lines = len(lines) if lossless_exact else 0

    templates_bytes = len(templates_raw.encode("utf-8","replace"))
    encoded_bytes   = len(encoded_raw.encode("utf-8","replace"))

    return {
        "tool": "log10x",
        "n_lines": len(lines),
        "orig_bytes": orig_bytes,
        "orig_gzip": gz_len(orig_text),
        "n_templates": n_templates,
        "n_recon_lines": len(recon_lines),
        "lossless_exact": lossless_exact,
        "lossless_lines": lossless_lines,
        "lossless_pct": round(100.0*lossless_lines/len(lines), 3),
        "templates_bytes": templates_bytes,
        "encoded_bytes": encoded_bytes,
        "repr_bytes": templates_bytes + encoded_bytes,
        "repr_gzip": gz_len(templates_raw) + gz_len(encoded_raw),
        "engine_ms": engine_ms,
        "wall_ms": round(wall*1000, 1),
    }

# ----------------------------------------------------------------------------

def cmd_drain3(dss):
    res = load_results()
    for ds in dss:
        for cfgname in ("default","masked"):
            print(f"[drain3-{cfgname}] {ds} ...", flush=True)
            r = run_drain3(ds, cfgname)
            res.setdefault(ds, {})[f"drain3-{cfgname}"] = r
            print(f"   templates={r['n_templates']} lossless={r['lossless_pct']}% repr_gzip={r['repr_gzip']}B t={r['time_ms']}ms")
        save_results(res)

def cmd_log10x(dss):
    res = load_results()
    for ds in dss:
        print(f"[log10x] {ds} ...", flush=True)
        r = run_log10x(ds)
        res.setdefault(ds, {})["log10x"] = r
        if "error" not in r:
            print(f"   templates={r['n_templates']} lossless_exact={r['lossless_exact']} ({r['lossless_pct']}%) repr_gzip={r['repr_gzip']}B engine={r['engine_ms']}ms")
        save_results(res)

def cmd_report():
    res = load_results()
    hdr = f"{'dataset':<12} | {'lx_tmpl':>7} {'d3_tmpl':>7} {'d3m_tmpl':>8} | {'lx_loss%':>8} {'d3_loss%':>8} {'d3m_loss%':>9} | {'lx_gz':>7} {'d3_gz':>7} {'orig_gz':>7}"
    print(hdr); print("-"*len(hdr))
    agg = {}
    for ds in DATASETS:
        d = res.get(ds, {})
        lx = d.get("log10x",{}); d3 = d.get("drain3-default",{}); d3m = d.get("drain3-masked",{})
        print(f"{ds:<12} | {lx.get('n_templates','?'):>7} {d3.get('n_templates','?'):>7} {d3m.get('n_templates','?'):>8} | "
              f"{lx.get('lossless_pct','?'):>8} {d3.get('lossless_pct','?'):>8} {d3m.get('lossless_pct','?'):>9} | "
              f"{lx.get('repr_gzip','?'):>7} {d3.get('repr_gzip','?'):>7} {lx.get('orig_gzip','?'):>7}")

# ----------------------------------------------------------------------------

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dss = sys.argv[2:] if len(sys.argv) > 2 else DATASETS
    if cmd == "normalize": normalize()
    elif cmd == "drain3": cmd_drain3(dss)
    elif cmd == "log10x": cmd_log10x(dss)
    elif cmd == "report": cmd_report()
    elif cmd == "all":
        normalize(); cmd_drain3(DATASETS); cmd_log10x(DATASETS); cmd_report()
    else:
        print(__doc__)
