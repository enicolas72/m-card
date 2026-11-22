"""Composes the proto 3 enclosure drawing (top view + section A) from the
2D SVG cuts exported by OpenSCAD (tools/cut2d.scad); run by render.sh.

Usage: python3 tools/compose_drawing.py <dir with the cut SVGs> drawing.svg
The dimensions written on the drawing are typed in below: update them when
the model's parameters change."""
import re
import sys

S = sys.argv[1]
OUT = sys.argv[2]
K = 4.0  # px per mm


def paths(name):
    s = open(f"{S}/{name}.svg").read()
    out = []
    for d in re.findall(r'd="([^"]+)"', s):
        subs = []
        for sub in re.split(r"[Mm]", d):
            pts = [tuple(map(float, p)) for p in re.findall(r"(-?[\d.]+),(-?[\d.]+)", sub)]
            if pts:
                subs.append(pts)
        out.append(subs)
    return out


def to_d(subs, ox, oy, x0, y0):
    """mm coords (x, svg y) -> px, origin (x0, y0) mapped to (ox, oy)."""
    d = []
    for pts in subs:
        d.append("M " + " L ".join(f"{ox + K * (x - x0):.1f},{oy + K * (y - y0):.1f}" for x, y in pts) + " Z")
    return " ".join(d)


svg = []
W, H = 1400, 720
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           'font-family="Helvetica, Arial, sans-serif">')
svg.append("""<style>
  .t { font-size: 15px; fill: #222; }
  .h { font-size: 19px; font-weight: bold; fill: #111; }
  .s { font-size: 13px; fill: #444; }
  .dim { stroke: #c0392b; stroke-width: 1; fill: none; }
  .dt { font-size: 13px; fill: #c0392b; }
  .tray { fill: #dfe3e8; stroke: #333; stroke-width: 1.2; fill-rule: evenodd; }
  .cover { fill: #a9b4c0; stroke: #333; stroke-width: 1.2; fill-rule: evenodd; }
  .card { fill: #2c5d8a; stroke: #1b3a57; stroke-width: 1; }
  .reader { fill: #c0392b; stroke: #7b241c; stroke-width: 1; }
  .lead { stroke: #555; stroke-width: 1; fill: none; }
</style>""")
svg.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')


def dim(x1, y1, x2, y2, text, side=1, off=14, ox=0, oy=0):
    """Dimension line between two px points, offset perpendicular by off px."""
    if abs(y1 - y2) < 0.5:   # horizontal
        y = y1 + side * off
        svg.append(f'<path class="dim" d="M{x1},{y1} V{y} M{x2},{y2} V{y} M{x1},{y} H{x2}"/>')
        svg.append(f'<path class="dim" d="M{x1 + 6},{y - 3} L{x1},{y} L{x1 + 6},{y + 3} M{x2 - 6},{y - 3} L{x2},{y} L{x2 - 6},{y + 3}"/>')
        svg.append(f'<text class="dt" x="{(x1 + x2) / 2}" y="{y - 4 if side < 0 else y + 15}" text-anchor="middle">{text}</text>')
    else:                     # vertical
        x = x1 + side * off
        svg.append(f'<path class="dim" d="M{x1},{y1} H{x} M{x2},{y2} H{x} M{x},{y1} V{y2}"/>')
        svg.append(f'<path class="dim" d="M{x - 3},{y1 + 6} L{x},{y1} L{x + 3},{y1 + 6} M{x - 3},{y2 - 6} L{x},{y2} L{x + 3},{y2 - 6}"/>')
        anchor = "start" if side > 0 else "end"
        svg.append(f'<text class="dt" x="{x + side * 5}" y="{(y1 + y2) / 2 + 5}" text-anchor="{anchor}">{text}</text>')


# ---------------- top view ----------------
TX, TY = 60, 150          # px position of the box's back-left corner (x=0, y=96)
svg.append(f'<text class="h" x="{TX}" y="60">Top view</text>')
svg.append(f'<text class="s" x="{TX}" y="80">front at the bottom · mm</text>')
for p in paths("t_outline"):
    svg.append(f'<path class="tray" d="{to_d(p, TX, TY, 0, -96)}"/>')
for p in paths("t_cover"):
    svg.append(f'<path class="cover" d="{to_d(p, TX, TY, 0, -96)}"/>')


