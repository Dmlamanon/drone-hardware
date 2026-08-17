"""WHY is there no legal fanout site? Not whether -- why.

`place_fanouts.py` answers "how many legal sites" and gets zero. Zero is
the right number (verified twice), but zero does not say what to DO about
it, and the manual guide was written as though it did: it attributed the
zero to 0.5 mm pin pitch and told a human to drag the traces that own
each escape channel.

If the binding constraint is actually that the plane does not reach the
pad, there are no traces to drag and that advice burns a session.

So this counts, for every candidate site in the search annulus, which
constraints it fails -- INDEPENDENTLY, not first-failure-wins, because
first-failure-wins just reports whatever the code happens to test first.

Two numbers decide it per pad:

  * clear of copper, ignoring the pour  -> is congestion binding?
  * inside the pour, ignoring copper    -> is plane reach binding?

If the first is large and the second is zero, the fix is the plane, not
the routing. Reports nothing but counts; it never modifies the board.

Usage: <kicad python> why_no_fanout.py board.kicad_pcb PAD [PAD ...]
"""
import sys as _sys
import os

_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width  # noqa: E402  (disables wx asserts)

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
    targets.append(argv[i]); i += 1

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
VR = VIA / 2.0


def mm(v):
    return v / MM


# TRUE PAD GEOMETRY, not a circumscribed circle.
#
# place_fanouts.py models every pad as a disc of radius hypot(w,h)/2. For
# U1's 1.55 x 0.30 mm LQFP pad that is a 0.789 mm disc against a true
# half-height of 0.15 mm -- it inflates the obstacle by 0.639 mm
# perpendicular to the pad, more than 3x the 0.2 mm clearance rule. That
# does not change the ANSWER (zero legal sites either way, checked), but
# it completely changes WHICH constraint you conclude is binding, and the
# whole point of this script is to attribute the blame correctly.
pads = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos, sz = p.GetPosition(), p.GetSize()
        try:
            ang = p.GetOrientationDegrees()
        except Exception:
            ang = 0.0
        pads.append((fp.GetReference(), p.GetNumber(), p.GetNetname(),
                     mm(pos.x), mm(pos.y), mm(sz.x), mm(sz.y), ang))


def pad_dist(x, y, cx, cy, w, h, ang_deg):
    """Distance from a point to a rotated rectangle; 0 if inside."""
    a = math.radians(-ang_deg)
    dx, dy = x - cx, y - cy
    ca, sa = math.cos(a), math.sin(a)
    rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
    ex = max(0.0, abs(rx) - w / 2.0)
    ey = max(0.0, abs(ry) - h / 2.0)
    return math.hypot(ex, ey)
tracks, vias = [], []
for t in list(b.GetTracks()):
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


print("candidate-site rejection census   via %.2f mm, clearance %.2f mm, "
      "search radius %.1f mm" % (VIA, CLR, RADIUS))
print("")
print("  %-8s %8s %9s %9s %8s   %s"
      % ("pad", "annulus", "copper-ok", "in-pour", "BOTH", "binding constraint"))
print("  %s" % ("-" * 76))

