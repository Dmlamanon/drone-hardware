"""Find a clear place to put a via, near a given point.

Searches a grid and reports positions where a via of the given size clears
every other net's copper (pads, tracks on the layers the via spans, and
other vias) by the board clearance.

Usage: python viasite.py <board> <net> <x> <y> [radius_mm] [via_size] [clear]
"""
import sys, math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width, set_via_width  # noqa: F401
BOARD, NET = sys.argv[1], sys.argv[2]
CX, CY = float(sys.argv[3]), float(sys.argv[4])
RAD = float(sys.argv[5]) if len(sys.argv) > 5 else 4.0
VIA = float(sys.argv[6]) if len(sys.argv) > 6 else 0.6
CLR = float(sys.argv[7]) if len(sys.argv) > 7 else 0.2

b = pcbnew.LoadBoard(BOARD)
MM = 1e6


def mm(v):
    return v / MM


pads, tracks, vias = [], [], []
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos = p.GetPosition()
        sz = p.GetSize()
        pads.append((fp.GetReference(), p.GetNumber(), p.GetNetname(),
                     mm(pos.x), mm(pos.y), math.hypot(mm(sz.x), mm(sz.y)) / 2.0))
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        # GetWidth() on a via needs a layer in KiCad 10; use the drill-based
        # outer diameter instead, which is what matters for clearance anyway.
        vias.append((t.GetNetname(), mm(pos.x), mm(pos.y), mm(via_width(t)) / 2.0))
    else:
        s, e = t.GetStart(), t.GetEnd()
        tracks.append((t.GetNetname(), mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth())))


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


VR = VIA / 2.0
best = []
step = 0.05
n = int(RAD / step)
for i in range(-n, n + 1):
    for j in range(-n, n + 1):
        x, y = CX + i * step, CY + j * step
        d = math.hypot(x - CX, y - CY)
        if d > RAD:
            continue
        worst = 99.0
        who = ""
        ok = True
        for ref, pn, net, px, py, pr in pads:
            if net == NET:
                continue
            g = math.hypot(x - px, y - py) - pr - VR
            if g < worst:
                worst, who = g, "%s.%s" % (ref, pn)
            if g < CLR:
                ok = False
                break
        if ok:
            for net, x1, y1, x2, y2, w in tracks:
                if net == NET:
                    continue
                g = seg_dist(x, y, x1, y1, x2, y2) - w / 2.0 - VR
                if g < worst:
                    worst, who = g, "track %s" % net
                if g < CLR:
                    ok = False
                    break
        if ok:
            for net, vx, vy, vr in vias:
                if net == NET:
                    continue
                g = math.hypot(x - vx, y - vy) - vr - VR
                if g < worst:
                    worst, who = g, "via %s" % net
                if g < CLR:
                    ok = False
                    break
        if ok:
            best.append((d, x, y, worst, who))

best.sort()
print("%d clear via sites within %.1f mm of (%.3f, %.3f) for %s"
      % (len(best), RAD, CX, CY, NET))
for d, x, y, worst, who in best[:12]:
    print("   (%7.3f, %7.3f)  %.2f mm away, tightest %s %.2f mm" % (x, y, d, who, worst))
if not best:
    print("   NONE -- nothing fits here")
