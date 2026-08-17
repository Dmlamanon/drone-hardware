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

        # KiCad rotates CLOCKWISE in its Y-down frame. Getting this sign
        # wrong mirrors every pad of a rotated footprint about the origin
        # and the checker then cheerfully passes a placement it never
        # actually looked at -- which is exactly what happened with J10
        # (pad 2 checked at x=52.46, really at x=57.54).
        gx = fx + px * math.cos(rot) + py * math.sin(rot)
        gy = fy - px * math.sin(rot) + py * math.cos(rot)
        prad = math.hypot(sw, sh) / 2.0     # conservative: circumscribed

        for tnet, tlay, x1, y1, x2, y2, w in tracks:
            if tnet == pnet:
                continue
            if not allcu and tlay != "F.Cu":
                continue
            d = seg_dist(gx, gy, x1, y1, x2, y2) - prad - w / 2.0
            if d < CLEAR:
                worst.append((d, r.group(1), pnum, pnet, "track", tnet, tlay, gx, gy))

        for vx, vy, vr, vnet in vias:
            if vnet == pnet:
                continue
            d = math.hypot(gx - vx, gy - vy) - prad - vr
            if d < CLEAR:
                worst.append((d, r.group(1), pnum, pnet, "via", vnet, "-", gx, gy))

worst.sort()
if not worst:
    print("CLEAR: every pad of %s is >= %.2f mm from other-net copper" % (",".join(sorted(refs)), CLEAR))
else:
    print("%d clearance problem(s):" % len(worst))
    for d, ref, pnum, pnet, kind, tnet, tlay, gx, gy in worst:
        print("  %s.%s [%s] at (%.2f,%.2f) -> %s [%s] on %s : %.3f mm"
              % (ref, pnum, pnet, gx, gy, kind, tnet, tlay, d))
