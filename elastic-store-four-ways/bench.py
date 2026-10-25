#!/usr/bin/env python3
"""
Elasticsearch store size, four ways, on one sample. Called by run.sh; Python 3 standard library only.

  bench.py compact-record --sample S --enc1 DIR --enc2 DIR --decoded F --image DIGEST --encode-config C --decode-config C --out F
  bench.py licence --es-image DIGEST --out F
  bench.py measure --rep N --sample S --compact-dir DIR --results DIR [--variants raw,logsdb,pattern,compact]
  bench.py report --results DIR

Elasticsearch is reached at $ES4_URL (default http://127.0.0.1:9205). METHOD.md states what each
variant is and why; the index definitions below are the only place they are written down.
"""
import argparse
import datetime
import filecmp
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ES = os.environ.get('ES4_URL', 'http://127.0.0.1:9205')
LINES_PER_SECOND = 7          # the pace the Elastic rigs replay this capture at; sets the synthetic @timestamp
BASE = datetime.datetime(2025, 10, 2, tzinfo=datetime.timezone.utc)
BATCH_DOCS = 2000
LEASE_WAIT_S = 180

COMMON = {'number_of_shards': 1, 'number_of_replicas': 0, 'codec': 'best_compression', 'refresh_interval': '-1'}
# Every string in the record other than message is a keyword, in all three native variants alike.
STRINGS_AS_KEYWORD = [{'strings_as_keyword': {'match_mapping_type': 'string',
                                              'mapping': {'type': 'keyword', 'ignore_above': 1024}}}]


def record_mapping(message_type):
    return {'dynamic_templates': STRINGS_AS_KEYWORD,
            'properties': {'@timestamp': {'type': 'date'}, 'message': {'type': message_type}}}


COMPACT_MAPPING = {'dynamic': 'strict', 'properties': {
    '@timestamp': {'type': 'date'}, 'message': {'type': 'text'}, 'l1x_tid': {'type': 'keyword'}}}
# The l1es plugin's own template index mapping (DmlConsts.DML_INDEX_MAPPING), _id = template hash.
DICT_MAPPING = {'dynamic': False, 'properties': {'pattern': {'type': 'text'}}}

INDEXES = {
    'es4-raw': {'settings': {'index': COMMON}, 'mappings': record_mapping('text')},
    'es4-logsdb': {'settings': {'index': {**COMMON, 'mode': 'logsdb'}}, 'mappings': record_mapping('text')},
    'es4-pattern': {'settings': {'index': {**COMMON, 'mode': 'logsdb',
                                           'logsdb.default_sort_on_message_template': True}},
                    'mappings': record_mapping('pattern_text')},
    'es4-compact': {'settings': {'index': COMMON}, 'mappings': COMPACT_MAPPING},
    'es4-compact-logsdb': {'settings': {'index': {**COMMON, 'mode': 'logsdb'}}, 'mappings': COMPACT_MAPPING},
    'es4-compact-dict': {'settings': {'index': COMMON}, 'mappings': DICT_MAPPING},
}
# variant -> (indexes whose store adds up to it, what is loaded into the first)
VARIANTS = {
    'raw': (['es4-raw'], 'records'),
    'logsdb': (['es4-logsdb'], 'records'),
    'pattern': (['es4-pattern'], 'records'),
    'compact': (['es4-compact', 'es4-compact-dict'], 'compact'),
    'compact_logsdb': (['es4-compact-logsdb', 'es4-compact-dict'], 'compact'),   # not in the default run
}
DEFAULT_VARIANTS = ['raw', 'logsdb', 'pattern', 'compact']
SETTING_KEYS = ['index.mode', 'index.codec', 'index.mapping.source.mode', 'index.sort.field', 'index.sort.order',
                'index.logsdb.default_sort_on_message_template', 'index.recovery.use_synthetic_source',
                'index.number_of_shards', 'index.number_of_replicas']


