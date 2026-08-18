"""Which copper is actually CONNECTED, and where is the real plane? (batch 6)

Read-only. Three subcommands:

  islands <net>              group the net's copper into touching islands,
                             and say which reach the MAIN plane polygon --
                             the largest filled polygon, not just any fill.
                             Batch 4's "for free" claim died on exactly
                             that distinction: J3's shields touch a GND
                             islet that goes nowhere.

  vias <net> <x> <y> [r]     the net's PLANE-CONNECTED vias/PTH nearest to
                             a point: existing safe landing sites for a
                             B.Cu or F.Cu hop.

  nearcu <layer> <x> <y> [r] every OTHER-net copper item on one layer near
                             a point -- the obstacle picture for a planned
                             trace, including PTH/via annuli which exist
                             on every layer.

Usage: <kicad python> island_map.py <subcommand> ...
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_safe import pcbnew, via_width  # noqa: E402

import math  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOARD = os.path.join(HW, "bench_board", "bench_board.kicad_pcb")

b = pcbnew.LoadBoard(BOARD)
MM = 1e6
PLANE = {"/GND": "In1.Cu", "/3V3": "In2.Cu"}


def mm(v):
    return v / MM


def V(x, y):
    return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))


def seg_pt_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def seg_seg_dist(a, c, d, e):
    """Min distance between segments a-c and d-e ((x,y) tuples)."""
    best = min(seg_pt_dist(a[0], a[1], d[0], d[1], e[0], e[1]),
               seg_pt_dist(c[0], c[1], d[0], d[1], e[0], e[1]),
               seg_pt_dist(d[0], d[1], a[0], a[1], c[0], c[1]),
               seg_pt_dist(e[0], e[1], a[0], a[1], c[0], c[1]))
    return best


def main_fill(net):
    """(zone, layer_id, main_poly_index, areas). Largest polygon = plane."""
    layer = PLANE[net]
    lid = b.GetLayerID(layer)
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != net:
            continue
        polys = z.GetFilledPolysList(lid)
        areas = []
        for i in range(polys.OutlineCount()):
            ch = polys.COutline(i)
            # shoelace, holes ignored -- ranking only
            s = 0.0
            n = ch.PointCount()
            for k in range(n):
                p1, p2 = ch.CPoint(k), ch.CPoint((k + 1) % n)
                s += mm(p1.x) * mm(p2.y) - mm(p2.x) * mm(p1.y)
            areas.append(abs(s) / 2.0)
        return z, lid, (areas.index(max(areas)) if areas else -1), areas
    return None, None, -1, []


def poly_outline_dist(polys, idx, x, y):
    """Distance from a point to one outline's boundary, mm."""
    ch = polys.COutline(idx)
    n = ch.PointCount()
    best = 1e9
    for k in range(n):
        p1, p2 = ch.CPoint(k), ch.CPoint((k + 1) % n)
        best = min(best, seg_pt_dist(x, y, mm(p1.x), mm(p1.y),
                                     mm(p2.x), mm(p2.y)))
    return best


def poly_contains_outline(polys, idx, x, y):
    """Point-in-one-specific-outline (ignoring its holes -- good enough
    for 'which lobe', wrong for 'exact copper here'; DRC stays the
    authority)."""
    ch = polys.COutline(idx)
    n = ch.PointCount()
    c = False
    for k in range(n):
        p1, p2 = ch.CPoint(k), ch.CPoint((k + 1) % n)
        x1, y1, x2, y2 = mm(p1.x), mm(p1.y), mm(p2.x), mm(p2.y)
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


class Item:
    def __init__(self, kind, name, layers, geom, r):
        self.kind, self.name = kind, name
        self.layers = layers        # set of layer ids ("*" = all copper)
        self.geom = geom            # point (x,y) or seg ((x1,y1),(x2,y2))
        self.r = r                  # half-width / radius


def collect(net):
    items = []
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != net:
                continue
            pos, sz = p.GetPosition(), p.GetSize()
            layers = ("*",) if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else \
                     tuple(l for l in (F, B) if p.IsOnLayer(l))
            items.append(Item("pad", "%s.%s" % (fp.GetReference(), p.GetNumber()),
                              layers, (mm(pos.x), mm(pos.y)),
                              max(mm(sz.x), mm(sz.y)) / 2.0))
    for t in b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            items.append(Item("via", "via", ("*",),
                              (mm(pos.x), mm(pos.y)), mm(via_width(t)) / 2.0))
        else:
            s, e = t.GetStart(), t.GetEnd()
            items.append(Item("seg", "seg", (t.GetLayer(),),
                              ((mm(s.x), mm(s.y)), (mm(e.x), mm(e.y))),
                              mm(t.GetWidth()) / 2.0))
    return items


def touch(a, c):
    shared = ("*" in a.layers or "*" in c.layers or
              any(l in c.layers for l in a.layers))
    if not shared:
        return False
    if a.kind != "seg" and c.kind != "seg":
        ax, ay = a.geom
        cx, cy = c.geom
        return math.hypot(ax - cx, ay - cy) <= a.r + c.r + 0.01
    if a.kind == "seg" and c.kind == "seg":
        return seg_seg_dist(a.geom[0], a.geom[1], c.geom[0], c.geom[1]) \
            <= a.r + c.r + 0.01
    seg, pt = (a, c) if a.kind == "seg" else (c, a)
    d = seg_pt_dist(pt.geom[0], pt.geom[1], seg.geom[0][0], seg.geom[0][1],
                    seg.geom[1][0], seg.geom[1][1])
    return d <= seg.r + pt.r + 0.01


