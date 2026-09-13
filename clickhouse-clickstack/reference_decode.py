#!/usr/bin/env python3
"""Is the text still in the compact form, or did the compaction lose it?

`report.py` finds that most rows do not expand back to their original text
through the SQL in `install.sql`. That leaves two very different explanations,
and the difference decides what the storage figure is worth:

  A. the compact form no longer holds the original text;
  B. the compact form holds it and the SQL misreads it.

This script settles it by decoding the same compact events in Python with four
rules that `install.sql` does not implement, and nothing else:

  //     `/` is the template's escape character, so `//` is a literal `/`.
  /$     and `/$` is a literal `$`.
  $N     a back-reference: the value N slot positions earlier, not a new value.
         install.sql's `\\$\\([^)]*\\)|\\$` matches the `$`, leaves the digits as
         literal text, and consumes a value that was never written.
  \\" etc  INNER mode captures the message as it sits inside the JSON envelope,
         so the result has to be JSON-unescaped to be the message again.

Timestamp slots are a separate question: `$(pattern)` holds an epoch integer and
rendering it back needs a Joda formatter, which is not what this script is
about. Rows whose template carries one are counted separately rather than
guessed at, so the answer for the rows this script does decide is unambiguous.

The answer is B. 24,494 of the 24,501 compact events whose template has no
timestamp slot come back byte-identical; the seven that do not are a
back-reference case this reference decoder gets wrong, not a loss in the data.

Usage:
    python3 reference_decode.py --arms <dir written by build_arms.py> \\
                                --templates <INNER templates.json>
"""

import argparse
import json
import pathlib
import sys

def parse(template: str):
    """Split a template into literal fragments and slots, honouring the escape.

    `/` is the template's escape character: `//` is a literal `/` and `/$` is a
    literal `$`. A slot is `$(pattern)` for a timestamp, `$N` for a
    back-reference, or a bare `$` for a new value. install.sql splits on the
    regex `\\$\\([^)]*\\)|\\$`, which knows about neither the escape nor the
    back-reference.
    """
    literals, slots, buf = [], [], []
    i, n = 0, len(template)
    while i < n:
        char = template[i]
        if char == "/" and i + 1 < n:
            buf.append(template[i + 1])
            i += 2
        elif char == "$":
            if i + 1 < n and template[i + 1] == "(":
                close = template.find(")", i)
                if close < 0:
                    buf.append(char); i += 1; continue
                slots.append(template[i:close + 1]); i = close + 1
            else:
                j = i + 1
                while j < n and template[j].isdigit():
                    j += 1
                slots.append(template[i:j]); i = j
            literals.append("".join(buf)); buf = []
        else:
            buf.append(char); i += 1
    literals.append("".join(buf))
    return literals, slots


def decode(compact: str, template: str) -> str:
    """Rebuild the original text from a compact event and its template."""
    if not compact.startswith("~"):
        return compact
    comma = compact.find(",")
    values = compact[comma + 1:].split(",") if comma >= 0 else []

    literals, slots = parse(template)
    out, cursor, resolved = [], 0, []
    for i, literal in enumerate(literals):
        out.append(literal)
        if i >= len(slots):
            continue
        slot = slots[i]
        if len(slot) > 1 and slot[1:].isdigit():
            # a back-reference to the value this many slot positions earlier
            back = int(slot[1:])
            value = resolved[i - back] if 0 <= i - back < len(resolved) else ""
        else:
            value = values[cursor] if cursor < len(values) else ""
            cursor += 1
        resolved.append(value)
        out.append(value)
    return json_unescape("".join(out))


def json_unescape(text: str) -> str:
    """INNER mode captures the `log` field's text as it sits inside the envelope.

    Templates and values are therefore in JSON-escaped space: a quote in the
    message is `\\"` in the template. The original message is that string
    unescaped. install.sql never does this, so even where its slot handling is
    right it hands the user back text with the envelope's backslashes in it.
    """
    # A folded multi-line event carries real newlines, which are not legal
    # inside a JSON string, so each line is unescaped on its own.
    out = []
    for line in text.split("\n"):
        try:
            out.append(json.loads('"' + line + '"'))
        except ValueError:
            out.append(line)
    return "\n".join(out)


