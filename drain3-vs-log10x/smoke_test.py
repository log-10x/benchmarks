#!/usr/bin/env python3
"""Self-contained smoke test — no Docker, no loghub download.

Exercises the Drain3 mine + reconstruct path on synthetic input and asserts the
whitespace-collapse behavior the post describes. Drain groups clusters by token
count, so the variables are recoverable by position (token alignment) and 100% of
the *content* comes back. The one thing alignment cannot restore is whitespace:
Drain3 tokenizes on whitespace and collapses every run, so a line with a run of
spaces does not return byte-for-byte. Clean single-space lines round-trip exactly;
padded lines lose only their spacing. Guards the core mechanism in CI without the
engine image or the corpus.
"""
import re
from drain3 import TemplateMiner


def align(template, line):
    """Reconstruct by token position (Drain clusters are length-homogeneous and
    <*> is a whole token). Recovers every token; joins them with single spaces,
    so a collapsed whitespace run is the only thing that cannot come back."""
    tt, lt = template.split(), line.split()
    if len(tt) != len(lt):
        return None
    return " ".join(lt[i] if tt[i] == "<*>" else tt[i] for i in range(len(tt)))


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def score(lines):
    tm = TemplateMiner()
    for ln in lines:
        tm.add_log_message(ln)
    exact = content = 0
    for ln in lines:
        m = tm.match(ln)
        r = align(m.get_template(), ln) if m else None
        if r is not None and r == ln:
            exact += 1
        if r is not None and norm(r) == norm(ln):
            content += 1
    return exact, content, len(lines)


def main():
    # clean single-space lines — Drain3 reconstructs them exactly
    clean = [f"user u{i} logged in from 10.0.0.{i}" for i in range(1, 40)]
    ex, ct, n = score(clean)
    assert ex == n, f"clean lines should fully reconstruct, got {ex}/{n}"

    # lines with a whitespace run (space-padded day, like syslog 'Jul  1'): NOT
    # byte-exact (the run collapses to one space), but the content fully recovers
    padded = [f"Jul  {i} 09:00:{i:02d} host kernel: event {i}" for i in range(1, 40)]
    ex, ct, n = score(padded)
    assert ex == 0, f"whitespace-run lines should fail byte-exact (0), got {ex}/{n}"
    assert ct == n, f"whitespace-run lines should still recover 100% of content, got {ct}/{n}"

    print("smoke ok: clean lines byte-exact; whitespace-run lines lose only spacing "
          "(0 byte-exact, 100% of content recovered) — as the post claims")


if __name__ == "__main__":
    main()