def tp(x, y):  # box mm -> px (top view)
    return TX + K * x, TY + K * (96 - y)


x0, y0 = tp(0, 0)
x1, y1 = tp(190, 96)
dim(x0, y0, x1, y0, "190", side=1, off=40)
dim(x1, y1, x1, y0, "96", side=1, off=30)
# slot
a, b = tp(8, 48)
c, _ = tp(64, 48)
dim(a, b, c, b, "slot 56 × 2", side=-1, off=60)
dim(x0, b, a, b, "8", side=1, off=30)
# window
wa, wb = tp(86.75, 79.7)
wc, _ = tp(166.75, 79.7)
dim(wa, wb, wc, wb, "screen window 80 × 22.4", side=-1, off=28)
# buttons
p1, q1 = tp(107, 34)
p2, _ = tp(129, 34)
p3, _ = tp(151, 34)
dim(p1, q1, p2, q1, "22", side=-1, off=40)
dim(p2, q1, p3, q1, "22", side=-1, off=40)
svg.append(f'<text class="s" x="{p2}" y="{q1 + 92}" text-anchor="middle">3 × Ø12 buttons ⏮ ⏯ ⏭, cut-through icons</text>')
# section mark A-A through the slot
sx, _ = tp(36, 0)
svg.append(f'<path d="M{sx},{y1 - 18} V{y1 - 4} M{sx},{y0 + 4} V{y0 + 18}" stroke="#2c5d8a" stroke-width="2.5"/>')
svg.append(f'<text class="h" x="{sx + 6}" y="{y1 - 6}" fill="#2c5d8a">A</text>')
svg.append(f'<text class="h" x="{sx + 6}" y="{y0 + 30}" fill="#2c5d8a">A</text>')
lx, ly = tp(36, 20)
svg.append(f'<text class="s" x="{lx}" y="{ly + 4}" text-anchor="middle">"M." logo on the front face</text>')

# ---------------- section A ----------------
SX, SY = 940, 150         # px position of (X=0, z=104)
svg.append(f'<text class="h" x="{SX}" y="60">Section A–A</text>')
svg.append(f'<text class="s" x="{SX}" y="80">through the slot, seen from the left · front on the right</text>')
for name, cls in (("s_tray", "tray"), ("s_cover", "cover"), ("s_reader", "reader"), ("s_card", "card")):
    for p in paths(name):
        svg.append(f'<path class="{cls}" d="{to_d(p, SX, SY, 0, -104)}"/>')


def sp(X, z):  # section mm (X = 96 - y, z) -> px
    return SX + K * X, SY + K * (104 - z)


fx, fz0 = sp(96, 0)
_, fz50 = sp(96, 50)
dim(fx, fz0, fx, fz50, "50", side=1, off=22)
cx, top = sp(47.62, 50)
_, bot = sp(47.62, 18)
dim(cx, top, cx, bot, "32", side=-1, off=70)
_, ctop = sp(47.62, 103.6)
dim(cx, ctop, cx, top, "card shows 53.6", side=-1, off=70)
rx, rz1 = sp(44.4, 46.5)
_, rz0 = sp(44.4, 6.1)
bx, _ = sp(0, 0)
dim(bx, rz1, bx, rz0, "40.4", side=-1, off=12)
# labels
lx, lz = sp(44.4, 40)
tx_, tz_ = sp(2, -14)
svg.append(f'<path class="lead" d="M{lx},{sp(44.4, 12)[1]} L{tx_ + 70},{tz_ - 16}"/>')
svg.append(f'<text class="t" x="{tx_ - 10}" y="{tz_}">PN532 reader,</text>')
svg.append(f'<text class="t" x="{tx_ - 10}" y="{tz_ + 18}">~3 mm behind the card</text>')
gx, gz = sp(48.0, 85)
svg.append(f'<text class="t" x="{gx + 14}" y="{gz}">card (portrait)</text>')
tx, tz = sp(10, 2)
svg.append(f'<text class="s" x="{SX}" y="{SY + K * 104 + 120}">light: tray (floor + walls) · dark: cover (whole top)</text>')

svg.append("</svg>")
open(OUT, "w").write("\n".join(svg))
print("written", OUT)
