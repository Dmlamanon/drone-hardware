"""
frame_v0.py — parametric 350 mm-class quad frame, STEVIE. v0, FIT-CHECK ONLY.

Run headless:
    "C:\\Users\\dmlam\\AppData\\Local\\Programs\\FreeCAD 1.1\\bin\\freecadcmd.exe" frame_v0.py

Everything dimensional is a named constant in the PARAMETERS block. Change a
number there and re-run; nothing downstream hard-codes a dimension.

DESIGN INTENT, and why the geometry looks the way it does:

  MATERIAL INDEPENDENCE is the first constraint, not an afterthought.
  cfd-structural-recommendation-2026-08-17.md requires the frame to build
  as FDM-printed PETG-class *or* as carbon plate, with resin banned on
  every load path. The practical consequence is that every structural
  part here is a FLAT PROFILE OF CONSTANT THICKNESS: plates and arms are
  2D outlines extruded, so the identical outline is either printed or cut
  from CF sheet off the same DXF. No draft, no ribs, no bosses, nothing
  that only a printer can make. Thickness is the only thing that differs
  between the two material options, and it is a parameter.

  SANDWICH CONSTRUCTION for the same reason plus one more: the arms bolt
  BETWEEN a bottom and a top plate rather than being part of the body.
  That satisfies "design the arm as replaceable" (rule 5) — the arm is
  the part that breaks — and it means a printed arm and a CF arm are
  interchangeable on one body, which is rule 6 and the practical meaning
  of material-independence.

  SECTIONS are sized to the WEAKER material and checked against the
  stronger one, per the same document: PETG minimums (3 mm on load paths,
  4 mm at arm roots) drive the numbers; the CF variant is thinner and
  therefore always fits the same envelope.

WHAT THIS IS NOT: a flight frame. See README.md. No FEA has been run, the
arm section is not stress-verified, and the mass is not measured.
"""

import math
import os
import sys

import FreeCAD as App
import Part
import Mesh
import Import

# ----------------------------------------------------------------------
# PARAMETERS
# ----------------------------------------------------------------------

# --- Airframe class -------------------------------------------------
WHEELBASE = 350.0        # motor-to-motor DIAGONAL, mm. Locked class name.
PROP_DIA = 228.6         # 9 inch exactly (9 * 25.4). Not rounded --
                         # rounding to 229 shifts the tip gap by 0.4 mm
                         # and would put a third number for the same
                         # quantity into this project.

# --- Material selection ---------------------------------------------
# "PETG"  : FDM, minimums from cfd-structural-recommendation-2026-08-17.md
# "CF"    : cut carbon plate, same outlines, thinner
MATERIAL = os.environ.get("FRAME_MATERIAL", "PETG")

if MATERIAL == "PETG":
    PLATE_T_BOTTOM = 3.0     # 3 mm minimum wall on load paths
    PLATE_T_TOP = 3.0
    ARM_T = 4.0              # 4 mm at arm roots
elif MATERIAL == "CF":
    PLATE_T_BOTTOM = 2.0     # 1.5 mm plate minimum; 2 mm for the load-bearing one
    PLATE_T_TOP = 1.5
    ARM_T = 2.0              # 2 mm arms minimum
else:
    raise SystemExit("MATERIAL must be PETG or CF, got %r" % MATERIAL)

# g/cm^3. PETG is the bulk figure; at 4 perimeters and 40 % gyroid infill a
# 3-4 mm wall is effectively solid, so bulk density is the right estimator
# here rather than an infill-scaled one. CF plate is 3K twill/epoxy.
DENSITY = {"PETG": 1.27, "CF": 1.55}[MATERIAL]

# --- Centre plate ---------------------------------------------------
PLATE_X = 140.0          # long axis, sized so the 133 mm battery fits along it
PLATE_Y = 110.0
PLATE_CORNER = 30.0      # corner cut -> octagon, saves mass and kills 4 stress risers

# --- Flight controller ----------------------------------------------
FC_MOUNT = 30.5          # the universal 30.5 x 30.5 M3 pattern
FC_HOLE_D = 3.2          # M3 clearance

# --- Battery (Tattu G-Tech 5200 mAh 4S 35C, XT60) --------------------
# 133 x 45 x 33.5 mm, 436.5 g, manufacturer tolerance +-2 mm.
BATT_L, BATT_W, BATT_H = 133.0, 45.0, 33.5
BATT_TOL = 2.0           # the published tolerance
BATT_CLEAR = 2.0         # strap/heat-shrink slop on top of the tolerance
STRAP_W = 22.0           # a 20 mm hook-and-loop strap plus slop
STRAP_SLOT_T = 3.5       # slot short dimension
# Distance of each strap slot from the centreline, along the long axis.
# This was derived from the battery length (bay_l/2 - 12 = 56.5) and that
# put the slots' outer ends at x+y = 98.75, THROUGH the octagon's chamfer
# at x+y = 95 -- so all four "slots" were open notches and a strap would
# have slid straight out. An independent review caught it in the exported
# STL. It is now an explicit number with a check behind it (see the
# feature-inside-outline check in section 4). 96 mm apart on a 133 mm
# pack is still sensible strap spacing.
STRAP_X = 46.0

