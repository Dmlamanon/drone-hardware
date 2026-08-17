"""Does the board's mounting pattern actually match the frame's?

The lead ruling for this batch was that the BOARD conforms to the frame's
30.5 mm FC standard, not the other way round. This asserts it from the two
real files rather than from the two source constants:

  * the board's mounting holes, read out of bench_board.kicad_pcb
  * the frame's FC holes, read out of the exported DXF

Reading the DXF matters. `FC_MOUNT = 30.5` in frame_v0.py is what the
frame *intends*; the DXF is what a cutter would actually make, and those
are only the same thing if the export works. Checking the constant would
prove nothing about the artifact.

Exit status is 0 only if both patterns are square, both are 30.5 mm, and
they are congruent.

Usage: python check_fc_pattern.py [board.kicad_pcb] [frame.dxf]
"""
import io, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "bench_board", "bench_board.kicad_pcb")
DXF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    HERE, "..", "mechanical", "frame-v0", "stevie-frame-v0-flats-petg.dxf")

PITCH = 30.5
TOL = 0.05          # mm; the pattern is a mechanical interface, not a fit
M3_R = (1.5, 1.75)  # plausible radius range for an M3 clearance hole in the frame

fails = []

SCRIPT = os.path.join(HERE, "..", "mechanical", "frame-v0", "frame_v0.py")


def check(desc, cond, detail=""):
    print("%s %-58s %s" % ("ok:  " if cond else "FAIL:", desc, detail))
    if not cond:
        fails.append(desc)


def square_of(pts, label):
    """Assert four points form an axis-aligned square, return its pitch+centre."""
    if len(pts) != 4:
        check("%s: exactly four holes" % label, False, "found %d" % len(pts))
        return None
    xs = sorted(set(round(p[0], 3) for p in pts))
    ys = sorted(set(round(p[1], 3) for p in pts))
    if len(xs) != 2 or len(ys) != 2:
        check("%s: holes form an axis-aligned rectangle" % label, False,
              "x values %s, y values %s" % (xs, ys))
        return None
    dx, dy = xs[1] - xs[0], ys[1] - ys[0]
    check("%s: holes form an axis-aligned rectangle" % label, True,
          "%.3f x %.3f mm" % (dx, dy))
    check("%s: that rectangle is square" % label, abs(dx - dy) <= TOL,
          "|%.3f - %.3f| = %.3f mm" % (dx, dy, abs(dx - dy)))
    check("%s: pitch is the %.1f mm standard" % (label, PITCH),
          abs(dx - PITCH) <= TOL and abs(dy - PITCH) <= TOL,
          "%.3f x %.3f mm" % (dx, dy))
    return dx, dy, ((xs[0] + xs[1]) / 2.0, (ys[0] + ys[1]) / 2.0)


# ---------------- the board ----------------
s = io.open(BOARD, encoding="utf-8", newline="").read()
board_holes = []
fps = [m.start() for m in re.finditer(r'\(footprint "', s)]
for i, st in enumerate(fps):
    end = fps[i + 1] if i + 1 < len(fps) else len(s)
    b = s[st:end]
    r = re.search(r'\(property "Reference" "(MH\d+)"', b)
    if not r:
        continue
    a = re.search(r"\(at ([-\d.]+) ([-\d.]+)", b)
    drill = re.search(r"\(drill ([-\d.]+)\)", b)
    board_holes.append((float(a.group(1)), float(a.group(2)),
                        float(drill.group(1)) if drill else 0.0, r.group(1)))

# STALENESS GUARD. This check reads the exported DXF rather than
# frame_v0.py's FC_MOUNT constant, deliberately -- the constant is what the
# frame intends, the DXF is what a cutter would actually make. But that
# only means something if the DXF is CURRENT. A DXF older than the script
# that generates it would let this check pass against an artifact nobody
# would build.
if os.path.exists(SCRIPT) and os.path.exists(DXF):
    dxf_age, src_age = os.path.getmtime(DXF), os.path.getmtime(SCRIPT)
    check("the frame DXF is newer than the script that generates it",
          dxf_age >= src_age,
          "DXF %s script" % ("newer than" if dxf_age >= src_age
                             else "is STALE by %.0f s vs" % (src_age - dxf_age)))

