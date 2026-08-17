"""Add a routed path (tracks + vias) to a board, without deleting anything.

  python addroute.py <board> <net> <width> SPEC [SPEC ...]

SPEC is either
    <layer>:<x>,<y>          a point on that layer
    via:<x>,<y>[:size:drill] a via at that point

Consecutive points on the SAME layer become a track. A `via` between two
points on different layers is what carries the net across. Nothing is
written unless every spec parses.

Imports kicad_safe first: this runs unattended and a wxWidgets assert
dialog would stall the batch (see docs/tooling-preflight-2026-08-17c.md).
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(_os.path.abspath(__file__))))
from kicad_safe import pcbnew, set_via_width  # noqa: E402

BOARD, NET, WIDTH = _sys.argv[1], _sys.argv[2], float(_sys.argv[3])
SPECS = _sys.argv[4:]

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
LAYERS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu,
          "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}


def V(x, y):
    return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))


NETS = {}
for t in list(b.GetTracks()):
    NETS.setdefault(t.GetNetname(), t.GetNet())
for fp in b.GetFootprints():
    for p in fp.Pads():
        NETS.setdefault(p.GetNetname(), p.GetNet())
if NET not in NETS:
    raise SystemExit("net %r not on this board" % NET)
netobj = NETS[NET]

parsed = []
for sp in SPECS:
    parts = sp.split(":")
    if parts[0] == "via":
        x, y = (float(v) for v in parts[1].split(","))
        size = float(parts[2]) if len(parts) > 2 else 0.6
        drill = float(parts[3]) if len(parts) > 3 else 0.4
        parsed.append(("via", x, y, size, drill))
    else:
        lay = parts[0]
        if lay not in LAYERS:
            raise SystemExit("unknown layer %r" % lay)
        x, y = (float(v) for v in parts[1].split(","))
        parsed.append(("pt", x, y, lay, None))

added = []
prev = None
for item in parsed:
    if item[0] == "via":
        _, x, y, size, drill = item
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(V(x, y))
        set_via_width(v, int(round(size * MM)))
        v.SetDrill(int(round(drill * MM)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(netobj)
        b.Add(v)
        added.append("via  at (%.3f, %.3f)  %.2f/%.2f mm" % (x, y, size, drill))
        prev = None
        continue
    _, x, y, lay, _u = item
    if prev is not None and prev[2] == lay:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(prev[0], prev[1]))
        t.SetEnd(V(x, y))
        t.SetWidth(int(round(WIDTH * MM)))
        t.SetLayer(LAYERS[lay])
        t.SetNet(netobj)
        b.Add(t)
        added.append("track (%.3f,%.3f)->(%.3f,%.3f) on %-6s w=%.2f"
                     % (prev[0], prev[1], x, y, lay, WIDTH))
    prev = (x, y, lay)

pcbnew.SaveBoard(BOARD, b)
print("%s: added %d item(s)" % (NET, len(added)))
for a in added:
    print("   + " + a)
print("SAVED")
