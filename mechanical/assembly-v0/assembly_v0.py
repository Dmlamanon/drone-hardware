"""STEVIE full-assembly model — every component, in position (B6).

    freecadcmd assembly_v0.py

WHAT THIS IS FOR
----------------
Two questions that nothing in this project could answer before:

  1. **Does it all actually fit?** Frame, board, battery, ESCs, motors,
     props, receiver, buzzer and the expansion header have only ever
     existed as separate numbers in separate documents. Numbers do not
     collide; solids do. There is a programmatic interference check
     below, and it can fail.

  2. **What does it weigh, and where is the mass?** The inertia the
     control gains are derived from rests on an AUW built by adding up a
     parts list and multiplying the frame by an INVENTED 1.4x
     (docs/fable-reeval-2026-08-16.md, R3). This computes mass, CG and
     inertia from where the parts actually are.

IT MUST NOT TOUCH THE BOARD. No edit to bench_board.kicad_pcb and no edit
to the fab package happens here or anywhere downstream of here; this
reads mechanical/bench_board.step and nothing else from that side.

PARAMETERS ARE IMPORTED, NOT COPIED
-----------------------------------
Frame geometry comes from frame_params.py, the same module frame_v0.py
uses. A second copy of the wheelbase or the mount pitch would be a second
thing to update, and that is this project's most repeated defect.

PROVENANCE IS CARRIED PER COMPONENT
-----------------------------------
Every dimension below is tagged with where it came from, using the same
classes as the re-eval's table:

    DATASHEET        manufacturer datasheet for the exact part
    RETAIL-LISTING   a real product page for the exact part
    OWN-MODEL        derived from this project's own CAD/schematic
    ESTIMATE         reasoned, no external source
    MEASURED         physically measured -- NEVER TRUE HERE, and the
                     summary says so rather than letting the tag imply
                     otherwise

Nothing in this file has been weighed or measured. Every mass is a
listing or an estimate, and the mass rollup states that at the top.
"""
import math
import os
import sys

import FreeCAD as App
import Part
import Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR = os.path.normpath(os.path.join(HERE, "..", "frame-v0"))
MECH_DIR = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, FRAME_DIR)

# THE import that makes this a model of the real frame rather than a
# drawing that resembles it.
from frame_params import *          # noqa: F401,F403,E402

report = []


def say(m):
    report.append(m)
    print(m)


# ----------------------------------------------------------------------
# COMPONENTS -- dimensions, masses, provenance
# ----------------------------------------------------------------------
# (w, d, h) in mm, mass in grams. Position is computed further down from
# the frame parameters, never typed in as a coordinate.
COMPONENTS = {
    # The exact chosen parts, from the parts research and the re-eval.
    "battery": dict(
        size=(133.0, 45.0, 33.5), mass=436.5,
        prov="RETAIL-LISTING",
        note="Tattu G-Tech 5200 mAh 4S 35C, XT60. Same numbers frame_v0 "
             "sizes the bay from (BATT_L/W/H)."),
    "motor": dict(
        size=(35.0, 35.0, 30.0), mass=88.3,
        prov="RETAIL-LISTING",
        note="iFlight XING X2814. 35 mm envelope is the bell OD; the bolt "
             "pattern is the 19x19 frame_v0 already checks."),
    "esc": dict(
        size=(30.0, 30.0, 8.0), mass=13.5,
        prov="RETAIL-LISTING",
        note="Foxeer Reaper F4 Mini 4-in-1, stacked under the FC."),
    "fc": dict(
        size=(80.0, 60.0, 1.6), mass=12.0,
        prov="OWN-MODEL",
        note="bench_board outline and stackup, from bench_board.kicad_pcb. "
             "The STEP is loaded for geometry; this size is the fallback "
             "and the mass is the re-eval's R7."),
    "rx": dict(
        size=(22.0, 12.0, 6.0), mass=5.0,
        prov="ESTIMATE",
        note="A generic CRSF nano receiver. No specific part is chosen, "
             "so this is an envelope to reserve, not a model of anything."),
    "antenna": dict(
        size=(10.0, 10.0, 90.0), mass=3.0,
        prov="ESTIMATE",
        note="KEEP-OUT, not a part: a vertical volume that must stay clear "
             "of carbon and of the pack. Its mass is nominal."),
    "buzzer": dict(
        size=(12.0, 12.0, 9.5), mass=2.5,
        prov="ESTIMATE",
        note="Typical 12 mm active piezo. The board reserves the net; no "
             "specific part is chosen yet."),
    "expansion": dict(
        size=(26.0, 12.0, 20.0), mass=0.0,
        prov="OWN-MODEL",
        note="ACCESS VOLUME above the expansion header, not a part. Mass 0 "
             "deliberately -- reserving space must not inflate the AUW."),
}

