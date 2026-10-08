#!/usr/bin/env python3
"""Build the single-file, offline game: embeds assets/manifest.json and every
asset as a data URI into src/jedan-dva-kung-fu.html.

Usage: python3 build_single_html.py <game_dir> <out.html>
   e.g. python3 build_single_html.py jedan-dva-kung-fu jedan-dva-kung-fu/jedan-dva-kung-fu-v11.html
"""
import base64
import json
import os
import sys

MIME = {'.png': 'image/png', '.webp': 'image/webp'}


def main(game_dir, out):
    adir = os.path.join(game_dir, 'assets')
    with open(os.path.join(adir, 'manifest.json')) as fh:
        man = json.load(fh)
    rels = list(man['images'].values())
    for frames in man['fighters'].values():
        rels += [d['src'] for d in frames.values()]
    data = {}
    for rel in sorted(set(rels)):
        with open(os.path.join(adir, rel), 'rb') as fh:
            b = base64.b64encode(fh.read()).decode('ascii')
        data[rel] = 'data:%s;base64,%s' % (MIME[os.path.splitext(rel)[1]], b)

    with open(os.path.join(game_dir, 'src', 'jedan-dva-kung-fu.html'), encoding='utf-8') as fh:
        html = fh.read()
    for key, val in (('/*@@MANIFEST@@*/null', json.dumps(man, separators=(',', ':'))),
                     ('/*@@DATA@@*/null', json.dumps(data, separators=(',', ':')))):
        assert html.count(key) == 1, key
        html = html.replace(key, val)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('%s: %d assets, %.1f MB' % (out, len(data), os.path.getsize(out) / 1e6))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
