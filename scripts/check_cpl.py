"""Does the pick-and-place file describe THIS board?

Batch 4 shipped a fab package whose CPL was missing six components,
because it had been generated before they were added. The check that
caught it was a one-off command typed at a shell -- which means it could
not be re-run, could not be audited, and would not have caught the same
mistake in the next package.

This is that check as an artifact. It compares, from the two real files:

  * every footprint on the board that is PLACEABLE -- i.e. not excluded
    from position files, which is how mounting holes and fiducials are
    correctly kept out
  * every data row in cpl_top.csv / cpl_bottom.csv

and asserts they are the same SET, not merely the same count. Two counts
matching while the contents differ is exactly the failure a count check
waves through.

Usage:
  python check_cpl.py [board.kicad_pcb] [fab_dir]
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "bench_board", "bench_board.kicad_pcb")
FABDIR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    HERE, "..", "fab", "2026-08-17b")

fails = []


def check(desc, cond, detail=""):
    print("%s %-56s %s" % ("ok:  " if cond else "FAIL:", desc, detail))
    if not cond:
        fails.append(desc)


# ---------------- the board ----------------
s = io.open(BOARD, encoding="utf-8", newline="").read()

placeable = set()
excluded = set()
starts = [m.start() for m in re.finditer(r'\(footprint "', s)]
for i, st in enumerate(starts):
    end = starts[i + 1] if i + 1 < len(starts) else len(s)
    body = s[st:end]
    ref = re.search(r'\(property "Reference" "([^"]+)"', body)
    if not ref:
        continue
    r = ref.group(1)
    # WHAT ACTUALLY EXCLUDES A FOOTPRINT HERE, checked against the file
    # rather than assumed.
    #
    # The batch-4 fab README said the four mounting holes "carry
    # FP_EXCLUDE_FROM_POS_FILES". They do not -- that string appears
    # nowhere in this board. What they have is no `(attr ...)` line at
    # all, and there are exactly 61 footprints with one against 61 CPL
    # rows. A footprint with no attributes has no mountable pads for a
    # machine to place, which is why kicad-cli leaves it out.
    #
    # Both rules are honoured, so this keeps working if the explicit flag
    # is ever set: an explicit exclusion wins, and a footprint with no
    # attr block at all is treated as not placeable.
    attr = re.search(r"\(attr ([^)]*)\)", body)
    if attr is None:
        excluded.add(r)
    elif "exclude_from_pos_files" in attr.group(1):
        excluded.add(r)
    else:
        placeable.add(r)

print("board: %s" % os.path.normpath(BOARD))
print("   %d placeable, %d excluded from position files"
      % (len(placeable), len(excluded)))
if excluded:
    print("   excluded: %s" % ", ".join(sorted(excluded)))

# ---------------- the CPL files ----------------
cpl_refs = set()
found_any = False
for name in ("cpl_top.csv", "cpl_bottom.csv"):
    p = os.path.join(FABDIR, name)
    if not os.path.exists(p):
        print("   %s: absent" % name)
        continue
    found_any = True
    rows = [ln for ln in io.open(p, encoding="utf-8-sig").read().splitlines()
            if ln.strip()]
    body = rows[1:] if rows else []
    refs = [ln.split(",")[0].strip().strip('"') for ln in body]
    print("   %s: %d data row(s)" % (name, len(refs)))
    dupes = sorted({r for r in refs if refs.count(r) > 1})
    check("%s has no duplicate references" % name, not dupes,
          ", ".join(dupes) if dupes else "")
    cpl_refs |= set(refs)

check("at least one CPL file exists", found_any,
      os.path.normpath(FABDIR))

# ---------------- do they agree ----------------
missing = sorted(placeable - cpl_refs)      # on the board, not in the CPL
extra = sorted(cpl_refs - placeable)        # in the CPL, not on the board

# SETS, not counts. Six missing and six spurious would give matching
# counts and a board nobody can assemble.
check("every placeable component is in the CPL", not missing,
      ("MISSING: " + ", ".join(missing)) if missing else "")
check("the CPL contains nothing that is not on the board", not extra,
      ("EXTRA: " + ", ".join(extra)) if extra else "")
check("no excluded footprint leaked into the CPL",
      not (excluded & cpl_refs),
      ", ".join(sorted(excluded & cpl_refs)))

print("")
if fails:
    print("%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("PASS: the CPL describes this board (%d components)" % len(placeable))
