#!/usr/bin/env python3
"""E103 sender. Interleaves containers on one Fluent Forward connection, in the record shape the Docker
fluentd driver sends (container_name, container_id, source, log) plus seq, through the pack and Sender of
elastic-hot-tier-budget/rig/forward_send.py (mounted at /rig, standard library only). Every line carries
the token e103id=<seq> (inside the JSON for the JSON line), and every line is written to the manifest.

Cases, each with its own container names, 10 s of quiet between cases:
  a  orders logs an ERROR head; billing's timestamped INFO lines arrive; then orders' stack trace lines.
  b  jaeger logs a JSON line; kafka's four startup banner lines arrive (no timestamp, no level, the lines of
     the hot-tier run), then kafka's own timestamped INFO line.
  c  orders and payments are both mid stack trace: orders' head and two frames, payments' head, then the
     remaining frames of both, alternating.
  d  control, orders only: the head, the stack trace, then 0 to 2 INFO lines.
  e  a, b and c in rotation, with one Fluent tag per container (docker.<id12>, the fluentd driver's
     default tag) instead of the shared app.replay tag of a to d.
Per case: <episodes> episodes sent back to back (lines within an episode with no sleep, 1 ms between
episodes) and twelve paused episodes (1, 2, 3, 4, 5, 6 s, twice each) spread through them, the pause sent
right after orders' (or jaeger's) head, for c after orders' second frame.
  send.py <host> <port> <manifest.jsonl> [cases=abcde] [episodes=500]"""
import hashlib, json, os, random, socket, sys, time
from datetime import datetime, timezone

sys.path.insert(0, os.environ.get('E103_RIG', '/rig'))
from forward_send import Sender, event_time, pack  # noqa: E402

SHARED_TAG = 'app.replay'
GAP_S = 10
PAUSES = [1, 2, 3, 4, 5, 6] * 2


class TaggedSender(Sender):
    def send(self, rec, tag=SHARED_TAG):
        msg = b'\x93' + pack(tag) + event_time(time.time()) + pack(rec)
        while True:
            try:
                if self.s is None:
                    self.s = socket.create_connection(self.addr, timeout=10)
                self.s.sendall(msg)
                return
            except OSError:
                self.s = None
                time.sleep(1)


def cid(name):
    return hashlib.sha256(name.encode()).hexdigest()


