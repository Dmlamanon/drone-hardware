---
type: requirements
status: current
created: 2026-08-17
tags: [stevie, mechanical, requirements]
---

# Mechanical requirements — STEVIE airframe

**Created 2026-08-17 (batch F item 8).** This file is the one that item 6
said was an input and that the item-0 pre-flight found did not exist.
The pre-flight then said the requirements would be "written this batch"
— and they were written as *prose scattered through*
`mechanical/frame-v0/README.md`, not as this document. An independent
review caught the gap. This is the document, gathered into one place.

**Every requirement below is traced to a source.** Nothing here is
invented for the sake of filling a table; where a number has no external
basis it says so.

---

## R1 — Airframe class

| | value | source |
|---|---|---|
| Wheelbase (motor-motor diagonal) | **350 mm** | LOCKED DECISION. Class-defining name; corroborated by the JeeFly LX350, a real 350 mm / 9 in / 4S product |
| Propeller | **9 in = 228.6 mm** | same platform decision |
| Target AUW | **~1.39 kg** | `drone-firmware/docs/inertia-estimate-350class-REAL-2026-08-16.md` |
| Frame mass budget | **469 g** | same doc. **Weak** — it is a real product's 335 g times an INVENTED ×1.4 print multiplier |

## R2 — Interfaces the frame must carry

| | value | source |
|---|---|---|
| FC mount | 30.5 × 30.5 mm, M3 | industry standard |
| Motor mount | **16 × 19 mm cross AND 19 × 19 mm square**, M3 | 2212-class is the cross; the chosen iFlight XING X2814 is the square. Both drilled — see R7 |
| Battery bay | 133 × 45 × 33.5 mm ± 2 mm | Tattu G-Tech 5200 mAh 4S 35C published dimensions |
| Battery mass | 436.5 g | same listing. **See the flag in R8** |

## R3 — Material independence *(the shape-driving requirement)*

From `cfd-structural-recommendation-2026-08-17.md`:

> The frame must build as **FDM-printed (PETG-class) OR as carbon plate.
> Resin is never structural.**

**Consequence, and it is a geometry constraint rather than a material
note:** every structural part must be a **flat profile of constant
thickness**. No draft, no ribs, no bosses, nothing that only a printer
can produce. The same outline is either printed or cut from sheet, off
the same DXF.

**Design to the weaker material and check the stronger one fits.**

| class | minimum section | status |
|---|---|---|
| PETG / ABS / ASA | 3 mm wall on load paths, **4 mm at arm roots**, ≥4 perimeters, ≥40 % gyroid | default structural print |
| PA-CF / PET-CF | 2.5 mm permitted | preferred if available |
| Carbon plate | 2 mm arms, 1.5 mm plates | the cut option |
| PLA | — | **fit-check only, not a flight material** |
| Resin | — | **BANNED on every load path** |

## R4 — Geometry rules (all materials)

1. Fillet every internal corner, **R2 minimum, R3 at arm roots**.
2. Print arms so layer lines are not perpendicular to the bending load —
   **print on edge**.
3. No unsupported bosses or thin pillars on load paths.
4. **Every fastener through a printed part gets a metal insert or a
   washer.** A bolt head bearing on plastic pulls through.
5. **The arm must be replaceable.** It is the part that breaks.
6. **The same bolt pattern for both material options**, so a printed arm
   and a carbon arm are interchangeable on one body.

## R5 — Propeller clearance

Tip-to-tip gap **≥10 % of propeller diameter**.

**CURRENTLY FAILED, and it cannot be met by frame geometry.** At 350 mm
with 9 in props the gap is 18.89 mm = **8.26 %**. For four motors on a
circle the minimum adjacent spacing is maximised exactly by the symmetric
X, so no arm layout improves it. Meeting it costs an **8.85 in prop** or
a **355.6 mm wheelbase**. Both change a locked platform decision and both
are David's call. See `mechanical/frame-v0/README.md`.

Also required and **not yet done**: check clearance with the props
**fitted and under load** — they cone upward, so the static number is the
optimistic one.

## R6 — Acceptance before flight

Not met by v0 and not claimed to be:

- [ ] Prop clearance verified with props fitted (R5)
- [ ] Every printed load-path part in PETG-class or better, never resin
- [ ] Arm root stress-checked against a real load case (no FEA yet)
- [ ] Frame mass measured, not estimated (`docs/thrust-test-procedure.md` §4.2)
- [ ] Props balanced

## R7 — Open interface mismatches

Both found 2026-08-17 by writing the numbers down, both still open:

1. **The bench board does not bolt to the frame.** The frame carries the
   30.5 mm standard; `bench_board` is 80 × 60 mm with M3 holes at
   (4.5, 19), (75.5, 16), (4.5, 55.5), (75.5, 41) — neither 30.5 nor
   symmetric. One of the two must move.
2. **Motor pattern** — resolved by drilling both patterns, at the cost of
   a 36 mm pad. Recorded here because the *requirement* was stated as
   "2212-class" while the *selected part* is not one.

## R8 — A flag on the battery figure

5.2 Ah × 14.8 V = 77.0 Wh at 436.5 g is **176 Wh/kg**, above the
practical ceiling for a 35C LiPo (typically 130–160 Wh/kg). Mass and
volume are at least mutually consistent (200.5 cm³ → 2.18 g/cm³, normal
for a pack), and 436.5 g is a pre-existing project number classed
RETAIL-LISTING — so this is a flag, not a proven error.

It matters because `PLATE_X` is sized to the 133 mm length. **If the real
pack is a 148–155 mm variant it does not fit the 137 mm bay** and the
plate must grow. Weigh and measure the actual pack on thrust-stand day
(§4.2) before the plate is locked.

Note also that "the listed mass matches the mass the AUW budget assumes"
is **circular** — both trace to the same listing.

---

## Related

- [[cfd-structural-recommendation-2026-08-17]] — R3, R4, R5 source
- [[stm32f405-pin-assignment]] — the board this frame carries
- `mechanical/frame-v0/README.md` — the v0 that implements this
- `../drone-firmware/docs/thrust-test-procedure.md` — where the measurements come from
