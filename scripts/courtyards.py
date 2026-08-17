import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width, set_via_width  # noqa: F401, sys

b = pcbnew.LoadBoard(sys.argv[1])
want = set(sys.argv[2:]) if len(sys.argv) > 2 else None


def mm(v):
    return v / 1e6


for fp in b.GetFootprints():
    r = fp.GetReference()
    if want and r not in want:
        continue
    p = fp.GetPosition()
    line = "%-5s at (%7.3f,%7.3f) rot %5.1f" % (r, mm(p.x), mm(p.y), fp.GetOrientationDegrees())
    try:
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount() > 0:
            bb = cy.BBox()
            line += "  CRTYD x[%7.2f,%7.2f] y[%7.2f,%7.2f]" % (
                mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom()))
        else:
            line += "  CRTYD (empty)"
    except Exception as e:
        line += "  CRTYD err %s" % e
    print(line)
