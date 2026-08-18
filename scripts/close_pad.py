"""Find a legal small-via site at/near one SMD pad tip (batch 6, item 3).

    <kicad python> close_pad.py <REF.PAD> [--via 0.30] [--drill 0.15]

The strategy this serves: tip-via -> B.Cu -> landing on a plane-connected
annulus. The via does NOT need plane fill under it (that requirement is
what doomed the batch-4 search); it needs only all-layer copper
clearance, because B.Cu carries the connection out.

Candidates are graded:

  TANGENT   drill fully outside the pad copper, annulus overlapping the
            tip -- connects with NO via-in-pad fabrication fee
  IN-PAD    drill inside the pad copper -- obligates epoxy fill+cap at
            order time (recorded per pad for the order sheet)

Checks per candidate, all at the Power-class 0.2 mm (same-net exempt):
  * other-net SMD/PTH pads as TRUE ROTATED RECTANGLES (the circumscribed
    -circle shortcut produced 29 phantom results in batch 5's review)
  * other-net segments on EVERY layer -- a through-via must clear In1/In2
    signal runs too; forgetting them is how attempt 3 made 387 violations
  * other-net via bodies, plus hole-to-hole 0.25 on all drills

Read-only: prints candidates, applies nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width  # noqa: E402

import math  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOARD = os.path.join(HW, "bench_board", "bench_board.kicad_pcb")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
TARGET = args[0]
VIA, DRILL = 0.30, 0.15
if "--via" in sys.argv:
    VIA = float(sys.argv[sys.argv.index("--via") + 1])
if "--drill" in sys.argv:
    DRILL = float(sys.argv[sys.argv.index("--drill") + 1])
CLR = 0.2          # Power netclass -- the lesson of A12 attempt 2
HOLE2HOLE = 0.25

b = pcbnew.LoadBoard(BOARD)
MM = 1e6


def mm(v):
    return v / MM


def pad_rect_dist(x, y, cx, cy, w, h, ang_deg):
    a = math.radians(-ang_deg)
    dx, dy = x - cx, y - cy
    ca, sa = math.cos(a), math.sin(a)
    rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
    return math.hypot(max(0.0, abs(rx) - w / 2.0),
                      max(0.0, abs(ry) - h / 2.0))


def seg_pt(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


ref, num = TARGET.split(".")
tgt, fp_c = None, None
for fp in b.GetFootprints():
    if fp.GetReference() == ref:
        fpos = fp.GetPosition()
        fp_c = (mm(fpos.x), mm(fpos.y))
        for p in fp.Pads():
            if p.GetNumber() == num:
                tgt = p
if tgt is None:
    sys.exit("pad %s not found" % TARGET)

tpos, tsz = tgt.GetPosition(), tgt.GetSize()
tx, ty = mm(tpos.x), mm(tpos.y)
tw, th = mm(tsz.x), mm(tsz.y)
trot = tgt.GetOrientationDegrees()
tnet = tgt.GetNetname()

# Outward unit vector: from footprint centre through the pad, snapped to
# an axis so the search walks out along the pin, not diagonally.
ux, uy = tx - fp_c[0], ty - fp_c[1]
if abs(ux) > abs(uy):
    ux, uy = (1.0 if ux > 0 else -1.0), 0.0
else:
    ux, uy = 0.0, (1.0 if uy > 0 else -1.0)
half_len = max(tw, th) / 2.0

# ---- obstacles, collected once ----
pads = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p is tgt:
            continue
        pos, sz = p.GetPosition(), p.GetSize()
        is_pth = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        drill_r = 0.0
        if is_pth:
            drill_r = max(mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)) / 2.0
        pads.append((p.GetNetname(), mm(pos.x), mm(pos.y), mm(sz.x),
                     mm(sz.y), p.GetOrientationDegrees(), is_pth, drill_r))
segs, vias, segs_l = [], [], []
F_CU = pcbnew.F_Cu
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        vias.append((t.GetNetname(), mm(pos.x), mm(pos.y),
                     mm(via_width(t)) / 2.0))
    else:
        s0, e0 = t.GetStart(), t.GetEnd()
        segs.append((t.GetNetname(), mm(s0.x), mm(s0.y), mm(e0.x), mm(e0.y),
                     mm(t.GetWidth()) / 2.0))
        segs_l.append((t.GetLayer(), t.GetNetname(), mm(s0.x), mm(s0.y),
                       mm(e0.x), mm(e0.y), mm(t.GetWidth()) / 2.0))

VR, DR = VIA / 2.0, DRILL / 2.0


def site_check(x, y):
    """(ok, blocker, margin). Margin is the tightest clearance left."""
    blocker, margin = "", 1e9
    for net, px, py, w, h, rot, is_pth, drill_r in pads:
        if net != tnet:
            d = pad_rect_dist(x, y, px, py, w, h, rot) - VR
            if d < margin:
                blocker, margin = "pad@(%.2f,%.2f)" % (px, py), d
            if d < CLR - 1e-6:
                return False, blocker, margin
        if is_pth and drill_r > 0:
            dd = math.hypot(x - px, y - py) - drill_r - DR
            if dd < HOLE2HOLE:
                return False, "hole2hole pad@(%.2f,%.2f)" % (px, py), dd
    for net, x1, y1, x2, y2, hw in segs:
        if net == tnet:
            continue
        d = seg_pt(x, y, x1, y1, x2, y2) - hw - VR
        if d < margin:
            blocker, margin = "seg %s" % net, d
        if d < CLR - 1e-6:
            return False, blocker, margin
    for net, vx, vy, vr in vias:
        d = math.hypot(x - vx, y - vy)
        if net != tnet:
            dc = d - vr - VR
            if dc < margin:
                blocker, margin = "via %s" % net, dc
            if dc < CLR - 1e-6:
                return False, blocker, margin
        dh = d - vr - DR      # conservative: their copper r >= their drill r
        if 0.01 < d and dh < 0.0:
            return False, "via-drill overlap", dh
    return True, blocker, margin


print("%s [%s] at (%.3f, %.3f), %.2fx%.2f rot=%.0f, outward=(%+.0f,%+.0f)"
      % (TARGET, tnet, tx, ty, tw, th, trot, ux, uy))
print("via %.2f/%.2f, class clearance %.2f\n" % (VIA, DRILL, CLR))

results = []
# Walk outward along the pin: lateral offsets +-0.30, longitudinal 0.30
# inside the tip to 1.60 beyond it.
for lon in [round(0.30 + 0.025 * i, 3) for i in range(0, 53)]:
    for lat in [round(-0.30 + 0.025 * i, 3) for i in range(0, 25)]:
        x = tx + ux * lon + (-uy) * lat
        y = ty + uy * lon + ux * lat
        ok, blocker, margin = site_check(x, y)
        if not ok:
            continue
        # Grade: does the DRILL sit fully outside the pad copper?
        pd = pad_rect_dist(x, y, tx, ty, tw, th, trot)
        drill_out = pd >= DR
        touches = pd < VR - 0.01
        if touches:
            grade = "TANGENT" if drill_out else "IN-PAD"
        else:
            # STUB-CONNECTED: a straight 0.15-wide run from the pad tip
            # to the via, checked against every obstacle at the class
            # clearance. This is the case the blocker probe exposed:
            # /EXP_SPI_CS1 on In1.Cu shadows the whole tip band of U1's
            # left column, but 0.5 mm further out is clear -- reachable
            # only by stub. (min_track_width is 0.15, so 0.15 is legal.)
            grade = "STUB"
            sw = 0.075
            tipx, tipy = tx + ux * half_len, ty + uy * half_len
            okstub = True
            for k in range(9):
                f = k / 8.0
                sx_, sy_ = tipx + (x - tipx) * f, tipy + (y - tipy) * f
                for net, px, py, w, h, rot, is_pth, drill_r in pads:
                    if net != tnet and \
                            pad_rect_dist(sx_, sy_, px, py, w, h, rot) - sw \
                            < CLR - 1e-6:
                        okstub = False
                        break
                if okstub:
                    # The STUB lives on F.Cu only -- checking it against
                    # inner-layer segments rejected every stub site for
                    # U1's left column, where /EXP_SPI_CS1 (In1.Cu) is
                    # exactly what the stub legitimately flies over.
                    for lay, net, x1, y1, x2, y2, hw in segs_l:
                        if lay != F_CU or net == tnet:
                            continue
                        if seg_pt(sx_, sy_, x1, y1, x2, y2) - hw - sw \
                                < CLR - 1e-6:
                            okstub = False
                            break
                if okstub:
                    for net, vx, vy, vr in vias:
                        if net != tnet and \
                                math.hypot(sx_ - vx, sy_ - vy) - vr - sw \
                                < CLR - 1e-6:
                            okstub = False
                            break
                if not okstub:
                    break
            if not okstub:
                continue
        results.append((grade, margin, lon, lat, x, y, blocker))

ORDER = {"TANGENT": 0, "STUB": 1, "IN-PAD": 2}
results.sort(key=lambda r: (ORDER[r[0]], -r[1]))
if not results:
    print("NO LEGAL SITE for a %.2f/%.2f via touching this pad." % (VIA, DRILL))
for grade, margin, lon, lat, x, y, blocker in results[:8]:
    print("%-7s (%.3f, %.3f)  lon=%.3f lat=%+.3f  margin %.3f (next: %s)"
          % (grade, x, y, lon, lat, margin, blocker))