# ---------------------------------------------------------------- Elasticsearch
def call(method, path, body=None, ndjson=False, timeout=600):
    data, headers = None, {}
    if body is not None:
        if ndjson:
            data, headers['content-type'] = body, 'application/x-ndjson'
        else:
            data, headers['content-type'] = json.dumps(body).encode(), 'application/json'
    req = urllib.request.Request(ES + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode('utf-8', 'replace')


def ok(method, path, body=None, **kw):
    status, resp = call(method, path, body, **kw)
    if status >= 300:
        raise SystemExit(f'{method} {path} -> {status}: {json.dumps(resp)[:1200]}')
    return resp


def effective_settings(index):
    r = ok('GET', f'/{index}/_settings?include_defaults=true&flat_settings=true')[index]
    merged = {**r.get('defaults', {}), **r.get('settings', {})}
    return {k: merged.get(k) for k in SETTING_KEYS}


# ---------------------------------------------------------------- documents
def iso(ms):
    return (BASE + datetime.timedelta(milliseconds=ms)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def record_docs(sample):
    """One document per line: the Fluentd record as captured, `log` renamed `message`, plus @timestamp."""
    with open(sample, 'rb') as f:
        for i, line in enumerate(f):
            rec = json.loads(line)
            doc = {'@timestamp': iso(i * 1000 // LINES_PER_SECOND)}
            for k, v in rec.items():
                doc['message' if k == 'log' else k] = v
            yield doc


def compact_docs(encoded, n_lines, n_events):
    """One document per encoded event; @timestamps spread over the same span as the lines'."""
    with open(encoded, 'rb') as f:
        for j, line in enumerate(f):
            text = line.rstrip(b'\n').decode('utf-8')
            doc = {'@timestamp': iso(j * n_lines * 1000 // (LINES_PER_SECOND * n_events)), 'message': text}
            if text.startswith('~'):
                doc['l1x_tid'] = text[1:].split(',', 1)[0]
            yield doc


def dict_docs(templates):
    with open(templates, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                yield obj['templateHash'], {'pattern': obj['template']}


def bulk(index, docs, with_id=False):
    n, buf = 0, []

    def flush():
        resp = ok('POST', f'/{index}/_bulk', ''.join(buf).encode('utf-8'), ndjson=True, timeout=900)
        if resp.get('errors'):
            first = next(it for it in resp['items'] if 'error' in next(iter(it.values())))
            raise SystemExit(f'{index}: bulk error {json.dumps(first)[:1200]}')
        buf.clear()

    for item in docs:
        if with_id:
            _id, doc = item
            buf.append(json.dumps({'index': {'_id': _id}}) + '\n')
        else:
            doc = item
            buf.append('{"index":{}}\n')
        buf.append(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n')
        n += 1
        if n % BATCH_DOCS == 0:
            flush()
    if buf:
        flush()
    return n


# ---------------------------------------------------------------- files
def lines_and_bytes(path):
    n, size, last = 0, 0, b'\n'
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            n += chunk.count(b'\n')
            size += len(chunk)
            last = chunk[-1:]
    return n + (1 if size and last != b'\n' else 0), size


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, obj):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1)
        f.write('\n')


# ---------------------------------------------------------------- subcommands
def cmd_compact_record(a):
    sample_lines, sample_bytes = lines_and_bytes(a.sample)
    r = {'engine_image': a.image, 'encode_config_sha256': sha256(a.encode_config),
         'decode_config_sha256': sha256(a.decode_config), 'sample_bytes': sample_bytes,
         'sample_lines': sample_lines, 'sample_sha256': sha256(a.sample)}
    for key, d in (('encode1', a.enc1), ('encode2', a.enc2)):
        d = pathlib.Path(d)
        ev, eb = lines_and_bytes(d / 'encoded.log')
        tn, tb = lines_and_bytes(d / 'templates.json')
        r[key] = {'events': ev, 'encoded_bytes': eb, 'templates': tn, 'templates_bytes': tb,
                  'sha256_encoded': sha256(d / 'encoded.log'), 'sha256_templates': sha256(d / 'templates.json')}
    e1, e2 = r['encode1'], r['encode2']
    r['encodes_identical'] = (e1['sha256_encoded'], e1['sha256_templates']) == (e2['sha256_encoded'], e2['sha256_templates'])
    r['compact_bytes'] = e1['encoded_bytes'] + e1['templates_bytes']
    r['reduction_before_codec_pct'] = round((1 - r['compact_bytes'] / sample_bytes) * 100, 2)
    dl, db = lines_and_bytes(a.decoded)
    r['decoded_bytes'], r['decoded_lines'] = db, dl
    r['roundtrip'] = 'BYTE-IDENTICAL' if filecmp.cmp(a.sample, a.decoded, shallow=False) else 'DIFFERS'
    dump(a.out, r)
    print(f"compact form: {e1['events']:,} events, {e1['templates']:,} templates, {r['compact_bytes']:,} B "
          f"({r['reduction_before_codec_pct']}% under the sample, no codec); decode {r['roundtrip']}; "
          f"two encodes identical: {r['encodes_identical']}")
    return 0


def cmd_licence(a):
    log = {'es_image': a.es_image}
    v = ok('GET', '/')
    log['version'] = {'number': v['version']['number'], 'build_hash': v['version'].get('build_hash'),
                      'lucene_version': v['version'].get('lucene_version')}
    lic_keys = ('type', 'status', 'issuer', 'max_nodes', 'issue_date', 'expiry_date')
    log['licence_before'] = {k: ok('GET', '/_license')['license'].get(k) for k in lic_keys}
    # pattern_text under the licence a new self-managed cluster starts on, before the trial
    probe = 'es4-probe-basic'
    call('DELETE', f'/{probe}')
    st, resp = call('PUT', f'/{probe}', {'settings': {'index': {**COMMON, 'mode': 'logsdb'}},
                                         'mappings': record_mapping('pattern_text')})
    p = {'create_status': st, 'create_response': resp}
    if st < 300:
        st2, resp2 = call('POST', f'/{probe}/_doc?refresh=true',
                          {'@timestamp': iso(0), 'message': 'probe user=1 took 5 ms'})
        p.update(index_status=st2, index_response=resp2, settings=effective_settings(probe),
                 mapping=ok('GET', f'/{probe}/_mapping'))
        call('DELETE', f'/{probe}')
    log['pattern_text_before_trial'] = p
    log['start_trial'] = call('POST', '/_license/start_trial?acknowledge=true')
    lic = ok('GET', '/_license')['license']
    log['licence_after'] = {k: lic.get(k) for k in lic_keys}
    dump(a.out, log)
    print(f"Elasticsearch {log['version']['number']}; before: {log['licence_before']['type']}, pattern_text "
          f"create {st}; after start_trial: {lic.get('type')} {lic.get('status')}")
    if lic.get('type') != 'trial' or lic.get('status') != 'active':
        raise SystemExit('the trial licence is not active; pattern_text and synthetic source need it')
    return 0


def leases_caught_up(index):
    s = ok('GET', f'/{index}/_stats?level=shards')['indices'][index]['shards']['0'][0]
    seq = s['seq_no']
    leases = s.get('retention_leases', {}).get('leases', [])
    done = all(le['retaining_seq_no'] > seq['max_seq_no'] for le in leases)
    return done, {'seq_no': seq, 'leases': [{'id': le['id'], 'retaining_seq_no': le['retaining_seq_no']} for le in leases]}


def cmd_measure(a):
    variants = a.variants.split(',')
    unknown = [v for v in variants if v not in VARIANTS]
    if unknown:
        raise SystemExit(f'unknown variant(s) {unknown}; known: {list(VARIANTS)}')
    indexes = []
    for v in variants:
        for ix in VARIANTS[v][0]:
            if ix not in indexes:
                indexes.append(ix)
    results = pathlib.Path(a.results)
    out_dir = results / f'rep{a.rep}'
    compact_dir = pathlib.Path(a.compact_dir)
    n_lines, _ = lines_and_bytes(a.sample)
    n_events, _ = lines_and_bytes(compact_dir / 'encoded.log')
    hashes = [h for h, _ in dict_docs(compact_dir / 'templates.json')]
    n_templates = len(set(hashes))   # one document per hash: _id is the hash
    expected = {'es4-raw': n_lines, 'es4-logsdb': n_lines, 'es4-pattern': n_lines, 'es4-compact': n_events,
                'es4-compact-logsdb': n_events, 'es4-compact-dict': n_templates}

    rep = {'rep': a.rep, 'es_url': ES, 'variants': variants, 'indexes': {},
           'inputs': {'lines': n_lines, 'events': n_events, 'template_lines': len(hashes), 'template_hashes': n_templates}}
    for ix in indexes:
        call('DELETE', f'/{ix}')
        ok('PUT', f'/{ix}', INDEXES[ix])
    for ix in indexes:
        t0 = time.time()
        if ix == 'es4-compact-dict':
            n = bulk(ix, dict_docs(compact_dir / 'templates.json'), with_id=True)
        elif ix.startswith('es4-compact'):
            n = bulk(ix, compact_docs(compact_dir / 'encoded.log', n_lines, n_events))
        else:
            n = bulk(ix, record_docs(a.sample))
        rep['indexes'][ix] = {'sent': n, 'expected': expected[ix], 'load_s': round(time.time() - t0, 1),
                              'definition': INDEXES[ix]}
        print(f'  {ix}: {n:,} documents sent in {time.time() - t0:.0f}s', flush=True)
    for ix in indexes:
        ok('POST', f'/{ix}/_refresh')
        ok('POST', f'/{ix}/_flush')
    # Synthetic-source indexes keep _recovery_source for operations a retention lease still covers, and a
    # merge keeps what it covers. Wait until every lease has moved past the last operation before merging.
    deadline = time.time() + LEASE_WAIT_S
    while True:
        states = {ix: leases_caught_up(ix) for ix in indexes}
        if all(s[0] for s in states.values()) or time.time() > deadline:
            break
        time.sleep(5)
    for ix in indexes:
        rep['indexes'][ix]['before_merge'] = {'leases_past_last_op': states[ix][0], **states[ix][1]}
    for ix in indexes:
        r = rep['indexes'][ix]
        t0 = time.time()
        ok('POST', f'/{ix}/_forcemerge?max_num_segments=1', timeout=3600)
        r['forcemerge_s'] = round(time.time() - t0, 1)
        ok('POST', f'/{ix}/_refresh')
        reads = []
        for _ in range(2):
            st = ok('GET', f'/{ix}/_stats/store,docs')['indices'][ix]['primaries']
            reads.append({'store_bytes': st['store']['size_in_bytes'], 'docs': st['docs']['count'],
                          'deleted': st['docs']['deleted']})
            time.sleep(5)
        r['stats_reads'] = reads
        r['store_bytes'] = reads[-1]['store_bytes']
        r['docs'] = reads[-1]['docs']
        segs = ok('GET', f'/_cat/segments/{ix}?format=json&bytes=b')
        r['segments'] = len(segs)
        r['settings'] = effective_settings(ix)
        dump(out_dir / f'{ix}.mapping.json', ok('GET', f'/{ix}/_mapping'))
        du = ok('POST', f'/{ix}/_disk_usage?run_expensive_tasks=true', timeout=3600)
        dump(out_dir / f'{ix}.disk_usage.json', du)
        fields = du[ix]['fields']
        r['disk_usage_bytes'] = du[ix].get('store_size_in_bytes')
        r['field_bytes'] = dict(sorted(((k, f['total_in_bytes']) for k, f in fields.items()),
                                       key=lambda kv: -kv[1])[:12])
        r['source_stored_bytes'] = fields.get('_source', {}).get('stored_fields_in_bytes', 0)
        r['recovery_source_stored_bytes'] = fields.get('_recovery_source', {}).get('stored_fields_in_bytes', 0)
        print(f"  {ix}: {r['docs']:,} docs, {r['segments']} segment(s), store {r['store_bytes']:,} B, "
              f"mode {r['settings']['index.mode']}, source {r['settings']['index.mapping.source.mode']}", flush=True)
    rep['variant_store_bytes'] = {v: sum(rep['indexes'][ix]['store_bytes'] for ix in VARIANTS[v][0]) for v in variants}
    dump(results / f'rep{a.rep}.json', rep)
    bad = [ix for ix, r in rep['indexes'].items() if r['docs'] != r['expected'] or r['sent'] != r['expected']]
    if bad:
        raise SystemExit(f'document counts differ from the input in {bad}')
    return 0


def fmt_b(n):
    return f'{n:,} B ({n / 1e6:.2f} MB)'


def cmd_report(a):
    results = pathlib.Path(a.results)
    reps = [json.load(open(p)) for p in sorted(results.glob('rep[0-9]*.json'))]
    if not reps:
        raise SystemExit(f'no rep*.json in {results}')
    compact = json.load(open(results / 'compact.json'))
    lic = json.load(open(results / 'licence.json'))
    variants = reps[0]['variants']
    store = {v: [r['variant_store_bytes'][v] for r in reps] for v in variants}
    mean = {v: sum(s) / len(s) for v, s in store.items()}
    spread = {v: (max(s) - min(s)) / mean[v] for v, s in store.items()}
    idx0 = reps[0]['indexes']

    checks = []

    def check(name, passed, detail=''):
        checks.append({'check': name, 'pass': bool(passed), 'detail': detail})

    check('trial licence active', lic['licence_after']['type'] == 'trial' and lic['licence_after']['status'] == 'active',
          f"{lic['licence_after']['type']} {lic['licence_after']['status']}")
    for r in reps:
        for ix, x in r['indexes'].items():
            check(f"rep {r['rep']} {ix}: documents equal the input", x['docs'] == x['expected'] == x['sent'],
                  f"{x['docs']:,} indexed, {x['expected']:,} expected")
            check(f"rep {r['rep']} {ix}: one segment", x['segments'] == 1, str(x['segments']))
            check(f"rep {r['rep']} {ix}: best_compression", x['settings']['index.codec'] == 'best_compression',
                  str(x['settings']['index.codec']))
            if x['settings']['index.mode'] == 'logsdb':
                check(f"rep {r['rep']} {ix}: synthetic source", x['source_stored_bytes'] == 0,
                      f"_source stored {x['source_stored_bytes']:,} B, mode setting {x['settings']['index.mapping.source.mode']}")
                check(f"rep {r['rep']} {ix}: no _recovery_source left", x['recovery_source_stored_bytes'] == 0,
                      f"{x['recovery_source_stored_bytes']:,} B")
    check('two encodes byte-identical', compact['encodes_identical'])
    check('compact form decodes to the sample byte for byte', compact['roundtrip'] == 'BYTE-IDENTICAL', compact['roundtrip'])
    check('repetitions agree within 1%', all(s <= 0.01 for s in spread.values()),
          ', '.join(f'{v} {s * 100:.2f}%' for v, s in spread.items()))

    ratios = {}
    if 'raw' in mean:
        ratios['of_raw'] = {v: mean[v] / mean['raw'] for v in variants}
    for c in ('compact', 'compact_logsdb'):
        if c in mean:
            ratios[f'{c}_against'] = {v: {'saving_pct': (1 - mean[c] / mean[v]) * 100, 'times_smaller': mean[v] / mean[c]}
                                      for v in variants if not v.startswith('compact')}
    out = {'es': lic['version'], 'es_image': lic['es_image'], 'licence': lic['licence_after'],
           'engine_image': compact['engine_image'], 'compact_form': {k: compact[k] for k in (
               'compact_bytes', 'reduction_before_codec_pct', 'roundtrip', 'encodes_identical')},
           'events': compact['encode1']['events'], 'templates': compact['encode1']['templates'],
           'sample': {'bytes': compact['sample_bytes'], 'lines': compact['sample_lines'], 'sha256': compact['sample_sha256']},
           'store_bytes': store, 'store_bytes_mean': mean, 'rep_spread': spread, 'ratios': ratios, 'checks': checks}
    dump(results / 'results.json', out)

    label = {'raw': ('standard', '`text`'), 'logsdb': ('logsdb', '`text`'),
             'pattern': ('logsdb, sorted on `message.template_id`', '`pattern_text`'),
             'compact': ('standard', 'encoded event, `text`, plus `l1x_tid` and the dictionary index'),
             'compact_logsdb': ('logsdb', 'encoded event, `text`, plus `l1x_tid` and the dictionary index')}
    md = ['# Elasticsearch store, four ways: results', '',
          f"- Elasticsearch {lic['version']['number']} (Lucene {lic['version']['lucene_version']}), `{lic['es_image']}`, "
          f"licence `{lic['licence_after']['type']}` `{lic['licence_after']['status']}`",
          f"- engine `{compact['engine_image']}`",
          f"- sample `otel-sample-200mb.log`: {compact['sample_bytes']:,} B, {compact['sample_lines']:,} lines, "
          f"sha256 `{compact['sample_sha256']}`",
          f"- compact form: {compact['encode1']['events']:,} events and {compact['encode1']['templates']:,} templates, "
          f"{compact['encode1']['encoded_bytes']:,} B encoded + {compact['encode1']['templates_bytes']:,} B dictionary = "
          f"{compact['compact_bytes']:,} B, {compact['reduction_before_codec_pct']}% under the sample before any codec; "
          f"decode {compact['roundtrip']}", '',
          '| Variant | Index mode | `message` | Documents | ' + ' | '.join(f'Store, rep {r["rep"]}' for r in reps) + ' | Of raw |',
          '|---|---|---|---:|' + '---:|' * len(reps) + '---:|']
    for v in variants:
        docs = ' + '.join(f"{idx0[ix]['docs']:,}" for ix in VARIANTS[v][0])
        of_raw = f"{ratios['of_raw'][v] * 100:.1f}%" if 'of_raw' in ratios else ''
        md.append(f'| {v} | {label[v][0]} | {label[v][1]} | {docs} | ' +
                  ' | '.join(f'{s:,} B' for s in store[v]) + f' | {of_raw} |')
    for c in ('compact', 'compact_logsdb'):
        if f'{c}_against' in ratios:
            md += ['', f'The {c} variant against each native one (mean of the repetitions):', '',
                   '| Against | Its store | Compact store | Compact saves | Times smaller |', '|---|---:|---:|---:|---:|']
            for v, x in ratios[f'{c}_against'].items():
                md.append(f"| {v} | {mean[v]:,.0f} B | {mean[c]:,.0f} B | {x['saving_pct']:.1f}% | {x['times_smaller']:.2f}x |")
    md += ['', '## Checks', '']
    md += [f"- {'pass' if c['pass'] else 'FAIL'}: {c['check']}" + (f" ({c['detail']})" if c['detail'] else '') for c in checks]
    md += ['', 'Per-index detail (settings, leases before the merge, per-field bytes) is in `rep<N>.json`; '
           'each index\'s mapping and `_disk_usage` output are in `rep<N>/`.', '']
    (results / 'results.md').write_text('\n'.join(md))
    print('\n'.join(md))
    return 0 if all(c['pass'] for c in checks) else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('compact-record')
    for k in ('--sample', '--enc1', '--enc2', '--decoded', '--image', '--encode-config', '--decode-config', '--out'):
        p.add_argument(k, required=True)
    p = sub.add_parser('licence')
    p.add_argument('--es-image', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('measure')
    p.add_argument('--rep', type=int, required=True)
    p.add_argument('--sample', required=True)
    p.add_argument('--compact-dir', required=True)
    p.add_argument('--results', required=True)
    p.add_argument('--variants', default=','.join(DEFAULT_VARIANTS))
    p = sub.add_parser('report')
    p.add_argument('--results', required=True)
    a = ap.parse_args()
    return {'compact-record': cmd_compact_record, 'licence': cmd_licence, 'measure': cmd_measure,
            'report': cmd_report}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