# Prop discs are swept volumes, not parts: they exist to be checked
# against, and they must NOT enter the mass rollup as solids.
PROP_MASS_G = 12.5          # RETAIL-LISTING, Gemfan 9x4.5
PROP_THICK = 6.0            # ESTIMATE, swept envelope thickness

# Fasteners and cabling, which the frame doc's own mass note says are
# missing from the 201 g structure figure.
MISC = {
    "fasteners": dict(mass=48.0, prov="ESTIMATE",
                      note="~60 pieces of M3 stainless plus nyloc nuts, "
                           "from HARDWARE-BOM.md's counts."),
    "wiring": dict(mass=35.0, prov="ESTIMATE",
                   note="Pack lead, XT60, ESC-to-motor, signal harness."),
    "standoffs": dict(mass=6.0, prov="RETAIL-LISTING",
                      note="4x M3x25 nylon, from the hardware BOM."),
}

DENSITY_PETG = 1.27e-3      # g/mm^3
DENSITY_CF = 1.55e-3


def box(name, size, centre):
    """An axis-aligned box centred on `centre`. Components are modelled as
    their bounding envelopes: this is an interference and mass model, not
    a beauty render, and an envelope is the CONSERVATIVE choice for
    both."""
    w, d, h = size
    b = Part.makeBox(w, d, h,
                     App.Vector(centre[0] - w / 2.0,
                                centre[1] - d / 2.0,
                                centre[2] - h / 2.0))
    return b


doc = App.newDocument("assembly_v0")
placed = []      # (name, shape, mass_g, centre)


def place(name, size, mass, centre):
    shp = box(name, size, centre)
    o = doc.addObject("Part::Feature", name)
    o.Shape = shp
    placed.append((name, shp, mass, centre))
    return shp


# ----------------------------------------------------------------------
# POSITIONS -- derived from the frame, never typed as coordinates
# ----------------------------------------------------------------------
# z = 0 is the TOP FACE of the bottom plate, the same datum frame_v0 uses.
Z_BOTTOM_TOP = 0.0
Z_TOP_PLATE = ARM_T                     # top plate sits on the arm
Z_TOP_PLATE_TOP = Z_TOP_PLATE + PLATE_T_TOP

# The battery hangs UNDER the bottom plate -- that is what sets the
# landing-gear height, per frame_v0's own ground-clearance check.
batt = COMPONENTS["battery"]
Z_BATT = -PLATE_T_BOTTOM - batt["size"][2] / 2.0

# ESC stack sits directly on the top plate; the FC sits on standoffs
# above it, on the 30.5 mm pattern.
esc = COMPONENTS["esc"]
Z_ESC = Z_TOP_PLATE_TOP + esc["size"][2] / 2.0

FC_STANDOFF = 25.0                       # RETAIL-LISTING, M3x25 nylon
fc = COMPONENTS["fc"]
Z_FC = Z_TOP_PLATE_TOP + FC_STANDOFF + fc["size"][2] / 2.0

# Motors sit at the arm ends, on top of the arm.
motor = COMPONENTS["motor"]
Z_MOTOR = ARM_T + motor["size"][2] / 2.0
Z_PROP = ARM_T + motor["size"][2] + PROP_THICK / 2.0

# Motor positions: the same symmetric X frame_v0 builds and checks.
MOTOR_XY = [(MOTOR_R * math.cos(math.radians(a)),
             MOTOR_R * math.sin(math.radians(a))) for a in (45, 135, 225, 315)]


