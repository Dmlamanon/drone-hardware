---
type: recommendation
status: current
created: 2026-08-17
tags: [stevie, structural, cfd, mechanical, freecad]
---

# CFD and structural analysis — what to do, and what not to bother with

**Recommendation: do not run CFD on the quadrotor. Do run it on the
tiltrotor transition, if that is ever built.** The reasoning, and what
replaces it in the meantime, is below.

This document is also the **input spec for the FreeCAD work**: §4's
material rules are the constraints the printed parts must be designed
against.

---

## 1. Why CFD is low-value for the quadrotor

**The flow is rotor-dominated and there are no lifting surfaces.**

A quadrotor has no wing, no fuselage shaped to produce lift, and no
control surfaces. Essentially all of the aerodynamics is happening inside
four rotor discs, and rotor flow is the single hardest case for
general-purpose CFD:

- It is **unsteady and periodic** at blade-pass frequency, so a steady
  solve is meaningless and a transient one is expensive.
- It requires **moving reference frames or overset meshes** to represent
  the rotating blades at all.
- The results are **acutely sensitive to the blade geometry**, which for
  an off-the-shelf Gemfan prop is not published — you would be meshing a
  scan or a guess.
- Rotor–rotor and rotor–airframe interaction on a quad is a **known-hard**
  validation problem even in the research literature.

So a CFD campaign would consume weeks, and the deliverable would be a
thrust and torque curve for a propeller **whose manufacturer already
publishes measured thrust data**, obtained more accurately with a $60
thrust stand.

**The one thing CFD would tell you that the datasheet does not** — how
the airframe disturbs the rotor inflow — is a second-order effect on an
open-frame quad where the arms are thin tubes below the discs.

## 2. What replaces it

In rough order of value per hour spent:

### a. Vibration management — the highest-value mechanical work

This project already has a concrete reason to care:
`make probe-railing` shows the rate loop reacting violently to gyro
noise. **Mechanical vibration is the other half of that problem**, and no
amount of filtering fixes a badly-mounted IMU.

- **Balance every prop** before first flight. A $10 balancer removes more
  gyro noise than any filter.
- **Soft-mount the flight controller** — silicone grommets or a gel pad.
  This is standard practice and it is not optional on a 9" airframe.
- **Measure it**: log `gx/gy/gz` from the telemetry stream at hover and
  look at the spread. That number is the acceptance criterion, and the
  ground station already records it.

### b. Physical arm testing — a real load test beats a simulated one

For a printed arm the failure mode that matters is a **crash landing**,
not steady flight. Simulating a crash requires knowing the impact
velocity, attitude and surface, none of which you know.

**Test instead:**
1. Clamp the arm at the body joint.
2. Hang weight at the motor mount and record deflection at 1×, 2× and 4×
   the hover thrust per motor (hover thrust ≈ AUW/4 ≈ 3.2 N; so ≈0.33,
   0.65 and 1.3 kg).
3. Look for **permanent set after unloading** — that, not fracture, is
   where a printed part has actually yielded.
4. Repeat on a part printed in the *worst* orientation you will accept.

That is an afternoon and it produces a number you can trust.

### c. Prop-clearance geometry — pure geometry, no simulation needed

- Prop tips must not overlap, and the **tip-to-tip gap should be ≥10 %**
  of prop diameter to keep interaction losses and noise down. At 350 mm
  wheelbase with 9" props the arithmetic is tight: diagonal spacing is
  350 mm, prop diameter 229 mm, so adjacent tip separation is
  350/√2 − 229 ≈ **18 mm**. That is about 8 % — **already marginal**, and
  it is a geometry fact, not an opinion.
- Keep the FC and any antenna **out of the disc plane**.
- Check clearance with the props *flexing* — they cone upward under load.

### d. Thermal — measure, don't model

The one component with a real thermal question is U2, the 3 A buck. It
has a thermal pad and the board has stitching. **Point an IR thermometer
at it under load** rather than meshing it.

## 3. Where CFD becomes mandatory

**The tiltrotor transition, and only that.** Once there are nacelles that
rotate and — per the tiltrotor analysis — ideally a wing:

