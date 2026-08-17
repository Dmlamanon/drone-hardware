"""Minimum distance from each named component's pads to every OTHER net's
existing copper (tracks and vias), on the layers that pad actually occupies.

Written after placing the buzzer block on top of a 15.7 mm NRST track: the
placement had been chosen by looking at component bounding boxes only, and
component bounding boxes say nothing about routed copper. check_placement_
clearance does not catch this either -- it classifies body/courtyard/silk,
not tracks.

Usage: python padclear.py <board.kicad_pcb> REF [REF ...]
"""
import io, re, sys, math

path = sys.argv[1]
refs = set(sys.argv[2:])
s = io.open(path, encoding="utf-8", newline="").read()

CLEAR = 0.20   # board setup copper clearance, mm


s_src = s


def sexp_blocks(text, kind):
    """Every balanced (kind ...) block in `text`. Needed because zones and
    their filled_polygons are nested and cannot be matched with a flat
    regex."""
    out = []
    for m in re.finditer(r"\(%s\b" % kind, text):
        st = m.start()
        d = 0
        ins = False
        i = st
        while i < len(text):
            ch = text[i]
            if ch == '"':
                ins = not ins
            elif not ins:
                if ch == "(":
                    d += 1
                elif ch == ")":
                    d -= 1
                    if d == 0:
                        break
            i += 1
        out.append(text[st:i + 1])
    return out


FRONT, BACK = "F.Cu", "B.Cu"
ALL_CU = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


tracks = []
for m in re.finditer(r'\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*'
                     r'\(width ([-\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net "([^"]*)"\)', s):
    tracks.append((m.group(7), m.group(6), float(m.group(1)), float(m.group(2)),
                   float(m.group(3)), float(m.group(4)), float(m.group(5))))

# Vias carry a net too. Ignoring it makes a deliberate stitching via next
# to its own pad look like a clearance failure, and a checker that cries
# wolf on correct work is a checker people stop reading.
vias = []
for m in re.finditer(r'\(via\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+)\)'
                     r'(?:(?!\(via ).)*?\(net "([^"]*)"\)', s, re.S):
    vias.append((float(m.group(1)), float(m.group(2)), float(m.group(3)) / 2.0, m.group(4)))

# footprints: origin, rotation, pads
fps = [m.start() for m in re.finditer(r'\(footprint "', s)]
worst = []
thru_pads = []
for i, st in enumerate(fps):
    end = fps[i + 1] if i + 1 < len(fps) else len(s)
    b = s[st:end]
    r = re.search(r'\(property "Reference" "([^"]+)"', b)
    if not r or r.group(1) not in refs:
        continue
    a = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
    fx, fy = float(a.group(1)), float(a.group(2))
    rot = math.radians(float(a.group(3) or 0))

    for pm in re.finditer(r'\(pad "([^"]*)" (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\)\s*'
                          r'\(size ([-\d.]+) ([-\d.]+)\)((?:(?!\(pad ).)*?)(?=\(pad |\Z)', b, re.S):
        pnum, ptype = pm.group(1), pm.group(2)
        px, py = float(pm.group(3)), float(pm.group(4))
        sw, sh = float(pm.group(5)), float(pm.group(6))
        tail = pm.group(7)
        nm = re.search(r'\(net "([^"]*)"\)', tail)
        pnet = nm.group(1) if nm else ""
        lays = re.search(r'\(layers ([^)]*)\)', tail)
        laytxt = lays.group(1) if lays else '"F.Cu"'
        allcu = "*.Cu" in laytxt
        front = ("F.Cu" in laytxt) or allcu
        back = ("B.Cu" in laytxt) and not front

        # KiCad rotates CLOCKWISE in its Y-down frame. Getting this sign
        # wrong mirrors every pad of a rotated footprint about the origin
        # and the checker then cheerfully passes a placement it never
        # actually looked at -- which is exactly what happened with J10
        # (pad 2 checked at x=52.46, really at x=57.54).
        gx = fx + px * math.cos(rot) + py * math.sin(rot)
        gy = fy - px * math.sin(rot) + py * math.cos(rot)
        prad = math.hypot(sw, sh) / 2.0     # conservative: circumscribed

        # Compare a pad only against copper on the layer(s) it actually
        # occupies. The first version hard-coded "F.Cu" here, so a
        # bottom-side SMD pad was checked against TOP-side tracks and
        # against nothing on its own layer -- a guaranteed false PASS. It
        # did not bite because every part checked so far is top-side.
        pad_layers = ALL_CU if allcu else ([FRONT] if front else [BACK])
        for tnet, tlay, x1, y1, x2, y2, w in tracks:
            if tnet == pnet:
                continue
            if tlay not in pad_layers:
                continue
            d = seg_dist(gx, gy, x1, y1, x2, y2) - prad - w / 2.0
            if d < CLEAR:
                worst.append((d, r.group(1), pnum, pnet, "track", tnet, tlay, gx, gy))

        if allcu:
            thru_pads.append((r.group(1), pnum, pnet, gx, gy, prad, allcu))

        for vx, vy, vr, vnet in vias:
            if vnet == pnet:
                continue
            d = math.hypot(gx - vx, gy - vy) - prad - vr
            if d < CLEAR:
                worst.append((d, r.group(1), pnum, pnet, "via", vnet, "-", gx, gy))