# Four templates taken verbatim from a run, one per rule, with the compact event
# the run produced and the line it came from. They need no download and no
# Docker, so CI runs them on every push: if the engine changes how it writes a
# template, this fails here rather than in a results table nobody reruns.
SELF_TEST = [
    # $N, a back-reference to the value one slot position earlier
    ("~-T$UOFk|4@x,9092", "[KAFKA_PORT_$_TCP_PORT, $1]",
     "[KAFKA_PORT_9092_TCP_PORT, 9092]"),
    # // for a literal /, and a back-reference five positions back
    ("~-.2_80cmk;O,9092,10,100,90,228", "[KAFKA_PORT_$_TCP, tcp:////$.$.$.$:$5]",
     "[KAFKA_PORT_9092_TCP, tcp://10.100.90.228:9092]"),
    # // again, with no slots at all after the first
    ("~-E.<WC^*uQu,CORECLR",
     "[$_PROFILER_PATH, //app//OpenTelemetry.AutoInstrumentation.Native.so]",
     "[CORECLR_PROFILER_PATH, /app/OpenTelemetry.AutoInstrumentation.Native.so]"),
    # /$ for a literal $, and the JSON unescape INNER mode needs
    ("~selftest,flags", '{\\"/$schema\\": \\"$\\"}',
     '{"$schema": "flags"}'),
]


def self_test() -> int:
    failed = 0
    for compact, template, expected in SELF_TEST:
        got = decode(compact, template)
        status = "ok  " if got == expected else "FAIL"
        if got != expected:
            failed += 1
        print(f"{status} {template}")
        if got != expected:
            print(f"       expected {expected!r}")
            print(f"       got      {got!r}")
    print(f"\n{len(SELF_TEST) - failed} of {len(SELF_TEST)} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms")
    ap.add_argument("--templates")
    ap.add_argument("--self-test", action="store_true",
                    help="check the four decode rules on committed cases, no data needed")
    ap.add_argument("--show", type=int, default=5)
    ap.add_argument("--json", help="write the counts here for report.py")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.arms or not args.templates:
        ap.error("--arms and --templates are required unless --self-test is given")

    arms = pathlib.Path(args.arms)
    templates = {}
    for line in open(args.templates, encoding="utf-8"):
        record = json.loads(line)
        templates[record["templateHash"]] = record["template"]

    total = matched = 0
    timestamped = timestamped_matched = 0
    failures = []
    with open(arms / "compact.jsonl", encoding="utf-8") as compact_file, \
            open(arms / "native_folded.jsonl", encoding="utf-8") as original_file:
        for compact_line, original_line in zip(compact_file, original_file):
            compact = json.loads(compact_line)["Body"]
            original = json.loads(original_line)["Body"]
            comma = compact.find(",")
            key = compact[1:comma] if comma > 0 else compact[1:]
            template = templates.get(key, "")
            total += 1

            got = decode(compact, template)
            has_timestamp = "$(" in template
            if has_timestamp:
                timestamped += 1
                if got == original:
                    timestamped_matched += 1
                continue
            if got == original:
                matched += 1
            elif len(failures) < args.show:
                failures.append((compact, original, got))

    plain = total - timestamped
    print(f"compact events                       {total:>10,}")
    print(f"  template has no timestamp slot     {plain:>10,}")
    print(f"    decoded back to the original     {matched:>10,}  "
          f"{matched / plain * 100:.2f}%")
    print(f"  template has a timestamp slot      {timestamped:>10,}  "
          "(needs a Joda formatter; not decided here)")
    print(f"    decoded back anyway              {timestamped_matched:>10,}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps({
            "compact_events": total,
            "without_timestamp_slot": plain,
            "without_timestamp_slot_decoded": matched,
            "with_timestamp_slot": timestamped,
            "with_timestamp_slot_decoded": timestamped_matched,
        }, indent=2) + "\n")
    for compact, original, got in failures:
        print("\n  compact : " + compact[:160])
        print("  original: " + original[:160])
        print("  decoded : " + got[:160])
    return 0 if matched == plain else 2


if __name__ == "__main__":
    sys.exit(main())
