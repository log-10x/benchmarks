#!/usr/bin/env python3
"""Gate for the Elastic budget run: does the engine's Elastic metric output, installed the way
log10x-mcp renders it (BACKENDS=elastic), count what two Receivers returned?

  gate-metrics.py up <values dir> <results dir>   writes compose.gate.yaml and two Fluent Bit
                                                   configs, starts both pairs
  gate-metrics.py check <results dir>              compares the metric documents with the captures

Two pairs (fluent-bit-a + tenx-a, fluent-bit-b + tenx-b), each fed its own half of the replay, so
both Receivers post the same statements from the same containers into one index. The Fluent Bit
configs keep the local captures only; no events go to Elasticsearch.
Substituted for the rig: ELASTICSEARCH_HOST (the MCP renders a placeholder) and ELASTIC_API_KEY (a
Secret in the install; security is off on the rig, so any value is accepted)."""
import collections, glob, json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ES = os.environ.get('ES_URL', 'http://127.0.0.1:9200')


def up(values, out):
    os.makedirs(out, exist_ok=True)
    src = open(os.path.join(values, 'compose.receiver.yaml')).read()
    body = src.split('  tenx:\n', 1)[1]
    services = []
    for side, ip in (('a', '172.29.0.250'), ('b', '172.29.0.251')):
        conf_dir = os.path.join(out, f'fluent-bit-{side}')
        os.makedirs(conf_dir, exist_ok=True)
        conf = open(os.path.join(HERE, 'fluent-bit', 'fluent-bit.conf')).read()
        conf = conf.split('[OUTPUT]\n    Name               es')[0]  # captures only
        conf = conf.replace('    Host                        tenx\n', f'    Host                        tenx-{side}\n')
        open(os.path.join(conf_dir, 'fluent-bit.conf'), 'w').write(conf)
        open(os.path.join(conf_dir, 'rig.lua'), 'w').write(open(os.path.join(HERE, 'fluent-bit', 'rig.lua')).read())
        os.makedirs(os.path.join(out, f'data-{side}'), exist_ok=True)
        b = body.replace('container_name: rig-tenx', f'container_name: rig-tenx-{side}')
        b = b.replace('"TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit"', f'"TENX_FLUENTBIT_OUTPUT_HOST=fluent-bit-{side}"')
        b = re.sub(r'"ELASTICSEARCH_HOST=[^"]*"', '"ELASTICSEARCH_HOST=http://es-hot:9200"', b)
        b = b.replace('    environment:\n', '    environment:\n      - "ELASTIC_API_KEY=cmlnOnJpZw=="\n', 1)
        b = b.replace('${RIG_DIR}/policy', f'{HERE}/policy')
        services.append(f'  tenx-{side}:\n' + b)
        services.append(
            f'  fluent-bit-{side}:\n'
            f'    image: fluent/fluent-bit:4.2\n'
            f'    container_name: rig-fluent-bit-{side}\n'
            f'    command: ["/fluent-bit/bin/fluent-bit", "-c", "/fluent-bit/etc/rig/fluent-bit.conf"]\n'
            f'    networks:\n      default:\n        ipv4_address: {ip}\n'
            f'    volumes:\n      - {conf_dir}:/fluent-bit/etc/rig:ro\n      - {out}/data-{side}:/data\n'
            f'    restart: unless-stopped\n')
    y = 'services:\n' + '\n'.join(services)
    path = os.path.join(out, 'compose.gate.yaml')
    open(path, 'w').write(y)
    print(path)


def get(path, body=None):
    req = urllib.request.Request(ES + path, data=json.dumps(body).encode() if body else None,
                                 headers={'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def records(out, name):
    for p in glob.glob(os.path.join(out, 'data-*', name + '.jsonl')):
        for line in open(p, errors='replace'):
            try:
                yield json.loads(line)
            except ValueError:
                pass


def check(out):
    get('/tenx-metrics*/_refresh', {}) if False else None
    sample = get('/tenx-metrics*/_search?size=3&sort=@timestamp:desc')
    hits = sample['hits']['hits']
    report = {'index_docs': sample['hits']['total'], 'sample_docs': [h['_source'] for h in hits], 'indices': get('/_cat/indices/tenx-metrics*?format=json&bytes=b')}
    names = get('/tenx-metrics*/_search?size=0', {'aggs': {'n': {'terms': {'field': 'name.keyword' if True else 'name', 'size': 50}}}})
    report['names'] = names.get('aggregations', {}).get('n', {}).get('buckets')
    json.dump(report, open(os.path.join(out, 'gate-raw.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if k != 'sample_docs'}, indent=1, default=str)[:3000])
    print(json.dumps(report['sample_docs'], indent=1, default=str)[:4000])
    # local truth: returned records by route and by (container, pattern)
    local = collections.Counter()
    local_bytes = collections.Counter()
    by_route = collections.Counter()
    for name, route in (('pass', 'pass'), ('tier_down', 'tier_down')):
        for r in records(out, name):
            if 'fb_ts' not in r:
                continue
            c = (r.get('kubernetes') or {}).get('container_name') or ''
            local[(c, r.get('message_pattern') or '')] += 1
            local_bytes[(c, r.get('message_pattern') or '')] += len((r.get('log') or '').encode())
            by_route[route] += 1
    json.dump({'by_route': by_route, 'statements': len(local), 'records': sum(local.values()), 'message_bytes': sum(local_bytes.values()),
               'top': [[list(k), local[k], local_bytes[k]] for k, _ in local.most_common(15)]},
              open(os.path.join(out, 'gate-local.json'), 'w'), indent=1)
    print('local by route', dict(by_route), 'records', sum(local.values()), 'statements', len(local), 'message bytes', sum(local_bytes.values()))


if __name__ == '__main__':
    if sys.argv[1] == 'up':
        up(os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]))
    else:
        check(os.path.abspath(sys.argv[2]))