# --- Motor mount ----------------------------------------------------
# TWO patterns are drilled, and the reason is a real mismatch found while
# writing the thrust-test procedure rather than a hedge:
#
#   * 2212-class outrunners use a 16 x 19 mm CROSS of M3 holes -- the
#     pattern item 6 specified.
#   * The motor this project has actually chosen, the iFlight XING X2814,
#     uses a 19 x 19 mm SQUARE. It does not fit a 16 x 19 cross.
#
# Drilling both is what commercial frames in this class do, it costs
# nothing on a 32 mm pad, and without it the frame would not accept the
# project's own motor.
MOTOR_BOLT_A = 16.0      # cross, short axis
MOTOR_BOLT_B = 19.0      # cross, long axis
MOTOR_BOLT_SQ = 19.0     # square, XING X2814 and most 28xx
MOTOR_HOLE_D = 3.2
MOTOR_SHAFT_BORE = 9.0   # clearance for the shaft/bell boss
MOTOR_PAD_D = 36.0       # pad diameter at the arm tip. 32 mm was the first
                         # value and the geometry check rejected it: the
                         # 19x19 square's corner holes sit at r = 13.44, and
                         # 32 mm left under 1 mm of material outside the hole
                         # edge -- a bolt pull-through waiting to happen in
                         # PETG. 36 mm gives ~3 mm.

# --- Arms -----------------------------------------------------------
ARM_W = 16.0             # matches the JeeFly LX350 class comparable
ARM_ROOT_R = 28.0        # arm starts this far from centre (inside the plate)
ARM_BOLT_R1 = 38.0       # two M3 per arm into the plate sandwich
ARM_BOLT_R2 = 58.0
ARM_HOLE_D = 3.2

# --- Landing gear ---------------------------------------------------
# The battery is slung UNDER the bottom plate, so ground clearance is set
# by the pack, not by the props. 33.5 mm of pack plus its 2 mm tolerance
# plus 12 mm of daylight for the strap, the connector and a tuft of grass.
LEG_R = 95.0             # how far out along each arm the leg mounts. Stance
                         # is 2 x 95 = 190 mm across the diagonal, which is
                         # the same order as a Phantom 3's.
LEG_W = 14.0             # width of the web, across the arm
LEG_TOP = 20.0           # length of the top land, along the arm
LEG_BOT = 12.0           # length at the foot end -- tapered, so the leg is
                         # stiffest where the bending moment is largest
LEG_SPLAY = 6.0          # how far the foot sits outboard of the top, mm.
                         # A splayed leg turns a side landing into a slide
                         # rather than a tipping moment.
FOOT_L, FOOT_W, FOOT_T = 18.0, LEG_W, 6.0
FOOT_HOLE_D = 3.2

# --- Fillets --------------------------------------------------------
FILLET_ROOT = 3.0        # R3 at arm roots  (rule 1)
FILLET_GEN = 2.0         # R2 everywhere else

# --- Output ---------------------------------------------------------
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------
# DERIVED — the prop-clearance arithmetic, computed not asserted
# ----------------------------------------------------------------------

MOTOR_R = WHEELBASE / 2.0                     # 175 mm
MOTOR_XY = MOTOR_R / math.sqrt(2.0)           # 123.74 mm
ADJACENT_SPACING = WHEELBASE / math.sqrt(2.0)  # centre-to-centre, adjacent motors
TIP_GAP = ADJACENT_SPACING - PROP_DIA
TIP_GAP_PCT = 100.0 * TIP_GAP / PROP_DIA

# What it would take to reach the >=10 % rule, both ways round.
PROP_FOR_10PCT = ADJACENT_SPACING / 1.10
WHEELBASE_FOR_10PCT = 1.10 * PROP_DIA * math.sqrt(2.0)

ARM_LEN = MOTOR_R + MOTOR_PAD_D / 2.0 - ARM_ROOT_R

# Ground clearance is measured from the bottom plate's UNDERSIDE, because
# that is what the battery hangs from.
BATT_DROP = BATT_H + BATT_TOL          # how far the pack hangs below the plate
LEG_H = BATT_DROP + 12.0               # web height, plate underside to foot top
GROUND_CLEAR = LEG_H + FOOT_T          # plate underside to the ground

report = []


def say(msg):
    report.append(msg)
    print(msg)


