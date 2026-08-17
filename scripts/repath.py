"""Replace a net's tracks on one layer, inside a region, with a new path.

  python repath.py <board> <net> <layer> --box x1 y1 x2 y2 --path x,y x,y ...
  python repath.py <board> <net> <layer> --del x1,y1,x2,y2 [...] --path x,y ...

Nets are captured before any removal: this SWIG build returns a bare
SwigPyObject from GetTracks() once Remove() has been called, so anything
needing the net list has to read it first.

Prints what it removed and what it added. Nothing is written unless the
new path is fully specified.
"""
import sys, math
import pcbnew

args = sys.argv[1:]
BOARD, NET, LAYER = args[0], args[1], args[2]
rest = args[3:]

box = None
dels = []
path = []
mode = None
for a in rest:
    if a == "--box":
        mode = "box"; continue
    if a == "--del":
        mode = "del"; continue
    if a == "--path":
        mode = "path"; continue
    if mode == "box":
        box = (box or []) + [float(a)]
    elif mode == "del":
        dels.append(tuple(float(v) for v in a.split(",")))
    elif mode == "path":
        path.append(tuple(float(v) for v in a.split(",")))

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
LAYERID = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu,
           "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}[LAYER]


def mm(v):
    return v / MM


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

WIDTH = None
removed = []
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        continue
    if t.GetNetname() != NET or t.GetLayer() != LAYERID:
        continue
    s, e = t.GetStart(), t.GetEnd()
    sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
    hit = False
    if box:
        x1, y1, x2, y2 = box
        lo_x, hi_x = min(x1, x2), max(x1, x2)
        lo_y, hi_y = min(y1, y2), max(y1, y2)
        if (lo_x <= sx <= hi_x and lo_y <= sy <= hi_y) or (lo_x <= ex <= hi_x and lo_y <= ey <= hi_y):
            hit = True
    for d in dels:
        ax, ay, bx, by = d
        if ((abs(sx - ax) < 0.002 and abs(sy - ay) < 0.002 and abs(ex - bx) < 0.002 and abs(ey - by) < 0.002)
                or (abs(sx - bx) < 0.002 and abs(sy - by) < 0.002 and abs(ex - ax) < 0.002 and abs(ey - ay) < 0.002)):
            hit = True
    if hit:
        WIDTH = WIDTH or mm(t.GetWidth())
        removed.append("(%.4f,%.4f)->(%.4f,%.4f) w=%.2f" % (sx, sy, ex, ey, mm(t.GetWidth())))
        b.Remove(t)

if not removed:
    raise SystemExit("nothing matched -- board untouched")
if len(path) < 2:
    raise SystemExit("removed nothing because --path needs at least 2 points")

print("%s on %s: removed %d segment(s)" % (NET, LAYER, len(removed)))
for r in removed:
    print("   - " + r)

added = 0
for k in range(len(path) - 1):
    (ax, ay), (bx, by) = path[k], path[k + 1]
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(V(ax, ay))
    t.SetEnd(V(bx, by))
    t.SetWidth(int(round(WIDTH * MM)))
    t.SetLayer(LAYERID)
    t.SetNet(netobj)
    b.Add(t)
    added += 1
    print("   + (%.4f,%.4f)->(%.4f,%.4f)" % (ax, ay, bx, by))

pcbnew.SaveBoard(BOARD, b)
old_len = 0.0
new_len = sum(math.hypot(path[k + 1][0] - path[k][0], path[k + 1][1] - path[k][1])
              for k in range(len(path) - 1))
print("   %d -> %d segments, new length %.2f mm. SAVED" % (len(removed), added, new_len))