print("board: %s" % os.path.normpath(BOARD))
for x, y, d, ref in sorted(board_holes, key=lambda h: (h[1], h[0])):
    print("   %-4s at (%8.3f, %8.3f)  drill %.2f mm" % (ref, x, y, d))
board = square_of([(h[0], h[1]) for h in board_holes], "board")
check("board holes are all the same drill size",
      len(set(round(h[2], 3) for h in board_holes)) == 1,
      "%s mm" % sorted(set(round(h[2], 3) for h in board_holes)))

# ---------------- the frame DXF ----------------
# DXF is a flat stream of (group code, value) PAIRS, two lines each. An
# ad-hoc entity walk found 1 circle out of 104 -- read the pairs properly.
# 10/20 are a CIRCLE's centre, 40 its radius, 8 its layer.
raw = io.open(DXF, encoding="utf-8", errors="ignore").read().splitlines()
pairs = [(raw[i].strip(), raw[i + 1].strip()) for i in range(0, len(raw) - 1, 2)]

circles = []
cur = None


def flush(c):
    if c and all(k in c for k in ("x", "y", "r")):
        circles.append((c["x"], c["y"], c["r"], c.get("layer", "?")))


for code, val in pairs:
    if code == "0":
        flush(cur)
        cur = {} if val == "CIRCLE" else None
        continue
    if cur is None:
        continue
    if code == "8":
        cur["layer"] = val
    elif code == "10":
        cur["x"] = float(val)
    elif code == "20":
        cur["y"] = float(val)
    elif code == "40":
        cur["r"] = float(val)
flush(cur)

print("\nframe DXF: %s" % os.path.normpath(DXF))
print("   %d circles in the export" % len(circles))

# The FC pattern is the set of four same-radius M3 holes arranged
# symmetrically about the origin at +-PITCH/2.
#
# DEDUPLICATE BY POSITION. A solid extrusion writes each hole circle once
# per face, so four holes come out as sixteen circles per plate. Counting
# raw circles reports 32 and fails a check that should pass -- the
# geometry is right and the naive count is wrong.
half = PITCH / 2.0
fc_all = [c for c in circles
          if M3_R[0] <= c[2] <= M3_R[1]
          and abs(abs(c[0]) - half) <= 1.0 and abs(abs(c[1]) - half) <= 1.0]

by_layer = {}
for cx, cy, rr, lay in fc_all:
    by_layer.setdefault(lay, set()).add((round(cx, 3), round(cy, 3), round(rr, 3)))

print("   %d FC-pattern circles across %d plate(s) -> deduplicated per plate:"
      % (len(fc_all), len(by_layer)))

frame = None
for lay in sorted(by_layer):
    holes = sorted(by_layer[lay])
    print("   [%s]" % lay)
    for cx, cy, rr in holes:
        print("      hole at (%8.3f, %8.3f)  r %.2f mm" % (cx, cy, rr))
    res = square_of([(h[0], h[1]) for h in holes], "frame %s" % lay)
    if res and frame is None:
        frame = res

check("the FC pattern is on BOTH plates, so the stack bolts together",
      len(by_layer) >= 2, "found on: %s" % ", ".join(sorted(by_layer)))

# ---------------- do they match ----------------
if board and frame:
    bd, _, bc = board
    fd, _, fc_c = frame
    check("board pitch == frame pitch", abs(bd - fd) <= TOL,
          "%.3f vs %.3f mm (delta %.3f)" % (bd, fd, abs(bd - fd)))
    check("the board bolts to the frame (patterns are congruent)",
          abs(bd - fd) <= TOL,
          "board %.3f, frame %.3f" % (bd, fd))
    print("\n   board pattern centre (%.3f, %.3f) in board coordinates" % bc)
    print("   frame pattern centre (%.3f, %.3f) in frame coordinates" % fc_c)
    print("   (centres are in different coordinate systems -- only the")
    print("    pitch has to match for the parts to bolt together)")

print("")
if fails:
    print("%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("PASS: the board's mounting pattern matches the frame's FC standard")