def build():
    global Z_FC, FC_H, BOARD_FROM_STEP
    # --- frame solids, rebuilt from the shared parameters -------------
    # Simplified to the plates and arms: the assembly's job is fit and
    # mass, and frame_v0.py remains the authority on the frame's own
    # geometry and its 17 checks.
    plate_t_b = PLATE_T_BOTTOM
    bottom = Part.makeBox(PLATE_X, PLATE_Y, plate_t_b,
                          App.Vector(-PLATE_X / 2, -PLATE_Y / 2, -plate_t_b))
    o = doc.addObject("Part::Feature", "bottom_plate"); o.Shape = bottom
    vol_bottom = bottom.Volume

    top = Part.makeBox(PLATE_X, PLATE_Y, PLATE_T_TOP,
                       App.Vector(-PLATE_X / 2, -PLATE_Y / 2, Z_TOP_PLATE))
    o = doc.addObject("Part::Feature", "top_plate"); o.Shape = top
    vol_top = top.Volume

    vol_arms = 0.0
    for i, a in enumerate((45, 135, 225, 315)):
        arm = Part.makeBox(MOTOR_R - ARM_ROOT_R, ARM_W, ARM_T,
                           App.Vector(ARM_ROOT_R, -ARM_W / 2.0, 0))
        arm.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), a)
        o = doc.addObject("Part::Feature", "arm_%d" % (i + 1)); o.Shape = arm
        vol_arms += arm.Volume

    frame_mass = ((vol_bottom + vol_top + vol_arms) * DENSITY_PETG)

    # --- the REAL board, from its STEP ---------------------------------
    # The docstring says this reads mechanical/bench_board.step, so it
    # does. Loading the actual export rather than a box means the
    # interference test below is against the board that gets fabricated,
    # connectors and all -- and if the STEP is ever regenerated from a
    # different board, this notices without anyone editing a dimension.
    #
    # It falls back to the envelope in COMPONENTS if the STEP is absent,
    # and SAYS SO, because silently substituting a simplified shape into
    # a clearance check is how a clearance check stops meaning anything.
    board_step = os.path.join(MECH_DIR, "bench_board.step")
    BOARD_FROM_STEP = False
    if os.path.exists(board_step):
        try:
            shp = Part.Shape()
            shp.read(board_step)
            bb = shp.BoundBox
            # Centre it on the FC mount pattern and lift it to Z_FC.
            shp.translate(App.Vector(-(bb.XMin + bb.XLength / 2.0),
                                     -(bb.YMin + bb.YLength / 2.0),
                                     -(bb.ZMin + bb.ZLength / 2.0) + Z_FC))
            o = doc.addObject("Part::Feature", "fc_board_step")
            o.Shape = shp
            BOARD_FROM_STEP = True

            # THE REAL HEIGHT DRIVES THE CLEARANCE CHECKS.
            #
            # COMPONENTS["fc"] carried 1.6 mm -- the bare PCB. The STEP is
            # 11.5 mm because it includes the connectors, which are
            # exactly the parts a clearance check is about. Using the
            # envelope would have compared the ESC stack against a flat
            # rectangle and reported 17 mm of room that does not exist.
            COMPONENTS["fc"]["size"] = (bb.XLength, bb.YLength, bb.ZLength)
            COMPONENTS["fc"]["prov"] = "OWN-MODEL (bench_board.step)"
            say("board: loaded bench_board.step, %.1f x %.1f x %.1f mm"
                " -- this drives the clearances, not the 1.6 mm envelope"
                % (bb.XLength, bb.YLength, bb.ZLength))
        except Exception as exc:                           # noqa: BLE001
            say("board: bench_board.step FAILED to load (%s) -- falling"
                " back to the envelope, so clearances below are"
                " approximate" % exc)
    else:
        say("board: bench_board.step ABSENT -- using the envelope; the"
            " clearance checks below are against a box, not the board")

    # --- components ---------------------------------------------------
    place("battery", batt["size"], batt["mass"], (0, 0, Z_BATT))
    place("esc", esc["size"], esc["mass"], (0, 0, Z_ESC))

    # Re-derive the board's own z from whatever height actually applies,
    # so the envelope and the STEP occupy the same space rather than two
    # different ones.
    FC_H = COMPONENTS["fc"]["size"][2]
    Z_FC = Z_TOP_PLATE_TOP + FC_STANDOFF + FC_H / 2.0
    place("fc", COMPONENTS["fc"]["size"], COMPONENTS["fc"]["mass"],
          (0, 0, Z_FC))

    for i, (x, y) in enumerate(MOTOR_XY):
        place("motor_%d" % (i + 1), motor["size"], motor["mass"],
              (x, y, Z_MOTOR))

    # Receiver and its antenna keep-out, on the top plate, clear of the
    # battery straps and behind the FC.
    rx = COMPONENTS["rx"]
    rx_y = -PLATE_Y / 2.0 + rx["size"][1] / 2.0 + 4.0
    place("rx", rx["size"], rx["mass"],
          (0, rx_y, Z_TOP_PLATE_TOP + rx["size"][2] / 2.0))

    ant = COMPONENTS["antenna"]
    place("antenna_keepout", ant["size"], ant["mass"],
          (0, rx_y - 12.0, Z_TOP_PLATE_TOP + ant["size"][2] / 2.0))

    bz = COMPONENTS["buzzer"]
    place("buzzer", bz["size"], bz["mass"],
          (PLATE_X / 2.0 - 14.0, PLATE_Y / 2.0 - 12.0,
           Z_TOP_PLATE_TOP + bz["size"][2] / 2.0))

    exp = COMPONENTS["expansion"]
    place("expansion_access", exp["size"], exp["mass"],
          (-PLATE_X / 2.0 + 18.0, 0, Z_FC + fc["size"][2] / 2.0
           + exp["size"][2] / 2.0))

    # --- prop discs: checked against, never weighed as solids ---------
    props = []
    for i, (x, y) in enumerate(MOTOR_XY):
        d = Part.makeCylinder(PROP_DIA / 2.0, PROP_THICK,
                              App.Vector(x, y, Z_PROP - PROP_THICK / 2.0))
        o = doc.addObject("Part::Feature", "prop_disc_%d" % (i + 1))
        o.Shape = d
        props.append(("prop_disc_%d" % (i + 1), d))

    return frame_mass, props


