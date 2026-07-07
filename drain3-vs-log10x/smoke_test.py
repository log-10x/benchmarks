#!/usr/bin/env python3
"""Self-contained smoke test — no Docker, no loghub download.

Exercises the Drain3 mine + reconstruct path on synthetic input and asserts the
whitespace-collapse behavior the post describes: clean single-space lines round-trip,
but lines with a run of consecutive spaces do not (Drain3 tokenizes on whitespace and
collapses runs, so the original spacing is unrecoverable). Guards the core mechanism
claim in CI without needing the engine image or the corpus.
"""
import re
from drain3 import TemplateMiner


def reconstruct(template, params):
    parts = re.split(r"<\*>", template)
    if len(parts) - 1 != len(params):
        return None
    return "".join(seg + (params[i] if i < len(parts) - 1 else "") for i, seg in enumerate(parts))


def drain3_reconstructable(lines):
    tm = TemplateMiner()
    for ln in lines:
        tm.add_log_message(ln)
    ok = 0
    for ln in lines:
        m = tm.match(ln)
        if not m:
            continue
        ps = tm.extract_parameters(m.get_template(), ln, exact_matching=True)
        if ps is not None and reconstruct(m.get_template(), [p.value for p in ps]) == ln:
            ok += 1
    return ok, len(lines)


def main():
    # clean single-space lines — Drain3 reconstructs them exactly
    clean = [f"user u{i} logged in from 10.0.0.{i}" for i in range(1, 40)]
    ok, n = drain3_reconstructable(clean)
    assert ok == n, f"clean lines should fully reconstruct, got {ok}/{n}"

    # lines with a whitespace run (space-padded day, like syslog 'Jul  1') —
    # Drain3 collapses the run, so they do NOT reconstruct byte-for-byte
    padded = [f"Jul  {i} 09:00:{i:02d} host kernel: event {i}" for i in range(1, 40)]
    ok, n = drain3_reconstructable(padded)
    assert ok == 0, f"whitespace-run lines should be lossy (0 reconstructable), got {ok}/{n}"

    print("smoke ok: clean lines lossless; whitespace-run lines lossy (as the post claims)")


if __name__ == "__main__":
    main()
