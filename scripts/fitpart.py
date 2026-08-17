"""Nearest viable position for one footprint, given everything else.

Used for L1 (the buck inductor) when the restored 30.5 mm mounting pattern
landed on top of it. Searches position and rotation, scores by distance
moved, and reports the best few with their actual clearances -- so the
choice is made on numbers rather than by nudging it in a GUI.

Usage: python fitpart.py <board> <REF> [search_radius_mm]
"""
import sys, math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width, set_via_width  # noqa: F401
BOARD, REF = sys.argv[1], sys.argv[2]
RADIUS = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0

MM = 1e6
HOLE_CRTYD = 3.0      # NPTH pad is 6 mm across
CRTYD_GAP = 0.10      # courtyard-to-courtyard

b = pcbnew.LoadBoard(BOARD)


def mm(v):
    return v / MM


target = None
others = []
holes = []
for fp in b.GetFootprints():
    ref = fp.GetReference()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else None
    ext = (mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom())) if bb else None
    p = fp.GetPosition()
    if ref == REF:
        target = (mm(p.x), mm(p.y), fp.GetOrientationDegrees(), ext)
    elif ref.startswith("MH"):
        holes.append((ref, mm(p.x), mm(p.y)))
    elif ext:
        others.append((ref, ext))

if not target or not target[3]:
    print("no courtyard for %s" % REF)
    sys.exit(2)

ox, oy, orot, (l, r, t, bo) = target
w, h = r - l, bo - t          # courtyard size at the CURRENT rotation
print("%s at (%.3f, %.3f) rot %.0f, courtyard %.2f x %.2f mm" % (REF, ox, oy, orot, w, h))
print("current: x[%.2f,%.2f] y[%.2f,%.2f]" % (l, r, t, bo))


def rect_dist(px, py, x1, x2, y1, y2):
    dx = max(x1 - px, 0.0, px - x2)
    dy = max(y1 - py, 0.0, py - y2)
    return math.hypot(dx, dy)


def overlap_gap(a, bb2):
    """Gap between two rects; negative means overlap."""
    ax1, ax2, ay1, ay2 = a
    bx1, bx2, by1, by2 = bb2
    dx = max(bx1 - ax2, ax1 - bx2)
    dy = max(by1 - ay2, ay1 - by2)
    if dx >= 0 and dy >= 0:
        return math.hypot(dx, dy)
    return max(dx, dy)


cands = []
step = 0.1
n = int(RADIUS / step)
for rot_swap in (False, True):
    ww, hh = (h, w) if rot_swap else (w, h)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            nx, ny = ox + i * step, oy + j * step
            box = (nx - ww / 2.0, nx + ww / 2.0, ny - hh / 2.0, ny + hh / 2.0)
            ok = True
            worst_hole = 99.0
            for hn, hx, hy in holes:
                d = rect_dist(hx, hy, *box)
                worst_hole = min(worst_hole, d)
                if d < HOLE_CRTYD:
                    ok = False
                    break
            if not ok:
                continue
            worst_part, worst_ref = 99.0, ""
            for oref, oext in others:
                g = overlap_gap(box, oext)
                if g < worst_part:
                    worst_part, worst_ref = g, oref
                if g < CRTYD_GAP:
                    ok = False
                    break
            if not ok:
                continue
            move = math.hypot(nx - ox, ny - oy)
            cands.append((move, nx, ny, rot_swap, worst_hole, worst_part, worst_ref))

cands.sort()
print("\n%d viable placements; nearest ten:" % len(cands))
for move, nx, ny, sw, wh, wp, wr in cands[:10]:
    print("  move %.2f mm -> (%.2f, %.2f)%s   hole gap %.2f, tightest neighbour %s %.2f"
          % (move, nx, ny, "  ROT 90" if sw else "", wh, wr, wp))
if not cands:
    print("  NONE within %.1f mm -- the part cannot stay in this neighbourhood" % RADIUS)