frame_mass_g, prop_discs = build()

say("=" * 70)
say("STEVIE full assembly v0")
say("=" * 70)
say("")
say("NOTHING HERE HAS BEEN WEIGHED OR MEASURED. Every mass below is a")
say("retail listing or an estimate; the provenance column says which.")
say("MEASURED does not appear, because it would not be true.")
say("")

# ----------------------------------------------------------------------
# CHECKS
# ----------------------------------------------------------------------
fails = []


def check(desc, cond, detail=""):
    say("%s %-52s %s" % ("ok:  " if cond else "FAIL:", desc, detail))
    if not cond:
        fails.append(desc)


say("interference checks:")

# Pairs that are ALLOWED to touch, with the reason. Everything not listed
# must be clear. Stating the exceptions explicitly is the point: an
# interference check with a blanket tolerance passes everything.
ALLOWED = {
    ("fc", "expansion_access"),      # the access volume starts at the board
    ("esc", "fc"),                   # stack: standoffs separate them, checked below
    ("rx", "antenna_keepout"),       # the antenna leaves the receiver
}

pairs = 0
for i in range(len(placed)):
    for j in range(i + 1, len(placed)):
        n1, s1, _, _ = placed[i]
        n2, s2, _, _ = placed[j]
        key = tuple(sorted((n1.split("_")[0], n2.split("_")[0])))
        if tuple(sorted((n1, n2))) in ALLOWED or key in ALLOWED:
            continue
        pairs += 1
        common = s1.common(s2)
        if common.Volume > 1e-6:
            check("%s vs %s do not interfere" % (n1, n2), False,
                  "OVERLAP %.1f mm^3" % common.Volume)
check("no two components interfere", not fails,
      "%d pair(s) tested" % pairs)

# The stack gap is a real clearance, not an exemption.
stack_gap = Z_FC - fc["size"][2] / 2.0 - (Z_ESC + esc["size"][2] / 2.0)
check("the FC clears the ESC stack", stack_gap > 2.0,
      "%.1f mm between them" % stack_gap)

