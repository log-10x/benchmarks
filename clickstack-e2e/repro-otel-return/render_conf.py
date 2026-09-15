#!/usr/bin/env python3
"""Render conf/collector.yaml.tmpl for one variant."""
import pathlib
import sys

RESOURCE = """      - type: copy
        from: attributes.kubernetes.container_name
        to: resource["service.name"]
"""

TIME_PROCESSORS = """processors:
  # A record time on the way IN, so `_tenx_time` reaching the output appender
  # is not zero. Everything else about the variant is unchanged.
  transform/intime:
    error_mode: ignore
    log_statements:
      - context: log
        statements:
          - set(log.time_unix_nano, 1759350845556000000)

"""

TIME_PIPELINE = "      processors: [ transform/intime ]\n"


def main() -> int:
    variant = sys.argv[1]
    here = pathlib.Path(__file__).parent
    text = (here / "conf" / "collector.yaml.tmpl").read_text()
    text = text.replace("__RESOURCE__\n", RESOURCE if variant != "noresource" else "")
    text = text.replace("__PROCESSORS__\n", TIME_PROCESSORS if variant == "withtime" else "")
    text = text.replace("__PIPEPROC__", TIME_PIPELINE if variant == "withtime" else "")
    out = here / "out" / variant / "collector.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
