"""Can each of our checks actually FAIL? (B4)

This project's most persistent failure class, by a wide margin, is not
broken code. It is a check that passes while looking at the wrong thing.
The last two batches alone produced:

  * a leg-thickness check that measured a variable the leg never uses
  * a ground-clearance check comparing a number against itself
  * "the feet are a separate part", which tested two constants
  * a mounting-pattern check that passed a board no M3 bolt fits through
  * a buzzer-name check that compared Python to Python
  * a fanout site search that was over-strict in one place and blind in
    another, and got the right answer by accident
  * a timing check whose measurement was below the clock's resolution

Every one of them was green. None of them could have failed.

So this file exists: for each automated check, apply ONE representative
defect, confirm the check fails, put it back. A check that survives its
own mutation is not a check, and this exits non-zero when it finds one.

    python falsifiability_audit.py            # run everything
    python falsifiability_audit.py --list     # just show the cases
    python falsifiability_audit.py --only fc  # substring filter

It restores every file it touches, including on Ctrl-C, and verifies the
restore rather than assuming it.
"""
import argparse
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.abspath(os.path.join(HERE, ".."))
FW = os.path.abspath(os.path.join(HW, "..", "drone-firmware"))

KICAD_PY = r"C:\Program Files\KiCad\10.0\bin\python.exe"
FREECAD = os.path.expanduser(
    r"~\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe")


RUNCHK = os.path.join(HERE, "run_freecad_check.py")

# EVERY FreeCAD CHECK GOES THROUGH THE WRAPPER, never through freecadcmd
# directly. freecadcmd exits 0 for a script that fails to parse, so an
# audit trusting that exit code would report a check as fine when it had
# stopped running entirely -- and would call a mutation "caught" when all
# it did was break the file.
FRAME_RPT = os.path.join(HW, "mechanical", "frame-v0", "build-report-petg.txt")
ASM_RPT = os.path.join(HW, "mechanical", "assembly-v0",
                       "build-report-assembly.txt")


def frame_cmd():
    return [[sys.executable, RUNCHK,
             os.path.join(HW, "mechanical", "frame-v0", "frame_v0.py"),
             FRAME_RPT]]


def asm_cmd():
    return [[sys.executable, RUNCHK,
             os.path.join(HW, "mechanical", "assembly-v0", "assembly_v0.py"),
             ASM_RPT]]


class Case:
    """One check, plus one defect that ought to break it."""

    def __init__(self, key, what, path, old, new, cmd, cwd, why, timeout=900):
        self.key = key          # short handle for --only
        self.what = what        # what the check is supposed to guarantee
        self.path = path        # file to mutate
        self.old = old          # exact text to replace
        self.new = new          # replacement (the defect)
        self.cmd = cmd          # command whose EXIT CODE is the verdict
        self.cwd = cwd
        self.why = why          # what the mutation represents, in words
        self.timeout = timeout


# ARTIFACT SNAPSHOT.
#
# Restoring mutated SOURCES is not enough. The frame and assembly cases
# re-run their generators, and FreeCAD stamps a fresh timestamp into every
# STEP -- so a clean repo came out of each audit run with two modified
# 124,000-line files whose only difference was a date. The wrapper also
# DELETES a build report and cannot recreate it if the run it was testing
# was the deliberately-broken one.
#
# Both train the same bad habit: `git checkout` a large diff after every
# audit, which is indistinguishable from discarding a real regeneration.
# So the audit snapshots every artifact it could disturb and puts them
# back byte-for-byte.
GENERATED_DIRS = [
    os.path.join(HW, "mechanical", "frame-v0"),
    os.path.join(HW, "mechanical", "assembly-v0"),
    os.path.join(HW, "docs"),
]
GENERATED_EXT = (".step", ".stl", ".dxf", ".svg", ".txt", ".md")


def snapshot_artifacts():
    snap = {}
    for d in GENERATED_DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith(GENERATED_EXT):
                fp = os.path.join(d, f)
                if os.path.isfile(fp):
                    snap[fp] = io.open(fp, "rb").read()
    return snap


