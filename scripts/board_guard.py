"""The revert contract for board edits (batch 6, item 1).

    python board_guard.py baseline      # record what "no worse" means
    python board_guard.py check         # after EVERY board change
    python board_guard.py check --no-revert   # report only (audits)

WHY THIS EXISTS
---------------
Three automated routing attempts preceded this batch. The worst of them
(a coordinate-search via placer) turned 43 DRC violations into 235, then
387 on a second pass, because nothing forced a measurement between
changes -- each edit was judged by the model that proposed it, and the
model was wrong about zone fills and drill spacing.

The contract this file enforces: **after every single change -- one via,
one zone edit, one trace -- run `check`. If the unconnected count, the
violation count, or the parity count went UP, the board file is reverted
immediately and the attempt is recorded as failed.** No batching, no
"I'll check at the end". The numbers come from the real
`kicad-cli pcb drc`, never from a geometric model.

THE LOG IS EVIDENCE, NOT DECORATION
-----------------------------------
Every run appends to docs/board-guard-log.txt: counts, verdict, and the
sha256 of the board file that was measured. A reviewer can therefore
verify, from git history alone, that every committed board state has a
matching PASS entry -- which is precisely the audit this batch's wrap
instructs. Commit the log together with each board change.

RATCHET
-------
On a passing check whose counts are BELOW baseline, the baseline is
rewritten to the new, better numbers. Without this, an improvement
(13 -> 12 unconnected) would leave slack for a later change to regress
back to 13 unnoticed. Improvements are one-way.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.abspath(os.path.join(HERE, ".."))
BOARD = os.path.join(HW, "bench_board", "bench_board.kicad_pcb")
BASELINE = os.path.join(HERE, "board_guard_baseline.json")
LOG = os.path.join(HW, "docs", "board-guard-log.txt")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

# The REAL check, exactly as the batch brief specifies it. --severity-all
# so nothing is filtered out of the comparison; --schematic-parity so a
# board edit that breaks agreement with the schematic is a regression
# like any other.
DRC_ARGS = ["pcb", "drc", "--severity-all", "--schematic-parity",
            "--format", "json"]


def board_sha() -> str:
    h = hashlib.sha256()
    with open(BOARD, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def run_drc():
    """Run the real DRC; return (violations, unconnected, parity) or None.

    None means THE MEASUREMENT ITSELF FAILED, which is treated as a
    regression by the caller: a board file so broken that DRC cannot run
    is the strongest possible reason to revert, and a tooling failure
    that merely looks like that costs one re-run of a single change --
    the bias-to-caution trade this batch's header demands.
    """
    out = os.path.join(HERE, "_guard_drc.json")
    try:
        if os.path.exists(out):
            os.remove(out)      # a stale report must never be judged
        p = subprocess.run([KICAD_CLI] + DRC_ARGS + ["--output", out, BOARD],
                           capture_output=True, text=True, timeout=600)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print("guard: DRC did not run (%s)" % exc)
        return None
    if not os.path.exists(out):
        print("guard: DRC produced no report (exit %d)\n%s"
              % (p.returncode, (p.stderr or "")[:500]))
        return None
    try:
        d = json.load(io.open(out, encoding="utf-8"))
    except ValueError as exc:
        print("guard: DRC report unparseable (%s)" % exc)
        return None
    return (len(d.get("violations", [])),
            len(d.get("unconnected_items", [])),
            len(d.get("schematic_parity", [])))


def log_line(text: str):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    with io.open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("%s  %s\n" % (stamp, text))


def cmd_baseline() -> int:
    counts = run_drc()
    if counts is None:
        print("guard: refusing to record a baseline from a failed DRC run")
        return 2
    v, u, pa = counts
    sha = board_sha()
    io.open(BASELINE, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"violations": v, "unconnected": u, "parity": pa,
         "board_sha256": sha,
         "recorded": datetime.now(timezone.utc).isoformat(),
         "invocation": " ".join(DRC_ARGS)}, indent=2) + "\n")
    print("baseline recorded: %d violations / %d unconnected / %d parity"
          % (v, u, pa))
    print("board sha256: %s" % sha[:12])
    log_line("BASELINE  v=%d u=%d p=%d  board=%s" % (v, u, pa, sha[:12]))
    return 0


def cmd_check(no_revert: bool) -> int:
    if not os.path.exists(BASELINE):
        print("guard: no baseline recorded. Run `board_guard.py baseline` "
              "first -- a guard with nothing to compare against is not a "
              "guard.")
        return 2
    base = json.load(io.open(BASELINE, encoding="utf-8"))
    counts = run_drc()
    sha = board_sha()

    if counts is None:
        # Measurement failure IS failure. See run_drc()'s docstring.
        print("guard: FAILED -- DRC could not measure the board at all.")
        return _fail(no_revert, "DRC-DID-NOT-RUN", sha)

    v, u, pa = counts
    bv, bu, bp = base["violations"], base["unconnected"], base["parity"]
    print("guard: %d/%d/%d (violations/unconnected/parity) vs baseline "
          "%d/%d/%d" % (v, u, pa, bv, bu, bp))

    regressed = []
    if v > bv:
        regressed.append("violations %d -> %d" % (bv, v))
    if u > bu:
        regressed.append("unconnected %d -> %d" % (bu, u))
    if pa > bp:
        regressed.append("parity %d -> %d" % (bp, pa))

    if regressed:
        print("guard: REGRESSION -- " + "; ".join(regressed))
        log_line("FAIL      v=%d u=%d p=%d (base %d/%d/%d)  board=%s  %s"
                 % (v, u, pa, bv, bu, bp, sha[:12], "; ".join(regressed)))
        return _fail(no_revert, "; ".join(regressed), sha)

    improved = (v < bv) or (u < bu) or (pa < bp)
    if improved:
        # RATCHET: better is the new floor. Without this, an improvement
        # leaves exactly enough slack for the next change to undo it
        # silently.
        io.open(BASELINE, "w", encoding="utf-8", newline="\n").write(
            json.dumps({"violations": v, "unconnected": u, "parity": pa,
                        "board_sha256": sha,
                        "recorded": datetime.now(timezone.utc).isoformat(),
                        "invocation": " ".join(DRC_ARGS)}, indent=2) + "\n")
        print("guard: PASS, improved -- baseline ratcheted to %d/%d/%d"
              % (v, u, pa))
        log_line("PASS+     v=%d u=%d p=%d (was %d/%d/%d, ratcheted)  board=%s"
                 % (v, u, pa, bv, bu, bp, sha[:12]))
    else:
        print("guard: PASS (unchanged)")
        log_line("PASS      v=%d u=%d p=%d  board=%s" % (v, u, pa, sha[:12]))
    return 0


def _fail(no_revert: bool, why: str, sha: str) -> int:
    if no_revert:
        print("guard: --no-revert given; the board is LEFT IN ITS FAILED "
              "STATE for inspection.")
        return 1
    p = subprocess.run(["git", "checkout", "--", os.path.relpath(BOARD, HW)],
                       cwd=HW, capture_output=True, text=True)
    if p.returncode == 0:
        print("guard: board REVERTED to the committed state.")
        log_line("REVERTED  board %s -> HEAD  (%s)" % (sha[:12], why))
    else:
        print("guard: REVERT FAILED (%s) -- fix by hand before anything "
              "else runs:\n%s" % (why, p.stderr))
        log_line("REVERT-FAILED  (%s)" % why)
        return 3
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["baseline", "check"])
    ap.add_argument("--no-revert", action="store_true",
                    help="report a regression without touching the file "
                         "(for audits and post-mortems)")
    args = ap.parse_args()
    if args.mode == "baseline":
        return cmd_baseline()
    return cmd_check(args.no_revert)


if __name__ == "__main__":
    sys.exit(main())
