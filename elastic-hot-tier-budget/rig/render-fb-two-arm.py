#!/usr/bin/env python3
"""Writes the two-arm Fluent Bit config with arm B's service list from top-half.py.
  render-fb-two-arm.py <arm-b-rule.json> <out dir>"""
import json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
rule, out = json.load(open(sys.argv[1])), sys.argv[2]
os.makedirs(out, exist_ok=True)
alt = '|'.join(re.escape(c) for c in rule['top_half'])
conf = open(os.path.join(HERE, 'fluent-bit-two-arm', 'fluent-bit.conf.tmpl')).read().replace('@TOP_HALF@', alt)
open(os.path.join(out, 'fluent-bit.conf'), 'w').write(conf)
shutil.copy(os.path.join(HERE, 'fluent-bit-two-arm', 'rig.lua'), os.path.join(out, 'rig.lua'))
print(alt)
