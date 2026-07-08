#!/usr/bin/env python3
"""Full-dataset run: template-dictionary amortization + losslessness at scale.

Runs the log10x engine (docker) and Drain3 on one big log file, streaming and
memory-bounded, and reports:
  - losslessness, checked on every line
  - template counts and the template dictionary's share of the representation
  - representation size relative to the raw text
  - wall times for both tools

The 2k samples measure losslessness and stability; this measures how the fixed
template-dictionary cost amortizes as the file grows. See the README for the
BGL download (Zenodo) and the committed reference results.

Usage:  python bigfile.py <name> <path-to-.log>
"""
import subprocess, os, sys, re, gzip, io, time

BASE = os.environ.get("BENCH_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENCODE_CFG = os.path.join(BASE, "tenx-encode.config.yaml")
DECODE_CFG = os.path.join(BASE, "tenx-decode.config.yaml")
IMAGE = "log10x/pipeline-10x:latest"

def gz_file(path, chunk=1 << 20):
    """Streaming gzip size: return (raw_bytes, gzipped_bytes) without holding the file."""
    raw = 0
    total_c = 0
    buf = io.BytesIO()
    g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0)
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            raw += len(b)
            g.write(b)
            total_c += buf.tell(); buf.seek(0); buf.truncate(0)
    g.close()
    total_c += buf.tell()
    return raw, total_c

def human(n): return f"{n/1024/1024:.1f} MB" if n >= 1024*1024 else f"{n/1024:.1f} KB"

def _docker(cfg, cfgname, outdir, input_file, input_mount):
    args = ["docker","run","--rm",
        "-e","OUTPUT_DIR=/out","-e","INPUT_FILE="+input_file,
        "-v",f"{outdir}:/out","-v",f"{cfg}:/cfg/{cfgname}:ro"]
    if input_mount:
        args += ["-v", f"{input_mount[0]}:{input_mount[1]}:ro"]
    args += [IMAGE, f"@/cfg/{cfgname}"]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("docker failed:\n", r.stderr[-2000:]); sys.exit(1)
    return r, time.time() - t

def run_log10x(name, logpath):
    outdir = os.path.join(BASE, "bigfile", name, "log10x")
    os.makedirs(outdir, exist_ok=True)
    for fn in ("templates.json", "encoded.log", "compact.log", "decoded.log"):
        p = os.path.join(outdir, fn)
        if os.path.exists(p): os.remove(p)
    indir = os.path.dirname(os.path.abspath(logpath)); inname = os.path.basename(logpath)
    # run 1: encode
    r1, w1 = _docker(ENCODE_CFG, "tenx-encode.config.yaml", outdir, "/in/"+inname, (indir, "/in"))
    # run 2: decode the compact stream (templates + encoded) back to text
    compact = os.path.join(outdir, "compact.log")
    with open(compact, "wb") as out, open(os.path.join(outdir,"templates.json"),"rb") as a, \
         open(os.path.join(outdir,"encoded.log"),"rb") as b:
        for chunk in iter(lambda: a.read(1<<20), b""): out.write(chunk)
        for chunk in iter(lambda: b.read(1<<20), b""): out.write(chunk)
    r2, w2 = _docker(DECODE_CFG, "tenx-decode.config.yaml", outdir, "/out/compact.log", None)
    m = re.search(r"completed in:\s*(\d+)ms", r1.stderr + r1.stdout)
    return outdir, w1 + w2, (int(m.group(1)) if m else None)

def count_lines(path):
    n = 0
    with open(path, "rb") as f:
        for _ in f: n += 1
    return n

def lossless_stream(orig, recon):
    """Stream-compare content line by line (LF-normalized, trailing-NL agnostic)."""
    import itertools
    ok = tot = 0
    with open(orig, "rb") as a, open(recon, "rb") as b:
        for la, lb in itertools.zip_longest(a, b, fillvalue=b""):
            la = la.replace(b"\r\n", b"\n").rstrip(b"\n"); lb = lb.replace(b"\r\n", b"\n").rstrip(b"\n")
            if la == b"" and lb == b"": continue
            tot += 1; ok += 1 if la == lb else 0
    return ok, tot

