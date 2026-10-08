"""Povratnik world props: procedural pixel art, 2x chunky, light from upper right."""
import math, random, sys, os
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1]
GOAT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

MAG = (255, 0, 255)
INK = (38, 27, 19)
SHADOW = (52, 40, 28)

def hx(s):
    s = s.lstrip('#'); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

R = {  # ramps dark -> light
 'lime':   [hx(c) for c in ('4f4a42','6e675b','8d8577','aaa293','c4bcab','dcd5c3','eee8d8')],
 'juni':   [hx(c) for c in ('17231a','203322','2b4429','3a5631','4e6a37','6a8442','8a9c52')],
 'berry':  [hx(c) for c in ('2f3754','465473','6a7c9c','9aabc4')],
 'wood':   [hx(c) for c in ('2e1f14','4a3221','654631','80603f','9c7a52','b89768')],
 'oak':    [hx(c) for c in ('3a2818','5a3e26','7a5835','98744a','b49162','ccae80')],
 'hazel':  [hx(c) for c in ('6b5638','8f7a55','b49f74','d2c09a','e8dbbb')],
 'bark':   [hx(c) for c in ('3d3125','5a4a38','76644c')],
 'cloth':  [hx(c) for c in ('8a7e66','aa9e82','c7bb9c','ded3b4','eee6cc')],
 'iron':   [hx(c) for c in ('23262b','3a3f47','56606b','7b8794')],
 'straw':  [hx(c) for c in ('7c6430','a2853f','c6a653','dcc27a')],
 'lichen': [hx(c) for c in ('7a7448','968f5c','b0a676','c2b98e')],
 'stub':   [hx(c) for c in ('6e5a40','9a8160','c2aa82','dccaa2')],
}

def ramp(name, t):
    r = R[name]; t = min(0.999, max(0.0, t)); return r[int(t * len(r))]

class Noise:
    def __init__(self, w, h, cell, seed):
        rnd = random.Random(seed)
        self.cell = cell
        gw, gh = w // cell + 3, h // cell + 3
        self.g = [[rnd.random() for _ in range(gw)] for _ in range(gh)]
    def __call__(self, x, y):
        c = self.cell; fx, fy = x / c, y / c; ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        g = self.g
        a = g[iy][ix] * (1 - tx) + g[iy][ix + 1] * tx
        b = g[iy + 1][ix] * (1 - tx) + g[iy + 1][ix + 1] * tx
        return a * (1 - ty) + b * ty

def layer(w, h): return Image.new('RGBA', (w, h), (0, 0, 0, 0))

def mask_poly(w, h, pts):
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).polygon(pts, fill=255); return m

def fill(img, m, fn):
    px = img.load(); mp = m.load(); w, h = img.size
    for y in range(h):
        for x in range(w):
            if mp[x, y] > 127:
                c = fn(x, y)
                if c: px[x, y] = c + (255,)

def outline(img, col=INK):
    """1 low-res px ink ring around opaque pixels (4-neighbour)."""
    w, h = img.size; src = img.load(); out = img.copy(); o = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0:
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] > 0:
                        o[x, y] = col + (255,); break
    return out

def comp(base, top):
    base.alpha_composite(top); return base

BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
def shadow(img, cx, cy, rx, ry, strength=0.75):
    """Ordered-dither contact shadow, drawn only where img is empty."""
    px = img.load(); w, h = img.size
    for y in range(max(0, int(cy - ry - 1)), min(h, int(cy + ry + 2))):
        for x in range(max(0, int(cx - rx - 1)), min(w, int(cx + rx + 2))):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d >= 1 or px[x, y][3]: continue
            dens = strength * (1 - d) ** 0.8
            if dens * 16 > BAYER[y % 4][x % 4] + 0.5:
                px[x, y] = SHADOW + (255,)

