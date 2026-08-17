"""Where can a 30.5 mm mounting square go on this board?

The pattern's SIZE is fixed by the frame standard. Its POSITION on the
board is a free choice, and picking it by eye is how the holes ended up in
the corners in the first place. This enumerates candidate centres and
reports, for each, exactly what it would collide with.

Courtyard clearance uses the real courtyard polygons via pcbnew; copper
uses the hole-clearance rule (3.2 mm drill / 2 + 0.25 mm).
"""
import sys, math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width, set_via_width  # noqa: F401
BOARD = sys.argv[1]
PITCH = 30.5
HOLE_R = 1.6          # 3.2 mm drill
COPPER_CLEAR = 0.25   # board setup hole clearance
CRTYD_R = 3.0         # the NPTH pad is 6 mm across

b = pcbnew.LoadBoard(BOARD)
MM = 1e6


def mm(v):
    return v / MM


# --- courtyards (skip the mounting holes themselves) ---
crtyds = []
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref.startswith("MH"):
        continue
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount() == 0:
        cy = fp.GetCourtyard(pcbnew.B_CrtYd)
    if cy.OutlineCount() == 0:
        continue
    bb = cy.BBox()
    crtyds.append((ref, mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom())))

# --- copper: tracks and vias ---
tracks, vias = [], []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        vias.append((mm(p.x), mm(p.y), mm(t.GetDrill()) / 2.0, t.GetNetname()))
    else:
        s, e = t.GetStart(), t.GetEnd()
        tracks.append((mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth()), t.GetNetname()))

pads = []
for fp in b.GetFootprints():
    if fp.GetReference().startswith("MH"):
        continue
    for pad in fp.Pads():
        p = pad.GetPosition()
        sz = pad.GetSize()
        pads.append((fp.GetReference(), pad.GetNumber(), mm(p.x), mm(p.y),
                     math.hypot(mm(sz.x), mm(sz.y)) / 2.0))


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def rect_dist(px, py, x1, x2, y1, y2):
    dx = max(x1 - px, 0.0, px - x2)
    dy = max(y1 - py, 0.0, py - y2)
    return math.hypot(dx, dy)


def evaluate(cx, cy):
    """Return (n_problems, detail list) for a pattern centred at (cx, cy)."""
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            hx, hy = cx + sx * PITCH / 2.0, cy + sy * PITCH / 2.0
            if not (4.0 <= hx <= 76.0 and 4.0 <= hy <= 56.0):
                out.append(("edge", "hole at (%.2f,%.2f) too close to the board edge" % (hx, hy)))
                continue
            for ref, x1, x2, y1, y2 in crtyds:
                d = rect_dist(hx, hy, x1, x2, y1, y2)
                if d < CRTYD_R:
                    out.append(("crtyd", "%s %.2f mm from hole (%.2f,%.2f)" % (ref, d, hx, hy)))
            for (x1, y1, x2, y2, w, net) in tracks:
                d = seg_dist(hx, hy, x1, y1, x2, y2) - w / 2.0
                if d < HOLE_R + COPPER_CLEAR:
                    out.append(("track", "%s %.2f mm from hole (%.2f,%.2f)" % (net, d, hx, hy)))
            for (vx, vy, vr, net) in vias:
                d = math.hypot(vx - hx, vy - hy) - vr
                if d < HOLE_R + COPPER_CLEAR:
                    out.append(("via", "%s %.2f mm from hole (%.2f,%.2f)" % (net, d, hx, hy)))
            for (ref, pn, px, py, pr) in pads:
                d = math.hypot(px - hx, py - hy) - pr
                if d < HOLE_R + COPPER_CLEAR:
                    out.append(("pad", "%s.%s %.2f mm from hole (%.2f,%.2f)" % (ref, pn, d, hx, hy)))
    return out


print("board is %d x %d mm; %d courtyards, %d tracks, %d vias, %d pads"
      % (mm(b.GetBoardEdgesBoundingBox().GetWidth()),
         mm(b.GetBoardEdgesBoundingBox().GetHeight()),
         len(crtyds), len(tracks), len(vias), len(pads)))

print("\n--- the centred pattern (40, 30) ---")
for kind, msg in evaluate(40.0, 30.0):
    print("  %-6s %s" % (kind, msg))

print("\n--- searching all centres on a 0.25 mm grid ---")
best = []
cx = 20.0
while cx <= 60.0:
    cy = 16.0
    while cy <= 44.0:
        probs = evaluate(cx, cy)
        # weight: a courtyard clash needs a component move, copper only a reroute
        w = sum(10 if k == "crtyd" else (100 if k == "edge" else 1) for k, _ in probs)
        best.append((w, len(probs), cx, cy, probs))
        cy += 0.25
    cx += 0.25
best.sort(key=lambda r: (r[0], abs(r[2] - 40) + abs(r[3] - 30)))
print("  %d candidate centres evaluated" % len(best))
for w, n, cx, cy, probs in best[:6]:
    kinds = {}
    for k, _ in probs:
        kinds[k] = kinds.get(k, 0) + 1
    print("  centre (%.2f, %.2f)  weight %-4d  %s  [offset from board centre: %.2f, %.2f]"
          % (cx, cy, w, kinds or "CLEAN", cx - 40, cy - 30))
