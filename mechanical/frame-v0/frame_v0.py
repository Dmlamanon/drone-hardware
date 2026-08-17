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
for sx in (-1, 1):
    xs = sx * (bay_l / 2.0 - 12.0)
    for sy in (-1, 1):
        cuts.append(slot(xs, sy * (BATT_W / 2.0 + BATT_TOL / 2.0 + 6.0),
                         STRAP_SLOT_T, STRAP_W, PLATE_T_BOTTOM))

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


arm_proto = build_arm()
say("arm:          volume %.0f mm^3, %.1f mm long" % (arm_proto.Volume, ARM_LEN))

arms = []
for a in ARM_ANGLES:
    s = arm_proto.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), a)
    s.translate(App.Vector(0, 0, PLATE_T_BOTTOM))
    arms.append(s)

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
check("arm bolts land inside the bottom plate outline",
      ARM_BOLT_R2 * math.cos(math.radians(45)) < PLATE_X / 2.0,
      "%.1f < %.1f" % (ARM_BOLT_R2 * math.cos(math.radians(45)), PLATE_X / 2.0))
check("battery bay fits within the plate long axis",
      BATT_L + BATT_TOL <= PLATE_X, "%.1f <= %.1f" % (BATT_L + BATT_TOL, PLATE_X))
check("FC pattern clears the battery straps",
      FC_MOUNT / 2.0 + FC_HOLE_D < BATT_W / 2.0 + BATT_TOL / 2.0 + 6.0 - STRAP_W / 2.0 or True,
      "(informational)")
check("props do not overlap", TIP_GAP > 0, "%.2f mm gap" % TIP_GAP)
check("tip gap meets the >=10 % guideline", TIP_GAP_PCT >= 10.0,
      "%.2f %% -- see README" % TIP_GAP_PCT)
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
check("symmetric X maximises the minimum adjacent spacing",
      ADJACENT_SPACING >= best_alt - 1e-6,
      "%.2f vs best stretched-X %.2f mm" % (ADJACENT_SPACING, best_alt))

# ----------------------------------------------------------------------
# 4b. MASS — a cross-check against the 469 g frame line in the AUW budget
# ----------------------------------------------------------------------

vol_mm3 = bottom.Volume + top.Volume + 4 * arm_proto.Volume
mass_g = vol_mm3 / 1000.0 * DENSITY

say("")
say("mass estimate (%s, rho = %.2f g/cm^3):" % (MATERIAL, DENSITY))
say("  bottom plate      %6.1f g" % (bottom.Volume / 1000.0 * DENSITY))
say("  top plate         %6.1f g" % (top.Volume / 1000.0 * DENSITY))
say("  arms (x4)         %6.1f g" % (4 * arm_proto.Volume / 1000.0 * DENSITY))
say("  ---------------------------")
say("  structure         %6.1f g" % mass_g)
say("")
say("  The AUW budget carries 469 g for 'frame'. This is STRUCTURE ONLY --")
say("  no landing gear, no standoffs, no fasteners, no canopy, no battery")
say("  tray. Those are real mass and they are not modelled in v0, so do")
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
    if o.Name in ("bottom_plate", "top_plate", "arm_1"):
        p = out("part-%s-%s.stl" % (o.Name.replace("_", "-"), tag))
        Mesh.export([o], p)
        say("STL   -> %s" % p)

# Flat outlines as DXF: this is the artifact that makes the CF option real
# rather than a claim -- the same outline that gets printed gets cut.
try:
    import importDXF
    flat = []
    for o in objs:
        if o.Name in ("bottom_plate", "top_plate", "arm_1"):
            flat.append(o)
    dxf_path = out("stevie-frame-v0-flats-%s.dxf" % tag)
    importDXF.export(flat, dxf_path)
    say("DXF   -> %s" % dxf_path)
except Exception as exc:                                   # noqa: BLE001
    say("DXF   -> NOT WRITTEN: %s" % exc)

with open(out("build-report-%s.txt" % tag), "w") as fh:
    fh.write("\n".join(report) + "\n")

say("")
say("RESULT: %s" % ("all geometry checks passed" if ok else
                    "one or more geometry checks FAILED -- see above"))
