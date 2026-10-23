#!/usr/bin/env python3
"""Turn the engine image's shipped config tree into the gate's config tree.

Copied from clickstack-e2e/patch_engine_config.py and reduced to what 1.1.147
still needs. Each edit is asserted, so a change in the shipped config fails here
rather than producing a silently unmarked run.

  1. apps/gate/config.yaml    a copy of the shipped receiver app with the
                              OpenTelemetry Collector forwarder input and the
                              Prometheus scrape metric output enabled.
  2. forwarder/config.yaml    the pattern TEXT added to the fullText splice list,
                              beside the pattern hash and routeState. Matched on
                              the expression, not on its indentation: 1.1.147
                              re-indented the block and the text is unchanged.

  3. rate/config.yaml         `unit: bytes` becomes `unit: events`. The literal in
                              the shipped file wins over the environment (a run
                              with rateReceiverUnit=events in the environment
                              still capped in bytes), so the unit is written here.

Not patched, on purpose: warmupMs (1.1.147 ships 0) and baselineCount (the
shipped 5 is one of the numbers the gate measures). The totals file path comes
from the environment (TOTAL_LOOKUP_FILE), which the shipped file does read.
"""
import argparse
import pathlib
import sys


def sub(path: pathlib.Path, old: str, new: str, what: str) -> None:
    text = path.read_text()
    if old not in text:
        sys.exit(f"patch failed, {what}: the shipped text is not in {path}")
    path.write_text(text.replace(old, new, 1))
    print(f"  patched {what}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-dir", required=True)
    args = ap.parse_args()
    root = pathlib.Path(args.config_dir)

    receiver = root / "apps" / "receiver" / "config.yaml"
    app = root / "apps" / "gate" / "config.yaml"
    app.parent.mkdir(parents=True, exist_ok=True)
    text = receiver.read_text()
    for old, new, what in (
        ("  # - run/input/forwarder/otel-collector",
         "  - run/input/forwarder/otel-collector",
         "otel-collector forwarder input enabled"),
        ("  # - run/output/metric/prometheus/scrape",
         "  - run/output/metric/prometheus/scrape",
         "prometheus scrape output enabled"),
    ):
        if old not in text:
            sys.exit(f"patch failed, {what}: the shipped text is not in {receiver}")
        text = text.replace(old, new, 1)
        print(f"  patched {what}")
    text = text.replace(
        'runtimeName: $=TenXEnv.get("TENX_RUNTIME_NAME", "myReceiver")',
        'runtimeName: $=TenXEnv.get("TENX_RUNTIME_NAME", "gateReceiver")', 1)
    app.write_text(text)

    rate = root / "pipelines" / "run" / "receive" / "rate" / "config.yaml"
    sub(rate, "  unit: bytes", "  unit: events", "regulator unit set to events")

    fwd = root / "pipelines" / "run" / "input" / "forwarder" / "config.yaml"
    old = ('? (TenXEnv.get("symbolMessageHashField") ? ("fullText(\\"" '
           '+ TenXEnv.get("symbolMessageHashField") + "\\",\\"routeState\\")") '
           ': "fullText(\\"routeState\\")")')
    new = ('? (TenXEnv.get("symbolMessageHashField") ? ("fullText(\\"" '
           '+ TenXEnv.get("symbolMessageHashField") + "\\",\\"" '
           '+ TenXEnv.get("symbolMessageField") + "\\",\\"routeState\\")") '
           ': ("fullText(\\"" + TenXEnv.get("symbolMessageField") '
           '+ "\\",\\"routeState\\")"))')
    sub(fwd, old, new, "pattern text added to the offload splice list")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