def fill(text, seq):
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    text = (text.replace('{TS}', now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{ms:03d}Z')
                .replace('{KTS}', now.strftime('%Y-%m-%d %H:%M:%S,') + f'{ms:03d}')
                .replace('{EPOCH}', f'{now.timestamp():.7f}'))
    if '{TOK}' in text:
        return text.replace('{TOK}', str(seq))
    return f'{text} e103id={seq}'


def trace(rng, svc, cls, method, msg, cause):
    """A Java ERROR head and its continuation lines (frames, Caused by, ... N more)."""
    f = cls + '.java'
    head = f'{{TS}} ERROR [http-nio-8080-exec-{rng.randint(1, 40)}] c.e.{svc}.{cls} - {msg}'
    frames = [f'\tat com.example.{svc}.{cls}.{method}({f}:{rng.randint(20, 400)})',
              f'\tat com.example.{svc}.{cls}Controller.handle({cls}Controller.java:{rng.randint(20, 200)})',
              f'\tat org.springframework.web.servlet.FrameworkServlet.service(FrameworkServlet.java:{rng.randint(800, 900)})',
              f'\tat jakarta.servlet.http.HttpServlet.service(HttpServlet.java:{rng.randint(500, 700)})',
              f'Caused by: {cause}',
              f'\tat com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:{rng.randint(150, 200)})',
              f'\tat com.example.{svc}.{cls}Repository.load({cls}Repository.java:{rng.randint(30, 90)})',
              f'\t... {rng.randint(20, 60)} more']
    n = rng.randint(3, 8)
    return head, frames[:n]


def orders_trace(rng):
    return trace(rng, 'orders', 'OrderService', 'place', f'Failed to place order {rng.randint(10000, 99999)}',
                 'java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms.')


def payments_trace(rng):
    return trace(rng, 'payments', 'ChargeService', 'charge', f'Charge declined for card ending {rng.randint(1000, 9999)}',
                 'java.net.SocketTimeoutException: Read timed out')


JAEGER = ('{"level":"info","ts":{EPOCH},"caller":"grpc@v1.60.0/clientconn.go:532",'
          '"msg":"[core][Channel #1] Channel Connectivity change to READY","system":"grpc","grpc_log":true,"e103id":"{TOK}"}')
KAFKA_BANNER = ['===> User', 'uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)',
                '===> Setting default values of environment variables if not already set.', '===> Configuring ...']


def episode(case, pattern, rng):
    """Steps in send order: ('line', container, event, kind, role, text) or ('pause',)."""
    c = lambda n: f'{case}-{n}'
    if pattern == 'a':
        head, conts = orders_trace(rng)
        s = [('line', c('orders'), 'A', 'trace', 'head', head), ('pause',)]
        for k in range(rng.randint(1, 3)):
            s.append(('line', c('billing'), f'B{k}', 'single', 'head',
                      f'{{TS}} INFO [scheduling-1] c.e.billing.InvoiceJob - Posted invoice INV-{rng.randint(100000, 999999)} amount={rng.randint(5, 900)}.{rng.randint(10, 99)}'))
        s += [('line', c('orders'), 'A', 'trace', 'cont', t) for t in conts]
        return s
    if pattern == 'b':
        s = [('line', c('jaeger'), 'A', 'single', 'head', JAEGER), ('pause',)]
        s += [('line', c('kafka'), 'Bbanner', 'banner', 'cont', t) for t in KAFKA_BANNER]
        s.append(('line', c('kafka'), 'B', 'single', 'head',
                  f'[{{KTS}}] INFO [KafkaRaftServer nodeId=1] Kafka Server started (kafka.server.KafkaRaftServer)'))
        return s
    if pattern == 'c':
        ah, ac = orders_trace(rng)
        bh, bc = payments_trace(rng)
        s = [('line', c('orders'), 'A', 'trace', 'head', ah)]
        s += [('line', c('orders'), 'A', 'trace', 'cont', t) for t in ac[:2]]
        s.append(('pause',))
        s.append(('line', c('payments'), 'B', 'trace', 'head', bh))
        ra, rb = ac[2:], list(bc)
        while ra or rb:
            if rb:
                s.append(('line', c('payments'), 'B', 'trace', 'cont', rb.pop(0)))
            if ra:
                s.append(('line', c('orders'), 'A', 'trace', 'cont', ra.pop(0)))
        return s
    if pattern == 'd':
        head, conts = orders_trace(rng)
        s = [('line', c('orders'), 'A', 'trace', 'head', head), ('pause',)]
        s += [('line', c('orders'), 'A', 'trace', 'cont', t) for t in conts]
        for k in range(rng.randint(0, 2)):
            s.append(('line', c('orders'), f'I{k}', 'single', 'head',
                      f'{{TS}} INFO [http-nio-8080-exec-{rng.randint(1, 40)}] c.e.orders.OrderService - Order {rng.randint(10000, 99999)} placed in {rng.randint(3, 300)} ms'))
        return s
    raise ValueError(pattern)


def main():
    host, port, manifest = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    cases = sys.argv[4] if len(sys.argv) > 4 else 'abcde'
    n_ep = int(sys.argv[5]) if len(sys.argv) > 5 else 500
    rng = random.Random(103)
    out = TaggedSender(host, port)
    seq = 0
    with open(manifest, 'w') as m:
        for ci, case in enumerate(cases):
            if ci:
                time.sleep(GAP_S)
            pauses = list(PAUSES)
            rng.shuffle(pauses)
            every = max(1, n_ep // len(pauses))
            plan = []
            for i in range(n_ep):
                plan.append(0)
                if pauses and i % every == every // 2:
                    plan.append(pauses.pop())
            plan += pauses
            t0, lines0 = time.time(), seq
            for ep, pause in enumerate(plan):
                pattern = 'abc'[ep % 3] if case == 'e' else case
                for st in episode(case, pattern, rng):
                    if st[0] == 'pause':
                        if pause:
                            time.sleep(pause)
                        continue
                    _, cont, ev, kind, role, text = st
                    seq += 1
                    line = fill(text, seq)
                    tag = 'docker.' + cid(cont)[:12] if case == 'e' else SHARED_TAG
                    out.send({'container_name': '/' + cont, 'container_id': cid(cont), 'source': 'stdout', 'log': line, 'seq': seq}, tag)
                    m.write(json.dumps({'seq': seq, 'case': case, 'ep': ep, 'pause': pause, 'pattern': pattern, 'tag': tag, 'container': cont,
                                        'event': f'{case}{ep}{ev}', 'kind': kind, 'role': role, 't': round(time.time(), 6), 'line': line}) + '\n')
                time.sleep(0.001)
            print(json.dumps({'case': case, 'episodes': len(plan), 'lines': seq - lines0, 'seconds': round(time.time() - t0, 1)}), flush=True)
    if out.s is not None:
        out.s.close()
    print(json.dumps({'final_seq': seq}), flush=True)


if __name__ == '__main__':
    main()
