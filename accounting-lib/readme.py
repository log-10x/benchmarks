"""
README blocks generated from the results.

A block is the text between `<!-- generated:NAME -->` and `<!-- /generated:NAME -->`. Every
figure a README quotes from a run sits in such a block, so `report.py` writes it from
results.json and `report.py --check` fails when the committed README differs from what the
kept outputs give.
"""
import re

BLOCK = re.compile(r'<!-- generated:([a-z0-9-]+) -->\n(.*?)<!-- /generated:\1 -->', re.S)


def apply(text: str, blocks: dict) -> str:
    """The README with each named block replaced by its rendering."""
    found = {m.group(1) for m in BLOCK.finditer(text)}
    missing = sorted(set(blocks) - found)
    if missing:
        raise SystemExit(f'README.md has no generated block for: {", ".join(missing)}')
    return BLOCK.sub(lambda m: f'<!-- generated:{m.group(1)} -->\n{blocks[m.group(1)].rstrip()}\n<!-- /generated:{m.group(1)} -->'
                     if m.group(1) in blocks else m.group(0), text)


def differing(text: str, blocks: dict) -> list:
    """Names of the blocks whose committed text is not what the results render."""
    committed = {m.group(1): m.group(2).rstrip() for m in BLOCK.finditer(text)}
    return sorted(n for n, body in blocks.items() if committed.get(n) != body.rstrip())
