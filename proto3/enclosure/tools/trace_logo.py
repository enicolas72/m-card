"""Traces the alpha channel of logo-m.png into OpenSCAD polygons (logo.scad).

Usage (Pillow needed):
    python3 tools/trace_logo.py ../../marketing/build/img/logo-m.png logo.scad

Marching squares on the anti-aliased alpha (threshold 0.5, linear interpolation
of the crossings: sub-pixel accurate), loops linked, simplified with
Douglas-Peucker, classified outer/hole by nesting. Output: logo.scad with
module logo_2d(w) = the logo scaled to width w (mm), centered on the origin.
"""
import sys
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
W, H = im.size
A = im.getchannel("A")
pad = 1
g = [[0.0] * (W + 2 * pad) for _ in range(H + 2 * pad)]
px = A.load()
for y in range(H):
    for x in range(W):
        g[y + pad][x + pad] = px[x, y] / 255.0
GW, GH = W + 2 * pad, H + 2 * pad
T = 0.5

def interp(p1, v1, p2, v2):
    t = (T - v1) / (v2 - v1)
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))

# edges of a cell: 0 top (tl-tr), 1 right (tr-br), 2 bottom (bl-br), 3 left (tl-bl)
segs = {}
def add(a, b):
    segs.setdefault(a, []).append(b)

for y in range(GH - 1):
    for x in range(GW - 1):
        tl, tr, br, bl = g[y][x], g[y][x + 1], g[y + 1][x + 1], g[y + 1][x]
        idx = (tl > T) * 8 + (tr > T) * 4 + (br > T) * 2 + (bl > T) * 1
        if idx in (0, 15):
            continue
        P = {0: ((x, y), tl, (x + 1, y), tr), 1: ((x + 1, y), tr, (x + 1, y + 1), br),
             2: ((x, y + 1), bl, (x + 1, y + 1), br), 3: ((x, y), tl, (x, y + 1), bl)}
        def pt(e):
            a, va, b, vb = P[e]
            return interp(a, va, b, vb)
        # oriented segments: inside on the left when walking (consistent winding)
        table = {
            1: [(3, 2)], 2: [(2, 1)], 3: [(3, 1)], 4: [(1, 0)], 6: [(2, 0)], 7: [(3, 0)],
            8: [(0, 3)], 9: [(0, 2)], 11: [(0, 1)], 12: [(1, 3)], 13: [(1, 2)], 14: [(2, 3)],
            5: [(3, 0), (1, 2)] if (tl + tr + br + bl) / 4 <= T else [(3, 2), (1, 0)],
            10: [(0, 1), (2, 3)] if (tl + tr + br + bl) / 4 <= T else [(0, 3), (2, 1)],
        }
        for e1, e2 in table[idx]:
            add(pt(e1), pt(e2))

def key(p):
    return (round(p[0], 6), round(p[1], 6))

nxt = {}
for a, bs in segs.items():
    for b in bs:
        nxt.setdefault(key(a), []).append((a, b))

loops = []
used = set()
for k0 in list(nxt):
    for a0, b0 in nxt[k0]:
        if (key(a0), key(b0)) in used:
            continue
        loop = [a0]
        a, b = a0, b0
        while True:
            used.add((key(a), key(b)))
            loop.append(b)
            cand = [(c, d) for c, d in nxt.get(key(b), []) if (key(c), key(d)) not in used]
            if not cand:
                break
            a, b = cand[0]
        if len(loop) > 8:
            loops.append(loop[:-1])

def area(l):
    return sum(l[i][0] * l[i - 1][1] - l[i - 1][0] * l[i][1] for i in range(len(l))) / 2

def dp(points, eps):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = (dx * dx + dy * dy) ** 0.5 or 1e-9
    dmax, imax = 0, 0
    for i in range(1, len(points) - 1):
        p = points[i]
        d = abs(dy * (p[0] - a[0]) - dx * (p[1] - a[1])) / n
        if d > dmax:
            dmax, imax = d, i
    if dmax > eps:
        return dp(points[: imax + 1], eps)[:-1] + dp(points[imax:], eps)
    return [a, b]

def simplify(l, eps=0.12):
    # split at the farthest point from l[0] so DP works on an open path
    far = max(range(len(l)), key=lambda i: (l[i][0] - l[0][0]) ** 2 + (l[i][1] - l[0][1]) ** 2)
    return dp(l[: far + 1], eps)[:-1] + dp(l[far:] + [l[0]], eps)[:-1]

loops = [simplify(l) for l in loops if abs(area(l)) > 4]

def inside(p, poly):
    x, y = p
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i - 1]
        x2, y2 = poly[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

depth = [sum(inside(l[0], o) for o in loops if o is not l) for l in loops]
xs = [p[0] for l in loops for p in l]
ys = [p[1] for l in loops for p in l]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
cx, cy, lw = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0
aspect = (y1 - y0) / lw

def fmt(l):
    # normalized to width 1, y up, centered
    return "[" + ",".join(f"[{(p[0] - cx) / lw:.5f},{(cy - p[1]) / lw:.5f}]" for p in l) + "]"

outers = [i for i, d in enumerate(depth) if d % 2 == 0]
holes = [i for i, d in enumerate(depth) if d % 2 == 1]
with open(dst, "w") as f:
    f.write("// M-Card \"M.\" logo, traced from marketing/build/img/logo-m.png\n")
    f.write("// (generated: marching squares on the alpha channel, do not edit by hand)\n")
    f.write(f"logo_aspect = {aspect:.5f};   // height / width\n\n")
    f.write("// the logo scaled to width w (mm), centered on the origin\n")
    f.write("module logo_2d(w) {\n  scale([w, w]) difference() {\n    union() {\n")
    for i in outers:
        f.write(f"      polygon({fmt(loops[i])});\n")
    f.write("    }\n")
    for i in holes:
        f.write(f"    polygon({fmt(loops[i])});\n")
    f.write("  }\n}\n")
print(f"{len(loops)} loops ({len(outers)} outer, {len(holes)} holes), "
      f"{sum(map(len, loops))} points, bbox {lw:.1f} x {y1 - y0:.1f} px, aspect {aspect:.4f}")
