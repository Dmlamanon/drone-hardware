"""Place fanout vias one at a time, revalidating after each.

The one-at-a-time rule is not ceremony here. U1.18 (/GND) and U1.19 (/3V3)
are adjacent pins whose best fanout sites are 0.05 mm apart -- place both
from one batch of pre-computed candidates and you short them. So each via
is chosen against the board INCLUDING every via placed before it, and a
pad whose site has been taken by a neighbour simply gets no via and is
reported.

Each via also has to satisfy both halves of the rule this project learned
the hard way: clear of other-net copper, AND inside the filled polygon of
the plane carrying that pad's net.

Usage: python place_fanouts.py <board> <REF.PAD> [...] [--clear mm] [--radius mm]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width, set_via_width  # noqa: E402

import math, re, io  # noqa: E402

argv = list(_sys.argv[1:])
BOARD = argv.pop(0)
RADIUS, CLR, VIA, DRILL, STUB_W = 3.0, 0.2, 0.6, 0.3, 0.3
targets = []
i = 0
while i < len(argv):
    if argv[i] == "--clear":
        CLR = float(argv[i + 1]); i += 2; continue
    if argv[i] == "--radius":
        RADIUS = float(argv[i + 1]); i += 2; continue
    if argv[i] == "--via":
        VIA = float(argv[i + 1]); i += 2; continue
    if argv[i] == "--drill":
        DRILL = float(argv[i + 1]); i += 2; continue
    if argv[i] == "--stub":
        STUB_W = float(argv[i + 1]); i += 2; continue
    targets.append(argv[i]); i += 1

# The board's own rules: min_via_diameter 0.45, min_through_hole_diameter
# 0.30, min_via_annular_width 0.10. So the smallest LEGAL fanout via is
# 0.50/0.30 -- 0.45/0.25 would break the hole minimum, and 0.45/0.30 would
# leave a 0.075 mm ring. Smaller vias matter here: at 0.5 mm pin pitch the
# escape channel is the constraint, and a 0.6 mm via found only one site
# out of eleven.

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
VR = VIA / 2.0


def mm(v):
    return v / MM


def V(x, y):
    return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))


# --- static geometry, read once ---
pads = []
NETS = {}
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos, sz = p.GetPosition(), p.GetSize()
        pads.append((fp.GetReference(), p.GetNumber(), p.GetNetname(),
                     mm(pos.x), mm(pos.y), math.hypot(mm(sz.x), mm(sz.y)) / 2.0))
        NETS.setdefault(p.GetNetname(), p.GetNet())
tracks, vias = [], []
for t in list(b.GetTracks()):
    NETS.setdefault(t.GetNetname(), t.GetNet())
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        vias.append((t.GetNetname(), mm(pos.x), mm(pos.y), mm(via_width(t)) / 2.0))
    else:
        s, e = t.GetStart(), t.GetEnd()
        tracks.append((t.GetNetname(), mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth())))

raw = io.open(BOARD, encoding="utf-8", newline="").read()


def sexp(text, kind):
    out = []
    for m in re.finditer(r"\(%s\b" % kind, text):
        st = m.start(); d = 0; ins = False; j = st
        while j < len(text):
            c = text[j]
            if c == '"':
                ins = not ins
            elif not ins:
                if c == "(":
                    d += 1
                elif c == ")":
                    d -= 1
                    if d == 0:
                        break
            j += 1
        out.append(text[st:j + 1])
    return out


pours = {}
for z in sexp(raw, "zone"):
    n = re.search(r'\(net(?:_name)? "([^"]*)"\)', z)
    polys = [[(float(a), float(c)) for a, c in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", fp)]
             for fp in sexp(z, "filled_polygon")]
    if n and polys:
        pours[n.group(1)] = polys


def in_pour(x, y, polys):
    for poly in polys:
        c, n = False, len(poly)
        for k in range(n):
            x1, y1 = poly[k]
            x2, y2 = poly[(k + 1) % n]
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
                c = not c
        if c:
            return True
    return False


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


placed = 0
skipped = []
for tgt in targets:
    ref, pn = tgt.split(".")
    hit = [p for p in pads if p[0] == ref and p[1] == pn]
    if not hit:
        skipped.append((tgt, "pad not found"))
        continue
    _, _, net, px, py, pr = hit[0]
    if net not in pours:
        skipped.append((tgt, "no pour on %s" % net))
        continue
    polys = pours[net]

    best = None
    step = 0.05
    n = int(RADIUS / step)
    for i2 in range(-n, n + 1):
        for j2 in range(-n, n + 1):
            x, y = px + i2 * step, py + j2 * step
            d = math.hypot(x - px, y - py)
            if d > RADIUS or d < pr + VR or (best and d >= best[0]):
                continue
            if not in_pour(x, y, polys):
                continue
            ok = True
            for r2, p2, n2, x2, y2, rr2 in pads:
                if n2 != net and math.hypot(x - x2, y - y2) - rr2 - VR < CLR:
                    ok = False; break
            if ok:
                for n2, x1, y1, x2, y2, w in tracks:
                    if n2 != net and seg_dist(x, y, x1, y1, x2, y2) - w / 2.0 - VR < CLR:
                        ok = False; break
            if ok:
                for n2, vx, vy, vr in vias:
                    if n2 != net and math.hypot(x - vx, y - vy) - vr - VR < CLR:
                        ok = False; break
            # the STUB must clear too, not just the via -- checking only the
            # via is how you get a legal via on the end of an illegal wire
            if ok:
                # Sample the stub from where it LEAVES THE PAD, not from the
                # pad centre. Inside the pad footprint the neighbouring
                # pins' own fanout traces are unavoidably close, and
                # measuring there rejects every site on the board -- which
                # is exactly what the first version did (0 of 11 placed
                # where the site search had found 8).
                t0 = min(0.95, pr / d) if d > 0 else 1.0
                stub_pts = [(px + (x - px) * (t0 + (1.0 - t0) * (k / 8.0)),
                             py + (y - py) * (t0 + (1.0 - t0) * (k / 8.0)))
                            for k in range(9)]
                for n2, x1, y1, x2, y2, w in tracks:
                    if n2 == net:
                        continue
                    for sx, sy in stub_pts:
                        if seg_dist(sx, sy, x1, y1, x2, y2) - w / 2.0 - STUB_W / 2.0 < CLR:
                            ok = False; break
                    if not ok:
                        break
                # ...and against PADS. Checking the stub against tracks only
                # is how U4.11's stub came out legal and then clipped U4's
                # own pad 10: a stub is copper and every neighbour counts,
                # not just the ones that happen to be tracks.
                if ok:
                    for r2, p2, n2, x2, y2, rr2 in pads:
                        if n2 == net or (r2 == ref and p2 == pn):
                            continue
                        for sx, sy in stub_pts:
                            if math.hypot(sx - x2, sy - y2) - rr2 - STUB_W / 2.0 < CLR:
                                ok = False; break
                        if not ok:
                            break
            if ok:
                best = (d, x, y)

    if not best:
        skipped.append((tgt, "no legal site within %.1f mm" % RADIUS))
        continue

    d, x, y = best
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y))
    set_via_width(v, int(round(VIA * MM)))
    v.SetDrill(int(round(DRILL * MM)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(NETS[net])
    b.Add(v)
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(V(px, py))
    t.SetEnd(V(x, y))
    t.SetWidth(int(round(STUB_W * MM)))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(NETS[net])
    b.Add(t)

    # register it so the NEXT pad sees it
    vias.append((net, x, y, VR))
    tracks.append((net, px, py, x, y, STUB_W))
    placed += 1
    print("placed %-8s [%-6s] via at (%7.3f, %7.3f), stub %.2f mm" % (tgt, net, x, y, d))

pcbnew.SaveBoard(BOARD, b)
print("\n%d via(s) placed, %d skipped" % (placed, len(skipped)))
for tgt, why in skipped:
    print("   skipped %-8s -- %s" % (tgt, why))
print("SAVED")
