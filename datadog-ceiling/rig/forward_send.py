#!/usr/bin/env python3
"""Send lines to the rig's Fluent Bit over the Fluent Forward protocol, in the record shape the
Docker fluentd driver sends (container_name, container_id, source, log), so each line enters
the rig's normal ingest as the named container's own line. Runs in a container on the demo
network (python:3.12-slim, standard library only; msgpack encoded here).
  forward_send.py replay <source.jsonl> <speed> <host> <port>
      the capture at its own pace times <speed>, looping
  forward_send.py storm <line.json> <lines per second> <until epoch> <host> <port>
      one real error line, its "time" field set to now"""
import json, re, socket, struct, sys, time


def pack(o):
    if isinstance(o, str):
        b = o.encode('utf-8')
        n = len(b)
        if n < 32:
            return bytes([0xa0 | n]) + b
        if n < 256:
            return b'\xd9' + bytes([n]) + b
        if n < 65536:
            return b'\xda' + struct.pack('>H', n) + b
        return b'\xdb' + struct.pack('>I', n) + b
    if isinstance(o, float):
        return b'\xcb' + struct.pack('>d', o)
    if isinstance(o, int):
        return b'\xd3' + struct.pack('>q', o)
    if isinstance(o, dict):
        n = len(o)
        h = bytes([0x80 | n]) if n < 16 else b'\xde' + struct.pack('>H', n)
        return h + b''.join(pack(k) + pack(v) for k, v in o.items())
    if isinstance(o, (list, tuple)):
        n = len(o)
        h = bytes([0x90 | n]) if n < 16 else b'\xdc' + struct.pack('>H', n)
        return h + b''.join(pack(v) for v in o)
    raise TypeError(type(o))


def event_time(t):
    # Forward protocol EventTime: ext type 0, 8 bytes (seconds, nanoseconds)
    s = int(t)
    return b'\xd7\x00' + struct.pack('>II', s, int((t - s) * 1e9))


class Sender:
    def __init__(self, host, port):
        self.addr = (host, int(port))
        self.s = None

    def send(self, rec):
        msg = b'\x93' + pack('app.replay') + event_time(time.time()) + pack(rec)
        while True:
            try:
                if self.s is None:
                    self.s = socket.create_connection(self.addr, timeout=10)
                self.s.sendall(msg)
                return
            except OSError:
                self.s = None
                time.sleep(1)


def shape(r):
    return {'container_name': r['container_name'], 'container_id': r['container_id'], 'source': r.get('source', 'stdout'), 'log': r['log']}


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'replay':
        src, speed, host, port = sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
        rows = [json.loads(l) for l in open(src)]
        t0 = rows[0]['t']
        span = rows[-1]['t'] - t0 + 1
        out = Sender(host, port)
        start = time.time()
        loop = 0
        while True:
            for r in rows:
                due = start + (loop * span + (r['t'] - t0)) / speed
                d = due - time.time()
                if d > 0:
                    time.sleep(d)
                out.send(shape(r))
            loop += 1
    elif mode == 'storm':
        line = json.load(open(sys.argv[2]))
        rate, until, host, port = float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]
        out = Sender(host, port)
        while time.time() < until:
            r = dict(line)
            r['log'] = re.sub(r'"time":\d+', '"time":%d' % (time.time() * 1000), r['log'], count=1)
            out.send(shape(r))
            time.sleep(1 / rate)
    else:
        raise SystemExit(__doc__)
