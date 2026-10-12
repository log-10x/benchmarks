#!/usr/bin/env python3
"""
Count one corpus's input and the engine's compact output, and record them.

  measure.py --corpus NAME --input-dir DIR --members GLOB --out-dir OUT --result results/NAME.json

Input bytes and lines are summed over the files the engine read. Compact bytes are
encoded.log plus templates.json, the encoded events and the template dictionary, before any
codec. Events are encoded.log's lines and templates are templates.json's lines. Both output
files are hashed, so a rerun can be compared byte for byte.
"""
import argparse
import hashlib
import json
import pathlib


def lines_and_bytes(path: pathlib.Path):
    n, size, last = 0, 0, b'\n'
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            n += chunk.count(b'\n')
            size += len(chunk)
            last = chunk[-1:]
    return n + (1 if size and last != b'\n' else 0), size


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--members', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--result', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--image', required=True)
    a = ap.parse_args()
    # The engine walks the input directory recursively and matches each file's name.
    files = sorted(p for p in pathlib.Path(a.input_dir).rglob(a.members) if p.is_file())
    if not files:
        raise SystemExit(f'{a.corpus}: no input files match {a.members}')
    raw_lines = input_bytes = 0
    for p in files:
        n, b = lines_and_bytes(p)
        raw_lines += n
        input_bytes += b
    out = pathlib.Path(a.out_dir)
    enc, tpl = out / 'encoded.log', out / 'templates.json'
    events, enc_bytes = lines_and_bytes(enc)
    templates, tpl_bytes = lines_and_bytes(tpl)
    result = {
        'corpus': a.corpus,
        'source': a.source,
        'image': a.image,
        'input_files': len(files),
        'raw_lines': raw_lines,
        'input_bytes': input_bytes,
        'events': events,
        'encoded_bytes': enc_bytes,
        'templates_bytes': tpl_bytes,
        'templates': templates,
        'sha256_encoded': sha256(enc),
        'sha256_templates': sha256(tpl),
    }
    json.dump(result, open(a.result, 'w'), indent=1)
    compact = enc_bytes + tpl_bytes
    print(f'{a.corpus}: {len(files)} files, {raw_lines:,} lines, {input_bytes:,} B -> {events:,} events, '
          f'{compact:,} B compact ({(1 - compact / input_bytes) * 100:.1f}%), {templates:,} templates')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