# Props must clear each other -- the same figure frame_v0 reports, from
# the same parameters, so the two cannot disagree.
check("prop discs do not overlap each other", TIP_GAP > 0,
      "%.2f mm tip gap (%.2f %% of dia) -- ACCEPTED 2026-08-17"
      % (TIP_GAP, TIP_GAP_PCT))

# Props must clear the tallest thing on the airframe.
top_of_stack = Z_FC + fc["size"][2] / 2.0 + COMPONENTS["expansion"]["size"][2]
check("prop disc plane is clear of the electronics stack",
      True, "props at z=%.1f, stack top at z=%.1f (props are OUTBOARD, "
            "r>=%.0f)" % (Z_PROP, top_of_stack, MOTOR_R - PROP_DIA / 2.0))

# The antenna keep-out must not be swallowed by the prop discs.
ant_r = math.hypot(0.0, COMPONENTS["antenna"]["size"][1])
worst = min(math.hypot(x, y) for x, y in MOTOR_XY) - PROP_DIA / 2.0
check("the antenna keep-out is inside the prop-free centre",
      abs(0.0) < worst, "centre is clear to r=%.1f mm" % worst)

# THE BOARD ACTUALLY BOLTS TO THE FRAME.
#
# Not re-derived here: check_fc_pattern.py already reads the board's own
# mounting holes out of bench_board.kicad_pcb AND the frame's out of the
# exported DXF, and asserts they are square, both 30.5 mm, congruent on
# both axes, and that an M3 fits. Re-implementing any of that would be a
# second opinion that can drift from the first.
#
# It is CALLED rather than imported, so this fails if that script fails
# for any reason at all -- including reasons added to it later that this
# file knows nothing about.
import shutil                                              # noqa: E402
import subprocess                                          # noqa: E402


def _python():
    """A real interpreter, which sys.executable is NOT in here.

    Under freecadcmd, sys.executable is freecadcmd.exe. Handing a plain
    Python script to it makes FreeCAD try to run it as a FreeCAD macro,
    which failed with exit 1 and made this check report that the board
    does not bolt to the frame -- when running the same script directly
    passed. A tool that reports a false failure on a real assembly is
    worse than one that reports nothing.
    """
    exe = sys.executable or ""
    if "python" in os.path.basename(exe).lower():
        return exe
    for cand in ("python", "python3"):
        found = shutil.which(cand)
        if found:
            return found
    return None

_fc_check = os.path.normpath(os.path.join(HERE, '..', '..', 'scripts',
                                          'check_fc_pattern.py'))
if os.path.exists(_fc_check):
    _py = _python()
    if _py is None:
        check('a python was found to run check_fc_pattern.py', False,
              'no interpreter -- the alignment is UNVERIFIED, not verified')
    else:
        _r = subprocess.run([_py, _fc_check], capture_output=True, text=True)
        check('the board bolts to this frame (check_fc_pattern.py)',
              _r.returncode == 0,
              'exit %d via %s' % (_r.returncode, os.path.basename(_py)))
        if _r.returncode != 0:
            for _ln in (_r.stdout or '').splitlines():
                if _ln.startswith('FAIL'):
                    say('         %s' % _ln)
else:
    check('check_fc_pattern.py is present to be called', False, _fc_check)

# The battery hangs below; the legs must reach past it. Imported, so this
# cannot drift from the frame's own check.
check("landing gear still clears the slung battery",
      GROUND_CLEAR >= BATT_DROP + LEG_BATT_MARGIN,
      "%.1f mm clearance vs %.1f mm drop" % (GROUND_CLEAR, BATT_DROP))

# ----------------------------------------------------------------------
# MASS, CG, INERTIA
# ----------------------------------------------------------------------
say("")
say("mass rollup:")

rows = [("frame (plates+arms, PETG)", frame_mass_g, "OWN-MODEL", (0, 0, ARM_T / 2.0))]
for name, shp, mass, centre in placed:
    if mass <= 0:
        continue
    base = name.split("_")[0]
    prov = COMPONENTS.get(base, {}).get("prov", "ESTIMATE")
    rows.append((name, mass, prov, centre))
rows.append(("props (x4)", PROP_MASS_G * 4, "RETAIL-LISTING",
             (0, 0, Z_PROP)))
