"""Find a legal fanout via for a pad: clear of copper AND inside its plane.

Both halves matter and this project has been bitten by having only one.
A via that clears every neighbour but lands outside the plane's filled
polygon connects to nothing -- that was the blocker two batches ago. A
via inside the plane that clips a neighbouring pad is a short.

For each named pad this reports the best candidate sites, scored by how
far they are from the pad (short stubs have less inductance, which on a
supply pin is the whole point).

Usage:
  python fanout.py <board> <REF.PAD> [<REF.PAD> ...] [--radius mm] [--clear mm]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width  # noqa: E402

import math, re, io  # noqa: E402

argv = [a for a in _sys.argv[1:]]
BOARD = argv.pop(0)
RADIUS, CLR, VIA = 3.0, 0.2, 0.6
targets = []
i = 0
while i < len(argv):
    if argv[i] == "--radius":
        RADIUS = float(argv[i + 1]); i += 2; continue
    if argv[i] == "--clear":
        CLR = float(argv[i + 1]); i += 2; continue
    if argv[i] == "--via":
        VIA = float(argv[i + 1]); i += 2; continue
    targets.append(argv[i]); i += 1

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
VR = VIA / 2.0


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
        vias.append((t.GetNetname(), mm(pos.x), mm(pos.y), mm(via_width(t)) / 2.0))
    else:
        s, e = t.GetStart(), t.GetEnd()
        tracks.append((t.GetNetname(), mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth())))

# --- the pours, read as real filled geometry from the file ---
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
    lay = re.search(r'\(layers? "?([^")\s]+)"?\)', z)
    polys = [[(float(a), float(c)) for a, c in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", fp)]
             for fp in sexp(z, "filled_polygon")]
    if n and polys:
        pours[n.group(1)] = (lay.group(1) if lay else "?", polys)


def in_pour(x, y, polys):
    for poly in polys:
        c = False
        n = len(poly)
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


for tgt in targets:
    ref, pn = tgt.split(".")
    hit = [p for p in pads if p[0] == ref and p[1] == pn]
    if not hit:
        print("%-8s NOT FOUND" % tgt)
        continue
    _, _, net, px, py, pr = hit[0]
    if net not in pours:
        print("%-8s [%s] -- no pour on that net; a fanout via would connect to nothing" % (tgt, net))
        continue
    lay, polys = pours[net]
    print("%-8s [%-6s] at (%.3f, %.3f), pour on %s" % (tgt, net, px, py, lay))

    found = []
    step = 0.05
    n = int(RADIUS / step)
    for i2 in range(-n, n + 1):
        for j2 in range(-n, n + 1):
            x, y = px + i2 * step, py + j2 * step
            d = math.hypot(x - px, y - py)
            if d > RADIUS or d < pr + VR:
                continue
            if not in_pour(x, y, polys):
                continue
            worst, who, ok = 99.0, "", True
            for r2, p2, n2, x2, y2, r_2 in pads:
                if n2 == net:
                    continue
                g = math.hypot(x - x2, y - y2) - r_2 - VR
                if g < worst:
                    worst, who = g, "%s.%s" % (r2, p2)
                if g < CLR:
                    ok = False; break
            if ok:
                for n2, x1, y1, x2, y2, w in tracks:
                    if n2 == net:
                        continue
                    g = seg_dist(x, y, x1, y1, x2, y2) - w / 2.0 - VR
                    if g < worst:
                        worst, who = g, "track %s" % n2
                    if g < CLR:
                        ok = False; break
            if ok:
                for n2, vx, vy, vr in vias:
                    if n2 == net:
                        continue
                    g = math.hypot(x - vx, y - vy) - vr - VR
                    if g < worst:
                        worst, who = g, "via %s" % n2
                    if g < CLR:
                        ok = False; break
            if ok:
                found.append((d, x, y, worst, who))
    found.sort()
    if not found:
        print("      no legal site within %.1f mm (clear >= %.2f AND inside the pour)"
              % (RADIUS, CLR))
    for d, x, y, worst, who in found[:3]:
        print("      (%7.3f, %7.3f)  stub %.2f mm, tightest %s %.2f mm" % (x, y, d, who, worst))
    print("")