- The **conversion corridor** is fundamentally an aerodynamic question:
  at what airspeed and nacelle angle does the wing carry enough load for
  the rotors to be unloaded? That cannot be answered by a thrust stand.
- **Rotor-wake-on-wing interaction** during transition is the classic
  tiltrotor problem and it is genuinely unsteady and three-dimensional.
- **Download** — the wing sitting in the rotor downwash in hover — is a
  direct hover-efficiency penalty and is geometry-dependent.
- Any **control surface** needs its effectiveness known as a function of
  airspeed to be scheduled correctly.

Even then, prefer **wind-tunnel data or published tiltrotor literature
first**, and use CFD to interpolate between measured points rather than to
predict from nothing.

---

## 4. Material-independence design rules — the FreeCAD input spec

**Lead ruling being executed: the frame must build as an FDM print
(PETG-class) OR as carbon plate. Resin is never structural.**

Designing for both at once is a real constraint, and it mostly means
**designing to the weaker material and checking the stronger one fits**.

### Material classes and minimum sections

| Class | Examples | Use | Minimum wall / section |
|---|---|---|---|
| **PETG / ABS / ASA** (tough, ductile) | PETG | **Default structural print.** Fails by bending and tearing, not shattering. | **3 mm minimum wall** on load paths; **4 mm** on arm roots. ≥4 perimeters, ≥40 % infill (gyroid) |
| **PA-CF / PET-CF** (stiff, engineering) | Nylon-carbon | **Preferred if available.** Much stiffer and more fatigue-tolerant; needs a dry filament and a hardened nozzle. | **2.5 mm** wall permitted on load paths; same perimeter count |
| **PLA** | — | **Prototype fit-checks only.** Creeps under sustained load and softens in a hot car. **Not a flight material.** | n/a |
| **Resin (SLA/DLP)** | — | **BANNED on any load path.** | n/a |
| **Carbon plate** | 2–3 mm CF sheet | Arms and main plates, if the CF option is taken | 2 mm arms minimum; 1.5 mm plates |

### Why resin is banned, specifically

Standard photopolymer resin is **brittle** — it fails by shattering with
almost no plastic deformation and very low impact energy absorption, and
it **continues to cure and embrittle with UV exposure** over time. A part
that survived assembly can fail months later from sunlight alone. It is
excellent for non-structural detail (camera mounts, light pipes,
cosmetic covers, jigs) and unacceptable for anything carrying flight or
landing loads.

**Banned specifically:** arms, arm roots, motor mounts, the main plate,
landing gear, battery retention, and any tilt mechanism.

### Geometry rules that apply to every material

1. **Fillet every internal corner**, minimum **R2**, and **R3 at arm
   roots.** A sharp internal corner is a stress concentrator and is by
   far the most common failure origin in printed drone parts.
2. **Print arms so layer lines are not perpendicular to the bending
   load** — for FDM, layer adhesion is the weak axis, and an arm printed
   flat on the bed bends across its layers. Print arms **on edge**, or
   design them so the load is carried in-plane.
3. **No unsupported bosses or thin pillars** on load paths.
4. **Every fastener through a printed part gets a metal insert or a
   washer** — a bolt head bearing directly on plastic will pull through.
5. **Design the arm as replaceable.** It is the part that breaks; make
   swapping one a five-minute job, not a rebuild.
6. **Keep the same bolt pattern for both material options** so a printed
   arm and a CF arm are interchangeable on the same body. This is the
   practical meaning of material-independence and it should be the first
   constraint fixed in CAD.

### Acceptance criteria for the printed frame

Before it flies:

- Arm passes the load test in §2b at **2× hover thrust with no permanent
  set**.
- Motor mount face is **flat and perpendicular** — a canted motor is a
  permanent trim offset the controller has to fight.
- Total frame mass within **±15 %** of the 469 g estimate used in the
  inertia work, or the inertia estimate gets redone.
- Prop clearance verified **with props fitted**, per §2c, given the
  ≈8 % tip gap is already marginal.