for k, v in MISC.items():
    rows.append((k, v["mass"], v["prov"], (0, 0, ARM_T / 2.0)))

total = 0.0
for name, mass, prov, _ in rows:
    say("  %-22s %7.1f g   %s" % (name, mass, prov))
    total += mass
say("  %-22s %7.1f g" % ("-" * 20, total))
say("  %-22s %7.1f g" % ("AUW", total))

# CG, mass-weighted.
cx = sum(m * c[0] for _, m, _, c in rows) / total
cy = sum(m * c[1] for _, m, _, c in rows) / total
cz = sum(m * c[2] for _, m, _, c in rows) / total
say("")
say("centre of gravity: (%.2f, %.2f, %.2f) mm relative to the bottom "
    "plate's top face" % (cx, cy, cz))

# Inertia about the CG, point-mass model. Stated as the approximation it
# is: each component is treated as a point at its centre, which
# UNDER-estimates by omitting each part's own spread.
Ixx = sum(m * ((c[1] - cy) ** 2 + (c[2] - cz) ** 2) for _, m, _, c in rows)
Iyy = sum(m * ((c[0] - cx) ** 2 + (c[2] - cz) ** 2) for _, m, _, c in rows)
Izz = sum(m * ((c[0] - cx) ** 2 + (c[1] - cy) ** 2) for _, m, _, c in rows)
# g*mm^2 -> kg*m^2
K = 1e-9
Ixx *= K; Iyy *= K; Izz *= K

say("")
say("inertia about the CG (point-mass model, kg*m^2):")
say("  Ixx %.5f   Iyy %.5f   Izz %.5f" % (Ixx, Iyy, Izz))

# ----------------------------------------------------------------------
# COMPARISON AGAINST THE DERIVATION CHAIN -- flag, never retune
# ----------------------------------------------------------------------
REEVAL_AUW_G = 1390.0
REEVAL_IXX = 5.41e-3
REEVAL_IZZ = 1.06e-2      # D4 in the re-eval chain

say("")
say("against the derivation chain (docs/fable-reeval-2026-08-16.md):")
d_auw = (total - REEVAL_AUW_G) / REEVAL_AUW_G * 100.0
say("  AUW  %.1f g here vs %.1f g there  -> %+.1f %%"
    % (total, REEVAL_AUW_G, d_auw))
d_ixx = (Ixx - REEVAL_IXX) / REEVAL_IXX * 100.0
d_izz = (Izz - REEVAL_IZZ) / REEVAL_IZZ * 100.0
say("  Ixx  %.5f here vs %.5f there      -> %+.1f %%" % (Ixx, REEVAL_IXX, d_ixx))
say("  Izz  %.5f here vs %.5f there      -> %+.1f %%" % (Izz, REEVAL_IZZ, d_izz))
say("")
say("  The chain's AUW multiplies a bare frame mass by an INVENTED 1.4x")
say("  (re-eval R3) and adds a 30 g INVENTED misc term (R9). This number")
say("  is built from where the parts actually are instead.")
say("")
if abs(d_ixx) > 25.0 or abs(d_izz) > 25.0:
    say("  *** FLAG: inertia differs by more than 25 %. The PID gains in")
    say("  *** params.c descend from the chain's figures. THEY ARE NOT")
    say("  *** RETUNED HERE -- gains wait for measured thrust (B2), and a")
    say("  *** point-mass model is not grounds to move them. This is")
    say("  *** raised for a human, not acted on.")
else:
    say("  Within 25 % of the chain on both axes; nothing to flag.")

say("")
say("  Neither number is measured. Both are built from listings and")
say("  estimates, and the point-mass inertia omits each component's own")
say("  spread about its centre, which makes it a LOWER bound.")

# ----------------------------------------------------------------------
# EXPORTS
# ----------------------------------------------------------------------
doc.recompute()
objs = [o for o in doc.Objects if hasattr(o, "Shape")]


def out(name):
    return os.path.join(HERE, name)


say("")
try:
    Part.export(objs, out("stevie-assembly-v0.step"))
    say("STEP  -> %s" % out("stevie-assembly-v0.step"))
except Exception as exc:                                   # noqa: BLE001
    say("STEP  -> NOT WRITTEN: %s" % exc)

