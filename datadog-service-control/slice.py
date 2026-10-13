#!/usr/bin/env python3
"""
Write one container's records from a capture, byte for byte, in their order.

  slice.py --capture FILE --container NAME --out FILE

A record is one line of the capture; it is kept when its `kubernetes.container_name` is the
container. Prints the slice's line count, bytes and sha256 as JSON.
"""
import argparse
import hashlib
import json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--capture', required=True)
    ap.add_argument('--container', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    h, lines, size, skipped = hashlib.sha256(), 0, 0, 0
    with open(a.capture, 'rb') as src, open(a.out, 'wb') as dst:
        for raw in src:
            try:
                rec = json.loads(raw)
            except ValueError:
                skipped += 1
                continue
            if ((rec.get('kubernetes') or {}).get('container_name')) != a.container:
                continue
            dst.write(raw)
            h.update(raw)
            lines += 1
            size += len(raw)
    print(json.dumps({'container': a.container, 'lines': lines, 'bytes': size, 'sha256': h.hexdigest(),
                      'capture_lines_not_json': skipped}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