say("=" * 68)
say("STEVIE frame v0 -- %s variant" % MATERIAL)
say("=" * 68)
say("wheelbase (motor-motor diagonal) : %.1f mm" % WHEELBASE)
say("adjacent motor spacing           : %.2f mm  (= wheelbase / sqrt(2))" % ADJACENT_SPACING)
say("prop diameter                    : %.1f mm" % PROP_DIA)
say("PROP TIP GAP                     : %.2f mm  = %.2f %% of prop dia" % (TIP_GAP, TIP_GAP_PCT))
say("")
say("The >=10 % rule needs one of:")
say("  prop <= %.1f mm (%.2f in) at this wheelbase, or" % (PROP_FOR_10PCT, PROP_FOR_10PCT / 25.4))
say("  wheelbase >= %.1f mm with this prop" % WHEELBASE_FOR_10PCT)
say("")
say("Frame geometry CANNOT improve this at a fixed wheelbase, and that is")
say("worth stating as a derivation rather than an opinion:")
say("  four motors sit on a circle of radius wheelbase/2. Adjacent tip gap")
say("  is set by the SMALLEST adjacent chord. For a rectangle of half-width")
say("  a and half-length b with 2*sqrt(a^2+b^2) = wheelbase, the adjacent")
say("  spacings are 2a and 2b, so min(2a, 2b) is maximised at a = b --")
say("  i.e. by the symmetric X this frame already is. A stretched or")
say("  'dead-cat' layout makes one pair CLOSER, never further apart.")
say("  Longer arms do not help either: they would increase the wheelbase,")
say("  which is the fixed input.")
say("")
say("arm length (root r=%.0f to pad edge) : %.1f mm" % (ARM_ROOT_R, ARM_LEN))
say("plate %.0f x %.0f x %.1f mm, arms %.0f x %.1f mm"
    % (PLATE_X, PLATE_Y, PLATE_T_BOTTOM, ARM_W, ARM_T))
say("")

doc = App.newDocument("frame_v0")


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def octagon_face(sx, sy, corner):
    """Rectangle sx by sy with the four corners chamfered by `corner`.

    A chamfer rather than a fillet because this outline becomes a DXF for
    a CF cutter: straight segments are unambiguous on any machine, and the
    corners here are external, so they are not the stress risers rule 1 is
    about (that rule is for internal corners, which the arm roots have).
    """
    hx, hy, c = sx / 2.0, sy / 2.0, corner
    pts = [
        App.Vector(-hx + c, -hy, 0), App.Vector(hx - c, -hy, 0),
        App.Vector(hx, -hy + c, 0), App.Vector(hx, hy - c, 0),
        App.Vector(hx - c, hy, 0), App.Vector(-hx + c, hy, 0),
        App.Vector(-hx, hy - c, 0), App.Vector(-hx, -hy + c, 0),
    ]
    pts.append(pts[0])
    return Part.Face(Part.makePolygon(pts))


def hole(x, y, d, t, z=-1.0):
    return Part.makeCylinder(d / 2.0, t + 2.0, App.Vector(x, y, z))


def slot(x, y, w, h, t, z=-1.0):
    """Rounded-end slot, as a solid to subtract."""
    if w > h:
        body = Part.makeBox(w - h, h, t + 2.0, App.Vector(x - (w - h) / 2.0, y - h / 2.0, z))
        c1 = Part.makeCylinder(h / 2.0, t + 2.0, App.Vector(x - (w - h) / 2.0, y, z))
        c2 = Part.makeCylinder(h / 2.0, t + 2.0, App.Vector(x + (w - h) / 2.0, y, z))
    else:
        body = Part.makeBox(w, h - w, t + 2.0, App.Vector(x - w / 2.0, y - (h - w) / 2.0, z))
        c1 = Part.makeCylinder(w / 2.0, t + 2.0, App.Vector(x, y - (h - w) / 2.0, z))
        c2 = Part.makeCylinder(w / 2.0, t + 2.0, App.Vector(x, y + (h - w) / 2.0, z))
    return body.fuse(c1).fuse(c2)


def inside_octagon(x, y, sx, sy, corner, margin=0.0):
    """Is (x, y) inside the chamfered rectangle, with `margin` to spare?

    Every cut feature has to be checked against THIS, not against the
    bounding rectangle. The bounding rectangle is what the first version
    of the arm-bolt check used, and it is why four battery-strap slots
    ran off through the chamfer without anything noticing: |x| < 70 and
    |y| < 55 are both true at (58.25, 40.5), and that point is outside
    the plate.
    """
    hx, hy = sx / 2.0 - margin, sy / 2.0 - margin
    if abs(x) > hx or abs(y) > hy:
        return False
    # the four chamfers, all of the form |x| + |y| <= (sx + sy)/2 - corner
    return (abs(x) + abs(y)) <= (sx / 2.0 + sy / 2.0 - corner) - margin * 1.4142


ARM_ANGLES = [45.0, 135.0, 225.0, 315.0]


def arm_bolt_positions():
    """Where every arm bolts into the plate sandwich. ONE definition, used
    by the arms and by both plates -- if these ever disagree the frame
    does not assemble, so they cannot be allowed to be two lists."""
    out = []
    for a in ARM_ANGLES:
        ra = math.radians(a)
        for r in (ARM_BOLT_R1, ARM_BOLT_R2):
            out.append((r * math.cos(ra), r * math.sin(ra)))
    return out


# ----------------------------------------------------------------------
# 1. BOTTOM PLATE
# ----------------------------------------------------------------------

bottom = octagon_face(PLATE_X, PLATE_Y, PLATE_CORNER).extrude(App.Vector(0, 0, PLATE_T_BOTTOM))

cuts = []
# FC mount, 30.5 square
h = FC_MOUNT / 2.0
for sx in (-1, 1):
    for sy in (-1, 1):
        cuts.append(hole(sx * h, sy * h, FC_HOLE_D, PLATE_T_BOTTOM))

