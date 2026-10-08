#!/usr/bin/env python3
"""Prepare the Jedan-Dva Kung-Fu raster asset pack for the game.

Input : the extracted ZIP folder (jdkf_complete_assets_v1/)
Output: jedan-dva-kung-fu/assets/  (game-ready files)
        jedan-dva-kung-fu/assets/manifest.json

What it does
- Fighter frames (1024x683, anchor 320,640, 2x game scale): crops each frame to
  its alpha bounding box, removes detached "ghost limbs" (stray fists/feet) left over
  from the generator, stores the crop offset relative to the anchor and saves WebP.
- Everything else is copied as PNG (backgrounds are converted to WebP).
- Adds a soft ground shadow (fx/shadow.png), the one helper sprite the pack did
  not contain, so the engine no longer has to draw an ellipse.

Usage: python3 prepare_assets.py <pack_dir> <out_dir>
"""
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FIGHTERS = ['saner', 'levat', 'bajo', 'mujo', 'zumbul', 'ero', 'ciro', 'mrkonja']
ANCHOR = (320, 640)
WEAPON_FIGHTERS = ('mujo', 'zumbul', 'ciro', 'mrkonja')
WEBP_Q = 88


def clean_fragments(im, fid):
    """Drop small alpha islands (stray fists/feet the generator left behind)."""
    a = np.array(im.getchannel('A'))
    step = 3
    m = a[::step, ::step] > 24
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    sizes = [0]
    cur = 0
    for y in range(h):
        row = m[y]
        for x in range(w):
            if row[x] and not lab[y, x]:
                cur += 1
                n = 0
                q = deque([(y, x)])
                lab[y, x] = cur
                while q:
                    cy, cx = q.popleft()
                    n += 1
                    for ny in (cy - 1, cy, cy + 1):
                        if ny < 0 or ny >= h:
                            continue
                        for nx in (cx - 1, cx, cx + 1):
                            if 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                                lab[ny, nx] = cur
                                q.append((ny, nx))
                sizes.append(n)
    if cur <= 1:
        return im, 0
    total = sum(sizes)
    main_id = int(np.argmax(sizes))
    drop = []
    for i in range(1, cur + 1):
        if i == main_id or sizes[i] >= total * 0.10:   # big detached parts (e.g. Mujo's pole) stay
            continue
        cy, cx = np.nonzero(lab == i)
        cxm, cym = cx.mean() * step, cy.mean() * step
        # weapon / chain pieces sit in front of the fighter at hand height
        if fid in WEAPON_FIGHTERS and cxm > ANCHOR[0] + 60 and cym < 520:
            continue
        # everything else detached is a ghost limb left over from the generator
        drop.append(i)
    if not drop:
        return im, 0
    kill = np.isin(lab, drop)
    kill = np.repeat(np.repeat(kill, step, 0), step, 1)[:a.shape[0], :a.shape[1]]
    # also clear the faint pixels around a dropped island
    a2 = a.copy()
    a2[kill] = 0
    out = im.copy()
    out.putalpha(Image.fromarray(a2))
    return out, len(drop)


def save_webp(im, path, lossless=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, 'WEBP', quality=WEBP_Q, method=6, lossless=lossless, exact=False)


def main(src, out):
    manifest = {'fighters': {}, 'images': {}}
    dropped_report = []

    for fid in FIGHTERS:
        fdir = os.path.join(src, 'fighters', fid)
        frames = {}
        for fn in sorted(os.listdir(fdir)):
            if not fn.endswith('.png') or not fn.startswith(fid + '_') or 'presentation' in fn:
                continue
            name = fn[len(fid) + 1:-4]
            im = Image.open(os.path.join(fdir, fn)).convert('RGBA')
            im, nd = clean_fragments(im, fid)
            if nd:
                dropped_report.append('%s_%s: %d fragment(s)' % (fid, name, nd))
            bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
            crop = im.crop(bb)
            rel = 'fighters/%s/%s.webp' % (fid, name)
            save_webp(crop, os.path.join(out, rel))
            frames[name] = {'src': rel, 'ox': bb[0] - ANCHOR[0], 'oy': bb[1] - ANCHOR[1],
                            'w': crop.width, 'h': crop.height}
        manifest['fighters'][fid] = frames

    # backgrounds -> webp
    for fn in sorted(os.listdir(os.path.join(src, 'backgrounds'))):
        key = 'bg/' + fn[:-4]
        rel = 'backgrounds/' + fn[:-4] + '.webp'
        save_webp(Image.open(os.path.join(src, 'backgrounds', fn)).convert('RGB'),
                  os.path.join(out, rel), lossless=True)
        manifest['images'][key] = rel

    # small sprites: keep PNG (tiny, crisp); skip strips + presentation sheets
    for sub in ['overlays', 'props', 'fx', 'ui/buttons', 'ui/icons', 'ui/hud', 'ui/screens']:
        d = os.path.join(src, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.png') or fn.endswith('_strip.png'):
                continue
            rel = sub + '/' + fn
            os.makedirs(os.path.join(out, sub), exist_ok=True)
            im = Image.open(os.path.join(d, fn))
            if im.width * im.height > 120000:   # logos, hud panel -> webp
                rel = rel[:-4] + '.webp'
                save_webp(im.convert('RGBA'), os.path.join(out, rel))
            else:
                im.save(os.path.join(out, rel), optimize=True)
            manifest['images'][sub.split('/')[-1] + '/' + fn[:-4]] = rel

    # generated helper: soft ground shadow, 2x of 92x20 game px
    sh = Image.new('L', (220, 60), 0)
    ImageDraw.Draw(sh).ellipse((18, 10, 202, 50), fill=200)
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    shadow = Image.new('RGBA', sh.size, (10, 6, 4, 0))
    shadow.putalpha(sh)
    shadow.save(os.path.join(out, 'fx/shadow.png'), optimize=True)
    manifest['images']['fx/shadow'] = 'fx/shadow.png'

    with open(os.path.join(out, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    with open(os.path.join(out, 'CLEANUP_REPORT.txt'), 'w') as fh:
        fh.write('Detached alpha fragments removed from fighter frames:\n')
        fh.write('\n'.join(dropped_report) + '\n')
    print('fighters:', sum(len(v) for v in manifest['fighters'].values()),
          'images:', len(manifest['images']), 'cleaned frames:', len(dropped_report))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