def build_islands(net):
    items = collect(net)
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if touch(items[i], items[j]):
                union(i, j)

    zone, lid, main_idx, areas = main_fill(net)
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)

    out = []
    polys = zone.GetFilledPolysList(lid) if zone else None
    for root, members in groups.items():
        connected = False
        for it in members:
            if "*" not in it.layers:      # only barrels touch inner planes
                continue
            x, y = it.geom
            if polys is None or main_idx < 0:
                continue
            # A thermally-relieved PTH connects through SPOKES, and its
            # CENTRE sits in void-space that is usually a fjord of the
            # outer contour, not an enclosed hole -- so plain containment
            # called nine genuinely-connected header pads "islands" and
            # made this map disagree with DRC's own cluster arithmetic
            # (8 GND clusters implied by 7 ratsnest edges; this said 21).
            # Connected = the main polygon's boundary passes within the
            # pad's copper radius of its centre (a spoke or solid fill
            # touching the annulus), OR the centre is inside outright.
            if poly_contains_outline(polys, main_idx, x, y) or \
                    poly_outline_dist(polys, main_idx, x, y) <= it.r + 0.01:
                connected = True
                break
        out.append((connected, members))
    return out, areas, main_idx


def cmd_islands(net):
    islands, areas, main_idx = build_islands(net)
    print("%s: filled polygon areas (mm^2): %s   <- #%d is THE plane"
          % (net, ["%.0f" % a for a in areas], main_idx))
    islands.sort(key=lambda t: (t[0], -len(t[1])))
    for connected, members in islands:
        if connected and len(members) > 12:
            print("  CONNECTED main component: %d items (not listed)"
                  % len(members))
            continue
        pads = [m.name for m in members if m.kind == "pad"]
        segs = sum(1 for m in members if m.kind == "seg")
        vias = sum(1 for m in members if m.kind == "via")
        xs = [m.geom[0] if m.kind != "seg" else m.geom[0][0] for m in members]
        ys = [m.geom[1] if m.kind != "seg" else m.geom[0][1] for m in members]
        print("  %-12s pads=%-28s segs=%d vias=%d  near (%.1f, %.1f)"
              % ("CONNECTED" if connected else "ISLAND",
                 ",".join(pads) or "-", segs, vias,
                 sum(xs) / len(xs), sum(ys) / len(ys)))


def cmd_vias(net, x, y, r):
    zone, lid, main_idx, _ = main_fill(net)
    polys = zone.GetFilledPolysList(lid)
    hits = []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net:
            pos = t.GetPosition()
            vx, vy = mm(pos.x), mm(pos.y)
            d = math.hypot(vx - x, vy - y)
            if d <= r and poly_contains_outline(polys, main_idx, vx, vy):
                hits.append((d, vx, vy, mm(via_width(t))))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                pos = p.GetPosition()
                vx, vy = mm(pos.x), mm(pos.y)
                d = math.hypot(vx - x, vy - y)
                if d <= r and poly_contains_outline(polys, main_idx, vx, vy):
                    hits.append((d, vx, vy, -1.0))
    hits.sort()
    print("%s plane-connected vias/PTH within %.1f mm of (%.2f, %.2f):"
          % (net, r, x, y))
    for d, vx, vy, w in hits[:15]:
        print("  (%.3f, %.3f)  %s  %.2f mm away"
              % (vx, vy, "PTH" if w < 0 else ("via %.2f" % w), d))
    if not hits:
        print("  none")


def cmd_nearcu(layer, x, y, r):
    lid = b.GetLayerID(layer)
    rows = []
    for t in b.GetTracks():
        nm = t.GetNetname()
        if t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            d = math.hypot(mm(pos.x) - x, mm(pos.y) - y)
            if d <= r:
                rows.append((d, "via", nm, "%.2f dia" % mm(via_width(t)),
                             mm(pos.x), mm(pos.y)))
        elif t.GetLayer() == lid:
            s, e = t.GetStart(), t.GetEnd()
            d = seg_pt_dist(x, y, mm(s.x), mm(s.y), mm(e.x), mm(e.y))
            if d <= r:
                rows.append((d, "seg", nm, "w=%.2f" % mm(t.GetWidth()),
                             mm(s.x), mm(s.y)))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            on = (p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH) or p.IsOnLayer(lid)
            if not on:
                continue
            pos = p.GetPosition()
            d = math.hypot(mm(pos.x) - x, mm(pos.y) - y)
            if d <= r:
                sz = p.GetSize()
                rows.append((d, "pad", p.GetNetname() or "(nc)",
                             "%s.%s %.2fx%.2f" % (fp.GetReference(),
                                                  p.GetNumber(), mm(sz.x),
                                                  mm(sz.y)),
                             mm(pos.x), mm(pos.y)))
    rows.sort()
    print("copper on %s within %.1f mm of (%.2f, %.2f):" % (layer, r, x, y))
    for d, kind, nm, extra, px, py in rows[:25]:
        print("  %.3f mm  %-4s %-16s %-22s at (%.3f, %.3f)"
              % (d, kind, nm, extra, px, py))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "islands":
        cmd_islands(sys.argv[2])
    elif cmd == "vias":
        cmd_vias(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]),
                 float(sys.argv[5]) if len(sys.argv) > 5 else 10.0)
    elif cmd == "nearcu":
        cmd_nearcu(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]),
                   float(sys.argv[5]) if len(sys.argv) > 5 else 3.0)
    else:
        print(__doc__)
