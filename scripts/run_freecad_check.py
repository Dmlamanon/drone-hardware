"""Run a FreeCAD check script and return a verdict you can trust.

WHY THIS EXISTS
---------------
**`freecadcmd` exits 0 when the script it was given fails to parse.**

    $ printf 'this is not python(((' > broken.py
    $ freecadcmd broken.py ; echo $?
    Exception while processing file: broken.py [...]
    0

Verified on FreeCAD 1.1.3, and it is not a corner case: it was found by a
real typo in assembly_v0.py, which reported "exit=0" for three runs in a
row while the script had never executed a single line. The exports on
disk were from an earlier run and looked current.

That makes a bare exit code worthless as a verdict. Every geometry check
this project has -- frame_v0.py's seventeen, assembly_v0.py's seven --
would report success if the file were merely broken, which is the exact
failure this project keeps finding in its own checkers.

WHAT THIS DOES INSTEAD
----------------------
The verdict comes from the ARTIFACT, not the process:

  1. the build report must exist,
  2. it must have been written by THIS run (the file is deleted first),
  3. it must end with the script's own explicit RESULT line, and
  4. that line must say the checks passed.

Any of those failing is a failure. A script that dies halfway leaves a
stale or truncated report and is caught by 2 or 3; a script that runs and
fails its checks is caught by 4.

Usage:
  python run_freecad_check.py <script.py> <report.txt> [env=VAL ...]
"""
import os
import subprocess
import sys

FREECAD = os.path.expanduser(
    r"~\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    script = os.path.abspath(sys.argv[1])
    report = os.path.abspath(sys.argv[2])
    env = dict(os.environ)
    for kv in sys.argv[3:]:
        if "=" in kv:
            k, _, v = kv.partition("=")
            env[k] = v

    if not os.path.exists(FREECAD):
        print("FAIL: freecadcmd not found at %s" % FREECAD)
        return 2

    # DELETE THE REPORT FIRST, rather than comparing timestamps.
    #
    # The first version of this took `started = time.time() - 1.0` and
    # called the report stale if it predated that. The one-second margin
    # -- added for filesystem granularity -- let a report written moments
    # earlier count as fresh, so running the wrapper straight after a good
    # run passed a script with a syntax error in it. A check that only
    # fails when the previous run was long enough ago is not a check.
    #
    # Removing the file has no race in it: if the report exists after the
    # run, this run wrote it. Nothing else can be true.
    if os.path.exists(report):
        try:
            os.remove(report)
        except OSError as exc:
            print("FAIL: could not clear %s first (%s) -- refusing to judge "
                  "a run against a report that may predate it."
                  % (report, exc))
            return 2

    proc = subprocess.run([FREECAD, os.path.basename(script)],
                          cwd=os.path.dirname(script), env=env,
                          capture_output=True, text=True)

    # The exit code is still worth looking at -- sys.exit(1) from a check
    # DOES propagate. It just cannot be trusted on its own.
    if proc.returncode != 0:
        print("FAIL: %s exited %d" % (os.path.basename(script), proc.returncode))
        return 1

    if not os.path.exists(report):
        print("FAIL: %s was not written.\n"
              "      freecadcmd exited 0 WITHOUT EXECUTING THE SCRIPT --\n"
              "      almost always a syntax error. Run it directly to see."
              % os.path.basename(report))
        # Surface the parse error, which freecadcmd prints and then hides
        # behind a zero exit.
        for ln in (proc.stdout or "").splitlines():
            if "Exception while processing" in ln:
                print("      %s" % ln.strip())
        return 1

    text = open(report, encoding="utf-8", errors="replace").read()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        print("FAIL: %s is empty" % os.path.basename(report))
        return 1

    last = lines[-1]
    if not last.startswith("RESULT:"):
        print("FAIL: %s does not end with a RESULT line -- the script died\n"
              "      partway. Last line was: %s" % (os.path.basename(report), last))
        return 1

    if "passed" not in last:
        print("FAIL: %s" % last)
        return 1

    print("ok: %s (%s)" % (last, os.path.basename(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