def run_drain3(logpath, sample_lossless=200000):
    from drain3 import TemplateMiner
    US = "\x1f"
    tm = TemplateMiner()
    t = time.time(); n = 0
    with open(logpath, encoding="utf-8", errors="replace") as f:
        for line in f:
            tm.add_log_message(line.rstrip("\n")); n += 1
    t_mine = time.time() - t
    clusters = list(tm.drain.clusters); ntmpl = len(clusters)
    templates = "\n".join(sorted(c.get_template() for c in clusters))
    # pass 2: stream encoded(+params) rows to a temp file for sizing; sample losslessness
    encp = os.path.join(os.path.dirname(logpath), "_d3_encoded.tmp")
    ph = re.compile(r"<\*>")
    ok = tot = 0
    t = time.time()
    with open(logpath, encoding="utf-8", errors="replace") as f, open(encp, "w", encoding="utf-8") as out:
        for i, line in enumerate(f):
            ln = line.rstrip("\n")
            m = tm.match(ln)
            if m is None:
                out.write("MISS" + US + ln + "\n")
                if i < sample_lossless: tot += 1
                continue
            tmpl = m.get_template(); ps = tm.extract_parameters(tmpl, ln, exact_matching=True)
            pv = [p.value for p in ps] if ps else None
            out.write((str(m.cluster_id) + US + (US.join(pv) if pv else "")) + "\n")
            if i < sample_lossless:
                tot += 1
                if pv is not None:
                    parts = ph.split(tmpl)
                    if len(parts) - 1 == len(pv):
                        recon = "".join(seg + (pv[k] if k < len(pv) else "") for k, seg in enumerate(parts))
                        ok += 1 if recon == ln else 0
    t_match = time.time() - t
    tdict_raw = len(templates.encode("utf-8", "replace"))
    tdict_gz = len(gzip.compress(templates.encode("utf-8", "replace"), 6))
    enc_raw, enc_gz = gz_file(encp)
    os.remove(encp)
    return dict(n=n, ntmpl=ntmpl, tdict_raw=tdict_raw, tdict_gz=tdict_gz, enc_raw=enc_raw, enc_gz=enc_gz,
                loss_ok=ok, loss_tot=tot, t_mine=t_mine, t_match=t_match)

def main(name, logpath):
    print(f"### {name}: {logpath}")
    print(f"# lines: {count_lines(logpath):,}  raw size: {human(os.path.getsize(logpath))}\n")

    orig_raw, orig_gz = gz_file(logpath)
    print(f"[baseline] original raw {human(orig_raw)} / gzip {human(orig_gz)}\n")

    print("[log10x] running engine (docker)...", flush=True)
    outdir, dt, ems = run_log10x(name, logpath)
    tj = os.path.join(outdir, "templates.json"); en = os.path.join(outdir, "encoded.log"); rc = os.path.join(outdir, "decoded.log")
    ntmpl = count_lines(tj)
    tj_raw, tj_gz = gz_file(tj); en_raw, en_gz = gz_file(en)
    repr_raw = tj_raw + en_raw
    print(f"   templates: {ntmpl:,}  ({human(tj_raw)} raw / {human(tj_gz)} gz)")
    print(f"   encoded:   {human(en_raw)} raw / {human(en_gz)} gz")
    print(f"   engine wall {dt:.1f}s (engine_ms={ems})")
    print("   verifying losslessness on every line (streaming)...", flush=True)
    ok, tot = lossless_stream(logpath, rc)
    print(f"   lossless: {ok:,}/{tot:,} lines ({100*ok/tot:.3f}%)")
    print(f"   representation (templates+encoded): {human(repr_raw)} raw = {100*repr_raw/orig_raw:.1f}% of raw original")
    print(f"   template share of representation: {100*tj_raw/repr_raw:.2f}% raw / {100*tj_gz/(tj_gz+en_gz):.2f}% gz\n")

    print("[drain3] mining + reconstructing (streaming)...", flush=True)
    d = run_drain3(logpath)
    print(f"   templates: {d['ntmpl']:,}  ({human(d['tdict_raw'])} raw / {human(d['tdict_gz'])} gz)")
    print(f"   encoded(+params): {human(d['enc_raw'])} raw / {human(d['enc_gz'])} gz")
    print(f"   lossless (sampled, first {d['loss_tot']:,} lines): {100*d['loss_ok']/max(d['loss_tot'],1):.2f}%")
    print(f"   drain3 time: mine {d['t_mine']:.0f}s + match/extract {d['t_match']:.0f}s")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
