"""MH3 rework: make room for the restored 30.5 mm mounting hole at (24.75, 45.25).

Done in one pcbnew pass so the board is never left half-changed.

WHAT AND WHY

The restored pattern puts MH3 in the buck converter's 3.3 V output node.
Three things were in the way: L1 (the inductor) courtyard, a /3V3 via, and
four /3V3 tracks on F.Cu that took the long way round exactly through where
the hole now is.

L1 moves 1.63 mm and rotates 270 deg. That position came from a search over
position and rotation (fitpart.py), not from nudging: it is the NEAREST
placement that clears the hole by >= 3.0 mm and every neighbouring courtyard
by >= 0.1 mm. Rotation 270 rather than 90 so the SW_NODE pad stays next to
the SW_NODE via -- at 90 the 3V3 pad would have landed 0.28 mm from that via,
which is a short.

The /3V3 routing changes shape rather than detouring. In2.Cu IS the 3V3
plane, so the output does not need an F.Cu trace snaking around the hole at
all: L1's output pad and the C2/R1 group each drop into the plane through a
via. Both via sites were checked point-in-polygon against the actual
filled_polygon before being placed.
"""
import sys, math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width, set_via_width  # noqa: F401
BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
MM = 1e6


def V(x, y):
    return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))


def mm(v):
    return v / MM


log = []

# Capture the net objects UP FRONT. b.GetTracks() is not safe to re-walk
# after b.Remove() in this SWIG build (it returns a bare SwigPyObject the
# second time), and GetNetsByName() is not usable at all here.
NETS = {}
for _t in list(b.GetTracks()):
    NETS.setdefault(_t.GetNetname(), _t.GetNet())
for _fp in b.GetFootprints():
    for _p in _fp.Pads():
        NETS.setdefault(_p.GetNetname(), _p.GetNet())
for _n in ("/3V3", "/SW_NODE"):
    if _n not in NETS:
        raise SystemExit("net %r not found on this board" % _n)

# ---- 1. L1 ----
L1 = b.FindFootprintByReference("L1")
old = (mm(L1.GetPosition().x), mm(L1.GetPosition().y), L1.GetOrientationDegrees())
L1.SetPosition(V(20.10, 44.70))
L1.SetOrientationDegrees(270)
log.append("L1 (%.2f,%.2f) rot %.0f -> (20.10,44.70) rot 270  [moved %.2f mm]"
           % (old[0], old[1], old[2], math.hypot(20.10 - old[0], 44.70 - old[1])))
for p in L1.Pads():
    pp = p.GetPosition()
    log.append("   pad %s [%s] now at (%.3f, %.3f)"
               % (p.GetNumber(), p.GetNetname(), mm(pp.x), mm(pp.y)))

# ---- 2. remove the copper that the hole displaces ----
DEAD_TRACKS = [
    ("/3V3", (24.8724, 46.8817), (23.1, 45.1093)),
    ("/3V3", (24.414, 47.3401), (24.8724, 46.8817)),
    ("/3V3", (24.414, 48.823), (24.414, 47.3401)),
    ("/3V3", (23.1, 45.1093), (23.1, 45.0)),
    # the SW_NODE stub ran from the via up to the OLD L1 pad; its far end
    # would now sit 0.48 mm from the 3V3 pad. The via sits inside the new
    # SW_NODE pad, so the connection is made without it.
    ("/SW_NODE", (20.3, 43.1025), (20.3, 45.0)),
]
DEAD_VIAS = [(24.8724, 46.8817)]

removed = []
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        for vx, vy in DEAD_VIAS:
            if abs(mm(p.x) - vx) < 0.002 and abs(mm(p.y) - vy) < 0.002:
                removed.append("via %s at (%.4f,%.4f)" % (t.GetNetname(), mm(p.x), mm(p.y)))
                b.Remove(t)
                break
    else:
        s, e = t.GetStart(), t.GetEnd()
        sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
        for net, (ax, ay), (bx, by) in DEAD_TRACKS:
            if t.GetNetname() != net:
                continue
            fwd = abs(sx - ax) < 0.002 and abs(sy - ay) < 0.002 and abs(ex - bx) < 0.002 and abs(ey - by) < 0.002
            rev = abs(sx - bx) < 0.002 and abs(sy - by) < 0.002 and abs(ex - ax) < 0.002 and abs(ey - ay) < 0.002
            if fwd or rev:
                removed.append("track %s (%.4f,%.4f)->(%.4f,%.4f)" % (net, sx, sy, ex, ey))
                b.Remove(t)
                break

log.append("removed %d item(s):" % len(removed))
for r in removed:
    log.append("   " + r)

def net_of(name):
    return NETS[name]


def add_track(net, x1, y1, x2, y2, width, layer):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(V(x1, y1))
    t.SetEnd(V(x2, y2))
    t.SetWidth(int(round(width * MM)))
    t.SetLayer(layer)
    t.SetNet(net_of(net))
    b.Add(t)
    log.append("   + track %s (%.3f,%.3f)->(%.3f,%.3f) w=%.2f on %s"
               % (net, x1, y1, x2, y2, width, b.GetLayerName(layer)))


def add_via(net, x, y, size=0.6, drill=0.4):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y))
    set_via_width(v, int(round(size * MM)))
    v.SetDrill(int(round(drill * MM)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net_of(net))
    b.Add(v)
    log.append("   + via %s at (%.3f,%.3f) size %.2f drill %.2f" % (net, x, y, size, drill))


log.append("added:")
# L1's 3V3 output -> the In2.Cu 3V3 plane
add_track("/3V3", 20.10, 46.10, 22.20, 46.10, 0.6, pcbnew.F_Cu)
add_via("/3V3", 22.20, 46.10)
# the C2 / R1 group -> the same plane (the via sits ON the kept track)
add_via("/3V3", 23.60, 49.136)

pcbnew.SaveBoard(BOARD, b)
print("\n".join(log))
print("\nSAVED")