# ---------------------------------------------------------------------
# ZONES. This section exists because the documentation claimed the tool
# did it and the tool did not: a via or through-hole pad has to land
# INSIDE the filled polygon of the plane carrying its own net, and has to
# stay clear of the filled polygons of every OTHER net's plane.
#
# The point-in-polygon work had been done once, ad hoc, in a throwaway
# script, and then written up as if this committed checker performed it.
# An independent review ran this file and got CLEAR on a placement that
# KiCad's own DRC flagged with eight zone errors. Now it is here.
zones = []
for zb in sexp_blocks(s_src, "zone"):
    # This board writes the zone's net as (net "NAME"), not (net_name ...).
    # Getting it wrong is silent: the checker still finds the zone and just
    # reports it with a blank name, and -- worse -- the "is this pad on the
    # SAME net as the pour" test never matches, so a via correctly landing
    # in its own pour would be reported as a fault.
    zname = re.search(r'\(net(?:_name)? "([^"]*)"\)', zb)
    zlay = re.search(r'\(layers? "?([^")\s]+)"?\)', zb)
    polys = []
    for fp in sexp_blocks(zb, "filled_polygon"):
        polys.append([(float(a), float(b))
                      for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", fp)])
    if polys:
        zones.append((zname.group(1) if zname else "", zlay.group(1) if zlay else "?", polys))


def pt_in_poly(x, y, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            c = not c
    return c


def poly_edge_dist(x, y, poly):
    best = 1e9
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        best = min(best, seg_dist(x, y, x1, y1, x2, y2))
    return best


zone_notes = []
for ref, pnum, pnet, gx, gy, prad, allcu in thru_pads:
    for znet, zlay, polys in zones:
        inside = any(pt_in_poly(gx, gy, pz) for pz in polys)
        d = min(poly_edge_dist(gx, gy, pz) for pz in polys)
        if znet == pnet:
            if not inside:
                zone_notes.append("  %s.%s [%s] at (%.2f,%.2f) is OUTSIDE its own "
                                  "%s pour on %s (nearest edge %.2f mm) -- it connects to NOTHING"
                                  % (ref, pnum, pnet, gx, gy, znet, zlay, d))
        else:
            if inside or d < prad + CLEAR:
                zone_notes.append("  %s.%s [%s] at (%.2f,%.2f) is %s the %s pour on %s "
                                  "(%.2f mm) -- needs an antipad; refill the zones"
                                  % (ref, pnum, pnet, gx, gy,
                                     "INSIDE" if inside else "within %.2f mm of" % d,
                                     znet, zlay, d))

worst.sort()
if not worst and not zone_notes:
    print("CLEAR: every pad of %s is >= %.2f mm from other-net tracks and vias,"
          % (",".join(sorted(refs)), CLEAR))
    print("       and every through-hole pad sits correctly against the plane pours.")
elif worst:
    print("%d clearance problem(s):" % len(worst))
    for d, ref, pnum, pnet, kind, tnet, tlay, gx, gy in worst:
        print("  %s.%s [%s] at (%.2f,%.2f) -> %s [%s] on %s : %.3f mm"
              % (ref, pnum, pnet, gx, gy, kind, tnet, tlay, d))

if zone_notes:
    print("%d zone problem(s):" % len(zone_notes))
    for n in zone_notes:
        print(n)
