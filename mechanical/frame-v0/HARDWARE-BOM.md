---
type: bom
status: current
created: 2026-08-17
tags: [stevie, mechanical, bom]
---

# Frame v0.1 — fastener plan and hardware BOM

Everything that is not printed or cut. One purchasable list.

**Prices are indicative UK retail (2026-08) for the small quantities a
one-off build needs.** They are for budgeting, not quotes, and buying a
100-piece assortment is usually cheaper than the exact counts below.

---

## The joint-by-joint plan

The frame is a bolted sandwich, so every joint is one of five kinds.

| # | joint | fastener | length | why that length |
|---|---|---|---|---|
| 1 | **Arm into the plate sandwich** (2 per arm, 8 total) | M3 socket cap | **PETG: 16 mm · CF: 12 mm** | through top plate + arm + bottom plate. PETG 3+4+3 = 10 mm of stack plus a nut; CF 1.5+2+2 = 5.5 mm |
| 2 | **Motor to arm** (4 per motor, 16 total) | M3 socket cap | **8 mm** | into the motor's own threaded bosses. **Measure before buying** — too long bottoms out on the windings and kills the motor |
| 3 | **FC board to top plate** (4) | M3 × 25 nylon standoff + M3 × 6 | — | standoff sets the board height; nylon so a short cannot find its way to the frame |
| 4 | **Landing-leg bracket** (2 per leg into the arm, 2 per leg into the web, 16 total) | M3 socket cap | **10 mm** | through the angle bracket plus one part |
| 5 | **Foot to leg** (1 per leg, 4 total) | M3 socket cap | **20 mm** | through the 14 mm web plus the 6 mm foot |

### Nuts versus heat-set inserts — this differs by material

**This is the one place the two builds genuinely diverge**, and getting it
wrong is how a printed frame fails at the fastener rather than in the part.

| | PETG / PA-CF print | CF plate |
|---|---|---|
| Arm sandwich (1) | **M3 nyloc nut** + washer both sides | M3 nyloc + washer both sides |
| Motor mount (2) | into the motor's own thread — no insert | same |
| Standoffs (3) | nylon standoff threads directly | same |
| Leg bracket (4) | **M3 heat-set insert** in the printed web | **M3 nyloc nut** (do not try to melt an insert into carbon) |
| Foot (5) | **M3 heat-set insert** in the leg web | M3 nyloc nut |

**Rule 4 from the structural doc is not optional: every fastener through a
printed part gets a metal insert or a washer.** A bolt head bearing
directly on PETG pulls through — slowly under vibration, then all at once.

Heat-set inserts (M3 × 5 mm, ~4.6 mm OD) go in with a soldering iron at
~230 °C. If you would rather not, a nyloc plus a **penny washer** on the
plastic side is an acceptable substitute everywhere except the leg
bracket, where the insert is doing real work in a crash.

---

## The parts that are not material-independent

There are **three**, and an earlier version of this file claimed one.
Naming them properly matters, because the flats DXF is a cutting file and
anything wrongly described as a sheet part gets cut from sheet.

**1–2. The landing legs and their feet.** The leg web is **14 mm** and the
foot **6 mm** — in *both* builds. Bending stiffness about a leg's weak
axis goes as thickness cubed, so a 2 mm CF blade 47.5 mm tall would have
**1/343** of the modelled stiffness, and 14 mm CF plate is not something
you buy. So the gear is **printed in both builds**, and `frame_v0.py`
excludes it from `stevie-frame-v0-flats-*.dxf`. That suits it: with the
bracket, the gear is the crash consumable.

The M3 × 20 in joint 5 below is sized for exactly this — 14 mm web plus
6 mm foot. If you ever see a 2 mm leg, the bolt is the tell.

**3. The landing-leg angle bracket.** A flat vertical web cannot bolt to a
flat horizontal arm without something at 90° between them, and modelling a
printed L that only works in one material would be pretending otherwise.

So it is bought, not made: **an off-the-shelf M3 aluminium angle bracket,
20 × 20 × 20 mm, 2 mm wall, four M3 holes.** Same part for both builds.

The rule still means something — the *load-bearing sheet* (plates, arms)
is genuinely material-independent, and the three exceptions are named
here and enforced by a check in `frame_v0.py` rather than left as a
comment.

---

## Buy list

| item | qty | note | ~unit | ~total |
|---|---|---|---|---|
| M3 × 8 mm socket cap, stainless A2 | 16 | motor mounts | £0.06 | £0.96 |
| M3 × 10 mm socket cap, A2 | 16 | leg brackets | £0.06 | £0.96 |
| M3 × 16 mm socket cap, A2 (**PETG**) | 8 | arm sandwich | £0.08 | £0.64 |
| M3 × 12 mm socket cap, A2 (**CF instead**) | 8 | arm sandwich | £0.07 | £0.56 |
| M3 × 20 mm socket cap, A2 | 4 | feet | £0.09 | £0.36 |
| M3 × 6 mm socket cap, A2 | 4 | FC to standoff | £0.05 | £0.20 |
| M3 nyloc nut, A2 | 30 | +spares | £0.05 | £1.50 |
| M3 washer, A2 | 40 | **both sides of every printed joint** | £0.02 | £0.80 |
| M3 penny washer (9 mm OD) | 16 | printed-side bearing faces | £0.04 | £0.64 |
| M3 × 5 mm heat-set insert, brass | 12 | **PETG build only** | £0.09 | £1.08 |
| M3 × 25 mm nylon standoff, F-F | 4 | FC mount | £0.22 | £0.88 |
| M3 aluminium angle bracket 20×20×20 | 4 | landing-leg joint | £0.65 | £2.60 |
| Threadlocker, medium (blue) | 1 | **motor bolts, mandatory** | £4.50 | £4.50 |
| 20 mm hook-and-loop battery strap | 2 | through the plate slots | £1.20 | £2.40 |
| Silicone anti-vibration grommet, M3 | 4 | optional, FC isolation | £0.30 | £1.20 |

**≈ £18.50 for the PETG build** including the threadlocker and strap, or
**≈ £17 for CF** (no inserts, shorter arm bolts).

Round every count up to the nearest packet. An M3 assortment box is
typically £12–15 and covers all of the above except the inserts, the
brackets and the standoffs.

### Two things worth spending on

- **Threadlocker on the motor bolts is not optional.** A motor bolt that
  backs out at 8000 rpm takes the prop with it. Medium strength (blue),
  not red — you will want to remove them again.
- **Buy the motor bolts to the motor's spec, not to this list.** Depth
  varies between makers and a bolt that bottoms out inside the bell will
  destroy the windings. Measure first.

---

## Related

- [[mechanical-requirements]] — R4, the geometry rules this implements
- `README.md` — the frame itself, and what v0.1 still is not
- [[cfd-structural-recommendation-2026-08-17]] — rule 4 on fasteners through printed parts
