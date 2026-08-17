"""Refill the copper pours with KiCad's own ZONE_FILLER, and measure the result.

WHY THIS EXISTS. The KiCad MCP's refill shattered both inner planes last
batch -- In1.Cu went from 2 filled polygons to 19, In2.Cu from 1 to 22 --
and that fill was discarded. This is a different code path: KiCad's own
in-tree filler, called through KiCad's own interpreter.

It does not assume the result is good. It measures fragment count before
and after and prints both, so "did this shatter the planes" is answered
with a number rather than a hope. Ship nothing on the strength of this
output alone -- compare against the git-stored copper too.

Usage: python refill_zones.py <board> [--dry-run]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from kicad_safe import pcbnew  # noqa: E402

import io, re  # noqa: E402

BOARD = _sys.argv[1]
DRY = "--dry-run" in _sys.argv


def fragments(path):
    """Filled polygons per pour, read from the FILE -- the same measurement
    on both sides of the change, which is the only way the comparison
    means anything."""
    s = io.open(path, encoding="utf-8", newline="").read()
    out = []
    for m in re.finditer(r"\(zone\b", s):
        st = m.start(); d = 0; ins = False; j = st
        while j < len(s):
            c = s[j]
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
        z = s[st:j + 1]
        if "(keepout" in z:          # footprint keepouts are not pours
            continue
        net = re.search(r'\(net(?:_name)? "([^"]*)"\)', z)
        lay = re.search(r'\(layers? "?([^")\s]+)"?\)', z)
        n = len(re.findall(r"\(filled_polygon", z))
        pts = len(re.findall(r"\(xy ", z))
        out.append((net.group(1) if net else "?", lay.group(1) if lay else "?", n, pts))
    return out


before = fragments(BOARD)
print("BEFORE:")
for net, lay, n, pts in before:
    print("   %-8s on %-7s  %d filled polygon(s), %d points" % (net, lay, n, pts))

b = pcbnew.LoadBoard(BOARD)
filler = pcbnew.ZONE_FILLER(b)
zones = b.Zones()
print("\nfilling %d zone(s) with pcbnew.ZONE_FILLER ..." % len(list(zones)))
ok = filler.Fill(zones)
print("ZONE_FILLER.Fill() returned %r" % (ok,))

if DRY:
    print("\n--dry-run: nothing written")
    _sys.exit(0)

pcbnew.SaveBoard(BOARD, b)
after = fragments(BOARD)
print("\nAFTER:")
for net, lay, n, pts in after:
    print("   %-8s on %-7s  %d filled polygon(s), %d points" % (net, lay, n, pts))

print("\nverdict:")
bad = False
for (n1, l1, c1, p1), (n2, l2, c2, p2) in zip(before, after):
    delta = c2 - c1
    flag = ""
    if c2 > c1 + 2:
        flag = "  <-- FRAGMENTED"
        bad = True
    print("   %-8s on %-7s  %d -> %d filled polygon(s)%s" % (n2, l2, c1, c2, flag))
print("")
if bad:
    print("FRAGMENTED -- do not ship this fill. Restore the previous copper.")
    _sys.exit(1)
print("Fill looks coherent. Still compare against git before shipping.")