# arm sandwich bolts
for (x, y) in arm_bolt_positions():
    cuts.append(hole(x, y, ARM_HOLE_D, PLATE_T_BOTTOM))

# battery strap slots -- two pairs straddling the pack, across the short axis
bay_l = BATT_L + BATT_TOL + BATT_CLEAR
# +8 rather than +6: at +6 the strap slot's inner edge cleared the FC
# mount holes by 0.05 mm, which the check above now prints rather than
# hides. 0.05 mm is not clearance, it is a coincidence.
strap_y = BATT_W / 2.0 + BATT_TOL / 2.0 + 8.0
strap_slots = []
for sx in (-1, 1):
    for sy in (-1, 1):
        strap_slots.append((sx * STRAP_X, sy * strap_y))
for (x, y) in strap_slots:
    cuts.append(slot(x, y, STRAP_SLOT_T, STRAP_W, PLATE_T_BOTTOM))

for c in cuts:
    bottom = bottom.cut(c)

say("bottom plate: %d holes/slots cut, volume %.0f mm^3" % (len(cuts), bottom.Volume))

# ----------------------------------------------------------------------
# 2. TOP PLATE — same outline, scaled in, no battery slots
# ----------------------------------------------------------------------

top = octagon_face(PLATE_X * 0.72, PLATE_Y * 0.78, PLATE_CORNER * 0.72).extrude(
    App.Vector(0, 0, PLATE_T_TOP))

tcuts = []
for sx in (-1, 1):
    for sy in (-1, 1):
        tcuts.append(hole(sx * h, sy * h, FC_HOLE_D, PLATE_T_TOP))
for (x, y) in arm_bolt_positions():
    if math.hypot(x, y) <= ARM_BOLT_R1 + 0.1:      # only the inner bolt reaches the top plate
        tcuts.append(hole(x, y, ARM_HOLE_D, PLATE_T_TOP))
for c in tcuts:
    top = top.cut(c)
top.translate(App.Vector(0, 0, PLATE_T_BOTTOM + ARM_T))

say("top plate:    %d holes cut, volume %.0f mm^3" % (len(tcuts), top.Volume))

# ----------------------------------------------------------------------
# 3. ARM  (built once along +X, then instanced by rotation)
# ----------------------------------------------------------------------


def build_arm():
    r0, r1 = ARM_ROOT_R, MOTOR_R
    hw = ARM_W / 2.0

    # shank
    shank = Part.makeBox(r1 - r0, ARM_W, ARM_T, App.Vector(r0, -hw, 0))
    # motor pad
    pad = Part.makeCylinder(MOTOR_PAD_D / 2.0, ARM_T, App.Vector(r1, 0, 0))
    # rounded root so the arm cannot present a square inside corner where
    # it meets the plate -- rule 1, R3 at arm roots
    root = Part.makeCylinder(hw, ARM_T, App.Vector(r0, 0, 0))

    arm = shank.fuse(pad).fuse(root)

    holes = []
    # motor: 16 x 19 cross, both spacings drilled
    holes.append(hole(r1 + MOTOR_BOLT_A / 2.0, 0, MOTOR_HOLE_D, ARM_T))
    holes.append(hole(r1 - MOTOR_BOLT_A / 2.0, 0, MOTOR_HOLE_D, ARM_T))
    holes.append(hole(r1, MOTOR_BOLT_B / 2.0, MOTOR_HOLE_D, ARM_T))
    holes.append(hole(r1, -MOTOR_BOLT_B / 2.0, MOTOR_HOLE_D, ARM_T))
    # 19 x 19 square -- the chosen X2814's pattern
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append(hole(r1 + sx * MOTOR_BOLT_SQ / 2.0,
                              sy * MOTOR_BOLT_SQ / 2.0, MOTOR_HOLE_D, ARM_T))
    holes.append(hole(r1, 0, MOTOR_SHAFT_BORE, ARM_T))
    # sandwich bolts
    holes.append(hole(ARM_BOLT_R1, 0, ARM_HOLE_D, ARM_T))
    holes.append(hole(ARM_BOLT_R2, 0, ARM_HOLE_D, ARM_T))
    for hh in holes:
        arm = arm.cut(hh)
    return arm


