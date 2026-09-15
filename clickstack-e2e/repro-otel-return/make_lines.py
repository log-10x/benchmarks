#!/usr/bin/env python3
"""Write the crafted capture the reproduction feeds.

Every line is one JSON object in the released capture's envelope shape: the
log line is the `log` value, the rest is Fluent's envelope. The container is
`kafka` on every line, so the per-service policy the harness uses applies
unchanged.

Two blocks:

  cases   the six shapes the handoff asks for, A to F, each carrying its own
          label inside the message so a returned record maps back to one line.
  sweep   one line per escape count N from 0 to 40, message otherwise
          identical, so the escape count is the only thing that moves.
"""
import json
import pathlib

CID = "21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c"


def envelope(message: str, noise: str = None) -> str:
    body = {
        "stream": "stdout",
        "log": message,
        "docker": {"container_id": CID},
        "kubernetes": {
            "container_name": "kafka",
            "namespace_name": "default",
            "pod_name": "kafka-5ff8667569-jbfmv",
            "container_image": "ghcr.io/open-telemetry/demo:2.1.3-kafka",
            "container_image_id": "ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0",
            "pod_id": "4bdaf655-5d02-4653-ba57-fece182730aa",
            "pod_ip": "192.168.37.206",
            "host": "ip-192-168-42-205.ec2.internal",
            "labels": {
                "app.kubernetes.io/component": "kafka",
                "app.kubernetes.io/name": "kafka",
                "opentelemetry.io/name": "kafka",
                "pod-template-hash": "5ff8667569",
            },
        },
        "tenx_tag": "kubernetes.var.log.containers.kafka-5ff8667569-jbfmv_default_kafka-" + CID + ".log",
    }
    if noise is not None:
        body["noise"] = noise
    return json.dumps(body, separators=(",", ":"))


HEAD = "[2025-10-01 20:34:05,556] INFO "

CASES = {
    "A": HEAD + "CASE_A ProducerStateManager wrote a snapshot at offset 2583 in 0 ms.",
    "B": HEAD + "CASE_B consumer group \"alpha\" rebalanced in 0 ms.",
    "C": HEAD + "CASE_C keys \"a\" \"b\" \"c\" \"d\" \"e\" settled.",
    "D": HEAD + "CASE_D " + " ".join('"f%d"' % i for i in range(15)) + " settled.",
    "E": HEAD + "CASE_E\tcolumnar field separated by a tab.",
    "F": '{"body":"CASE_F inner","level":"INFO","k":"v"}',
}


def sweep_message(n: int) -> str:
    # n escaped double quotes, nothing else that escapes. The message length
    # moves with n, which is exactly the variable under test.
    return HEAD + ("SWEEP_%02d " % n) + ('"' * n) + " settled."


def noise_message(n: int) -> str:
    # The escapes live in a field of their own, ahead of `tag` on the rendered
    # record, and the message itself carries none. Separates "escapes anywhere
    # before the field" from "escapes in the captured message".
    return ('"' * n) + " noise"


def main() -> None:
    out = pathlib.Path(__file__).parent / "lines" / "crafted.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [envelope(m) for m in CASES.values()]
    lines += [envelope(sweep_message(n)) for n in range(0, 41)]
    lines += [envelope(HEAD + ("NOISE_%02d plain message, no escapes." % n), noise_message(n))
              for n in (0, 3, 4, 5, 6, 10, 16, 20, 30)]
    out.write_text("\n".join(lines) + "\n")
    print("wrote %d lines to %s" % (len(lines), out))


if __name__ == "__main__":
    main()
