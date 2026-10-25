#!/usr/bin/env python3
"""Writes <results>/build.json: every image the run uses with its local id and registry digest, the
log10x-mcp checkout (commit, version), and this repository's commit.
  MCP=<log10x-mcp checkout> ENGINE_IMAGE=<image> record-build.py <results dir>"""
import json, os, subprocess, sys

R = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()


images = ['docker.elastic.co/elasticsearch/elasticsearch:9.5.5', 'fluent/fluent-bit:4.2', os.environ.get('ENGINE_IMAGE', ''), 'python:3.12-slim', 'alpine:latest']
out = {'images': {}}
for i in filter(None, images):
    d = json.loads(sh('docker', 'image', 'inspect', i) or '[{}]')[0]
    out['images'][i] = {'id': d.get('Id'), 'repo_digests': d.get('RepoDigests'), 'created': d.get('Created')}
mcp = os.environ['MCP']
out['log10x_mcp'] = {'path': mcp, 'commit': sh('git', '-C', mcp, 'rev-parse', 'HEAD'), 'branch': sh('git', '-C', mcp, 'rev-parse', '--abbrev-ref', 'HEAD'), 'describe': sh('git', '-C', mcp, 'log', '-1', '--format=%h %s'),
                     'version': json.load(open(os.path.join(mcp, 'package.json')))['version'], 'dirty': bool(sh('git', '-C', mcp, 'status', '--porcelain', '--untracked-files=no'))}
out['benchmarks'] = {'commit': sh('git', '-C', HERE, 'rev-parse', 'HEAD'), 'branch': sh('git', '-C', HERE, 'rev-parse', '--abbrev-ref', 'HEAD'),
                     'rig_changes_uncommitted': sh('git', '-C', HERE, 'status', '--porcelain', '--', '.').splitlines()}
json.dump(out, open(os.path.join(R, 'build.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