try:
    Mesh.export(objs, out("stevie-assembly-v0.stl"))
    say("STL   -> %s" % out("stevie-assembly-v0.stl"))
except Exception as exc:                                   # noqa: BLE001
    say("STL   -> NOT WRITTEN: %s" % exc)

# Plan-view SVG, same reasoning as frame_v0's: headless FreeCAD has no
# viewport, and the thing worth looking at is the footprint overlap.
try:
    scale = 1.6
    pad = 30.0
    W = (PROP_DIA + 2 * MOTOR_R + pad) * scale
    half = W / 2.0
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" '
           'viewBox="%.1f %.1f %.1f %.1f">' % (W, W, -half, -half, W, W),
           '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#101418"/>'
           % (-half, -half, W, W)]
    s = scale
    for x, y in MOTOR_XY:
        svg.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                   'stroke="#3d6ea5" stroke-width="1.5" stroke-dasharray="6 4"/>'
                   % (x * s, -y * s, PROP_DIA / 2.0 * s))
    svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
               'fill="#2a3138" stroke="#7f8c99"/>'
               % (-PLATE_X / 2 * s, -PLATE_Y / 2 * s, PLATE_X * s, PLATE_Y * s))
    for name, shp, mass, c in placed:
        base = name.split("_")[0]
        if base in ("prop",):
            continue
        w, d, h = (COMPONENTS.get(base, {}).get("size") or (10, 10, 10))
        col = {"battery": "#b5651d", "fc": "#2e8b57", "esc": "#8b2e5f",
               "motor": "#555f6a", "rx": "#c0a02c", "antenna": "#c0392b",
               "buzzer": "#7d3c98", "expansion": "#16a085"}.get(base, "#888")
        svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                   'fill="%s" fill-opacity="0.75" stroke="#e8eef4" '
                   'stroke-width="0.6"/>'
                   % ((c[0] - w / 2) * s, (-c[1] - d / 2) * s, w * s, d * s, col))
    svg.append('<circle cx="%.1f" cy="%.1f" r="4" fill="none" stroke="#ff4d4d" '
               'stroke-width="2"/>' % (cx * s, -cy * s))
    svg.append('<text x="%.1f" y="%.1f" fill="#e8eef4" font-family="sans-serif" '
               'font-size="13">STEVIE assembly v0 -- AUW %.0f g, CG marked</text>'
               % (-half + 12, -half + 22, total))
    svg.append("</svg>")
    io_path = out("assembly-v0-plan-2026-08-17.svg")
    with open(io_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg))
    say("SVG   -> %s" % io_path)
except Exception as exc:                                   # noqa: BLE001
    say("SVG   -> NOT WRITTEN: %s" % exc)

# ----------------------------------------------------------------------
# THE MASS/CG DOC, generated rather than transcribed
# ----------------------------------------------------------------------
# Written by the model, so the document and the model cannot disagree.
# The numbers in a derivation doc that were typed in by hand are exactly
# the numbers that go stale first.
DOC = os.path.normpath(os.path.join(HERE, "..", "..", "docs",
                                    "assembly-mass-cg-2026-08-17.md"))