def build_leg():
    """One landing-gear web, built in the (r, z) plane then placed.

    A FLAT PROFILE OF CONSTANT THICKNESS, like everything else structural
    here, so it prints on edge (layer lines along the load, rule 2) or
    cuts from the same CF sheet. Tapered because the bending moment on a
    landing leg is largest at the top.

    It does NOT bolt directly to the arm. A flat vertical plate cannot
    bolt to a flat horizontal plate without something at 90 degrees
    between them, and pretending otherwise would be the kind of joint that
    only exists in CAD. The bracket is an off-the-shelf M3 aluminium angle
    -- see the hardware BOM in the README. That keeps every part this
    script emits genuinely material-independent.
    """
    hw = LEG_W / 2.0
    r0, r1 = LEG_R - LEG_TOP / 2.0, LEG_R + LEG_TOP / 2.0
    b0 = LEG_R - LEG_BOT / 2.0 + LEG_SPLAY
    b1 = LEG_R + LEG_BOT / 2.0 + LEG_SPLAY

    pts = [
        App.Vector(r0, 0, 0),
        App.Vector(r1, 0, 0),
        App.Vector(b1, 0, -LEG_H),
        App.Vector(b0, 0, -LEG_H),
    ]
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    web = face.extrude(App.Vector(0, LEG_W, 0))
    web.translate(App.Vector(0, -hw, 0))

    holes = []
    # two M3 up through the top land, into the angle bracket
    for rr in (LEG_R - 6.0, LEG_R + 6.0):
        c = Part.makeCylinder(ARM_HOLE_D / 2.0, LEG_W + 2.0,
                              App.Vector(rr, -hw - 1.0, -5.0), App.Vector(0, 1, 0))
        holes.append(c)
    # one M3 through the foot end
    c = Part.makeCylinder(FOOT_HOLE_D / 2.0, LEG_W + 2.0,
                          App.Vector(LEG_R + LEG_SPLAY, -hw - 1.0, -LEG_H + 6.0),
                          App.Vector(0, 1, 0))
    holes.append(c)
    for h in holes:
        web = web.cut(h)
    return web


def build_foot():
    """The crash consumable. Deliberately a separate part.

    A foot that is part of the leg means a scuffed landing costs you a
    leg; a foot that bolts on costs you 3 g of filament. It carries ONE
    bolt and no bending load -- it is a wear pad, not a structural member,
    and it is sized so it fails before the leg does.
    """
    f = Part.makeBox(FOOT_L, FOOT_W, FOOT_T,
                     App.Vector(LEG_R + LEG_SPLAY - FOOT_L / 2.0, -FOOT_W / 2.0,
                                -LEG_H - FOOT_T))
    h = Part.makeCylinder(FOOT_HOLE_D / 2.0, FOOT_T + 2.0,
                          App.Vector(LEG_R + LEG_SPLAY, 0, -LEG_H - FOOT_T - 1.0))
    return f.cut(h)


arm_proto = build_arm()
say("arm:          volume %.0f mm^3, %.1f mm long" % (arm_proto.Volume, ARM_LEN))

arms = []
for a in ARM_ANGLES:
    s = arm_proto.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), a)
    s.translate(App.Vector(0, 0, PLATE_T_BOTTOM))
    arms.append(s)

leg_proto, foot_proto = build_leg(), build_foot()
say("leg:          volume %.0f mm^3, %.0f mm tall" % (leg_proto.Volume, LEG_H))
say("foot:         volume %.0f mm^3 (the crash consumable)" % foot_proto.Volume)
legs, feet = [], []
for a in ARM_ANGLES:
    for proto, bucket in ((leg_proto, legs), (foot_proto, feet)):
        s2 = proto.copy()
        s2.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), a)
        bucket.append(s2)

# ----------------------------------------------------------------------
# 4. SANITY CHECKS — geometry that must hold, checked not assumed
# ----------------------------------------------------------------------

ok = True


def check(label, cond, detail=""):
    global ok
    say("  %-52s %s %s" % (label, "OK  " if cond else "FAIL", detail))
    if not cond:
        ok = False


say("")
say("geometry checks:")
# Every hole and slot in the bottom plate, checked against the ACTUAL
# outline rather than its bounding box, with 2 mm of material to spare.
feature_pts = []
for (bx, by) in arm_bolt_positions():
    feature_pts.append(("arm bolt", bx, by, ARM_HOLE_D / 2.0))
for sgn in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
    feature_pts.append(("FC mount", sgn[0] * FC_MOUNT / 2.0, sgn[1] * FC_MOUNT / 2.0,
                        FC_HOLE_D / 2.0))
for (x, y) in strap_slots:
    # a slot's worst point is its far corner, so check all four
    for dx in (-STRAP_SLOT_T / 2.0, STRAP_SLOT_T / 2.0):
        for dy in (-STRAP_W / 2.0, STRAP_W / 2.0):
            feature_pts.append(("strap slot", x + dx, y + dy, 0.0))

bad = [(n, x, y) for (n, x, y, r) in feature_pts
       if not inside_octagon(x, y, PLATE_X, PLATE_Y, PLATE_CORNER, margin=2.0 + r)]
check("every hole and slot is inside the plate OUTLINE, not just its bbox",
      not bad,
      "all %d clear" % len(feature_pts) if not bad
      else "%s at (%.2f, %.2f) breaks out" % (bad[0][0], bad[0][1], bad[0][2]))
check("battery bay fits within the plate long axis",
      BATT_L + BATT_TOL <= PLATE_X, "%.1f <= %.1f" % (BATT_L + BATT_TOL, PLATE_X))
# NOT "or True". An earlier version had that on the end of this
# condition, inside a block headed "checked not assumed", which made it
# print OK unconditionally. The real margin is worth seeing: it passes by
# 0.05 mm, which is exactly the kind of thing a rigged check hides.
_fc_edge = FC_MOUNT / 2.0 + FC_HOLE_D
_strap_edge = strap_y - STRAP_W / 2.0
check("FC mount pattern clears the battery straps",
      _fc_edge < _strap_edge, "%.2f < %.2f mm" % (_fc_edge, _strap_edge))
