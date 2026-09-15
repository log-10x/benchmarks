#!/usr/bin/env python3
"""Turn the engine image's shipped config tree into the harness config tree.

The tree is copied out of the pinned engine image by run.sh; this script makes
four edits to it and asserts every one, so a change in the shipped config fails
here rather than producing a silently unmarked run.

  1. apps/e2e/config.yaml     a copy of the shipped receiver app with the
                              OpenTelemetry Collector forwarder input and the
                              Prometheus scrape metric output enabled.
  2. rate/config.yaml         warmupMs and baselineCount set to zero. Both are
                              hard-coded in the shipped file and both hold the
                              regulator off for the length of a test run.
  3. forwarder/config.yaml    the pattern TEXT added to the fullText splice
                              list, beside the pattern hash and routeState.
                              The shipped expression splices the hash and the
                              route only, so the pattern text never reaches the
                              wire and the offloaded object cannot carry it.
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

    # ---------------------------------------------------------------- the app
    receiver = root / "apps" / "receiver" / "config.yaml"
    app = (root / "apps" / "e2e" / "config.yaml")
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
        'runtimeName: $=TenXEnv.get("TENX_RUNTIME_NAME", "e2eReceiver")', 1)
    app.write_text(text)

    # ------------------------------------------------------------ the rate knobs
    rate = root / "pipelines" / "run" / "receive" / "rate" / "config.yaml"
    sub(rate, '  warmupMs: $=parseDuration("5m")',
        '  warmupMs: $=parseDuration("0s")', "regulator warmup set to zero")
    sub(rate, "  baselineCount: 5", "  baselineCount: 0",
        "regulator baseline count set to zero")

    # --------------------------------------------------------- the splice list
    fwd = root / "pipelines" / "run" / "input" / "forwarder" / "config.yaml"
    old = ('          ? (TenXEnv.get("symbolMessageHashField") ? ("fullText(\\"" '
           '+ TenXEnv.get("symbolMessageHashField") + "\\",\\"routeState\\")") '
           ': "fullText(\\"routeState\\")")')
    new = ('          ? (TenXEnv.get("symbolMessageHashField") ? ("fullText(\\"" '
           '+ TenXEnv.get("symbolMessageHashField") + "\\",\\"" '
           '+ TenXEnv.get("symbolMessageField") + "\\",\\"routeState\\")") '
           ': ("fullText(\\"" + TenXEnv.get("symbolMessageField") '
           '+ "\\",\\"routeState\\")"))')
    sub(fwd, old, new, "pattern text added to the offload splice list")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
