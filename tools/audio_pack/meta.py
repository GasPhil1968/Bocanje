"""Append-only registry: every generator records how/why each master file exists."""
import json, os
REG = os.path.join(os.path.dirname(__file__), '..', 'registry')
os.makedirs(REG, exist_ok=True)

def add(batch, **kw):
    with open(os.path.join(REG, batch + '.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + '\n')

def reset(batch):
    p = os.path.join(REG, batch + '.jsonl')
    if os.path.exists(p): os.remove(p)

def load_all():
    out = []
    for fn in sorted(os.listdir(REG)):
        if fn.endswith('.jsonl'):
            for line in open(os.path.join(REG, fn), encoding='utf-8'):
                if line.strip(): out.append(json.loads(line))
    return out

PROC = ('procedural synthesis (original, Python/NumPy/SciPy, written for this pack); '
        'no external samples; licence: produced for the Boce na rivi project, no attribution required')