verdicts = {}
for tgt in targets:
    ref, pn = tgt.split(".")
    hit = [p for p in pads if p[0] == ref and p[1] == pn]
    if not hit:
        print("  %-8s pad not found" % tgt)
        continue
    _, _, net, px, py, pw, ph, pa = hit[0]
    pr = math.hypot(pw, ph) / 2.0   # own pad: circumscribed is correct here,
                                    # the via must clear the WHOLE pad
    polys = pours.get(net)
    if polys is None:
        print("  %-8s no pour on %s" % (tgt, net))
        continue

    n_annulus = n_copper = n_pour = n_both = 0
    n_via_bad = n_via_ok_stub_bad = 0
    step = 0.05
    n = int(RADIUS / step)
    for i2 in range(-n, n + 1):
        for j2 in range(-n, n + 1):
            x, y = px + i2 * step, py + j2 * step
            d = math.hypot(x - px, y - py)
            if d > RADIUS or d < pr + VR:
                continue
            n_annulus += 1

            # --- constraint A: clear of other-net copper (via AND stub) ---
            ok = True
            for r2, p2, n2, x2, y2, w2, h2, a2 in pads:
                if n2 != net and pad_dist(x, y, x2, y2, w2, h2, a2) - VR < CLR:
                    ok = False; break
            if ok:
                for n2, x1, y1, x2, y2, w in tracks:
                    if n2 != net and seg_dist(x, y, x1, y1, x2, y2) - w / 2.0 - VR < CLR:
                        ok = False; break
            if ok:
                for n2, vx, vy, vr in vias:
                    if n2 != net and math.hypot(x - vx, y - vy) - vr - VR < CLR:
                        ok = False; break
            if ok:
                t0 = min(0.95, pr / d) if d > 0 else 1.0
                stub_pts = [(px + (x - px) * (t0 + (1.0 - t0) * (k / 8.0)),
                             py + (y - py) * (t0 + (1.0 - t0) * (k / 40.0)))
                            for k in range(41)]
                for n2, x1, y1, x2, y2, w in tracks:
                    if n2 == net:
                        continue
                    for sx, sy in stub_pts:
                        if seg_dist(sx, sy, x1, y1, x2, y2) - w / 2.0 - STUB_W / 2.0 < CLR:
                            ok = False; break
                    if not ok:
                        break
                if ok:
                    for r2, p2, n2, x2, y2, w2, h2, a2 in pads:
                        if n2 == net or (r2 == ref and p2 == pn):
                            continue
                        for sx, sy in stub_pts:
                            if pad_dist(sx, sy, x2, y2, w2, h2, a2) - STUB_W / 2.0 < CLR:
                                ok = False; break
                        if not ok:
                            break
                # ...AND against VIAS. This is the third time this same
                # omission has bitten: the stub was checked against tracks
                # but not pads (a stub clipped U4 pad 10), then against
                # tracks and pads but not vias -- and DRC caught a 1.60 mm
                # /GND stub landing on a /MPU_INT via. A stub is copper and
                # EVERY class of neighbour counts, not the ones the author
                # happened to think of.
                if ok:
                    for n2, vx, vy, vr in vias:
                        if n2 == net:
                            continue
                        for sx, sy in stub_pts:
                            if math.hypot(sx - vx, sy - vy) - vr - STUB_W / 2.0 < CLR:
                                ok = False; break
                        if not ok:
                            break
            copper_ok = ok

            # WHICH copper constraint binds? Evaluated independently too:
            # if the answer is 'the stub', the escape-channel story is
            # right and a human has traces to drag. If it is 'the via
            # body', it is not.
            if not ok:
                v_ok = True
                for r2, p2, n2, x2, y2, w2, h2, a2 in pads:
                    if n2 != net and pad_dist(x, y, x2, y2, w2, h2, a2) - VR < CLR:
                        v_ok = False; break
                if v_ok:
                    for n2, x1, y1, x2, y2, w in tracks:
                        if n2 != net and seg_dist(x, y, x1, y1, x2, y2) - w / 2.0 - VR < CLR:
                            v_ok = False; break
                if v_ok:
                    for n2, vx, vy, vr in vias:
                        if n2 != net and math.hypot(x - vx, y - vy) - vr - VR < CLR:
                            v_ok = False; break
                if v_ok:
                    n_via_ok_stub_bad += 1
                else:
                    n_via_bad += 1

            # --- constraint B: inside the pour, evaluated INDEPENDENTLY ---
            pour_ok = in_pour(x, y, polys)

            if copper_ok:
                n_copper += 1
            if pour_ok:
                n_pour += 1
            if copper_ok and pour_ok:
                n_both += 1

    if n_both:
        verdict = "none -- %d legal site(s)" % n_both
    elif n_pour == 0 and n_copper > 0:
        verdict = "PLANE REACH (no copper problem at all)"
    elif n_copper == 0 and n_pour > 0:
        verdict = "congestion"
    elif n_copper == 0 and n_pour == 0:
        verdict = "both"
    else:
        verdict = "disjoint (each alone is satisfiable)"
    verdicts[tgt] = verdict
    print("  %-8s %8d %9d %9d %8d   %s"
          % (tgt, n_annulus, n_copper, n_pour, n_both, verdict))
    if n_copper == 0 and n_annulus:
        print("           of the %d copper rejections: %d the VIA BODY, "
              "%d the STUB only (%.0f%% stub)"
              % (n_annulus, n_via_bad, n_via_ok_stub_bad,
                 100.0 * n_via_ok_stub_bad / max(1, n_annulus)))

print("")
plane = [t for t, v in verdicts.items() if v.startswith("PLANE")]
cong = [t for t, v in verdicts.items() if v == "congestion"]
print("  plane reach is the ONLY blocker for %d of %d pads: %s"
      % (len(plane), len(verdicts), ", ".join(plane) or "-"))
print("  congestion is the only blocker for  %d of %d pads: %s"
      % (len(cong), len(verdicts), ", ".join(cong) or "-"))
print("")
print("  A pad in the first list has NO trace to drag. Telling a human to")
print("  widen its escape channel sends them after copper that is not")
print("  there; the fix is to close the plane void under the part.")
