"""Does the thrust tool actually refuse fabricated data?

A pass/fail wrapper so falsifiability_audit.py can mutate the guard and
watch this go red. The guard's whole claim is that it uses TWO
INDEPENDENT signals -- the filename and an in-file marker -- so this
exercises each one ALONE, with the other deliberately satisfied.

That separation is the point. The shipped version had a dead filename
check (a lowercase needle against an uppercased haystack) and nobody
noticed, because every test that "verified" it also left the marker in
place, and the marker caught it.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.abspath(os.path.join(HERE, "..", "..", "drone-firmware"))
INGEST = os.path.join(FW, "tools", "thrust-ingest", "ingest.py")
SAMPLE = os.path.join(FW, "tools", "thrust-ingest", "sample-FAKE-2026-08-17.csv")

fails = []


def check(desc, cond, detail=""):
    print("%s %-52s %s" % ("ok:  " if cond else "FAIL:", desc, detail))
    if not cond:
        fails.append(desc)


def write_variant(tmp, name, marker):
    """Copy the sample, forcing the marker line to `marker` (or dropping it)."""
    out = []
    for ln in io.open(SAMPLE, encoding="utf-8").read().splitlines():
        if ln.startswith("# fake:"):
            if marker is None:
                continue
            out.append("# fake: %s" % marker)
        else:
            out.append(ln)
    p = os.path.join(tmp, name)
    io.open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return p


def refuses(path):
    r = subprocess.run([sys.executable, INGEST, path, "--write", "--dry-run"],
                       capture_output=True, text=True)
    return r.returncode == 2, (r.stdout or "")


with tempfile.TemporaryDirectory() as tmp:
    # 1. FILENAME ALONE. The marker says this is real data; only the name
    #    betrays it. This is the signal that was dead.
    p = write_variant(tmp, "stand-FAKE-2026-09-01.csv", "false")
    ref, _ = refuses(p)
    check("refuses on the FILENAME alone (marker says real)", ref,
          "stand-FAKE-2026-09-01.csv")

    # 2. MARKER ALONE. Nothing in the name suggests anything.
    p = write_variant(tmp, "stand-2026-09-01.csv", "true")
    ref, _ = refuses(p)
    check("refuses on the MARKER alone (filename is innocent)", ref)

    # 3. ABSENCE. Silence must fail safe.
    p = write_variant(tmp, "stand-2026-09-02.csv", None)
    ref, _ = refuses(p)
    check("refuses when the marker is ABSENT (silence is not consent)", ref)

    # 4. And it must still ACCEPT genuinely-real data, or the guard is
    #    just a wall.
    p = write_variant(tmp, "stand-2026-09-03.csv", "false")
    ref, out = refuses(p)
    check("ACCEPTS data that clears both signals", not ref,
          "would otherwise be unusable")

print("")
if fails:
    print("%d CHECK(S) FAILED" % len(fails))
    sys.exit(1)
print("PASS: the fake-data guard refuses on each signal independently")