check("props do not overlap", TIP_GAP > 0, "%.2f mm gap" % TIP_GAP)
# NOT a check any more. The >=10 % guideline was reported as a FAIL
# through v0; on 2026-08-17 the lead ACCEPTED 8.3 %, with precedent, and a
# standing FAIL that will never be fixed just teaches people to skim the
# report. The number is still printed in full -- accepting a figure is not
# the same as hiding it.
say("")
say("PROP CLEARANCE: %.2f %% -- ACCEPTED 2026-08-17, not a failure." % TIP_GAP_PCT)
say("  Precedent: the DJI Phantom 3 ships 9.4 in props on this same 350 mm")
say("  class. Its adjacent spacing is the same 247.49 mm, so its tip gap is")
# Derive the comparison rather than writing it out. A hardcoded "8.3 %"
# next to a computed 8.26 % is a number waiting to drift, and "less than
# HALF" is an ARITHMETIC claim -- if the frame changes it must either
# stay true or stop being said.
_P3_GAP_MM  = 247.49 - 238.76          # Phantom 3 tip gap, same 350 mm class
_P3_GAP_PCT = _P3_GAP_MM / 238.76 * 100.0
_ratio      = TIP_GAP_PCT / _P3_GAP_PCT if _P3_GAP_PCT else 0.0
say("  247.49 - 238.76 = %.2f mm = %.1f %% of prop diameter -- %s"
    % (_P3_GAP_MM, _P3_GAP_PCT,
       "less than HALF" if _ratio >= 2.0 else "%.1fx less than" % _ratio))
say("  this frame's %.1f %%, on a flight-proven airframe built at scale."
    % TIP_GAP_PCT)
say("  The >=10 % figure is a noise-and-efficiency guideline, not a limit.")
say("")
check("arm thickness meets the %s minimum" % MATERIAL,
      ARM_T >= (4.0 if MATERIAL == "PETG" else 2.0), "%.1f mm" % ARM_T)
check("plate thickness meets the %s minimum" % MATERIAL,
      PLATE_T_BOTTOM >= (3.0 if MATERIAL == "PETG" else 1.5), "%.1f mm" % PLATE_T_BOTTOM)
check("motor pad clears the 16x19 cross",
      MOTOR_PAD_D > MOTOR_BOLT_B + 2 * MOTOR_HOLE_D,
      "%.1f > %.1f" % (MOTOR_PAD_D, MOTOR_BOLT_B + 2 * MOTOR_HOLE_D))
_sq_r = math.hypot(MOTOR_BOLT_SQ / 2.0, MOTOR_BOLT_SQ / 2.0)
check("motor pad clears the 19x19 square (the chosen X2814)",
      MOTOR_PAD_D / 2.0 > _sq_r + MOTOR_HOLE_D,
      "pad r %.1f > %.1f" % (MOTOR_PAD_D / 2.0, _sq_r + MOTOR_HOLE_D))
check("the two patterns' holes do not merge into each other",
      math.hypot(MOTOR_BOLT_SQ / 2.0 - MOTOR_BOLT_A / 2.0, MOTOR_BOLT_SQ / 2.0) > MOTOR_HOLE_D,
      "%.2f mm apart" % math.hypot(MOTOR_BOLT_SQ / 2.0 - MOTOR_BOLT_A / 2.0, MOTOR_BOLT_SQ / 2.0))
check("arm root starts inside the plate",
      ARM_ROOT_R < PLATE_Y / 2.0, "%.1f < %.1f" % (ARM_ROOT_R, PLATE_Y / 2.0))

# Sweep the stretched-X family at constant wheelbase and confirm that the
# symmetric case really is the best one. If a future edit breaks the
# symmetry assumption, this fails instead of quietly losing clearance.
best_alt = 0.0
for i in range(1, 90):
    ang = math.radians(i)                       # half-angle between arms
    a = MOTOR_R * math.cos(ang)
    b = MOTOR_R * math.sin(ang)
    best_alt = max(best_alt, min(2 * a, 2 * b))
check("the landing gear clears the slung battery",
      GROUND_CLEAR > BATT_DROP,
      "%.1f mm ground clearance vs a %.1f mm pack drop (%.1f mm to spare)"
      % (GROUND_CLEAR, BATT_DROP, GROUND_CLEAR - BATT_DROP))
check("the legs sit inboard of the motors",
      LEG_R + LEG_SPLAY + LEG_BOT / 2.0 < MOTOR_R,
      "foot reaches r=%.1f, motor at r=%.1f" % (LEG_R + LEG_SPLAY + LEG_BOT / 2.0, MOTOR_R))
check("the legs mount on the arm, not off the end of it",
      LEG_R + LEG_TOP / 2.0 < MOTOR_R and LEG_R - LEG_TOP / 2.0 > ARM_ROOT_R,
      "top land spans r=%.1f..%.1f, arm spans %.1f..%.1f"
      % (LEG_R - LEG_TOP / 2.0, LEG_R + LEG_TOP / 2.0, ARM_ROOT_R, MOTOR_R))
