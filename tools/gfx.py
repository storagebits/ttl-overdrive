#!/usr/bin/env python3
"""Graphics for the demo, quantized to the Gigatron's 64 colours (byte = 0bBBGGRR)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = '/System/Library/Fonts/Supplemental/Arial Black.ttf'


def rgb(c):
    return ((c & 3) * 85, ((c >> 2) & 3) * 85, ((c >> 4) & 3) * 85)


def col(r, g, b):
    return r | g << 2 | b << 4


def logo(w=160, h=36):
    """'TTL' over 'OVERDRIVE': chrome gradient, dark outline, returns rows of colour bytes."""
    big = Image.new('L', (w * 4, h * 4), 0)
    d = ImageDraw.Draw(big)
    f1 = ImageFont.truetype(FONT, 100)
    f2 = ImageFont.truetype(FONT, 72)
    def centered(text, font, y):
        bb = d.textbbox((0, 0), text, font=font)
        d.text(((w * 4 - (bb[2] - bb[0])) // 2 - bb[0], y - bb[1]), text, 255, font=font)
    centered('TTL', f1, 3)
    centered('OVERDRIVE', f2, 84)
    # slant for speed
    big = big.transform(big.size, Image.AFFINE, (1, 0.18, -h * 4 * 0.09, 0, 1, 0), Image.BICUBIC)
    m = big.resize((w, h), Image.LANCZOS)
    mask = [[m.getpixel((x, y)) > 110 for x in range(w)] for y in range(h)]
    out = [[0] * w for _ in range(h)]
    # chrome: sky blue to white on the top half of each line of text, orange to yellow below
    grad1 = [col(0, 1, 3), col(1, 2, 3), col(2, 3, 3), col(3, 3, 3), col(3, 3, 3), col(1, 1, 2), col(2, 1, 1), col(3, 2, 0), col(3, 3, 1)]
    grad2 = [col(1, 2, 3), col(2, 3, 3), col(3, 3, 3), col(1, 1, 2), col(3, 1, 0), col(3, 2, 0), col(3, 3, 1)]
    rows1 = [y for y in range(h) if any(mask[y]) and y < 19]
    rows2 = [y for y in range(h) if any(mask[y]) and y >= 19]
    for rows, g in ((rows1, grad1), (rows2, grad2)):
        if not rows:
            continue
        y0, y1 = rows[0], rows[-1]
        for y in range(y0, y1 + 1):
            c = g[min(len(g) - 1, (y - y0) * len(g) // (y1 - y0 + 1))]
            for x in range(w):
                if mask[y][x]:
                    out[y][x] = c
    # outline
    for y in range(h):
        for x in range(w):
            if not mask[y][x] and any(0 <= y + dy < h and 0 <= x + dx < w and mask[y + dy][x + dx]
                                      for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1))):
                out[y][x] = col(1, 0, 1)
    return out


def plasma_palette():
    """32 colours in a loop, one channel step at a time."""
    path = [(0, 0, 1), (0, 0, 2), (1, 0, 2), (1, 0, 3), (2, 0, 3), (3, 0, 3), (3, 0, 2), (3, 0, 1),
            (3, 1, 1), (3, 1, 0), (3, 2, 0), (3, 3, 0), (3, 3, 1), (3, 3, 2), (3, 3, 3), (2, 3, 3),
            (1, 3, 3), (0, 3, 3), (0, 2, 3), (0, 2, 2), (0, 1, 2), (0, 1, 1), (1, 1, 1), (1, 0, 1),
            (2, 0, 1), (2, 0, 2), (1, 0, 2), (1, 0, 1), (0, 0, 1), (0, 0, 0), (0, 0, 0), (0, 0, 1)]
    return [col(*c) for c in path]


def preview(rows, path, scale=4):
    h, w = len(rows), len(rows[0])
    im = Image.new('RGB', (w, h))
    im.putdata([rgb(c) for r in rows for c in r])
    im.resize((w * scale, h * scale), Image.NEAREST).save(path)


# ---------------------------------------------------------------- memory plan (see src/demomap.py)
import math, sys

LOGO_PAGES = [0x4c, 0x4d, 0x4e, 0x4f] + list(range(0x5c, 0x7c))      # 36 full pages
STRIPS = 0x5c                                                      # 32 strip pages 0x5c-0x7b
TAB1, TAB2, TAB3, TAB4 = 0x7c, 0x7d, 0x7e, 0x7f                    # 4 table pages
LOGO_X = 48                                                        # logo at columns 48..207
BLACK = 0x1c                                                       # code page, visible part black
BARS = 0x08                                                        # 4 hues x 5 shades: pages 0x08-0x1b
HUES = [[col(1, 0, 0), col(2, 0, 0), col(3, 1, 0), col(3, 2, 1), col(3, 3, 2)],
        [col(0, 0, 1), col(0, 1, 2), col(0, 2, 3), col(1, 3, 3), col(2, 3, 3)],
        [col(1, 0, 1), col(2, 0, 2), col(3, 1, 3), col(3, 2, 3), col(3, 3, 3)],
        [col(0, 1, 0), col(0, 2, 0), col(1, 3, 0), col(2, 3, 1), col(3, 3, 2)]]


def frag(frags, name, body, at=None, export=True):
    frags.append((name, body, at, export))


def prog_frags(frags, name, entries, limit=150):
    """A span program cut in pieces of <= limit bytes at entry boundaries, each ending with 0,
    and `name` = the list of pieces (words, 0-ended)."""
    pieces, cur = [], []
    for e in entries:
        if len(cur) + len(e) + 1 > limit:
            pieces.append(cur); cur = []
        cur += e
    pieces.append(cur)
    for i, pc in enumerate(pieces):
        frag(frags, f'{name}{i}', f"bytes({','.join(map(str, pc + [0]))})", export=False)
    frag(frags, name, 'words(' + ','.join(f"'{name}{i}'" for i in range(len(pieces))) + ',0)')


def emit_s(path):
    frags = []
    rows = logo()
    for r, pg in enumerate(LOGO_PAGES):
        line = [0] * 256
        line[LOGO_X:LOGO_X + 160] = rows[r]
        frag(frags, f'logo_r{r}', f"bytes({','.join(map(str, line))})", at=pg << 8, export=False)
    frag(frags, 'logo_pages', f"bytes({','.join(map(str, LOGO_PAGES))})")
    # wobble: 0..2*LOGO_X-1 around LOGO_X, one period over 256 entries, page aligned at 0x500
    wob = [round(LOGO_X + (LOGO_X - 1) * math.sin(2 * math.pi * i / 256)) for i in range(256)]
    frag(frags, 'wob', f"bytes({','.join(map(str, wob))})", at=0x500)
    # bar heights: 0..108 (the top row of a 12-row bar), 64 entries
    bary = [round(54 + 54 * math.sin(2 * math.pi * i / 64)) for i in range(64)]
    frag(frags, 'bary', f"bytes({','.join(map(str, bary))})")
    # Sprite6 sources for lbuf (one page byte per row): a 12-row bar = 2 chunks of 6, each followed by -1
    for h in range(4):
        pages = [BARS + 5 * h + i for i in (0, 1, 1, 2, 3, 4, 4, 3, 2, 1, 1, 0)]
        out = pages[:6] + [255] + pages[6:] + [255]
        frag(frags, f'bar{h}', f"bytes({','.join(map(str, out))})")
    frag(frags, 'bars', "words('bar0','bar1','bar2','bar3')")
    # plasma: 32 strips, strip k = PAL[(I(x) + k) & 31]; stored as runs (len, I) from x = 0, 0 = end
    pal = plasma_palette()
    frag(frags, 'pal32', f"bytes({','.join(map(str, pal))})")
    I = [round(15.5 + 9.5 * math.sin(2 * math.pi * x / 128) + 6 * math.sin(2 * math.pi * 3 * x / 256 + 1)) for x in range(256)]
    runs, x = [], 0
    while x < 256:
        e = x
        while e < 256 and I[e] == I[x]:
            e += 1
        runs += [e - x, I[x] & 31]
        x = e
    runs.append(0)
    assert len(runs) <= 256, len(runs)
    frag(frags, 'plasma_runs', f"bytes({','.join(map(str, runs + [0] * (256 - len(runs))))})", at=TAB3 << 8)
    # row tables: F1D[i] = (STRIPS + v1) | delta << 8, 128 words; F2[i] = v2, 256 bytes; v1 + v2 <= 31
    o = [round(36 * math.sin(2 * math.pi * 2 * i / 128) + 20 * math.sin(2 * math.pi * i / 128)) for i in range(128)]
    f1d = []
    for i in range(128):
        v1 = round(7 + 7 * math.sin(2 * math.pi * i / 128))
        f1d.append((STRIPS + v1) | ((o[i] - o[i - 1]) & 255) << 8)
    frag(frags, 'plasma_f1d', 'words(' + ','.join(map(str, f1d)) + ')', at=TAB1 << 8)
    f2 = [round(8.5 + 8.5 * math.sin(2 * math.pi * 3 * i / 256)) for i in range(256)]
    frag(frags, 'plasma_f2', f"bytes({','.join(map(str, f2))})", at=TAB2 << 8)

    # ---- synthwave: sky gradient + sun rows (code pages, 160 wide), ground row tables
    sky_cols = [col(0, 0, 1), col(0, 0, 1), col(1, 0, 1), col(1, 0, 2), col(2, 0, 2), col(2, 0, 2), col(3, 0, 2),
                col(3, 0, 1), col(3, 1, 1), col(3, 1, 0)]
    sun_cols = [col(3, 3, 0), col(3, 3, 0), col(3, 3, 1), col(3, 2, 0), col(3, 2, 0), col(3, 1, 0), col(3, 1, 1), col(3, 0, 1), col(3, 0, 2)]
    SKY_PAGES = [0x08 + i for i in range(len(sky_cols))]
    SUN_PAGES = list(range(0x08 + len(sky_cols), 0x1c)) + list(range(0x20, 0x38))
    prog, rows = [], []
    for i, c in enumerate(sky_cols):
        prog.append([SKY_PAGES[i], 160, c, 0])
    cy, R, sp = 46, 24, 0
    gaps = {47, 51, 54, 56, 58}
    for y in range(60):
        sky = min(len(sky_cols) - 1, y * len(sky_cols) // 60)
        dy = y - cy
        if abs(dy) < R and y not in gaps:
            half = round((R * R - dy * dy) ** 0.5 * 1.0)
            pg = SUN_PAGES[sp]; sp += 1
            sc = sun_cols[min(len(sun_cols) - 1, max(0, (y - (cy - R)) * len(sun_cols) // (R + (59 - cy))))]
            prog.append([pg, 160, sky_cols[sky], 1, 80 - half, 2 * half, sc])
            rows.append(pg)
        else:
            rows.append(SKY_PAGES[sky])
    assert sp <= len(SUN_PAGES), sp
    prog_frags(frags, 'sky_prog', prog)
    frag(frags, 'sky_rows', f"bytes({','.join(map(str, rows))})")
    # ground: 60 rows; strip level per row, line page per row, z per row (8 bits, lines every 32)
    NL = 24
    lev, lin, zt = [], [], []
    for y in range(60):
        z = 1400 / (y + 3)
        zt.append(round(z) & 255)
        lev.append(STRIPS + min(NL - 1, y * NL // 60))
        lin.append(STRIPS + NL + min(3, y // 15))
    for y in range(59):                     # rows where z jumps a whole line spacing: always a line
        if 1400 / (y + 3) - 1400 / (y + 4) >= 32:
            lev[y] = lin[y]
    frag(frags, 'grid_lev', f"bytes({','.join(map(str, lev))})")
    frag(frags, 'grid_lin', f"bytes({','.join(map(str, lin))})")
    frag(frags, 'grid_z', f"bytes({','.join(map(str, zt))})")
    # grid strips (full pages): level L, vertical lines at 128 +- i*s converge to the vanishing point
    gp = []
    for L in range(NL):
        y = (L + 0.5) * 60 / NL
        sp8 = round((y + 3) * 0.55 * 256)      # line spacing, 8.8 fixed point
        w = 1 if sp8 < 14 * 256 else 2
        lc = [col(1, 0, 1), col(2, 0, 2), col(3, 0, 3), col(3, 1, 3)][min(3, L * 4 // NL)]
        gp += [sp8 & 255, sp8 >> 8, w, lc]
    frag(frags, 'grid_lv', f"bytes({','.join(map(str, gp))})")
    lp = []
    for k, c in enumerate([col(1, 0, 2), col(2, 0, 3), col(3, 0, 3), col(3, 2, 3)]):
        lp.append([STRIPS + NL + k, 0, c, 0])
    prog_frags(frags, 'grid_prog', lp)

    # ---- twister: 32 slices (full pages) of a square bar seen at 0..90 degrees, centred at x = 80
    tp = []
    hues = [[col(0, 1, 2), col(0, 2, 3), col(1, 3, 3), col(2, 3, 3)], [col(1, 0, 2), col(2, 0, 3), col(3, 1, 3), col(3, 2, 3)]]
    for a in range(32):
        th = a * (math.pi / 2) / 32
        xs = [26 * math.sin(th + k * math.pi / 2) for k in range(5)]
        spans = []
        for k in range(4):
            x1, x2 = xs[k], xs[k + 1]
            if x2 - x1 > 0.5:
                b = min(3, int((x2 - x1) / 37 * 4))
                spans.append((80 + round(x1), max(1, round(x2) - round(x1)), hues[k & 1][b]))
        tp.append([STRIPS + a, 0, 0, len(spans)] + [b for sp_ in spans for b in sp_])
    prog_frags(frags, 'twist_prog', tp)
    sway = [round(28 * math.sin(2 * math.pi * 2 * i / 256) + 10 * math.sin(2 * math.pi * 5 * i / 256)) for i in range(256)]
    frag(frags, 'twist_d', f"bytes({','.join(str((sway[i] - sway[i - 1]) & 255) for i in range(256))})", at=TAB4 << 8)

    # ---- scroller: colour of each font row, background black
    frag(frags, 'scroll_cols', f"bytes({','.join(map(str, [col(3,3,3), col(3,3,2), col(3,3,0), col(3,2,0), col(3,1,0), col(3,0,1), col(2,0,2), col(1,0,3)][::-1]))})")

    # solid colour fills: (page, colour) pairs, 0-terminated
    fills = [(BARS + 5 * h + i, HUES[h][i]) for h in range(4) for i in range(5)] + [(BLACK, 0)]
    frag(frags, 'fills', f"bytes({','.join(str(b) for pc in fills for b in pc)},0)")

    with open(path, 'w') as f:
        w = f.write
        w('#VCPUv4\n# generated by tools/gfx.py: do not edit\n\n')
        for i, (name, body, at, export) in enumerate(frags):
            w(f'def g{i}():\n    label({name!r}); {body}\n')
        w('\ncode = [\n')
        for i, (name, body, at, export) in enumerate(frags):
            if export:
                w(f"    ('EXPORT', {name!r}),\n")
            w(f"    ('DATA', {name!r}, g{i}, 0, 1),\n")
            if at is not None:
                w(f"    ('PLACE', {name!r}, {at:#x}, {at + 256:#x}),\n")
        w(']\nmodule(code=code, name="gfx.s", cpu=4)\n')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        emit_s(sys.argv[1])
    preview(logo(), 'media/preview/logo.png')
