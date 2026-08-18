"""J3 order blocker: is any JLCPCB-stocked USB-C pad-compatible? (item 4)

The board carries KiCad's USB_C_Receptacle_Amphenol_12401548E4-2A
hybrid footprint (12 SMD A-row pads + 12 staggered-PTH B-row pads +
4 shield slots + 2 NPTH pegs). Amphenol 12401548E4 is NOT stocked at
JLCPCB, so any assembly-time substitute must land on THESE pads.

This script pulls candidates' EasyEDA footprints (the geometry JLCPCB
assembly itself references) via the public API and prints each pad
table normalized to the same frame as the Amphenol pattern: origin at
the A-row centre, +x pointing from A-row toward B-row, +y along the
row. Comparison against the reference is then a straight table diff.

EasyEDA canvas unit = 10 mil = 0.254 mm.

Usage: python j3_footprint_compare.py C456013 [C...]
"""
import json
import sys
import urllib.request

MM = 0.254  # per EasyEDA unit

# Reference: the board's Amphenol footprint, absolute board mm from the
# batch dump, rewritten relative to the A-row centre (68.980, 30.000),
# +x toward B row, +y along the row. (type, name, x, y, w, h, drill_w,
# drill_h) -- drills 0 for SMD.
REF = [
    ("SMD", "A-row", 0.0, 0.0, 0.30, 0.70, 0, 0),      # 12 pads, pitch 0.5, span +-2.75
    ("PTH", "B-col1", 1.310, 0.0, 0.65, 0.65, 0.40, 0.40),   # y = +-0.4,+-1.2,+-2.0,+-2.8 col x=70.29
    ("PTH", "B-col2", 2.010, 0.0, 0.65, 0.65, 0.40, 0.40),   # y = +-0.8,+-1.6,+-2.4 (x=70.99) etc.
    ("PTH", "SH-near", 1.910, 4.130, 0.80, 1.40, 0.50, 1.10),
    ("PTH", "SH-far", 7.860, 4.490, 0.80, 1.40, 0.50, 1.10),
    ("NPTH", "peg-round", 0.660, 3.600, 0.65, 0.65, 0.65, 0.65),
    ("NPTH", "peg-slot", 0.660, -3.600, 0.95, 0.65, 0.95, 0.65),
]


def fetch(lcsc):
    url = ("https://easyeda.com/api/products/%s/components?version=6.4.19.5"
           % lcsc)
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.load(fh)


def parse_pads(dataStr):
    pads = []
    for s in dataStr.get("shape", []):
        if not s.startswith("PAD~"):
            continue
        f = s.split("~")
        shape, x, y, w, h = f[1], float(f[2]), float(f[3]), float(f[4]), float(f[5])
        layer, num = f[6], f[8]
        hole_r = float(f[9] or 0)
        rot = float(f[11] or 0)
        hole_len = float(f[13] or 0) if len(f) > 13 and f[13] else 0.0
        plated = f[15] if len(f) > 15 else ""
        pads.append({"shape": shape, "x": x * MM, "y": y * MM,
                     "w": w * MM, "h": h * MM, "layer": layer, "num": num,
                     "hole_d": 2 * hole_r * MM, "hole_len": hole_len * MM,
                     "rot": rot, "plated": plated})
    return pads


def classify(p):
    if p["layer"] == "11":            # multi-layer = through
        return "NPTH" if (p["plated"] == "N" or not p["num"]) else "PTH"
    return "SMD"


def main():
    for lcsc in sys.argv[1:]:
        try:
            d = fetch(lcsc)
        except Exception as exc:
            print("%s: FETCH FAILED (%s)" % (lcsc, exc))
            continue
        r = d.get("result") or {}
        title = r.get("title") or "?"
        pkg = (r.get("packageDetail") or {}).get("dataStr") or {}
        pads = parse_pads(pkg)
        if not pads:
            print("%s (%s): no pad data" % (lcsc, title))
            continue
        smd = [p for p in pads if classify(p) == "SMD"]
        pth = [p for p in pads if classify(p) == "PTH"]
        npth = [p for p in pads if classify(p) == "NPTH"]
        # A-row detection: the largest colinear 0.5-pitch group of SMD pads
        # EasyEDA orientations vary; try grouping by x then by y.
        def rowgroups(pads_, key, other):
            groups = {}
            for p in pads_:
                groups.setdefault(round(p[key], 2), []).append(p)
            return sorted(groups.items(), key=lambda kv: -len(kv[1]))
        gx = rowgroups(smd, "x", "y")
        gy = rowgroups(smd, "y", "x")
        along_y = bool(gx and (not gy or len(gx[0][1]) >= len(gy[0][1])))
        g = gx if along_y else gy
        axis = "y" if along_y else "x"
        row = g[0][1] if g else []
        row_c = (sum(p["x"] for p in row) / len(row),
                 sum(p["y"] for p in row) / len(row)) if row else (0, 0)
        print("=" * 72)
        print("%s  \"%s\"  pads: %d SMD / %d PTH / %d NPTH"
              % (lcsc, title[:44], len(smd), len(pth), len(npth)))
        if row:
            ys = sorted(p[axis] for p in row)
            pitches = [round(b - a, 3) for a, b in zip(ys, ys[1:])]
            print("  main SMD row: %d pads, pitch %s, span %.2f, pad %.2fx%.2f"
                  % (len(row), sorted(set(pitches)), ys[-1] - ys[0],
                     row[0]["w"], row[0]["h"]))
        # print all through pads relative to the row centre
        for tag, plist in (("PTH", pth), ("NPTH", npth)):
            for p in sorted(plist, key=lambda q: (q["x"], q["y"])):
                print("  %-4s %-4s dx=%7.3f dy=%7.3f  pad %.2fx%.2f  "
                      "hole %.2f%s"
                      % (tag, p["num"] or "-", p["x"] - row_c[0],
                         p["y"] - row_c[1], p["w"], p["h"], p["hole_d"],
                         ("x%.2f slot" % p["hole_len"]) if p["hole_len"] else ""))
        # reference reminder
    print("=" * 72)
    print("REFERENCE (board's Amphenol 12401548E4-2A, A-row centre origin,")
    print("dx toward B-row, dy along row):")
    print("  A-row: 12 SMD 0.30x0.70, pitch 0.500, span 5.50")
    print("  B PTH col1 dx=1.310 dy=+-0.4/1.2/2.0/2.8; col2 dx=2.010 "
          "dy=0? -- actual: staggered 0.8 within col")
    print("  B drills 0.40, pad 0.65")
    print("  SH slots: dx=1.910 dy=+-4.130 and dx=7.860 dy=+-4.490, "
          "pad 0.8x1.4 slot 0.5x1.1")
    print("  NPTH pegs: dx=0.660 dy=+3.600 round 0.65; dy=-3.600 "
          "slot 0.95x0.65")


if __name__ == "__main__":
    main()
