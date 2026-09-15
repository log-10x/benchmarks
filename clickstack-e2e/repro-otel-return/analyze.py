#!/usr/bin/env python3
"""Read out/<variant>/wire/returned.json and write out/tables.md.

Every number in results.md comes from here.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent

# Everything the run is configured to put on a returned record.
EXPECTED = {
    "noise", "routeState", "tenx_hash", "message_pattern",
    "k8s_container", "k8s_namespace", "kubernetes", "docker", "stream",
    "log.file.name", "tenx_tag", "service.name",
}

LABEL = re.compile(r"(CASE_[A-F]|SWEEP_\d\d|NOISE_\d\d)")

# The `tag` field the extractor drops, and the text that follows it on the
# rendered record, per variant. `tag` is the synthetic field the input
# renderer writes: service.name when the resource carries one, else the
# literal `otel`.
BLOCK = {"resource": ',"tag":"kafka"', "noresource": ',"tag":"otel"',
         "nodrop": ',"tag":"kafka"', "withtime": ',"tag":"kafka"'}
TAIL = {
    "resource": ',"_tenx_resource_keys":["service.name"],"_tenx_time":0,"_tenx_observed_time":',
    "withtime": ',"_tenx_resource_keys":["service.name"],"_tenx_time":',
    "noresource": ',"_tenx_time":0,"_tenx_observed_time":',
    "nodrop": ',"_tenx_resource_keys":["service.name"],"_tenx_time":0,"_tenx_observed_time":',
}


def any_value(v):
    if not isinstance(v, dict):
        return v
    for k in ("stringValue", "boolValue", "intValue", "doubleValue"):
        if k in v:
            return v[k]
    if "arrayValue" in v:
        return [any_value(x) for x in v["arrayValue"].get("values", [])]
    if "kvlistValue" in v:
        return {kv["key"]: any_value(kv.get("value", {})) for kv in v["kvlistValue"].get("values", [])}
    return None


def load(variant):
    path = HERE / "out" / variant / "wire" / "returned.json"
    out = []
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        doc = json.loads(line)
        for rl in doc.get("resourceLogs", []):
            res = {kv["key"]: any_value(kv.get("value", {}))
                   for kv in rl.get("resource", {}).get("attributes", [])}
            for sl in rl.get("scopeLogs", []):
                for lr in sl.get("logRecords", []):
                    attrs = {kv["key"]: any_value(kv.get("value", {}))
                             for kv in lr.get("attributes", [])}
                    out.append({
                        "body": any_value(lr.get("body", {})),
                        "attrs": attrs,
                        "resource": res,
                        "timeUnixNano": lr.get("timeUnixNano"),
                        "observedTimeUnixNano": lr.get("observedTimeUnixNano"),
                    })
    return out


def body_text(rec):
    return rec["body"] if isinstance(rec["body"], str) else json.dumps(rec["body"])


def label_of(rec):
    m = LABEL.search(body_text(rec) + " " + json.dumps(rec["attrs"]))
    return m.group(1) if m else "?"


def escapes_of(label):
    if label.startswith(("SWEEP_", "NOISE_")):
        return int(label.split("_")[1])
    import make_lines
    return sum(1 for c in make_lines.CASES.get(label.replace("CASE_", ""), "")
               if c in '"\\\t\n\r')


def spliced(k, variant):
    """The text from `,"tag"` onward after a drop range shifted by k.

    The range keeps the length of `,"tag":"<v>"` and starts k characters past
    its true start, which is the whole of the defect.
    """
    whole = BLOCK[variant] + TAIL[variant]
    return whole[:k] + whole[k + len(BLOCK[variant]):]


def visible_keys(text):
    """What the output appender would make of a spliced fragment.

    It drops the `tag` field and strips every `_tenx_` marker, so part of the
    damage never reaches the returned attributes.
    """
    names = re.findall(r'"([^"]*)":', text)
    return [n for n in names if n != "tag" and not n.startswith("_tenx_")]


def shift_from_key(bad_key, variant):
    for k in range(0, len(TAIL[variant])):
        if bad_key in visible_keys(spliced(k, variant)):
            return k
    return None


def candidates(rec, variant):
    """Every shift whose spliced text explains this returned record.

    Some shifts cannot be told apart: when the character at the splice
    boundary repeats, two neighbouring shifts produce the same text.
    """
    whole = BLOCK[variant] + TAIL[variant]
    span = range(0, len(TAIL[variant]))
    if not rec["attrs"]:
        # The appender could not parse it, so the whole emitted record came
        # back as the body and the text can be compared directly.
        text = body_text(rec)
        i = text.find(',"tag')
        if i == -1:
            return []
        actual = text[i:i + len(whole)]
        return [k for k in span
                if spliced(k, variant)[:len(actual)] == actual[:len(spliced(k, variant))]]
    observed = sorted(k for k in rec["attrs"] if k not in EXPECTED)
    resource_set = bool(rec["resource"])
    out = []
    for k in span:
        text = spliced(k, variant)
        if sorted(visible_keys(text)) != observed:
            continue
        intact = '"_tenx_resource_keys":["service.name"]' in text
        if variant in ("resource", "withtime", "nodrop") and intact != resource_set:
            continue
        out.append(k)
    return out


def compact(ks):
    if not ks:
        return "none"
    if len(ks) == 1:
        return str(ks[0])
    if len(ks) > 5:
        return "not distinguishable"
    return "%d to %d" % (min(ks), max(ks))


def shift_of(rec, variant):
    ks = candidates(rec, variant)
    if not rec["attrs"]:
        how = "not parsed, whole record in the body"
    elif [k for k in rec["attrs"] if k not in EXPECTED]:
        how = "parsed, key `%s`" % [k for k in rec["attrs"] if k not in EXPECTED][0]
    elif 0 in ks:
        how = "parsed, nothing visibly wrong"
    else:
        how = "parsed, damage inside the `_tenx_` markers the appender strips"
    return ks, how


def render(variants):
    out = []
    for variant in variants:
        recs = load(variant)
        out.append("\n## Variant `%s`\n" % variant)
        out.append("Records returned: **%d**.\n" % len(recs))
        if not recs:
            out.append("Nothing came back.\n")
            continue
        parsed = [r for r in recs if r["attrs"]]
        out.append("| Measure | Records |")
        out.append("|---|---:|")
        out.append("| carrying attributes | %d |" % len(parsed))
        out.append("| carrying no attribute at all | %d |" % (len(recs) - len(parsed)))
        out.append("| carrying `routeState` | %d |" % len([r for r in recs if "routeState" in r["attrs"]]))
        out.append("| carrying `tenx_hash` | %d |" % len([r for r in recs if "tenx_hash" in r["attrs"]]))
        out.append("| carrying `message_pattern` | %d |" % len([r for r in recs if "message_pattern" in r["attrs"]]))
        out.append("| `timeUnixNano` set | %d |" % len([r for r in recs if r["timeUnixNano"] not in (None, "0", 0)]))
        out.append("| `timeUnixNano` zero or absent | %d |" % len([r for r in recs if r["timeUnixNano"] in (None, "0", 0)]))
        out.append("| `observedTimeUnixNano` set | %d |" % len([r for r in recs if r["observedTimeUnixNano"] not in (None, "0", 0)]))
        out.append("| a resource attribute present | %d |" % len([r for r in recs if r["resource"]]))
        out.append("| `service.name` as a log attribute | %d |" % len([r for r in recs if "service.name" in r["attrs"]]))
        out.append("")

        bad = {}
        for r in recs:
            for k in r["attrs"]:
                if k not in EXPECTED:
                    bad[k] = bad.get(k, 0) + 1
        if bad:
            out.append("Attribute names nothing configured:\n")
            out.append("| Name | Records | Shift of the drop range that produces it |")
            out.append("|---|---:|---:|")
            for k, n in sorted(bad.items(), key=lambda kv: -kv[1]):
                s = shift_from_key(k, variant)
                out.append("| `%s` | %d | %s |" % (k, n, s if s is not None else "beyond the modelled window"))
            out.append("")
        else:
            out.append("No attribute name outside the configured set.\n")

        sweep = [(escapes_of(label_of(r)), r) for r in recs if label_of(r).startswith("SWEEP_")]
        if sweep:
            out.append("Escape count against the shift of the drop range:\n")
            out.append("| Escapes in the message | Shift of the drop range | Shift equals the escape count | Outcome | Attributes |")
            out.append("|---:|---:|---|---|---:|")
            for n, r in sorted(sweep):
                ks, how = shift_of(r, variant)
                out.append("| %d | %s | %s | %s | %d |" % (
                    n, compact(ks), "yes" if n in ks else "no", how, len(r["attrs"])))
            out.append("")

        rest = [r for r in recs if not label_of(r).startswith("SWEEP_")]
        out.append("The six shapes, and the escapes-elsewhere control:\n")
        out.append("| Line | Escapes in the message | Attributes | `timeUnixNano` | Anomalous key | Body, first 80 characters |")
        out.append("|---|---:|---:|---|---|---|")
        for r in sorted(rest, key=label_of):
            lab = label_of(r)
            anom = ",".join("`%s`" % k for k in r["attrs"] if k not in EXPECTED) or "none"
            out.append("| %s | %d | %d | %s | %s | `%s` |" % (
                lab, escapes_of(lab), len(r["attrs"]), r["timeUnixNano"] or "absent", anom,
                body_text(r)[:80].replace("|", "\\|").replace("\n", "\\n").replace("\t", "\\t")))
        out.append("")
    return "\n".join(out)


def samples(variants):
    """One raw returned record per outcome, verbatim off the wire."""
    out = ["\n# Raw records\n",
           "Straight out of `out/<variant>/wire/returned.json`, which the "
           "collector's file exporter wrote with no processor in between. The "
           "full files are in the folder.\n"]
    for variant in variants:
        recs = load(variant)
        picked = []
        for want in ("clean", "damaged key", "not parsed"):
            for r in recs:
                bad = [k for k in r["attrs"] if k not in EXPECTED]
                kind = "not parsed" if not r["attrs"] else ("damaged key" if bad else "clean")
                if kind == want and label_of(r).startswith("SWEEP_"):
                    picked.append((kind, r))
                    break
        if not picked:
            continue
        out.append("\n## `%s`\n" % variant)
        for kind, r in picked:
            out.append("%s, line %s:\n" % (kind, label_of(r)))
            out.append("```json")
            out.append(json.dumps({
                "timeUnixNano": r["timeUnixNano"],
                "observedTimeUnixNano": r["observedTimeUnixNano"],
                "resource": r["resource"],
                "attributes": r["attrs"],
                "body": r["body"],
            }, indent=1))
            out.append("```\n")
    return "\n".join(out)


def main():
    variants = sys.argv[1:] or ["resource", "noresource", "nodrop", "withtime"]
    text = render(variants)
    (HERE / "out" / "tables.md").write_text(text)
    head = (HERE / "results.head.md").read_text()
    (HERE / "results.md").write_text(head + "\n# The numbers\n" + text + samples(variants) + "\n")
    print(text)


if __name__ == "__main__":
    main()
