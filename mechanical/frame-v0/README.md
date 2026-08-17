# STEVIE frame v0.1 — **FIT-CHECK ONLY, NOT A FLIGHT FRAME**

**2026-08-17, Batch F item 6.** First mechanical geometry in this project.

> ## This frame has not been stress-analysed and must not be flown.
>
> It exists to check that things fit: that the board mounts, that the
> battery goes where it is supposed to, that the arms reach 175 mm
> without fouling anything, and that the motor pattern is right. Every
> section thickness here is the **minimum** the material rules allow, not
> a number that came out of an analysis. No FEA has been run. The arm
> root — the part that actually breaks on real quads — has not been
> checked against any load case at all.
>
> Print it, bolt it together, check the fit, and then design v1 with the
> loads in hand.

---

## Build it

```bash
# PETG variant (default)
"C:\Users\dmlam\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe" frame_v0.py

# carbon-plate variant, same script, same outlines
FRAME_MATERIAL=CF "C:\...\freecadcmd.exe" frame_v0.py
```

There is no FreeCAD MCP on this machine (checked — see
`docs/tooling-preflight-2026-08-17b.md`), so this is the headless
`freecadcmd.exe` route. FreeCAD **rejects MSYS-style paths**; every
export path in the script is built with `os.path.join` on a Windows base
for that reason.

Every dimension is a named constant in one `PARAMETERS` block. Nothing
downstream hard-codes a number.

---

## What it is

A **sandwich-construction X quad**: four flat arms bolted between a
bottom and a top plate.