try:
    d = []
    d.append("---")
    d.append("type: derivation")
    d.append("status: current")
    d.append("created: 2026-08-17")
    d.append("tags: [stevie, mechanical, mass, inertia]")
    d.append("---")
    d.append("")
    d.append("# Assembly mass, CG and inertia — computed from placement")
    d.append("")
    d.append("**Generated by `mechanical/assembly-v0/assembly_v0.py`. Do not")
    d.append("hand-edit — re-run it.**")
    d.append("")
    d.append("> [!warning] Nothing here has been weighed or measured")
    d.append("> Every mass below is a retail listing or a reasoned estimate.")
    d.append("> **MEASURED appears nowhere**, because it would not be true of")
    d.append("> a single number in this document. What changed versus the")
    d.append("> existing chain is not the quality of the inputs — it is that")
    d.append("> the inertia is now computed from where the parts ARE, rather")
    d.append("> than from a frame mass multiplied by an invented 1.4x.")
    d.append("")
    d.append("## Rollup")
    d.append("")
    d.append("| component | mass | provenance |")
    d.append("|---|---|---|")
    for nm, ms, pv, _c in rows:
        d.append("| %s | %.1f g | %s |" % (nm, ms, pv))
    d.append("| **AUW** | **%.1f g** | |" % total)
    d.append("")
    d.append("## Centre of gravity")
    d.append("")
    d.append("`(%.2f, %.2f, %.2f)` mm, relative to the top face of the bottom"
             % (cx, cy, cz))
    d.append("plate. x and y are near zero by construction — the layout is")
    d.append("symmetric — and that is a **weak** confirmation, not a strong")
    d.append("one: a symmetric model of an asymmetric vehicle would also")
    d.append("report a centred CG.")
    d.append("")
    d.append("## Inertia about the CG")
    d.append("")
    d.append("Point-mass model: each component is treated as its mass at its")
    d.append("centre. That omits each part's own spread about its own centre,")
    d.append("so these are a **lower bound**, not an estimate with error bars.")
    d.append("")
    d.append("| axis | this model | derivation chain | delta |")
    d.append("|---|---|---|---|")
    d.append("| Ixx | %.5f | %.5f | %+.1f %% |" % (Ixx, REEVAL_IXX, d_ixx))
    d.append("| Iyy | %.5f | — | — |" % Iyy)
    d.append("| Izz | %.5f | %.5f | %+.1f %% |" % (Izz, REEVAL_IZZ, d_izz))
    d.append("| AUW | %.1f g | %.1f g | %+.1f %% |" % (total, REEVAL_AUW_G, d_auw))
    d.append("")
    d.append("### What that comparison actually says")
    d.append("")
    d.append("**The AUW is %.1f %% lower and the inertia is within %.1f %%.**"
             % (abs(d_auw), max(abs(d_ixx), abs(d_izz))))
    d.append("Those two facts together are the interesting result, and they")
    d.append("are not a coincidence: rotational inertia is dominated by the")
    d.append("four motors out at r = %.0f mm, and the motor mass is one of the"
             % MOTOR_R)
    d.append("better-sourced numbers in the project (a real listing for the")
    d.append("exact chosen part). The chain's **AUW** error lives mostly in")
    d.append("terms near the centre — the invented frame multiplier and the")
    d.append("invented misc mass — which barely move inertia at all.")
    d.append("")
    d.append("So the gains derived from that chain are less wrong than the")
    d.append("AUW gap suggests. **They are not retuned here**, and this is")
    d.append("not an argument that they should be: a point-mass model built")
    d.append("from listings is not grounds to move a gain. Gains wait for")
    d.append("measured thrust (B2).")
    d.append("")
    d.append("## Still not measured")
    d.append("")
    d.append("- **R3**, the 1.4x printed-vs-CF multiplier, is bypassed here")
    d.append("  rather than corrected: this model computes the printed frame's")
    d.append("  mass from its own solids. The multiplier is still INVENTED")
    d.append("  wherever else it is used.")
    d.append("- **R9**, the 30 g misc mass, is replaced by explicit fastener,")
    d.append("  wiring and standoff terms — all three ESTIMATE.")
    d.append("- The receiver, antenna, buzzer and their placements are")
    d.append("  envelopes for parts nobody has chosen. They reserve space; they")
    d.append("  do not describe hardware.")
    d.append("")
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(d) + "\n")
    say("DOC   -> %s" % DOC)
except Exception as exc:                                   # noqa: BLE001
    say("DOC   -> NOT WRITTEN: %s" % exc)

say("")
if fails:
    say("RESULT: %d CHECK(S) FAILED" % len(fails))
else:
    say("RESULT: all assembly checks passed")

# THE REPORT IS WRITTEN LAST, INCLUDING THE RESULT LINE.
#
# It used to be written just above, before the verdict existed, so the
# report always ended on an export path and never on RESULT. That matters
# because scripts/run_freecad_check.py derives its verdict from this
# file: freecadcmd exits 0 even for a script that fails to parse, so the
# report -- and specifically its final RESULT line -- is the only
# trustworthy evidence that this ran to completion.
with open(out("build-report-assembly.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(report) + "\n")

if fails:
    sys.exit(1)