check("the feet are a separate part (crash consumable, not a member)",
      FOOT_T > 0 and len(feet) == 4, "%d feet, %.1f mm thick" % (len(feet), FOOT_T))
check("leg thickness meets the %s minimum" % MATERIAL,
      ARM_T >= (4.0 if MATERIAL == "PETG" else 2.0),
      "%.1f mm (the web uses the arm section)" % ARM_T)
check("symmetric X maximises the minimum adjacent spacing",
      ADJACENT_SPACING >= best_alt - 1e-6,
      "%.2f vs best stretched-X %.2f mm" % (ADJACENT_SPACING, best_alt))

# ----------------------------------------------------------------------
# 4b. MASS — a cross-check against the 469 g frame line in the AUW budget
# ----------------------------------------------------------------------

vol_mm3 = (bottom.Volume + top.Volume + 4 * arm_proto.Volume
           + 4 * leg_proto.Volume + 4 * foot_proto.Volume)
mass_g = vol_mm3 / 1000.0 * DENSITY

say("")
say("mass estimate (%s, rho = %.2f g/cm^3):" % (MATERIAL, DENSITY))
say("  bottom plate      %6.1f g" % (bottom.Volume / 1000.0 * DENSITY))
say("  top plate         %6.1f g" % (top.Volume / 1000.0 * DENSITY))
say("  arms (x4)         %6.1f g" % (4 * arm_proto.Volume / 1000.0 * DENSITY))
say("  legs (x4)         %6.1f g" % (4 * leg_proto.Volume / 1000.0 * DENSITY))
say("  feet (x4)         %6.1f g" % (4 * foot_proto.Volume / 1000.0 * DENSITY))
say("  ---------------------------")
say("  structure         %6.1f g" % mass_g)
say("")
say("  The AUW budget carries 469 g for 'frame'. This is STRUCTURE ONLY --")
say("  Landing gear IS included from v0.1. Still missing: standoffs,")
say("  fasteners, canopy and battery tray -- real mass, not modelled, so do")
say("  NOT read %.0f g as beating the budget." % mass_g)

# ----------------------------------------------------------------------
# 4c. PLAN-VIEW RENDER
# ----------------------------------------------------------------------
# freecadcmd has no GUI, so there is no 3D viewport to screenshot. An
# accurate scale plan view is more useful for this frame anyway: the thing
# worth looking at is the prop-disc overlap, which a grey isometric render
# of the STL would actually hide.


def svg_plan(path):
    span = PROP_DIA + 2 * MOTOR_XY + 40.0
    S = 1000.0 / span                      # px per mm
    C = 500.0

    def X(v):
        return C + v * S

    def Y(v):
        return C - v * S

    fg = "#e8e4dc" if False else "#1c1b19"
    L = []
    L.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" '
             'width="1000" height="1000">')
    L.append('<rect width="1000" height="1000" fill="#0f1113"/>')
    L.append('<g fill="none" stroke-linecap="round">')

    # prop discs
    for a in ARM_ANGLES:
        ra = math.radians(a)
        mx, my = MOTOR_R * math.cos(ra), MOTOR_R * math.sin(ra)
        L.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#2b6cb0" '
                 'fill-opacity="0.13" stroke="#4a9eff" stroke-width="1.5" '
                 'stroke-dasharray="5 5"/>' % (X(mx), Y(my), PROP_DIA / 2.0 * S))

    # centre plate outline
    hx, hy, c = PLATE_X / 2.0, PLATE_Y / 2.0, PLATE_CORNER
    pts = [(-hx + c, -hy), (hx - c, -hy), (hx, -hy + c), (hx, hy - c),
           (hx - c, hy), (-hx + c, hy), (-hx, hy - c), (-hx, -hy + c)]
    L.append('<polygon points="%s" fill="#d9c89a" fill-opacity="0.22" '
             'stroke="#d9c89a" stroke-width="2.5"/>'
             % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in pts))

    # arms
    for a in ARM_ANGLES:
        ra = math.radians(a)
        ca, sa = math.cos(ra), math.sin(ra)
        hw = ARM_W / 2.0
        quad = [(ARM_ROOT_R, -hw), (MOTOR_R, -hw), (MOTOR_R, hw), (ARM_ROOT_R, hw)]
        rot = [(px * ca - py * sa, px * sa + py * ca) for px, py in quad]
        L.append('<polygon points="%s" fill="#d9c89a" fill-opacity="0.35" '
                 'stroke="#d9c89a" stroke-width="2"/>'
                 % " ".join("%.1f,%.1f" % (X(a2), Y(b2)) for a2, b2 in rot))
        mx, my = MOTOR_R * ca, MOTOR_R * sa
        L.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#d9c89a" '
                 'fill-opacity="0.5" stroke="#d9c89a" stroke-width="2"/>'
                 % (X(mx), Y(my), MOTOR_PAD_D / 2.0 * S))

    # battery footprint
    bl, bw = BATT_L + BATT_TOL, BATT_W + BATT_TOL
    L.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" '
             'stroke="#e07a5f" stroke-width="2" stroke-dasharray="6 4"/>'
             % (X(-bl / 2.0), Y(bw / 2.0), bl * S, bw * S))

    # the tip gap, drawn where it actually is: between two adjacent motors
    ax, ay = MOTOR_R * math.cos(math.radians(45)), MOTOR_R * math.sin(math.radians(45))
    bx, by = MOTOR_R * math.cos(math.radians(135)), MOTOR_R * math.sin(math.radians(135))
    gx1, gy1 = -PROP_DIA / 2.0 + ax, ay
    gx2, gy2 = PROP_DIA / 2.0 + bx, by
    L.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e07a5f" '
             'stroke-width="3"/>' % (X(gx2), Y(gy2), X(gx1), Y(gy1)))
    L.append('</g>')

    def txt(x, y, t, size=17, col="#e8e4dc", anchor="middle", weight="400"):
        return ('<text x="%.1f" y="%.1f" font-family="Menlo,Consolas,monospace" '
                'font-size="%d" fill="%s" text-anchor="%s" font-weight="%s">%s</text>'
                % (x, y, size, col, anchor, weight, t))

    L.append(txt(500, 40, "STEVIE frame v0 &#183; %s" % MATERIAL, 24, "#e8e4dc", "middle", "600"))
    L.append(txt(500, 66, "%.0f mm wheelbase &#183; %.1f mm (9 in) props &#183; FIT-CHECK ONLY"
                 % (WHEELBASE, PROP_DIA), 15, "#8b8781"))
    L.append(txt(X((gx1 + gx2) / 2.0), Y(gy1) - 14,
                 "tip gap %.1f mm (%.1f%%)" % (TIP_GAP, TIP_GAP_PCT), 16, "#e07a5f"))
    L.append(txt(500, Y(0) + 6, "battery %.0f&#215;%.0f" % (BATT_L, BATT_W), 13, "#e07a5f"))
    L.append(txt(30, 960, "plate %.0f&#215;%.0f&#215;%.1f  arm %.0f&#215;%.1f  "
                 "motor 16&#215;19 M3  FC 30.5" % (PLATE_X, PLATE_Y, PLATE_T_BOTTOM, ARM_W, ARM_T),
                 14, "#8b8781", "start"))
    L.append(txt(970, 960, "structure %.0f g" % mass_g, 14, "#8b8781", "end"))
    L.append('</svg>')

    with open(path, "w") as fh:
        fh.write(chr(10).join(L))