| | value | source |
|---|---|---|
| Wheelbase (motor-motor diagonal) | **350 mm** | locked class name, `inertia-estimate-350class-REAL-2026-08-16` |
| Props | 9 in = **228.6 mm** | same |
| FC mount | **30.5 × 30.5 mm**, M3 | the universal pattern |
| Motor mount | **16 × 19 cross AND 19 × 19 square**, M3 | see below — 2212-class is the cross ([components101](https://components101.com/motors/2212-brushless-motor), [Altitude Hobbies Suppo 2212](https://www.altitudehobbies.com/products/suppo-2212-13-1000kv-brushless-motor-park-400-equiv)); the square is the chosen X2814 ([iFlight XING X2814](https://pyrodrone.com/products/iflight-xing-x2814-fpv-nextgen-1100kv)) |
| Battery bay | **133 × 45 × 33.5 mm** + 2 mm tol | Tattu G-Tech 5200 mAh 4S 35C — [GensTattu](https://genstattu.com/tattu-5200mah-14-8v-35c-4s1p-lipo-battery-pack-with-xt60-plug.html), 436.5 g, matches the mass the AUW budget already assumes |
| Centre plate | 140 × 110 mm octagon | sized so the 133 mm pack fits along the long axis |
| Arm | 16 × 165 mm | 16 mm matches the JeeFly LX350 class comparable |

### Material independence is the *shape* constraint, not a note

`cfd-structural-recommendation-2026-08-17.md` requires the frame to build
as FDM-printed PETG-class **or** as carbon plate, resin never structural.
That requirement is what makes the plates and arms here **flat profiles
of constant thickness** — no draft, no ribs, no bosses, nothing that only
a printer can produce. The same outline is either printed or cut, off the
same DXF, which is exported.

**The landing gear is the exception, and it is a deliberate one.** The
leg web is 14 mm and the foot is 6 mm *in both builds* — their thickness
is a constant, not a function of material. Bending stiffness about a
leg's weak axis goes as the cube of thickness, so a 2 mm CF blade 47.5 mm
tall would have **1/343** of the modelled value, and 14 mm CF plate is
not something you buy. So **legs and feet are printed in both builds**,
and they are excluded from the flats DXF. That suits them: with the
bracket they are the crash consumables.

For the parts that do come off a sheet, thickness is the only difference
between the two builds:

| | PETG | CF plate | rule |
|---|---|---|---|
| Bottom plate | 3.0 mm | 2.0 mm | 3 mm min wall on load paths / 1.5 mm plate min |
| Top plate | 3.0 mm | 1.5 mm | same |
| Arm | 4.0 mm | 2.0 mm | 4 mm at arm roots / 2 mm CF arms |
| Leg web | **14.0 mm** | **14.0 mm** | printed both builds — not a sheet part |
| Foot | **6.0 mm** | **6.0 mm** | printed both builds — not a sheet part |
| **Structure mass** | **201.2 g** | **156.3 g** | incl. landing gear; sheet at 1.27 / 1.55 g·cm⁻³, printed gear at 1.27 in both |

Sections are sized to the **weaker** material and the stronger one is
checked to fit the same envelope, which is what that document asks for.

**Do not read 201 g as beating the 469 g frame line in the AUW budget.**
Landing gear is included from v0.1, but standoffs, fasteners, canopy and
battery tray are not. The fasteners alone are ~60 pieces of M3 stainless —
see `HARDWARE-BOM.md`, which is a real buy list, not an estimate.

### The motor pattern carries TWO hole sets, and why

Item 6 specified a 2212-class pattern, which is a **16 × 19 mm cross**.
That is what went in first. Then, while writing the thrust-test procedure
against the parts list, the motor this project has actually chosen turned
out to be the **iFlight XING X2814**, whose pattern is a **19 × 19 mm
square**. A square does not fit a cross. The frame as first built would
not have accepted the project's own motor.

Both are now drilled — eight M3 holes on one pad, which is what
commercial frames in this class do and costs nothing but pad diameter.

The pad diameter was 32 mm and the geometry check **rejected it**: the
square's corner holes sit at r = 13.44 mm, leaving under 1 mm of material
outside the hole edge, which is a bolt pull-through waiting to happen in
PETG. 36 mm gives about 3 mm. The check is in the script, so a future
change to either pattern re-tests this automatically.

### Why the arms bolt on rather than being part of the body

Rule 5 of the geometry rules: *design the arm as replaceable — it is the
part that breaks.* Rule 6: *keep the same bolt pattern for both material
options so a printed arm and a CF arm are interchangeable.* The sandwich
satisfies both. Two M3 per arm, at r = 38 and r = 58, and that bolt list
has exactly **one definition in the script** used by the arms and by both
plates — if they could drift apart the frame would not assemble.

---

## The prop-clearance finding — the geometry check that FAILS

```
adjacent motor spacing = 350 / √2   = 247.49 mm
prop diameter (9 in)                = 228.60 mm
TIP GAP                             =  18.89 mm  =  8.26 %
```

The guideline is **≥10 %** of prop diameter. This is **8.26 %**, which
reproduces the 18.9 mm / 8.3 % figure already in this project exactly.

> [!success] **ACCEPTED by the lead, 2026-08-17. Bottleneck #4 is closed.**
> No prop change, no wheelbase change.
>
> **The precedent, checked rather than repeated:** the DJI Phantom 3 ships
> **9.4 in** props on this same **350 mm** class. Its adjacent motor
> spacing is therefore the same 247.49 mm, and 9.4 in is 238.76 mm, so its
> tip gap is **8.73 mm = 3.7 %** — *less than half* this frame's 8.26 %,
> on an airframe that was flight-proven and built at scale.
>
> The ≥10 % figure is a **noise-and-efficiency guideline, not a limit**.
> Below it you pay in interaction losses and sound, not in airworthiness.
>
> The script no longer reports this as a FAIL. It still prints the number
> in full — accepting a figure is not the same as hiding it — but a
> standing failure that will never be fixed only teaches people to skim
> the report. **All 16 geometry checks now pass.**

The analysis below stands and is why the ruling was needed — the geometry
genuinely cannot be improved, so the only options were to change the prop,
change the wheelbase, or accept it. **It was accepted.**

The earlier brief asked to *"do better than the current geometry if arm
length allows within the wheelbase."* **It does not allow it, and that is
a proof rather than an opinion:**

> Four motors sit on a circle of radius wheelbase/2. The tip gap is set
> by the *smallest* adjacent spacing. For a rectangular layout with
> half-width `a` and half-length `b` constrained by
> `2·√(a² + b²) = wheelbase`, the two adjacent spacings are `2a` and
> `2b`, and `min(2a, 2b)` is maximised exactly when `a = b` — the
> symmetric X this frame already is. A stretched or "dead-cat" layout
> makes one pair **closer**, never further apart. Longer arms do not help
> either: lengthening them *is* increasing the wheelbase, which is the
> fixed input.

The script sweeps the whole stretched-X family at constant wheelbase and
confirms 247.49 mm is the maximum achievable. The two options that *would*
have bought the clearance are recorded for the file — **neither was
taken**:

| option | result | cost |
|---|---|---|
| Keep 350 mm, drop to **8.85 in props** (≤ 225.0 mm) | ≥10 % | less thrust and less disc area |
| Keep 9 in props, grow wheelbase to **≥ 355.6 mm** | ≥10 % | +1.6 % on a locked class name; re-opens the inertia/gain derivation |

The remaining note from the source document still stands and is not
addressed by any of this: **check clearance with the props fitted and
under load** — they cone upward, so the static number is the optimistic
one.

---

## Outputs

| file | what |
|---|---|
| `stevie-frame-v0-petg.step` / `-cf.step` | full assembly, both variants |
| `stevie-frame-v0-petg.stl` / `-cf.stl` | assembly mesh |
| `part-bottom-plate-*.stl`, `part-top-plate-*.stl`, `part-arm-1-*.stl` | per-part, because you print the arm four times |
| `stevie-frame-v0-flats-*.dxf` | **flat outlines for CF cutting** — this is what makes the carbon option real rather than claimed. **Sheet parts only:** bottom plate, top plate, arm. The legs and feet are printed in both builds and are deliberately *not* in this file |
| `part-leg-1-*.stl`, `part-foot-1-*.stl` | the landing gear — **print these even for the CF build** |
| `stevie-frame-v0-*-plan.svg` | scale plan view, gallery render |
| `build-report-*.txt` | the run's own numbers and check results |

The render is a **plan view, not a 3D render**, for two reasons: headless
FreeCAD has no viewport to screenshot, and the one thing worth looking at
on this frame is the prop-disc overlap — which a grey isometric render of
the STL would actually hide.

---

## The battery-strap slots were wrong, and the check that now catches it

The first version put all four strap slots at x = ±56.5. Their outer ends
reach x + y = 98.75, and the octagon's chamfer is the line x + y = 95 —
so **all four "slots" were open notches** in the exported STL, STEP and
DXF, with a ~4.4 mm gap wider than the 3.5 mm slot itself. A strap would
have slid straight out. An independent review found it by reading the
exported mesh and confirmed it in the volume figure.

The slots are now at x = ±46 and, more importantly, **the script checks
it**. Every hole and slot corner is tested against the actual outline —
chamfers included — with 2 mm of material to spare. That check would have
caught this on the first run. It also replaced a weaker arm-bolt check
that compared only against the bounding rectangle, and so could not have
caught it either: |x| < 70 and |y| < 55 are both true at (58.25, 40.5),
and that point is outside the plate.

Verified in the rebuilt mesh: the slot's rounded tip arc is present, and
no vertex lies on the chamfer line anywhere in the slot region.

Three related fixes from the same review:

- The strap slots' inner edge cleared the FC mount holes by **0.05 mm**,
  which is a coincidence rather than clearance. Now 2.05 mm — and the
  check prints the margin instead of a bare OK.
- One check ended in `... or True`, inside a block headed *"geometry that
  must hold, checked not assumed"*, so it passed unconditionally. Removed.
- The build report was written *before* the verdict line, so every
  `build-report-*.txt` ended at the DXF path with no pass/fail in it at
  all. It now contains the verdict, and the script exits non-zero when a
  check fails.

---

## Landing gear — new in v0.1

Four legs, one per arm, at **r = 95 mm** — a **190 mm stance** across the
diagonal, the same order as a Phantom 3's.

**Ground clearance is set by the battery, not the props.** The pack hangs
under the bottom plate, so the legs have to clear 33.5 mm of pack plus its
2 mm tolerance. They give **53.5 mm**, which is **18.0 mm of daylight**
for the strap, the connector and a tuft of grass. The script checks that
relationship rather than the absolute number, so changing the pack
re-tests it automatically.

The web is a **flat profile of constant thickness** like everything else
structural here — printed on edge so the layer lines run along the load
(rule 2), or cut from the same CF sheet. It is tapered, because the
bending moment on a landing leg is largest at the top, and splayed 6 mm
outboard so a side landing becomes a slide rather than a tipping moment.

### The feet are deliberately a separate part

A foot that is part of the leg means a scuffed landing costs you a leg. A
foot that bolts on costs you **3 g of filament**. It carries one bolt and
no bending load: it is a **wear pad, not a structural member**, and it is
sized to fail before the leg does. Print a dozen.

### The one part that is NOT material-independent, said plainly

**The leg-to-arm bracket.** A flat vertical web cannot bolt to a flat
horizontal arm without something at 90° between them. Modelling a printed
L that only works in one material would be pretending the rule held when
it did not, so the bracket is **bought**: an off-the-shelf M3 aluminium
angle, 20 × 20 × 20 mm, same part for both builds. See `HARDWARE-BOM.md`.

That keeps the rule meaningful. The *frame* is material-independent; the
one joint that cannot be is an off-the-shelf metal part rather than a
quiet exception buried in a model.

---

## Fasteners

`HARDWARE-BOM.md` — the joint-by-joint plan, M3 lengths per joint, the
nuts-versus-heat-set-inserts split (which is the one place the two builds
genuinely diverge), and a purchasable list at ≈£18.50 for the PETG build.

Two things from it worth repeating here: **threadlocker on the motor bolts
is not optional**, and **buy the motor bolts to the motor's own spec** —
one that bottoms out inside the bell destroys the windings.

---

## Known gaps in v0.1, listed rather than discovered later

1. **No FEA.** Sections are material minimums, not analysis results.
2. **No landing gear, standoffs, canopy or battery tray.** The mass
   estimate is structure only.
3. **The board STEP exists but is not imported into the frame model.**
   `../bench_board.step` was generated this batch with
   `kicad-cli pcb export step` — real output from the real board, 4.6 MB,
   one 3D model missing (U4's QFN-24 shape is not in the installed
   library, so the MPU-6000 body is absent; the footprint and its pads
   are present).

   The frame carries the standard **30.5 mm** FC pattern, which is the
   interface that matters for any FC. But **this bench board does not use
   a 30.5 mm pattern** — it is 80 × 60 mm with four M3 holes at
   (4.5, 19), (75.5, 16), (4.5, 55.5), (75.5, 41), which is neither
   30.5 mm nor symmetric. So the board as it stands **does not bolt to
   this frame**. Either the board's mounting holes move to 30.5 mm on a
   future revision, or the frame gets a second hole pattern, or an
   adapter plate. This is a real interface mismatch, found by writing the
   number down rather than by assuming the standard applied.
4. **Fillets are not applied as fillet features.** `FILLET_ROOT` / 
   `FILLET_GEN` are defined and the arm root is round-ended by
   construction, but rule 1 ("fillet every internal corner, R2 minimum,
   R3 at arm roots") is only partly honoured geometrically. The internal
   corners that matter are where the arm meets the plate in the sandwich
   — which in this construction is a bolted joint, not a moulded corner,
   so the rule applies differently. Worth a deliberate pass in v1.
5. **The battery figure deserves a second look before `PLATE_X` is
   locked.** 5.2 Ah × 14.8 V = 77.0 Wh at 436.5 g is **176 Wh/kg**, above
   the practical ceiling for a 35C LiPo (typically 130–160). Mass and
   volume are mutually consistent (2.18 g/cm³, normal for a pack) and
   436.5 g is a pre-existing project number classed RETAIL-LISTING, so
   this is a flag rather than a proven error. It matters because the plate
   is sized to the 133 mm length: **if the real pack is a 148–155 mm
   variant it does not fit the 137 mm bay.** Weigh and measure the actual
   pack on thrust-stand day before locking the plate. Note also that
   "matches the mass the AUW budget assumes" is circular — both trace to
   the same listing.
6. **Arm print orientation is a slicer decision, not captured here.**
   Rule 2 requires arms printed on edge so bending is not across layer
   lines. The STL is exported in the assembly orientation; whoever slices
   it must rotate the arm.

---

## Related

- [[cfd-structural-recommendation-2026-08-17]] — material rules, minimum sections, the ≥10 % prop rule
- [[tooling-preflight-2026-08-17b]] — why this is headless FreeCAD and not an MCP
- [[stm32f405-pin-assignment]] — the board this frame carries
