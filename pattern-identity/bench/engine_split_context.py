#!/usr/bin/env python3
"""engine_split_context.py - does a template hash depend on what the engine read before?

`bench/engine_split.py` finds probe records that both engine instances group into
the same event, with the same text, and name with the same pattern hash, but give
different template hashes. This script takes the first such probe from
`results/engine_split_raw.json`, rebuilds the feed instance A read up to and
including that event, and runs the engine on the event alone and on the last
2,000, 20,000 and 60,000 records of that feed, each twice. The event's text is the
same in every run; only the history before it changes.

Writes results/engine_split_context.md. Needs Docker and the image engine_split.py
pins; skips cleanly without them.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import engine_split as es  # noqa: E402
import identity  # noqa: E402

SUFFIXES = [2000, 20000, 60000]
REPEATS = 2


def main() -> int:
    digest, why = es.image_digest()
    if digest is None:
        print(f"SKIP engine_split_context: {why}; results/ left as committed", file=sys.stderr)
        return 0
    raw = json.loads((es.RESULTS_DIR / "engine_split_raw.json").read_text())
    cands = [x for x in raw["disagreements"]
             if x["a"]["tenx_hash"] == x["b"]["tenx_hash"]
             and x["a"]["templateHash"] != x["b"]["templateHash"]
             and x["a"]["position_in_event"] == 0]
    if not cands:
        print("no probe with the same pattern hash and different template hashes", file=sys.stderr)
        return 0
    x = sorted(cands, key=lambda c: (c["trial"], c["probe_position"]))[0]
    cfg = raw["config"]
    records = es.load_records(identity.resolve_sample())
    plan = es.build_plan(len(records), x["trial"] + 1, cfg["seed"], cfg["probes"])[x["trial"]]
    k = x["a"]["event_records"]
    feed = plan["a"] + plan["probe"][:x["probe_position"] + k]

    rows = []
    for label, order in ([("the event alone", feed[-k:])]
                         + [(f"last {s:,} records of A's feed", feed[-s:]) for s in SUFFIXES]):
        answers = []
        for r in range(REPEATS):
            res = es.run_engine(records, order, f"ctx{len(order)}r{r}")
            head = res[len(order) - k]
            answers.append((head[0], head[1], head[3]))
        rows.append((label, len(order), answers))

    L = ["# A template hash and the history before it", "",
         "Written by `bench/engine_split_context.py`. The first probe record of "
         "`results/engine_split_raw.json` that both engine instances grouped into the same "
         "event and named with the same pattern hash, but gave different template hashes:", "",
         f"- trial {x['trial'] + 1}, probe position {x['probe_position']}, an event of {k} records, "
         f"pattern `{x['a']['pattern']}`",
         f"- instance A (its half, then the probes): pattern hash `{x['a']['tenx_hash']}`, "
         f"template hash `{x['a']['templateHash']}`",
         f"- instance B: pattern hash `{x['b']['tenx_hash']}`, template hash `{x['b']['templateHash']}`",
         f"- image: `{es.IMAGE}`", "",
         "The same event, at the end of shorter stretches of instance A's feed. Each input runs "
         f"{REPEATS} times in a fresh container.", "",
         "| input | records | pattern hash | template hash | records in the event |",
         "|---|---:|---|---|---:|"]
    for label, n, answers in rows:
        for a in answers:
            L.append(f"| {label} | {n:,} | `{a[0]}` | `{a[1]}` | {a[2]} |")
    L.append("")
    same_input_same_answer = all(len(set(a)) == 1 for _, _, a in rows)
    distinct_tpl = sorted({a[1] for _, _, ans in rows for a in ans})
    L.append(f"Each input gave the same answer on every run: {'yes' if same_input_same_answer else 'no'}. "
             f"Template hashes seen for this one event: {', '.join(f'`{t}`' for t in distinct_tpl)}. "
             f"Pattern hashes seen: {', '.join(sorted({f'`{a[0]}`' for _, _, ans in rows for a in ans}))}.")
    L.append("")
    (es.RESULTS_DIR / "engine_split_context.md").write_text("\n".join(L))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
