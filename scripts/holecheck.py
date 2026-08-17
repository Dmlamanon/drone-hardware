"""What is in the way of the TRUE 30.5 mm mounting pattern?

Reports, for each of the four true hole positions, every footprint pad,
track and via that falls inside the hole's keepout radius. A mounting hole
is a physical hole through the board -- copper in that circle is not a
clearance problem, it is drilled away.

Usage: python holecheck.py <board.kicad_pcb> [keepout_radius_mm]
"""
import io, re, sys, math

PATH = sys.argv[1]
KEEP = float(sys.argv[2]) if len(sys.argv) > 2 else 3.3   # 3.2 mm hole + pad ring

TRUE = {
    "MH1": (24.75, 14.75),
    "MH2": (55.25, 14.75),
    "MH3": (24.75, 45.25),
    "MH4": (55.25, 45.25),
}

s = io.open(PATH, encoding="utf-8", newline="").read()


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


# --- footprints and their pads / courtyards ---
fps = [m.start() for m in re.finditer(r'\(footprint "', s)]
parts = []
for i, st in enumerate(fps):
    end = fps[i + 1] if i + 1 < len(fps) else len(s)
    b = s[st:end]
    r = re.search(r'\(property "Reference" "([^"]+)"', b)
    a = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", b)
    if not r or not a:
        continue
    ref = r.group(1)
    fx, fy = float(a.group(1)), float(a.group(2))
    rot = math.radians(float(a.group(3) or 0))
    pads = []
    for pm in re.finditer(
        r'\(pad "([^"]*)" \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\)\s*'
        r"\(size ([-\d.]+) ([-\d.]+)\)", b):
        px, py = float(pm.group(2)), float(pm.group(3))
        sw, sh = float(pm.group(4)), float(pm.group(5))
        gx = fx + px * math.cos(rot) + py * math.sin(rot)
        gy = fy - px * math.sin(rot) + py * math.cos(rot)
        pads.append((pm.group(1), gx, gy, math.hypot(sw, sh) / 2.0))
    parts.append((ref, fx, fy, pads))

tracks = []
for m in re.finditer(
    r"\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*"
    r'\(width ([-\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net "([^"]*)"\)', s):
    tracks.append((m.group(7), m.group(6), *map(float, m.group(1, 2, 3, 4, 5))))

vias = []
for m in re.finditer(
    r'\(via\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+)\)'
    r'(?:(?!\(via ).)*?\(net "([^"]*)"\)', s, re.S):
    vias.append((float(m.group(1)), float(m.group(2)), float(m.group(3)) / 2.0, m.group(4)))

total = 0
for name, (hx, hy) in TRUE.items():
    hits_pads, hits_tracks, hits_vias = [], [], []
    for ref, fx, fy, pads in parts:
        if ref.startswith("MH"):
            continue
        for pn, gx, gy, pr in pads:
            d = math.hypot(gx - hx, gy - hy) - pr
            if d < KEEP:
                hits_pads.append((d, ref, pn, gx, gy))
        # also flag a body that overlaps even if no pad does
        if not any(h[1] == ref for h in hits_pads):
            if math.hypot(fx - hx, fy - hy) < KEEP + 3.0:
                hits_pads.append((math.hypot(fx - hx, fy - hy), ref, "(body)", fx, fy))
    for net, lay, x1, y1, x2, y2, w in tracks:
        d = seg_dist(hx, hy, x1, y1, x2, y2) - w / 2.0
        if d < KEEP:
            hits_tracks.append((d, net, lay))
    for vx, vy, vr, vnet in vias:
        d = math.hypot(vx - hx, vy - hy) - vr
        if d < KEEP:
            hits_vias.append((d, vnet, vx, vy))

    n = len(hits_pads) + len(hits_tracks) + len(hits_vias)
    total += n
    print("%s at (%.2f, %.2f) -- %d obstruction(s) within %.2f mm"
          % (name, hx, hy, n, KEEP))
    for d, ref, pn, gx, gy in sorted(hits_pads):
        print("    PAD   %-5s pad %-6s at (%.2f,%.2f)  gap %.2f mm" % (ref, pn, gx, gy, d))
    for d, net, lay in sorted(hits_tracks):
        print("    TRACK %-12s on %-7s gap %.2f mm" % (net, lay, d))
    for d, net, vx, vy in sorted(hits_vias):
        print("    VIA   %-12s at (%.2f,%.2f) gap %.2f mm" % (net, vx, vy, d))
    if n == 0:
        print("    clear")

print("\nTOTAL obstructions: %d" % total)
sys.exit(1 if total else 0)
