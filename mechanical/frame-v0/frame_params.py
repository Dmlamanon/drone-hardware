"""Frame v0.1 parameters -- THE single definition, imported by both users.

Extracted from frame_v0.py so that mechanical/assembly-v0/assembly_v0.py
can IMPORT these rather than copy them. A second copy of a wheelbase or a
mount pitch is a second thing to update, and this project's most repeated
defect is exactly that: two numbers that were meant to be one.

Deliberately FreeCAD-free. It is plain arithmetic, so an ordinary python
can read it -- which is what lets check_fc_pattern.py and the assembly's
own tooling use it without dragging in a CAD kernel.

Everything here is either a measured/sourced input or derived from one.
Provenance for each class of number is in frame_v0.py's own header and in
docs/fable-reeval-2026-08-16.md.
"""
import math
import os

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

# WHICH PARTS COME OFF A SHEET AND WHICH DO NOT.
#
# The project rule is that every structural part is a flat profile of
# constant thickness, so a printed frame and a CF frame differ only in
# thickness. That rule holds for the plates and the arms -- their
# thickness IS a function of MATERIAL. It does NOT hold for the landing
# gear: LEG_W and FOOT_T above are plain constants, identical in both
# builds, and 14 mm CF plate is not a thing you buy.
#
# That is a deliberate design choice, not an oversight. A 2 mm CF blade
# 47.5 mm tall is a bad landing leg -- bending stiffness about the weak
# axis goes as thickness cubed, so it would have 1/343 of the modelled
# value. The legs and feet are therefore PRINTED IN BOTH BUILDS, which
# also suits them: they are the crash consumables.
SHEET_PARTS   = ("bottom_plate", "top_plate", "arm_1")
PRINTED_PARTS = ("leg_1", "foot_1")
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
# LEG_H IS AN INDEPENDENT CONSTANT, DELIBERATELY.
#
# It used to be `BATT_DROP + 12.0`, which made the ground-clearance check
# below unfalsifiable: both sides of `GROUND_CLEAR > BATT_DROP` moved
# together, so the predicate reduced to `12 + FOOT_T > 0` and the margin
# was pinned at 18.0 mm for every conceivable battery. Setting BATT_H to
# 200 mm produced 214 mm legs and still passed all sixteen checks.
#
# Fixing the number in place is what makes the check mean something:
# change the pack and the check now actually re-tests the gear.
LEG_H = 47.5                           # web height, plate underside to foot top
LEG_BATT_MARGIN = 12.0                 # required air under the pack, mm
GROUND_CLEAR = LEG_H + FOOT_T          # plate underside to the ground