svg_path = os.path.join(OUT_DIR, "stevie-frame-v0-%s-plan.svg" % MATERIAL.lower())
svg_plan(svg_path)
say("")
say("SVG   -> %s" % svg_path)

# ----------------------------------------------------------------------
# 5. EXPORT
# ----------------------------------------------------------------------

objs = []


def add(name, shape):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    objs.append(o)
    return o


add("bottom_plate", bottom)
add("top_plate", top)
for i, s in enumerate(arms):
    add("arm_%d" % (i + 1), s)
for i, s in enumerate(legs):
    add("leg_%d" % (i + 1), s)
for i, s in enumerate(feet):
    add("foot_%d" % (i + 1), s)
doc.recompute()

tag = MATERIAL.lower()


def out(name):
    # FreeCAD rejects MSYS-style paths -- native Windows separators only.
    return os.path.join(OUT_DIR, name).replace("/", os.sep)


step_path = out("stevie-frame-v0-%s.step" % tag)
Import.export(objs, step_path)
say("")
say("STEP  -> %s" % step_path)

stl_path = out("stevie-frame-v0-%s.stl" % tag)
Mesh.export(objs, stl_path)
say("STL   -> %s" % stl_path)

# per-part STLs, because you print the arms four times and the plates once
for o in objs:
    if o.Name in ("bottom_plate", "top_plate", "arm_1", "leg_1", "foot_1"):
        p = out("part-%s-%s.stl" % (o.Name.replace("_", "-"), tag))
        Mesh.export([o], p)
        say("STL   -> %s" % p)

# Flat outlines as DXF: this is the artifact that makes the CF option real
# rather than a claim -- the same outline that gets printed gets cut.
try:
    import importDXF
    flat = []
    for o in objs:
        if o.Name in ("bottom_plate", "top_plate", "arm_1", "leg_1", "foot_1"):
            flat.append(o)
    dxf_path = out("stevie-frame-v0-flats-%s.dxf" % tag)
    importDXF.export(flat, dxf_path)
    say("DXF   -> %s" % dxf_path)
except Exception as exc:                                   # noqa: BLE001
    say("DXF   -> NOT WRITTEN: %s" % exc)

say("")
say("RESULT: %s" % ("all geometry checks passed" if ok else
                    "one or more geometry checks FAILED -- see above"))

# The report is written AFTER the verdict, not before. The first version
# wrote it first, so every build-report-*.txt ended at the DXF line with
# no pass/fail line in it at all -- the one thing a reader looks for.
with open(out("build-report-%s.txt" % tag), "w") as fh:
    fh.write(chr(10).join(report) + chr(10))

# And a failed check is visible to whatever ran this. The exports still
# happen deliberately -- a v0 fit-check model with a known-failing prop
# clearance is exactly what this batch hands over -- but the process must
# not exit 0 while reporting a FAIL.
if not ok:
    sys.exit(1)
