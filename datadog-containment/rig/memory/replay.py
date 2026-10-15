#!/usr/bin/env python3
"""Replay the run's raw capture into Fluent Bit over the Fluent Forward protocol, at the
pace it was captured.

    replay.py <raw.jsonl.gz> <host> <port> <start epoch> [<end epoch>]

Each record of raw.jsonl with fb_ts in [start, end] is sent as it was written (the record
Fluent Bit handed to the Receiver in the run), tagged app.<container> as the Docker fluentd
driver tagged it, with the current time as its event time. A record is sent when the time
since the replay began reaches its fb_ts minus <start>; a record whose fb_ts is earlier than
the record before it (the driver writes asynchronously) is sent at once, so file order is
kept. Standard library only.
"""
import gzip
import json
import socket
import struct
import sys
import time


def pack(o, out):
    if o is None:
        out.append(b"\xc0")
    elif o is True:
        out.append(b"\xc3")
    elif o is False:
        out.append(b"\xc2")
    elif isinstance(o, int):
        if 0 <= o < 128:
            out.append(struct.pack("B", o))
        elif -32 <= o < 0:
            out.append(struct.pack("b", o))
        else:
            out.append(b"\xd3" + struct.pack(">q", o))
    elif isinstance(o, float):
        out.append(b"\xcb" + struct.pack(">d", o))
    elif isinstance(o, str):
        b = o.encode("utf-8")
        n = len(b)
        if n < 32:
            out.append(struct.pack("B", 0xa0 | n))
        elif n < 256:
            out.append(b"\xd9" + struct.pack("B", n))
        elif n < 65536:
            out.append(b"\xda" + struct.pack(">H", n))
        else:
            out.append(b"\xdb" + struct.pack(">I", n))
        out.append(b)
    elif isinstance(o, (list, tuple)):
        n = len(o)
        out.append(struct.pack("B", 0x90 | n) if n < 16 else b"\xdc" + struct.pack(">H", n))
        for x in o:
            pack(x, out)
    elif isinstance(o, dict):
        n = len(o)
        out.append(struct.pack("B", 0x80 | n) if n < 16 else b"\xde" + struct.pack(">H", n))
        for k, v in o.items():
            pack(k, out)
            pack(v, out)
    else:
        raise TypeError(type(o))


def event_time(t):
    """Fluent Forward EventTime: msgpack ext type 0, seconds and nanoseconds."""
    sec = int(t)
    return b"\xd7\x00" + struct.pack(">II", sec, int((t - sec) * 1e9))


def message(tag, rec):
    out = [b"\x93"]
    pack(tag, out)
    out.append(event_time(time.time()))
    pack(rec, out)
    return b"".join(out)


def main():
    path, host, port, start = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
    end = float(sys.argv[5]) if len(sys.argv) > 5 else float("inf")
    recs = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            ts = float(r["fb_ts"])
            if start <= ts <= end:
                recs.append((ts, "app." + r["kubernetes"]["container_name"], r))
    print(f"{len(recs)} records from {recs[0][0]:.3f} to {recs[-1][0]:.3f}", flush=True)
    for attempt in range(60):
        try:
            sock = socket.create_connection((host, port), timeout=30)
            break
        except OSError:
            time.sleep(2)
    else:
        sys.exit(f"cannot connect to {host}:{port}")
    t0 = time.time()
    last_report = t0
    max_late = 0.0
    sent = 0
    high = start
    for ts, tag, rec in recs:
        due = t0 + (ts - start)
        now = time.time()
        if due > now:
            time.sleep(due - now)
        elif ts >= high:
            max_late = max(max_late, now - due)
        high = max(high, ts)
        sock.sendall(message(tag, rec))
        sent += 1
        if time.time() - last_report >= 60:
            last_report = time.time()
            print(f"{time.strftime('%H:%M:%S', time.gmtime())} sent {sent} "
                  f"capture time {ts - start:.0f} s, wall {time.time() - t0:.0f} s", flush=True)
    sock.close()
    print(f"done: sent {sent} records in {time.time() - t0:.1f} s; capture span "
          f"{recs[-1][0] - start:.1f} s; in-order records sent at most {max_late:.3f} s "
          f"after their slot", flush=True)


if __name__ == "__main__":
    main()
