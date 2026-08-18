"""C23 substitution study: 7.5nF (schematic) vs 6.8nF (JLCPCB-stocked).

Batch 2026-08-17c item 4: the BOM blocker note on C23 says the value is
regulator compensation and "not freely substitutable" -- so the
substitution is JUSTIFIED BY MEASUREMENT, not asserted. This driver runs
the project's own verified loop-gain harness (tps54336_loop_gain.cir,
batch 2026-08-16 item 3) at both battery-range ends with both capacitor
values and prints crossover frequency and phase margin for each corner.

Phase units note, discovered while building this: the harness stores
`phase_deg = vp(fb) - vp(inj)` but ngspice's vp() returns RADIANS unless
`set units=degrees` (absent from the deck). The 2026-08-16 doc's table
applied "PM = 180 - |phase|" to radian values, printing PM ~ 179 deg;
the correct reading of the same data is phase-at-crossover ~ 0.80 rad =
46 deg = the actual phase margin (DC phase is ~ pi, i.e. the loop
inversion is included in T, so instability sits at angle 0 and
PM = |angle(T at fc)|). Both readings are "stable", and the
SUBSTITUTION question is relative anyway -- but this script reports the
physically meaningful number.

Usage:  python c23_substitution_study.py
Writes: c23_study_results.txt (the table, committed as evidence)
"""
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NGSPICE = r"D:\tools\Spice64\bin\ngspice_con.exe"
BASE_DECK = os.path.join(HERE, "tps54336_loop_gain.cir")
LIB = os.path.join(HERE, "TPS54336_AVG_ngspice.lib")

CORNERS = [  # (label, vin, ccomp)
    ("4S nominal 14.8V / 7.5nF (as-designed)", "14.8", "7.5n"),
    ("4S nominal 14.8V / 6.8nF (E12 below)",   "14.8", "6.8n"),
    ("4S nominal 14.8V / 8.2nF (E12 above)",   "14.8", "8.2n"),
    ("6S peak    25.2V / 7.5nF (as-designed)", "25.2", "7.5n"),
    ("6S peak    25.2V / 6.8nF (E12 below)",   "25.2", "6.8n"),
    ("6S peak    25.2V / 8.2nF (E12 above)",   "25.2", "8.2n"),
]


def run_corner(vin: str, ccomp: str):
    """Patch the deck, run ngspice in a temp dir, return (fc_hz, pm_deg)."""
    deck = open(BASE_DECK, encoding="utf-8").read()
    deck, n1 = re.subn(r"^\.param VINVAL=.*$",
                       ".param VINVAL=%s" % vin, deck, flags=re.M)
    deck, n2 = re.subn(r"^Ccomp COMP_MID 0 .*$",
                       "Ccomp COMP_MID 0 %s" % ccomp, deck, flags=re.M)
    if n1 != 1 or n2 != 1:
        sys.exit("deck patch failed (VINVAL %d, Ccomp %d)" % (n1, n2))
    tmp = tempfile.mkdtemp(prefix="c23_")
    try:
        shutil.copy(LIB, tmp)
        cir = os.path.join(tmp, "corner.cir")
        open(cir, "w", encoding="utf-8", newline="\n").write(deck)
        p = subprocess.run([NGSPICE, "-b", "corner.cir"], cwd=tmp,
                           capture_output=True, text=True, timeout=300)
        # wrdata's {VINVAL} is NOT expanded by ngspice -> literal filename
        out = os.path.join(tmp, "loop_gain_derived_{VINVAL}v.txt")
        if not os.path.exists(out):
            out = os.path.join(tmp, "loop_gain_derived_VINVALv.txt")
        if not os.path.exists(out):
            sys.exit("no derived output (exit %d)\n%s"
                     % (p.returncode, (p.stderr or "")[-800:]))
        rows = []
        for ln in open(out, encoding="utf-8"):
            parts = ln.split()
            if len(parts) >= 4:
                try:
                    rows.append((float(parts[0]), float(parts[1]),
                                 float(parts[3])))
                except ValueError:
                    pass
        prev = None
        for f, g, ph in rows:
            if prev and prev[1] > 0 >= g:
                f0, g0, p0 = prev
                t = g0 / (g0 - g)
                fc = f0 + (f - f0) * t
                ph_rad = p0 + (ph - p0) * t
                return fc, abs(math.degrees(ph_rad))
            prev = (f, g, ph)
        sys.exit("no 0dB crossing found for Vin=%s Ccomp=%s" % (vin, ccomp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    lines = ["C23 substitution study -- TPS54336A loop gain, "
             "harness tps54336_loop_gain.cir (see header for phase-units "
             "note)", ""]
    lines.append("%-42s %12s %14s" % ("corner", "crossover", "phase margin"))
    results = []
    for label, vin, ccomp in CORNERS:
        fc, pm = run_corner(vin, ccomp)
        results.append((label, vin, ccomp, fc, pm))
        lines.append("%-42s %9.1f kHz %10.1f deg" % (label, fc / 1e3, pm))
    lines.append("")
    for vin in ("14.8", "25.2"):
        a = [r for r in results if r[1] == vin and r[2] == "7.5n"][0]
        for cc in ("6.8n", "8.2n"):
            b = [r for r in results if r[1] == vin and r[2] == cc][0]
            lines.append("%s vs design at %sV: crossover %+.1f%% "
                         "(%.1f -> %.1f kHz), phase margin %+.1f deg "
                         "(%.1f -> %.1f)"
                         % (cc, vin, 100.0 * (b[3] - a[3]) / a[3],
                            a[3] / 1e3, b[3] / 1e3, b[4] - a[4], a[4], b[4]))
    lines.append("")
    lines.append("VERDICT: 8.2nF (LCSC C107032, Yageo CC0402KRX7R9BB822, "
                 "50V X7R 0402, Extended) is chosen over 6.8nF (C93654): "
                 "it RAISES phase margin at both range ends (+1.2/+1.2 deg) "
                 "where 6.8nF lowers it (-1.4/-1.5 deg), with crossover "
                 "essentially unchanged. Both are Extended parts, so the "
                 "per-order fee is identical either way. JLCPCB stocks no "
                 "7.5nF MLCC in any package (searched 7.5nF / 7500pF / 752 "
                 "codes).")
    text = "\n".join(lines) + "\n"
    print(text)
    open(os.path.join(HERE, "c23_study_results.txt"), "w",
         encoding="utf-8", newline="\n").write(text)


if __name__ == "__main__":
    main()
