#!/usr/bin/env python3
"""The two edits the reproduction needs in the shipped engine config tree.

Both assert: a change in the shipped text fails here rather than producing a
silently unmarked run. This repeats what the harness's patch_engine_config.py
does, minus the regulator knobs the short run does not need.
"""
import os
import pathlib
import sys

root = pathlib.Path(os.environ["CONFIG_DIR"])

receiver = root / "apps" / "receiver" / "config.yaml"
app = root / "apps" / "e2e" / "config.yaml"
app.parent.mkdir(parents=True, exist_ok=True)
text = receiver.read_text()
old = "  # - run/input/forwarder/otel-collector"
if old not in text:
    sys.exit("patch failed: the shipped receiver app no longer carries the commented otel-collector include")
text = text.replace(old, "  - run/input/forwarder/otel-collector", 1)
text = text.replace(
    'runtimeName: $=TenXEnv.get("TENX_RUNTIME_NAME", "myReceiver")',
    'runtimeName: $=TenXEnv.get("TENX_RUNTIME_NAME", "reproReceiver")', 1)
app.write_text(text)

fwd = root / "pipelines" / "run" / "input" / "forwarder" / "config.yaml"
old = ('          ? (TenXEnv.get("symbolMessageHashField") ? ("fullText(\\"" '
       '+ TenXEnv.get("symbolMessageHashField") + "\\",\\"routeState\\")") '
       ': "fullText(\\"routeState\\")")')
new = ('          ? (TenXEnv.get("symbolMessageHashField") ? ("fullText(\\"" '
       '+ TenXEnv.get("symbolMessageHashField") + "\\",\\"" '
       '+ TenXEnv.get("symbolMessageField") + "\\",\\"routeState\\")") '
       ': ("fullText(\\"" + TenXEnv.get("symbolMessageField") '
       '+ "\\",\\"routeState\\")"))')
t = fwd.read_text()
if old not in t:
    sys.exit("patch failed: the shipped splice expression has moved")
fwd.write_text(t.replace(old, new, 1))

# The regulator holds off for five minutes and five baseline intervals out of
# the box, which is longer than this run.
rate = root / "pipelines" / "run" / "receive" / "rate" / "config.yaml"
t = rate.read_text()
for old, new in (('  warmupMs: $=parseDuration("5m")', '  warmupMs: $=parseDuration("0s")'),
                 ("  baselineCount: 5", "  baselineCount: 0")):
    if old not in t:
        sys.exit("patch failed: the shipped rate config has moved: " + old)
    t = t.replace(old, new, 1)
rate.write_text(t)
print("  config patched")
