"""WHY does the plane not reach this pad? Outline, or carving? (batch 6)

Read-only diagnosis for the seven coverage-problem pads. The batch
hypothesis is that these are ZONE OUTLINE problems -- deterministic
geometry -- rather than the congestion puzzle that broke attempts 1-3.
This script tests that hypothesis per pad before anything is edited:

  * is the pad centre inside the zone's OUTLINE polygon at all?
  * how far is it from the outline boundary?
  * is it inside (or near) the FILLED copper?
  * what other-net copper occupies that inner layer nearby -- the 214
    known signal segments, other nets' vias, other nets' PTH barrels --
    i.e. the things whose clearance carves voids no outline edit can fix?

Usage: <kicad python> pour_reach.py [radius_mm]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_safe import pcbnew  # noqa: E402  (disables wx asserts first)

import math  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOARD = os.path.join(HW, "bench_board", "bench_board.kicad_pcb")
RADIUS = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0

# The seven, per the batch brief and the batch-4 census.
TARGETS = [
    ("U1", "1",  "/3V3"), ("U1", "48", "/3V3"), ("U1", "64", "/3V3"),
    ("J3", "A1", "/GND"), ("J3", "A12", "/GND"),
    ("J3", "B1", "/GND"), ("J3", "B12", "/GND"),
]

b = pcbnew.LoadBoard(BOARD)
MM = 1e6


def mm(v):
    return v / MM


def V(x, y):
    return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))


# ---- zones, by net+layer ----
zones = {}
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    for lid in z.GetLayerSet().Seq():
        zones[(z.GetNetname(), b.GetLayerName(lid))] = z

print("zones present:")
for (net, layer), z in sorted(zones.items()):
    o = z.Outline()
    filled = z.GetFilledPolysList(b.GetLayerID(layer))
    print("  %-8s on %-7s outline verts=%d  filled polys=%d  "
          "priority=%d  min_thick=%.2f  thermal gap/bridge=%.2f/%.2f"
          % (net, layer, o.COutline(0).PointCount() if o.OutlineCount() else 0,
             filled.OutlineCount(), z.GetAssignedPriority(),
             mm(z.GetMinThickness()),
             mm(z.GetThermalReliefGap()), mm(z.GetThermalReliefSpokeWidth())))

PLANE_LAYER = {"/GND": "In1.Cu", "/3V3": "In2.Cu"}


def poly_min_dist(poly, x, y):
    """Min distance from (x,y) to the polygon's edges, mm."""
    best = 1e9
    for oi in range(poly.OutlineCount()):
        ch = poly.COutline(oi)
        n = ch.PointCount()
        for i in range(n):
            a, c = ch.CPoint(i), ch.CPoint((i + 1) % n)
            ax, ay, cx, cy = mm(a.x), mm(a.y), mm(c.x), mm(c.y)
            dx, dy = cx - ax, cy - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
            d = math.hypot(x - (ax + t * dx), y - (ay + t * dy))
            best = min(best, d)
    return best


def pad_abs(ref, num):
    for fp in b.GetFootprints():
        if fp.GetReference() == ref:
            for p in fp.Pads():
                if p.GetNumber() == num:
                    return p
    return None


for ref, num, net in TARGETS:
    p = pad_abs(ref, num)
    if p is None:
        print("\n%s.%s: PAD NOT FOUND" % (ref, num))
        continue
    pos = p.GetPosition()
    x, y = mm(pos.x), mm(pos.y)
    layer = PLANE_LAYER[net]
    lid = b.GetLayerID(layer)
    z = zones.get((net, layer))

    attr = []
    if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
        attr.append("PTH")
    elif p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
        attr.append("SMD")
    sz = p.GetSize()
    print("\n%s.%s [%s]  at (%.3f, %.3f)  %s %.2fx%.2f mm"
          % (ref, num, net, x, y, "/".join(attr) or "?", mm(sz.x), mm(sz.y)))

    if z is None:
        print("   NO ZONE for %s on %s" % (net, layer))
        continue

    inside_outline = z.Outline().Contains(V(x, y))
    d_outline = poly_min_dist(z.Outline(), x, y)
    filled = z.GetFilledPolysList(lid)
    inside_fill = filled.Contains(V(x, y))
    d_fill = poly_min_dist(filled, x, y)

    print("   outline: %s  (boundary %.3f mm away)"
          % ("INSIDE" if inside_outline else "OUTSIDE", d_outline))
    print("   fill:    %s  (nearest filled copper %.3f mm away)"
          % ("INSIDE" if inside_fill else "OUTSIDE", d_fill))

    # What else lives on that inner layer nearby -- the carving suspects.
    segs, vias_n, pths = [], 0, []
    for t in b.GetTracks():
        if t.GetNetname() == net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            vp = t.GetPosition()
            if math.hypot(mm(vp.x) - x, mm(vp.y) - y) <= RADIUS:
                vias_n += 1
        elif t.GetLayer() == lid:
            s, e = t.GetStart(), t.GetEnd()
            sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
            dx, dy = ex - sx, ey - sy
            L2 = dx * dx + dy * dy
            tt = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - sx) * dx + (y - sy) * dy) / L2))
            d = math.hypot(x - (sx + tt * dx), y - (sy + tt * dy))
            if d <= RADIUS:
                segs.append((d, t.GetNetname()))
    for fp in b.GetFootprints():
        for pp in fp.Pads():
            if pp.GetNetname() == net:
                continue
            if pp.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            ppos = pp.GetPosition()
            d = math.hypot(mm(ppos.x) - x, mm(ppos.y) - y)
            if d <= RADIUS:
                pths.append((d, "%s.%s" % (fp.GetReference(), pp.GetNumber()),
                             pp.GetNetname()))

    segs.sort()
    pths.sort()
    print("   other-net on %s within %.1f mm: %d signal seg(s), %d via(s), "
          "%d PTH pad(s)" % (layer, RADIUS, len(segs), vias_n, len(pths)))
    for d, n in segs[:6]:
        print("      seg  %-16s %.3f mm away" % (n, d))
    for d, nm, n in pths[:6]:
        print("      pth  %-10s %-14s %.3f mm away" % (nm, n, d))

    # The verdict the hypothesis needs.
    if not inside_outline:
        print("   => OUTLINE problem: the zone boundary does not cover this "
              "pad. Extension is the candidate fix.")
    elif not inside_fill and (segs or vias_n or pths):
        print("   => CARVED: outline covers it, but other-net copper "
              "clearance ate the fill here. An outline edit cannot fix "
              "this.")
    elif not inside_fill:
        print("   => OUTLINE-ADJACENT: inside the outline, fill missing, "
              "no obvious carver -- look at min-thickness necking.")
    else:
        print("   => fill already reaches the pad centre?! Re-check why "
              "this pad is on the list.")
