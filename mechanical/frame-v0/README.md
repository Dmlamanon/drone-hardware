# STEVIE frame v0 — **FIT-CHECK ONLY, NOT A FLIGHT FRAME**

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
That requirement is what makes every structural part here a **flat
profile of constant thickness** — no draft, no ribs, no bosses, nothing
that only a printer can produce. The same outline is either printed or
cut, off the same DXF, which is exported.

Thickness is the only difference between the two builds:

| | PETG | CF plate | rule |
|---|---|---|---|
| Bottom plate | 3.0 mm | 2.0 mm | 3 mm min wall on load paths / 1.5 mm plate min |
| Top plate | 3.0 mm | 1.5 mm | same |
| Arm | 4.0 mm | 2.0 mm | 4 mm at arm roots / 2 mm CF arms |
| **Structure mass** | **141.5 g** | **96.6 g** | bulk density 1.27 / 1.55 g·cm⁻³ |

Sections are sized to the **weaker** material and the stronger one is
checked to fit the same envelope, which is what that document asks for.

**Do not read 141 g as beating the 469 g frame line in the AUW budget.**
That is structure only — no landing gear, no standoffs, no fasteners, no
canopy, no battery tray. Those are real mass and v0 does not model them.

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

The guideline is **≥10 %** of prop diameter. This is **8.26 %**, and the
script reports it as a FAIL rather than rounding it into acceptability.
It reproduces the 18.9 mm / 8.3 % figure already in this project exactly.

Item 6 asked to *"do better than the current geometry if arm length
allows within the wheelbase."* **It does not allow it, and that is a
proof rather than an opinion:**

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
confirms 247.49 mm is the maximum achievable. So the clearance can only
be bought with one of two things, both of which are **David's call**
because both change a locked platform decision:

| option | result | cost |
|---|---|---|
| Keep 350 mm, drop to **9.0 → 8.85 in props** (≤ 225.0 mm) | ≥10 % | less thrust and less disc area at the same wheelbase |
| Keep 9 in props, grow wheelbase to **≥ 355.6 mm** | ≥10 % | +1.6 % on a locked class name; re-opens the inertia/gain derivation |

355.6 mm is **1.6 % more than 350 mm**. That is how close this is to
passing, and it is the cheaper of the two options if the class name can
move at all. Recorded, not decided.

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
| `stevie-frame-v0-flats-*.dxf` | **flat outlines for CF cutting** — this is what makes the carbon option real rather than claimed |
| `stevie-frame-v0-*-plan.svg` | scale plan view, gallery render |
| `build-report-*.txt` | the run's own numbers and check results |

The render is a **plan view, not a 3D render**, for two reasons: headless
FreeCAD has no viewport to screenshot, and the one thing worth looking at
on this frame is the prop-disc overlap — which a grey isometric render of
the STL would actually hide.

---

## Known gaps in v0, listed rather than discovered later

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
5. **Arm print orientation is a slicer decision, not captured here.**
   Rule 2 requires arms printed on edge so bending is not across layer
   lines. The STL is exported in the assembly orientation; whoever slices
   it must rotate the arm.

---

## Related

- [[cfd-structural-recommendation-2026-08-17]] — material rules, minimum sections, the ≥10 % prop rule
- [[tooling-preflight-2026-08-17b]] — why this is headless FreeCAD and not an MCP
- [[stm32f405-pin-assignment]] — the board this frame carries
