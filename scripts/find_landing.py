"""Find a legal spot for a plane-landing via ON the main fill (batch 6).

    <kicad python> find_landing.py <net> <x> <y> [r] [--via 0.5 --drill 0.3]

A landing via is the far end of a B.Cu leg: it must clear every layer's
copper like any via, AND its centre must sit on the net's MAIN filled
polygon with enough margin that the refill keeps copper around it. The
tip-via search (close_pad.py) deliberately dropped the fill requirement;
this is the half that keeps it.

Margin rule: centre >= (via radius + 0.05) inside the main outline, so
the annulus lands on copper, not on the crumbling edge of a clearance
carve. Read-only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width  # noqa: E402

import math  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOARD = os.path.join(HW, "bench_board", "bench_board.kicad_pcb")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
NET, CX, CY = args[0], float(args[1]), float(args[2])
RAD = float(args[3]) if len(args) > 3 else 6.0
VIA, DRILL = 0.5, 0.3
if "--via" in sys.argv:
    VIA = float(sys.argv[sys.argv.index("--via") + 1])
if "--drill" in sys.argv:
    DRILL = float(sys.argv[sys.argv.index("--drill") + 1])
CLR, HOLE2HOLE = 0.2, 0.25
VR, DR = VIA / 2.0, DRILL / 2.0

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
PLANE = {"/GND": "In1.Cu", "/3V3": "In2.Cu"}


def mm(v):
    return v / MM


def seg_pt(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def pad_rect(x, y, cx, cy, w, h, ang):
    a = math.radians(-ang)
    dx, dy = x - cx, y - cy
    ca, sa = math.cos(a), math.sin(a)
    rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
    return math.hypot(max(0.0, abs(rx) - w / 2.0), max(0.0, abs(ry) - h / 2.0))


# main fill polygon of the net's plane
lid = b.GetLayerID(PLANE[NET])
zone = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == NET][0]
polys = zone.GetFilledPolysList(lid)
areas = []
for i in range(polys.OutlineCount()):
    ch = polys.COutline(i)
    ssum, n = 0.0, ch.PointCount()
    for k in range(n):
        p1, p2 = ch.CPoint(k), ch.CPoint((k + 1) % n)
        ssum += mm(p1.x) * mm(p2.y) - mm(p2.x) * mm(p1.y)
    areas.append(abs(ssum) / 2.0)
MAIN = areas.index(max(areas))
CH = polys.COutline(MAIN)
NPTS = CH.PointCount()


def in_main(x, y):
    c = False
    for k in range(NPTS):
        p1, p2 = CH.CPoint(k), CH.CPoint((k + 1) % NPTS)
        x1, y1, x2, y2 = mm(p1.x), mm(p1.y), mm(p2.x), mm(p2.y)
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def main_edge_dist(x, y):
    best = 1e9
    for k in range(NPTS):
        p1, p2 = CH.CPoint(k), CH.CPoint((k + 1) % NPTS)
        best = min(best, seg_pt(x, y, mm(p1.x), mm(p1.y), mm(p2.x), mm(p2.y)))
    return best


# HOLES of the main outline matter too: the fill polygon's enclosed voids
# (thermal antipads chained into lakes) are stored as holes, and a via
# centre inside one is NOT on copper. Approximate: also require distance
# to every hole boundary of the main outline >= VR + 0.05 when inside one
# -- cheaper: sample the polyset's Contains on the FULL polyset, which is
# hole-aware.
FULL = polys


def on_copper(x, y):
    return FULL.Contains(pcbnew.VECTOR2I(int(round(x * MM)),
                                         int(round(y * MM))))


pads, segs, vias = [], [], []
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos, sz = p.GetPosition(), p.GetSize()
        is_pth = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        dr = max(mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)) / 2.0 if is_pth else 0.0
        pads.append((p.GetNetname(), mm(pos.x), mm(pos.y), mm(sz.x), mm(sz.y),
                     p.GetOrientationDegrees(), is_pth, dr))
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        vias.append((t.GetNetname(), mm(pos.x), mm(pos.y), mm(via_width(t)) / 2.0))
    else:
        s0, e0 = t.GetStart(), t.GetEnd()
        segs.append((t.GetNetname(), mm(s0.x), mm(s0.y), mm(e0.x), mm(e0.y),
                     mm(t.GetWidth()) / 2.0))


def ok(x, y):
    for net, px, py, w, h, rot, is_pth, dr in pads:
        if net != NET and pad_rect(x, y, px, py, w, h, rot) - VR < CLR - 1e-6:
            return False
        if is_pth and dr > 0 and math.hypot(x - px, y - py) - dr - DR < HOLE2HOLE:
            return False
    for net, x1, y1, x2, y2, hw in segs:
        if net != NET and seg_pt(x, y, x1, y1, x2, y2) - hw - VR < CLR - 1e-6:
            return False
    for net, vx, vy, vr in vias:
        d = math.hypot(x - vx, y - vy)
        if net != NET and d - vr - VR < CLR - 1e-6:
            return False
        if 0.01 < d and d - vr - DR < HOLE2HOLE:
            return False
    return True


hits = []
step = 0.1
n = int(RAD / step)
for i in range(-n, n + 1):
    for j in range(-n, n + 1):
        x, y = CX + i * step, CY + j * step
        d = math.hypot(x - CX, y - CY)
        if d > RAD:
            continue
        if not in_main(x, y) or not on_copper(x, y):
            continue
        if main_edge_dist(x, y) < VR + 0.05:
            continue
        if not ok(x, y):
            continue
        hits.append((d, x, y))

hits.sort()
print("landing sites for %s (%.2f/%.2f via) near (%.2f, %.2f):"
      % (NET, VIA, DRILL, CX, CY))
for d, x, y in hits[:10]:
    print("  (%.2f, %.2f)  %.2f mm away" % (x, y, d))
if not hits:
    print("  none within %.1f mm" % RAD)