def restore_artifacts(snap):
    """Put every snapshotted artifact back, and report what moved."""
    changed, recreated = [], []
    for fp, data in snap.items():
        if not os.path.exists(fp):
            io.open(fp, "wb").write(data)
            recreated.append(os.path.basename(fp))
        elif io.open(fp, "rb").read() != data:
            io.open(fp, "wb").write(data)
            changed.append(os.path.basename(fp))
    return changed, recreated


def run(cmd, cwd, timeout):
    """Exit code is the verdict.

    `cmd` may be a list of argv lists, run in sequence, stopping at the
    first non-zero. That replaces an earlier `shell=True` string with
    `make x && ./build/x` in it -- which worked when pasted into bash and
    silently failed under Python, because shell=True on Windows is
    cmd.exe. Every baseline using it reported "already failing", which
    would have been read as five broken checks rather than one broken
    harness.
    """
    steps = cmd if (cmd and isinstance(cmd[0], list)) else [cmd]
    for step in steps:
        # The Makefile's target is `build/test_x`; the file it produces on
        # this host is `build/test_x.exe`. Resolve it rather than encoding
        # the platform into every case.
        step = list(step)
        if (not os.path.isabs(step[0]) and os.sep in step[0]
                and not os.path.exists(os.path.join(cwd, step[0]))
                and os.path.exists(os.path.join(cwd, step[0] + ".exe"))):
            step[0] += ".exe"
        if os.path.exists(os.path.join(cwd, step[0])):
            step[0] = os.path.join(cwd, step[0])
        try:
            p = subprocess.run(step, cwd=cwd, timeout=timeout,
                               capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            return -1
        except OSError as exc:
            print("    (could not run %s: %s)" % (step[0], exc))
            return -2
        if p.returncode != 0:
            return p.returncode
    return 0


CASES = [
    Case("frame-leg",
         "the frame's leg-thickness check measures the LEG",
         os.path.join(HW, "mechanical", "frame-v0", "frame_params.py"),
         "LEG_W = 14.0", "LEG_W = 0.5",
         frame_cmd(), HW,
         "a leg thinner than any material rule allows. The previous "
         "version of this check read ARM_T and printed OK 4.0 mm."),

    Case("frame-batt",
         "the frame's ground-clearance check can fail",
         os.path.join(HW, "mechanical", "frame-v0", "frame_params.py"),
         "BATT_L, BATT_W, BATT_H = 133.0, 45.0, 33.5",
         "BATT_L, BATT_W, BATT_H = 133.0, 45.0, 200.0",
         frame_cmd(), HW,
         "a 200 mm pack. LEG_H used to be DERIVED from the pack, so this "
         "passed with 214 mm legs and 18.0 mm of margin."),

    Case("frame-dxf",
         "the flats DXF carries sheet parts only",
         os.path.join(HW, "mechanical", "frame-v0", "frame_params.py"),
         'SHEET_PARTS   = ("bottom_plate", "top_plate", "arm_1")',
         'SHEET_PARTS   = ("bottom_plate", "top_plate", "arm_1", "leg_1")',
         frame_cmd(), HW,
         "the 14 mm leg back in the carbon cutting file -- the batch-4 "
         "blocker, which shipped."),

    Case("assembly-fit",
         "the assembly's interference check catches a collision",
         os.path.join(HW, "mechanical", "assembly-v0", "assembly_v0.py"),
         "size=(30.0, 30.0, 8.0), mass=13.5,",
         "size=(30.0, 90.0, 8.0), mass=13.5,",
         asm_cmd(), HW,
         "an ESC grown until it occupies the receiver's space. Numbers do "
         "not collide; solids do, and this is the check that notices."),

    Case("assembly-bolts",
         "the assembly re-verifies that the board bolts to the frame",
         os.path.join(HW, "bench_board", "bench_board.kicad_pcb"),
         "(drill 3.2)", "(drill 2.0)",
         asm_cmd(), HW,
         "a board whose holes an M3 does not fit. The assembly CALLS "
         "check_fc_pattern.py rather than re-deriving it, so this also "
         "proves that call is wired up and not silently swallowed."),

    Case("freecad-exit",
         "a FreeCAD check that does not RUN is reported as a failure",
         os.path.join(HW, "mechanical", "assembly-v0", "assembly_v0.py"),
         "import math", "import math" + chr(10) + "this is not python(((",
         asm_cmd(), HW,
         "a syntax error. freecadcmd exits 0 for a file it cannot parse, "
         "so without run_freecad_check.py every geometry check in this "
         "project would pass by simply being broken."),

    Case("ingest-guard-name",
         "the thrust tool refuses fake data on the FILENAME signal",
         os.path.join(FW, "tools", "thrust-ingest", "ingest.py"),
         'if "FAKE" in os.path.basename(self.path).upper():',
         'if "fake" in os.path.basename(self.path).upper():',
         [[sys.executable, os.path.join(HW, "scripts", "check_ingest_guard.py")]],
         HW,
         "the exact bug that shipped: a LOWERCASE needle against an "
         "UPPERCASED haystack, so the filename half of a supposedly "
         "two-signal guard could never fire. The commit claimed it had "
         "been 'verified all three ways'; all three had been caught by "
         "the marker rules."),

    Case("ingest-guard-marker",
         "the thrust tool refuses fake data on the MARKER signal",
         os.path.join(FW, "tools", "thrust-ingest", "ingest.py"),
         'elif marker not in ("false", "no", "0"):',
         'elif False:',
         [[sys.executable, os.path.join(HW, "scripts", "check_ingest_guard.py")]],
         HW,
         "the in-file marker ignored. Both signals get their own case "
         "because the whole claim is that they are INDEPENDENT -- one "
         "case could not tell a two-signal guard from a one-signal one."),

    Case("torque-value",
         "a physically impossible torque default is caught",
         os.path.join(FW, "src", "params.h"),
         "#define PARAMS_DEFAULT_MAX_TORQUE_RP   5.41f",
         "#define PARAMS_DEFAULT_MAX_TORQUE_RP   0.50f",
         [["make", "build/test_torque_clamp_param"],
          [os.path.join("build", "test_torque_clamp_param")]],
         FW,
         "a 10.8x error in the primary roll/pitch authority clamp. Until "
         "this batch the tests read the SAME macro the table reads, so "
         "both sides moved together and all 46 binaries passed."),

    Case("board-guard",
         "the board guard catches a DRC regression",
         os.path.join(HW, "bench_board", "bench_board.kicad_pcb"),
         "(width 0.2)", "(width 9.2)",
         [[sys.executable, os.path.join(HW, "scripts", "board_guard.py"),
           "check", "--no-revert"]],
         HW,
         "one trace widened 0.2 -> 9.2 mm: guaranteed clearance carnage "
         "(54 -> 60 violations when first proven). --no-revert inside the "
         "audit so the audit's own byte-restore machinery stays the single "
         "authority on file state -- the guard's live auto-revert path was "
         "proven separately and fires on every real regression. This is "
         "batch 6's revert contract: the exact mechanism whose absence let "
         "attempt 3 turn 43 violations into 387."),

    Case("fc-drill",
         "the mounting pattern check requires a hole an M3 fits",
         os.path.join(HW, "bench_board", "bench_board.kicad_pcb"),
         "(drill 3.2)", "(drill 2.0)",
         [sys.executable, os.path.join(HW, "scripts", "check_fc_pattern.py")],
         HW,
         "a 2.0 mm mounting hole. The check used to compare the four "
         "drills only to EACH OTHER and pass."),

    Case("fc-stale",
         "the mounting pattern check refuses a stale DXF",
         os.path.join(HW, "mechanical", "frame-v0", "frame_v0.py"),
         "PITCH_MARKER_UNUSED", "PITCH_MARKER_UNUSED",   # touch-only, see below
         [sys.executable, os.path.join(HW, "scripts", "check_fc_pattern.py")],
         HW,
         "a DXF older than the script that generates it, so the check "
         "would pass against an artifact nobody would build."),

    Case("cpl",
         "the CPL describes the board it ships with",
         os.path.join(HW, "fab", "2026-08-18a", "cpl_top.csv"),
         None, None,       # handled specially: drop the last data row
         [sys.executable, os.path.join(HW, "scripts", "check_cpl.py")],
         HW,
         "one component missing from the pick-and-place file -- the "
         "batch-3 defect, which shipped six of them."),

    Case("decoder-names",
         "the C encoder and the Python decoder agree",
         os.path.join(FW, "src", "buzzer.c"),
         '= "lost-model",', '= "beacon",',
         [sys.executable, os.path.join(FW, "tools", "ground-station",
                                       "test_decoder.py")],
         FW,
         "a renamed pattern string. Two earlier versions of this check "
         "compared enum identifiers, or Python to Python, and missed it."),

    Case("crash-order",
         "the crash log reads oldest-first",
         os.path.join(FW, "src", "crash_ring.c"),
         "uint32_t oldest = (r->p->count == r->capacity) ? r->p->head : 0u;",
         "uint32_t oldest = 0u;",
         [["make", "build/test_crash_ring"], [os.path.join("build", "test_crash_ring")]],
         FW,
         "a dump that reads time in reverse after the ring wraps -- a log "
         "where nothing looks broken."),

    Case("bringup-hello",
         "the bring-up identity block reports the real versions",
         os.path.join(FW, "src", "main_loop.c"),
         "(unsigned)TELEMETRY_VERSION,", "(unsigned)99,",
         [["make", "build/test_bringup_cli"], [os.path.join("build", "test_bringup_cli")]],
         FW,
         "`hello` reporting a hardcoded number instead of the macro the "
         "encoder uses -- a board that lies to the bring-up tool about "
         "which wire format it speaks. "
         "The FIRST mutation tried here was bumping "
         "TELEMETRY_VERSION itself, and it could not fail: the test "
         "compares hello's output against the same macro hello reads, so "
         "both sides moved together. Self-referential, exactly like the "
         "buzzer-name check before it was rebuilt."),

    Case("telemetry-version",
         "a telemetry version drift is caught SOMEWHERE",
         os.path.join(FW, "src", "telemetry.h"),
         "#define TELEMETRY_VERSION       6",
         "#define TELEMETRY_VERSION       99",
         [[sys.executable, os.path.join(FW, "tools", "ground-station",
                                        "test_decoder.py")]],
         FW,
         "the firmware and the ground station disagreeing about the wire "
         "version. This is the case that proves the drift IS guarded -- "
         "by the decoder cross-check, which carries its own independent "
         "VERSION constant, and not by the bring-up test above."),

    Case("params-link",
         "a params write reaches the running control loop",
         os.path.join(FW, "src", "main_loop.c"),
         "int applied = control_loop_request_config(&ml->cl, &ml->cfg);",
         "int applied = 1;",
         [["make", "build/test_params_over_link"], [os.path.join("build", "test_params_over_link")]],
         FW,
         "the missing wiring restored: a `set` that edits config and "
         "never reaches a PID, which is how it actually was."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    cases = [c for c in CASES if args.only.lower() in c.key.lower()]
    if args.list:
        for c in cases:
            print("  %-16s %s" % (c.key, c.what))
        return 0

    print("CHECKER FALSIFIABILITY AUDIT")
    print("Each check is run clean, then with one deliberate defect.")
    print("A check that passes BOTH times is not a check.\n")

    # Snapshot BEFORE anything runs, so the baseline runs cannot pollute
    # it either -- a clean baseline still regenerates exports.
    artifacts = snapshot_artifacts()
    print("  (snapshotted %d generated artifact(s) for restoration)\n"
          % len(artifacts))

    results = []
    restore_failed = []
    for c in cases:
        print("--- %s: %s" % (c.key, c.what))
        if not os.path.exists(c.path):
            print("    SKIP: %s not found\n" % c.path)
            results.append((c, None, None))
            continue

        original = io.open(c.path, "rb").read()
        try:
            # 1. clean run
            base = run(c.cmd, c.cwd, c.timeout)

            # 2. mutated run
            if c.key == "cpl":
                # Drop the last data row: one component silently absent.
                txt = original.decode("utf-8-sig").splitlines()
                io.open(c.path, "w", encoding="utf-8",
                        newline="\n").write("\n".join(txt[:-1]) + "\n")
            elif c.key == "fc-stale":
                # No text change -- just make the SOURCE newer than the
                # DXF, which is exactly the staleness the guard exists for.
                os.utime(c.path, None)
            else:
                data = original.decode("utf-8", errors="surrogateescape")
                if c.old not in data:
                    # NOT a skip. A mutation target that has vanished
                    # means the case no longer tests anything -- and three
                    # of these went quietly "skipped" the moment a
                    # refactor moved some constants into another file,
                    # while the audit still exited 0. An audit that can
                    # silently stop auditing is the same failure it exists
                    # to catch, so a stale case counts as a failure.
                    print("    STALE CASE: %r is no longer in %s -- this "
                          "check is UNAUDITED."
                          % (c.old, os.path.basename(c.path)))
                    results.append((c, base, "stale"))
                    continue
                io.open(c.path, "w", encoding="utf-8", newline="").write(
                    data.replace(c.old, c.new, 1))
            mut = run(c.cmd, c.cwd, c.timeout)
        finally:
            io.open(c.path, "wb").write(original)
            # VERIFY the restore. An audit that left a mutation behind
            # would be worse than no audit at all.
            back = io.open(c.path, "rb").read()
            if back != original:
                # Flag it; returning from a `finally` would swallow any
                # exception that brought us here.
                restore_failed.append(c.path)
            # REGENERATE ANY ARTIFACT THE MUTANT PRODUCED.
            #
            # Restoring the source is not enough for a generator: the
            # frame cases run frame_v0.py, which rewrites the STEP/STL/DXF
            # exports. Leaving a mutant's DXF behind made every LATER
            # case that reads it fail its clean baseline -- so an audit
            # that did not clean up after itself reported other checks as
            # broken. Exactly the failure class this file hunts, in the
            # file that hunts it.
            # REGENERATE THROUGH THE WRAPPER, whose absence here violated
            # this file's own header rule ("EVERY FreeCAD CHECK GOES
            # THROUGH THE WRAPPER") -- a silent regeneration failure would
            # leave a stale DXF and make later cases fail their baselines,
            # the exact hazard the wrapper exists for. And regenerate BOTH
            # generators when either side's inputs changed: the assembly
            # imports frame_params, so a frame mutation invalidates the
            # assembly's exports too. This hook previously covered
            # frame-v0 only ("full runs only avoid this by luck of case
            # ordering" -- the reviewer, correctly).
            d = os.path.normpath(os.path.dirname(c.path))
            touched_frame = d.endswith(os.path.join("mechanical", "frame-v0"))
            touched_asm = d.endswith(os.path.join("mechanical", "assembly-v0"))
            if touched_frame or touched_asm:
                if touched_frame:
                    rc = run(frame_cmd()[0], HW, 900)
                    if rc != 0:
                        print("    (WARNING: frame regeneration failed, "
                              "exit %d -- later cases may be unreliable)" % rc)
                rc = run(asm_cmd()[0], HW, 900)
                if rc != 0:
                    print("    (WARNING: assembly regeneration failed, "
                          "exit %d -- later cases may be unreliable)" % rc)

        verdict = "FALSIFIABLE" if (base == 0 and mut != 0) else "*** CANNOT FAIL ***"
        if base != 0:
            verdict = "BASELINE ALREADY FAILING (exit %d)" % base
        print("    clean exit %s / mutated exit %s -> %s\n"
              % (base, mut, verdict))
        results.append((c, base, mut))

    changed, recreated = restore_artifacts(artifacts)
    if changed or recreated:
        print("  restored %d artifact(s) the audit disturbed%s"
              % (len(changed) + len(recreated),
                 (", recreated %d deleted" % len(recreated)) if recreated else ""))
        for f in sorted(set(changed + recreated)):
            print("    %s" % f)
        print("")

    if restore_failed:
        print("*** RESTORE FAILED: %s" % ", ".join(restore_failed))
        print("*** Check `git status` before trusting anything below.")
        return 3

    print("=" * 66)
    bad = []
    for c, base, mut in results:
        if base is None:
            state = "skipped"
        elif mut is None:
            state = "skipped (no target)"
        elif base != 0:
            state = "BASELINE FAILING"; bad.append(c)
        elif mut == "stale":
            state = "STALE CASE (unaudited)"; bad.append(c)
        elif mut == 0:
            state = "CANNOT FAIL"; bad.append(c)
        else:
            state = "ok"
        print("  %-16s %s" % (c.key, state))

    print("")
    if bad:
        print("%d CHECK(S) COULD NOT BE MADE TO FAIL." % len(bad))
        print("A checker that cannot fail is worse than none: it launders")
        print("a guess into a fact. Fix or delete each one.")
        return 1
    print("Every check listed here fails when it should.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