def finish(lo, name, size):
    """2x nearest upscale, crop/pad to exact size (anchored bottom-centre), write magenta + rgba."""
    big = lo.resize((lo.width * 2, lo.height * 2), Image.NEAREST)
    W, H = size
    canvas = layer(W, H)
    canvas.alpha_composite(big, ((W - big.width) // 2, H - big.height)) if big.width <= W and big.height <= H else None
    if big.width > W or big.height > H:
        bx = (big.width - W) // 2; by = big.height - H
        canvas = big.crop((bx, by, bx + W, by + H))
    # hard alpha only
    a = canvas.split()[3].point(lambda v: 255 if v > 127 else 0); canvas.putalpha(a)
    canvas.save(os.path.join(OUT, 'rgba', name + '.png'))
    m = Image.new('RGB', (W, H), MAG); m.paste(canvas, (0, 0), canvas)
    m.save(os.path.join(OUT, 'magenta', name + '.png'))
    return canvas

os.makedirs(os.path.join(OUT, 'rgba'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'magenta'), exist_ok=True)

# ---------------------------------------------------------------- 01 limestone block
def steinblock():
    w, h = 105, 78
    rnd = random.Random(1)
    img = layer(w, h)
    def jag(pts, amt, seed):
        r = random.Random(seed); out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            n = max(2, int(math.dist(a, b) / 4))
            for k in range(n):
                t = k / n
                x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
                if k: x += r.uniform(-amt, amt); y += r.uniform(-amt, amt)
                out.append((x, y))
        return out
    A, B, C, D = (9, 17), (50, 7), (101, 12), (58, 24)
    A2, D2, C2 = (10, 69), (58, 74), (100, 63)
    top = jag([A, B, C, D], 1.3, 2)
    left = jag([A, D, D2, A2], 1.2, 3)
    right = jag([D, C, C2, D2], 1.2, 4)
    big = Noise(w, h, 9, 5); small = Noise(w, h, 3, 6); layers_n = Noise(w, h, 5, 7)
    lich = Noise(w, h, 6, 8)
    # karst fluting: vertical crack positions
    cracks_l = [16, 27, 38, 49]; cracks_r = [66, 76, 88, 95]
    def stone(x, y, base, cracks, slope):
        v = base + (big(x, y) - .5) * .28 + (small(x, y) - .5) * .22
        v += (math.sin((y + x * slope) * 0.9 + layers_n(x, y) * 4) * .05)
        for c in cracks:
            cc = c + (layers_n(x, y) - .5) * 4
            dd = abs(x - cc)
            if dd < .8: v -= .38
            elif dd < 1.6: v += .07
        if lich(x, y) > .80 and small(x, y) > .55 and (x * 7 + y * 3) % 5:
            return ramp('lichen', v * .6)
        return ramp('lime', v)
    fill(img, mask_poly(w, h, left), lambda x, y: stone(x, y, .33 - (y - 20) * .002, cracks_l, .15))
    fill(img, mask_poly(w, h, right), lambda x, y: stone(x, y, .72 - (y - 20) * .003, cracks_r, -.25))
    tl = layer(w, h)
    fill(tl, mask_poly(w, h, top), lambda x, y: ramp('lime', .80 + (x - 50) * .002 + (big(x, y) - .5) * .2 + (small(x, y) - .5) * .18))
    img.alpha_composite(tl)
    # crisp edge highlight along top/right arris
    px = img.load()
    for t in range(60):
        x = int(D[0] + (C[0] - D[0]) * t / 60); y = int(D[1] + (C[1] - D[1]) * t / 60)
        if px[x, y][3] and rnd.random() > .25: px[x, y] = R['lime'][6] + (255,)
    # dark crevice between left face and right face
    for y in range(24, 74):
        x = 58 + int((small(58, y) - .5) * 2)
        if px[x, y][3]: px[x, y] = R['lime'][1] + (255,)
    img = outline(img)
    shadow(img, 48, 72, 50, 6)
    return img

# ---------------------------------------------------------------- juniper (02/03/04 share this)
def juniper_parts(seed=11):
    rnd = random.Random(seed)
    clumps = []
    # irregular flame/cone shape, taller than wide
    for i in range(95):
        t = rnd.random() ** 0.75             # 0 top .. 1 bottom
        y = 4 + t * 39
        half = 2.5 + t * 13 + math.sin(t * 9) * 1.5
        x = 24 + rnd.uniform(-half, half)
        r = rnd.uniform(2.0, 3.6) * (0.8 + t * 0.35)
        clumps.append((x, y, r))
    clumps.append((24, 2.5, 1.8)); clumps.append((23, 5, 2.2))
    clumps.sort(key=lambda c: c[1])
    berries = []
    for i in range(26):
        c = rnd.choice(clumps[5:])
        berries.append((c[0] + rnd.uniform(-c[2], c[2]) * .6, c[1] + rnd.uniform(-c[2], c[2]) * .5))
    stems = [  # woody stems: polyline from base
        [(24, 53), (23, 46), (21, 38), (18, 30)],
        [(25, 53), (27, 45), (30, 37), (33, 28)],
        [(24, 53), (24, 44), (25, 32), (24, 20)],
        [(23, 52), (17, 47), (12, 42)],
        [(26, 52), (32, 48), (37, 44)],
    ]
    return clumps, berries, stems

def draw_stems(img, stems, ramp_name='wood', width_base=2.4):
    d = ImageDraw.Draw(img)
    for s in stems:
        for i in range(len(s) - 1):
            wdt = max(1, round(width_base * (1 - i / len(s))))
            d.line([s[i], s[i + 1]], fill=R[ramp_name][1] + (255,), width=wdt)
        # lit right edge
        for i in range(len(s) - 1):
            a, b = s[i], s[i + 1]
            d.line([(a[0] + 1, a[1]), (b[0] + 1, b[1])], fill=R[ramp_name][3] + (255,), width=1)

def draw_clumps(img, clumps, seed=12, keep=lambda x, y: True):
    w, h = img.size; px = img.load()
    fine = Noise(w, h, 2, seed); mid = Noise(w, h, 4, seed + 1)
    for (cx, cy, r) in clumps:
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if not (0 <= x < w and 0 <= y < h) or not keep(x, y): continue
                dx, dy = (x - cx) / r, (y - cy) / r
                d = dx * dx + dy * dy
                edge = 1 - (fine(x, y) - .5) * 1.1
                if d > edge: continue
                # light from upper right per clump + global
                v = .30 + dx * .26 - dy * .24 + (fine(x, y) - .5) * .55 + (mid(x, y) - .5) * .2
                if (x + 2 * y) % 5 == 0 and fine(x, y) > .55: v += .18   # needle glints
                v += (x - 24) * .006 - (y - 30) * .004
                if d > .7 * edge and dx + dy > 0.3: v -= .25   # underside shade
                px[x, y] = ramp('juni', v) + (255,)

def draw_berries(img, berries, keep=lambda x, y: True):
    px = img.load(); w, h = img.size
    for (x, y) in berries:
        x, y = int(round(x)), int(round(y))
        if not (1 <= x < w - 1 and 1 <= y < h - 1) or not keep(x, y) or not px[x, y][3]: continue
        px[x, y] = R['berry'][2] + (255,)
        px[x - 1, y + 1] = R['berry'][1] + (255,) if px[x - 1, y + 1][3] else px[x - 1, y + 1]
        px[x, y + 1] = R['berry'][0] + (255,)
        if (x + y) % 3 == 0: px[x + 1, y] = R['berry'][3] + (255,)

W_J, H_J = 48, 55
def juniper():
    clumps, berries, stems = juniper_parts()
    img = layer(W_J, H_J)
    draw_stems(img, stems)
    draw_clumps(img, clumps)
    # woody base visible below foliage + stems peeking through gaps
    base = layer(W_J, H_J)
    draw_stems(base, [[(24, 54), (24, 44)], [(23, 53), (18, 47)], [(26, 53), (31, 48)]], width_base=3)
    bpx = base.load(); ipx = img.load()
    for y in range(44, 55):
        for x in range(W_J):
            if bpx[x, y][3]: ipx[x, y] = bpx[x, y]
    gaps = layer(W_J, H_J)
    draw_stems(gaps, [[(21, 38), (18, 31)], [(28, 41), (31, 35)], [(24, 30), (25, 24)]], width_base=1.4)
    gp = gaps.load()
    for y in range(H_J):
        for x in range(W_J):
            if gp[x, y][3] and ipx[x, y][3] and ipx[x, y][:3] in (R['juni'][0], R['juni'][1], R['juni'][2]):
                ipx[x, y] = gp[x, y]
    draw_berries(img, berries)
    img = outline(img)
    big = layer(W_J, H_J + 1); big.alpha_composite(img, (0, 0))
    shadow(big, 20, 53, 17, 3)
    return big

def juniper_bitten():
    clumps, berries, stems = juniper_parts()
    rnd = random.Random(31)
    cut = Noise(W_J, H_J, 3, 40)
    keep = lambda x, y: x < 24 + (cut(x, y) - .5) * 5 - (1 if y > 40 else 0)
    img = layer(W_J, H_J)
    left_stems = [stems[0], stems[2][:2] + [(24, 30)], stems[3]]
    draw_stems(img, left_stems)
    # right half: pale broken stubs (bark stripped by goats)
    stub_stems = [
        [(25, 53), (27, 46), (29, 40)], [(26, 50), (31, 47), (34, 45)],
        [(25, 44), (29, 37)], [(25, 36), (30, 31)], [(24, 31), (28, 25)],
        [(27, 46), (32, 41)], [(29, 40), (33, 36)], [(26, 28), (24, 22)],
        [(31, 47), (36, 43), (38, 40)], [(33, 45), (37, 46)], [(32, 41), (36, 37)],
        [(29, 37), (34, 33)], [(30, 31), (33, 27)], [(28, 25), (30, 19)],
        [(33, 36), (36, 31)], [(34, 33), (37, 34)], [(29, 40), (34, 40)],
        [(26, 20), (27, 14)], [(25, 14), (26, 9)],
    ]
    d = ImageDraw.Draw(img)
    for s in stub_stems:
        d.line(s, fill=R['stub'][1] + (255,), width=2 if s[0][1] > 45 else 1)
        for a, b in zip(s, s[1:]):
            d.line([(a[0] + 1, a[1]), (b[0] + 1, b[1])], fill=R['stub'][3] + (255,), width=1)
        ex, ey = s[-1]  # splintered end
        d.point((ex, ey - 1), fill=R['stub'][2] + (255,)); d.point((ex + 1, ey), fill=R['stub'][0] + (255,))
    draw_clumps(img, clumps, keep=keep)
    # sparse ragged leftovers along the bite line
    px = img.load()
    for _ in range(40):
        y = rnd.randint(8, 46); x = int(24 + rnd.uniform(0, 7))
        if not px[x, y][3] and rnd.random() > .4:
            px[x, y] = (R['juni'][2] if rnd.random() > .5 else R['straw'][1]) + (255,)
    base = layer(W_J, H_J)
    draw_stems(base, [[(24, 54), (24, 44)], [(23, 53), (18, 47)]], width_base=3)
    d2 = ImageDraw.Draw(base)
    d2.line([(26, 53), (31, 48)], fill=R['stub'][1] + (255,), width=2)
    d2.line([(27, 53), (32, 48)], fill=R['stub'][3] + (255,), width=1)
    bpx = base.load()
    for y in range(44, 55):
        for x in range(W_J):
            if bpx[x, y][3]: px[x, y] = bpx[x, y]
    draw_berries(img, berries, keep=keep)
    img = outline(img)
    big = layer(W_J, H_J + 1); big.alpha_composite(img, (0, 0))
    shadow(big, 20, 53, 17, 3)
    return big

def sprig():
    w, h = 36, 14
    img = layer(w, h)
    stem = [(2, 10), (12, 9), (22, 7), (33, 5)]
    d = ImageDraw.Draw(img)
    d.line(stem, fill=R['wood'][2] + (255,), width=1)
    d.line([(14, 9), (20, 11), (25, 11)], fill=R['wood'][2] + (255,), width=1)
    clumps = [(9, 8, 2.6), (14, 7, 2.9), (19, 6, 2.8), (24, 5.5, 2.6), (29, 4.5, 2.3), (33, 4, 1.8),
              (21, 10, 2.2), (25, 10.5, 1.9), (6, 8.5, 2.0)]
    draw_clumps(img, clumps, seed=55)
    draw_berries(img, [(13, 8), (20, 6), (23, 9), (27, 5)])
    px = img.load()
    for x in range(1, 5): px[x, 10] = R['wood'][3] + (255,)  # cut end of the twig
    img = outline(img)
    shadow(img, 17, 12, 16, 2, .7)
    return img

# ---------------------------------------------------------------- goat (from the game's own sheet)
def goat():
    src = Image.open(GOAT).convert('RGBA')
    tw = round(src.width * 121 / src.height); th = 121
    sm = src.resize((tw // 2, th // 2), Image.BOX)
    a = sm.split()[3].point(lambda v: 255 if v > 110 else 0)
    rgb = sm.convert('RGB')
    pal = []
    for name in ('wood', 'cloth', 'straw', 'oak'):
        pal += R[name]
    pal += [INK, (232, 222, 196), (246, 238, 214), (60, 44, 30), (120, 84, 50)]
    p = Image.new('P', (1, 1)); flat = []
    for c in pal: flat += list(c)
    flat += [0] * (768 - len(flat)); p.putpalette(flat)
    q = rgb.quantize(palette=p, dither=Image.Dither.NONE).convert('RGBA')
    q.putalpha(a)
    w, h = q.width + 4, q.height + 3
    img = layer(w, h); img.alpha_composite(q, (2, 0))
    img = outline(img)
    shadow(img, w / 2 - 3, h - 3, w / 2 - 6, 3)
    return img

# ---------------------------------------------------------------- wood props
def plank_fill(img, m, rn, base, horiz=True, seed=60, dv=0):
    w, h = img.size; n = Noise(w, h, 2, seed); g = Noise(w, h, 6, seed + 1)
    def f(x, y):
        k = y if horiz else x
        grain = math.sin((x if horiz else y) * .35 + g(x, y) * 6) * .08
        v = base + grain + (n(x, y) - .5) * .25 + dv * (x / w)
        return ramp(rn, v)
    fill(img, m, f)

def stool():
    w, h = 28, 28
    img = layer(w, h); d = ImageDraw.Draw(img)
    legs = layer(w, h); dl = ImageDraw.Draw(legs)
    dl.line([(14, 10), (14, 21)], fill=R['oak'][1] + (255,), width=2)           # back leg
    dl.line([(7, 11), (3, 26)], fill=R['oak'][2] + (255,), width=3)             # front-left
    dl.line([(21, 11), (25, 26)], fill=R['oak'][3] + (255,), width=3)           # front-right (lit)
    lp = legs.load()
    for y in range(11, 27):
        for x in range(w):
            if lp[x, y][3] and x > 22: lp[x, y] = R['oak'][4] + (255,)
    legs = outline(legs)
    img.alpha_composite(legs)
    # seat: ellipse top + rim
    rim = layer(w, h); ImageDraw.Draw(rim).ellipse((1, 7, 26, 14), fill=(1, 1, 1, 255))
    plank_fill(rim, rim.split()[3], 'oak', .30, dv=.25, seed=61)
    top = layer(w, h); ImageDraw.Draw(top).ellipse((1, 5, 26, 12), fill=(1, 1, 1, 255))
    n = Noise(w, h, 2, 62)
    def seat(x, y):
        dx = (x - 13.5) / 12.5; dy = (y - 8.5) / 3.5
        worn = .2 * max(0, 1 - (dx * dx + dy * dy) * 1.6)
        return ramp('oak', .55 + dx * .18 - dy * .1 + worn + (n(x, y) - .5) * .22 + math.sin(x * .9 + n(x, y) * 3) * .05)
    fill(top, top.split()[3], seat)
    rim.alpha_composite(top)
    rim = outline(rim)
    img.alpha_composite(rim)
    shadow(img, 12, 26, 12, 2)
    return img

def table():
    w, h = 85, 75
    img = layer(w, h)
    # back posts
    posts = layer(w, h); dp = ImageDraw.Draw(posts)
    dp.line([(14, 5), (14, 42)], fill=R['wood'][2] + (255,), width=2)
    dp.line([(72, 3), (72, 40)], fill=R['wood'][3] + (255,), width=2)
    posts = outline(posts); img.alpha_composite(posts)
    # cloth shade, sagging
    pts = [(11, 6), (45, 3), (76, 3), (77, 15)]
    sag = [(77, 15)] + [(77 - i * 3.3, 15 + math.sin(i / 20 * math.pi) * 5 + i * .15) for i in range(21)] + [(11, 21)]
    cl = layer(w, h)
    m = mask_poly(w, h, pts + sag[1:])
    n = Noise(w, h, 3, 70)
    def cloth(x, y):
        fold = .08 if (x % 11) in (0, 1) else (-.06 if (x % 11) == 2 else 0)
        return ramp('cloth', .62 + (x - 40) * .005 - (y - 6) * .022 + fold + (n(x, y) - .5) * .07)
    fill(cl, m, cloth)
    dcl = ImageDraw.Draw(cl)
    for x0, y0 in ((11, 6), (76, 3)):  # ties
        dcl.point((x0, y0), fill=R['straw'][0] + (255,))
    cl = outline(cl); img.alpha_composite(cl)
    # legs
    legs = layer(w, h); dl = ImageDraw.Draw(legs)
    dl.rectangle((9, 50, 12, 72), fill=R['wood'][2] + (255,))
    dl.line([(12, 50), (12, 72)], fill=R['wood'][3] + (255,))
    dl.rectangle((73, 50, 76, 72), fill=R['wood'][3] + (255,))
    dl.line([(76, 50), (76, 72)], fill=R['wood'][4] + (255,))
    dl.line([(13, 64), (72, 64)], fill=R['wood'][1] + (255,), width=1)  # stretcher behind
    legs = outline(legs); img.alpha_composite(legs)
    # top surface: trapezoid planks + front edge
    tp = layer(w, h)
    top_pts = [(12, 40), (75, 38), (82, 46), (5, 48)]
    plank_fill(tp, mask_poly(w, h, top_pts), 'wood', .62, seed=71, dv=.2)
    tpx = tp.load()
    for gy in (42, 45):  # plank seams
        for x in range(w):
            if tpx[x, gy][3] and (x + gy) % 9: tpx[x, gy] = R['wood'][2] + (255,)
    edge = mask_poly(w, h, [(5, 48), (82, 46), (82, 50), (5, 52)])
    plank_fill(tp, edge, 'wood', .30, seed=72, dv=.25)
    tp = outline(tp); img.alpha_composite(tp)
    # small dark wooden box
    bx = layer(w, h); db = ImageDraw.Draw(bx)
    db.polygon([(50, 37), (59, 36), (62, 38), (53, 39)], fill=R['wood'][2] + (255,))   # lid
    db.polygon([(50, 37), (53, 39), (53, 44), (50, 42)], fill=R['wood'][0] + (255,))   # left side
    db.polygon([(53, 39), (62, 38), (62, 43), (53, 44)], fill=R['wood'][1] + (255,))   # front (toward light)
    db.line([(53, 41), (62, 40)], fill=R['wood'][3] + (255,))
    bx = outline(bx); img.alpha_composite(bx)
    shadow(img, 38, 72, 38, 3)
    return img

def tally():
    w, h = 46, 14
    img = layer(w, h)
    n = Noise(w, h, 2, 80)
    def half(y0, x0, x1, inner_down):
        lay = layer(w, h)
        m = mask_poly(w, h, [(x0, y0), (x1, y0 - 1), (x1, y0 + 2), (x0 + 1, y0 + 3)])
        fill(lay, m, lambda x, y: ramp('hazel', .62 + (x / w) * .2 + (n(x, y) - .5) * .25))
        px = lay.load()
        bark_y = y0 if not inner_down else y0 + 3
        for x in range(w):  # bark strip on the round outer side
            for yy in range(h):
                if px[x, yy][3]:
                    top_edge = yy == 0 or not px[x, yy - 1][3]
                    bot_edge = yy == h - 1 or not px[x, yy + 1][3]
                    if (bot_edge if inner_down else top_edge):
                        px[x, yy] = ramp('bark', .4 + (n(x, yy) - .5) * .6) + (255,)
        return lay
    a = half(3, 4, 44, inner_down=True)
    b = half(8, 1, 41, inner_down=True)
    for lay, off in ((a, 3), (b, 0)):
        px = lay.load()
        for x in [off + v for v in (7, 9, 11, 13, 18, 20, 22, 28, 30, 32, 34)]:  # notch tallies, top edge only
            for yy in range(h):
                if px[x, yy][3]:
                    px[x, yy] = R['wood'][0] + (255,)
                    if yy + 1 < h and px[x, yy + 1][3]: px[x, yy + 1] = R['wood'][1] + (255,)
                    break
    a = outline(a); b = outline(b)
    img.alpha_composite(a); img.alpha_composite(b)
    shadow(img, 21, 12, 21, 2, .7)
    return img

# ---------------------------------------------------------------- wheel (shared by 09 and 10)
def wheel_layer(D=35, spokes=10):
    w = h = D + 2
    img = layer(w, h); px = img.load()
    cx, cy = w / 2 - .5, h / 2 - .5
    ry = D / 2; rx = ry * .86
    n = Noise(w, h, 2, 90)
    # thickness: tread seen on the left (shadow side)
    for y in range(h):
        for x in range(w):
            dx = (x - cx + 1.3) / rx; dy = (y - cy) / ry
            if dx * dx + dy * dy <= 1: px[x, y] = R['iron'][0] + (255,)
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / rx; dy = (y - cy) / ry; d = math.sqrt(dx * dx + dy * dy)
            ang = math.atan2(dy, dx)
            lit = .5 + math.cos(ang + math.pi / 4) * .35   # upper right lit
            if d <= 1 and d > .9:
                px[x, y] = ramp('iron', lit + (n(x, y) - .5) * .2) + (255,)
            elif .9 >= d > .76:
                px[x, y] = ramp('wood', .45 + lit * .45 + (n(x, y) - .5) * .25) + (255,)
            elif d <= .76:
                px[x, y] = (0, 0, 0, 0)
    img = outline(img)
    d = ImageDraw.Draw(img)
    for i in range(spokes):
        a = i * 2 * math.pi / spokes + .13
        x0, y0 = cx + math.cos(a) * rx * .2, cy + math.sin(a) * ry * .2
        x1, y1 = cx + math.cos(a) * rx * .78, cy + math.sin(a) * ry * .78
        lit = .55 + math.cos(a + math.pi / 4) * .3
        d.line([(x0 - .6, y0 + .8), (x1 - .6, y1 + .8)], fill=INK + (255,), width=1)
        d.line([(x0, y0), (x1, y1)], fill=ramp('wood', lit) + (255,), width=1)
    # hub
    d.ellipse((cx - rx * .26, cy - ry * .26, cx + rx * .26, cy + ry * .26), fill=INK + (255,))
    d.ellipse((cx - rx * .2, cy - ry * .2, cx + rx * .2, cy + ry * .2), fill=R['wood'][2] + (255,))
    d.ellipse((cx - rx * .12 + .7, cy - ry * .12 - .7, cx + rx * .12 + .7, cy + ry * .12 - .7), fill=R['wood'][4] + (255,))
    d.point((round(cx), round(cy)), fill=R['iron'][1] + (255,))
    return img

def wheel():
    wl = wheel_layer()
    img = layer(wl.width + 6, wl.height + 3)
    img.alpha_composite(wl, (4, 0))
    shadow(img, img.width / 2 - 3, wl.height + 0, 13, 2.5)
    return img

def wagon():
    w, h = 140, 80
    img = layer(w, h)
    # shaft (behind front wheel), pointing left down to the ground
    sh = layer(w, h); ds = ImageDraw.Draw(sh)
    ds.line([(40, 58), (3, 71)], fill=R['wood'][2] + (255,), width=2)
    ds.line([(40, 57), (4, 70)], fill=R['wood'][3] + (255,), width=1)
    ds.line([(8, 66), (9, 74)], fill=R['wood'][2] + (255,), width=2)  # singletree stub / prop
    sh = outline(sh); img.alpha_composite(sh)
    # bed
    bed = layer(w, h)
    side = mask_poly(w, h, [(28, 44), (128, 40), (128, 56), (30, 60)])
    plank_fill(bed, side, 'wood', .55, seed=101, dv=.25)
    front = mask_poly(w, h, [(22, 41), (28, 44), (30, 60), (24, 56)])
    plank_fill(bed, front, 'wood', .25, seed=102)
    bp = bed.load()
    for x in range(w):  # plank seams along the side
        for t in (0.33, 0.66):
            y0 = 44 + (40 - 44) * (x - 28) / 100; y1 = 60 + (56 - 60) * (x - 28) / 100
            yy = int(y0 + (y1 - y0) * t)
            if 0 <= yy < h and bp[x, yy][3] and x > 29: bp[x, yy] = R['wood'][2] + (255,)
    for xs in (52, 78, 104):  # iron straps
        for y in range(h):
            if bp[xs, y][3]: bp[xs, y] = R['iron'][1] + (255,)
    bed = outline(bed); img.alpha_composite(bed)
    # canvas tilt
    cv = layer(w, h)
    top_y = lambda x: 9 + (x - 26) * -.02
    pts = [(24, 43)]
    for i in range(0, 11):
        t = i / 10; pts.append((24 + t * 6 - math.sin(t * math.pi / 2) * 2, 43 - math.sin(t * math.pi / 2) * 33))
    pts += [(40, 7), (120, 5), (126, 6), (130, 10), (132, 18), (132, 40)]
    m = mask_poly(w, h, pts)
    n = Noise(w, h, 3, 103)
    hoops = [40, 63, 86, 109]
    def canvas(x, y):
        v = .45 + (x - 30) * .004 - (y - 10) * .006
        v += math.sin((y - 6) / 36 * math.pi) * .12
        for hx_ in hoops:
            if abs(x - hx_) < 1: v -= .18
            elif abs(x - hx_ - 1.5) < 1: v += .08
        if y > 36: v -= .1
        return ramp('cloth', v + (n(x, y) - .5) * .15)
    fill(cv, m, canvas)
    # front opening, puckered
    op = mask_poly(w, h, [(26, 41), (25, 26), (28, 15), (33, 11), (35, 22), (34, 38)])
    fill(cv, op, lambda x, y: ramp('wood', .12 + (n(x, y) - .5) * .15))
    cp = cv.load()
    for x in range(30, 132, 3):  # lacing rope along the lower hem
        yy = int(42 + (40 - 42) * (x - 30) / 100)
        if cp[x, yy][3]: cp[x, yy] = R['straw'][1] + (255,)
    cv = outline(cv); img.alpha_composite(cv)
    # wheels identical to 09
    wl = wheel_layer()
    img.alpha_composite(wl, (30, h - wl.height - 2))
    img.alpha_composite(wl, (98, h - wl.height - 3))
    shadow(img, 64, 76, 64, 3.5)
    return img

builders = [
 ('01_steinblock', steinblock, (210, 155)),
 ('02_wacholder', juniper, (96, 110)),
 ('03_wacholder_verbissen', juniper_bitten, (96, 110)),
 ('04_wacholderzweig', sprig, (72, 28)),
 ('05_ziege', goat, None),
 ('06_zaehltisch', table, (170, 150)),
 ('07_schemel', stool, (56, 56)),
 ('08_kerbholz', tally, (92, 28)),
 ('09_wagenrad', wheel, (80, 76)),
 ('10_planwagen', wagon, (280, 160)),
]
only = sys.argv[3:] or None
for name, fn, size in builders:
    if only and name[:2] not in only: continue
    lo = fn()
    if size is None: size = (lo.width * 2, lo.height * 2)
    c = finish(lo, name, size)
    bb = c.getbbox()
    print(name, size, 'bbox', bb)
