---
type: fab-package
status: NOT-READY-TO-ORDER
created: 2026-08-17
tags: [drone, hardware, pcb, fab]
---

# Fab package — bench_board, 2026-08-17

## Status: **NOT READY TO ORDER**

This is a complete set of fabrication outputs, and it is **not**
orderable. **Two blockers remain of the four** — and they turn out to be
the same underlying problem. Stated first because the rest of this
document describes a package that otherwise looks finished.

**Regenerated 2026-08-17 (second batch)** after C23 was reconnected, Y1
and C1 were re-footprinted, the mounting holes were moved off nine
components, and the net names were normalised. All outputs in this folder
come from that board, not the earlier one.

Ordering is David's call and David's alone. Nothing here has been sent
anywhere.

> [!success] Two blockers cleared since the previous version
> - **C23 is connected.** Its net genuinely did not exist: the buck's
>   compensation network is `COMP_NODE → R11 → ? → C23 → GND` and the
>   middle junction had no wire. Added; ERC still 0/0; C23 no longer
>   appears anywhere in the parity report.
> - **U2 is in stock.** The claim that it might not be came from a
>   search-result snippet rather than the part page. Fetching the page
>   directly: **245 units, $1.07 at qty 1, $0.86 at 10+.** The
>   bottleneck was not real.

> [!warning] Much of this document was rewritten after an independent review
> An earlier version called the inner layers "solid planes", said all
> 199 net conflicts were the same harmless kind, and presented a
> 267 → 43 DRC drop as pure improvement. A review found those wrong. The
> corrections are inline and each says what it replaced, rather than
> being silently edited.

---

## Blockers

### 1 + 2. The inner layers and the unconnected pins — ONE problem

**15 unconnected items**, mostly **U1's 3V3 supply pins (1, 13, 19, 32,
48, 64)**. An STM32 with unconnected VDD pins does not run.

**214 signal segments routed through the inner layers** — 118 on In1.Cu
(the GND pour) and 96 on In2.Cu (the 3V3 pour) — including `SW_NODE`
(the highest dV/dt node on the board), `VBAT_4S`, `HSE_IN`/`HSE_OUT` and
the regulator feedback nets.

**These are not two tasks. They are one, and the evidence is direct.**

A fanout via was placed at **(27.90, 26.25)** on net `3V3` with a stub to
U1 pad 1, and the zones were refilled. DRC **still** reported the pad as
unconnected. Extracting the actual filled copper from the board file
shows why:

| Zone layer | Filled polygons | Extent |
|---|---|---|
| In1.Cu (GND) | 2 | main pour 2,2–78,58 **+ a 1.4 × 1.2 mm island** |
| In2.Cu (3V3) | 2 | main pour 2,2–78,58 **+ a 5.5 × 0.8 mm island** |

The via landed inside the **5.5 × 0.8 mm island** — a sliver cut off from
the main pour — and connects to nothing. Sampling the pours confirms the
cause: **(40, 30), the middle of the board directly under the MCU, is not
covered by filled copper on either inner layer.**

**You cannot via down to a plane that is not there.** Fix the planes
first; most of the pins may then fix themselves. The experimental via was
removed rather than left as dead copper.

**Why this was not fixed automatically.** Freerouting v2.3.0 logs
`Layer 'In1.Cu' has been automatically configured as a dedicated power
plane` and routes signals on it anyway. A DSN hand-edited to declare both
inner layers `(type power)` — the correct Specctra mechanism — made
Freerouting **hang for 16 minutes** with completely flat memory before
being killed.

**The fix is manual and is fully specified** in
`docs/manual-fanout-guide-2026-08-17.md`: the ordering, a custom DRC
keepout rule to stop signals re-entering the planes, the per-net list of
what must not touch an inner layer, and the verification commands. B.Cu
carries only 19 segments, so there is a nearly empty layer to move the
traffic onto. **1–2 hours.**

---

## What is in this package

| File | Contents |
|---|---|
| `gerbers/` | 11 layers (F/B copper, In1/In2, paste, silk, mask, Edge.Cuts), Excellon PTH + NPTH drill, drill maps, `.gbrjob` |
| `cpl_top.csv` | Pick-and-place, 55 parts, all top side |
| `cpl_bottom.csv` | Header only — nothing is mounted on the back |
| `bom_jlcpcb.csv` | 37 BOM lines with sourcing notes |

Board: **80 × 60 mm, 4 layers**, 55 components, 543 track segments,
94 vias, all **52 nets** routed (was 51 — `COMP_RC` is new, and is the
C23 fix).

**Mounting holes**: 4 × M3 (3.2 mm NPTH, 6 mm pad) at **(4.5, 19)**,
**(75.5, 16)**, **(4.5, 55.5)** and **(75.5, 41)**.

They were added in the previous batch on the standard 30.5 × 30.5 mm
flight-controller pattern — **and that pattern put them on top of nine
components** (D1, J2, R12, R13, C2, J4, L1, R1, U2, C6, J6, R3). The
positions above were found by scanning every component courtyard for
clear space, and the board now reports **zero courtyard overlaps**.

The 30.5 × 30.5 pattern does not fit this board's layout. That pattern
belongs on a flight board designed around it; this is an 80 × 60 mm bench
board whose components were placed first. If the standard pattern is
required later, the components move, not the holes.

The holes are excluded from `cpl_top.csv` — `kicad-cli` emits them, which
would tell an assembler to place four holes. The file lists exactly the
55 placeable parts.

## DRC state — verbatim

```
Found 46 violations
Found 15 unconnected items
Found 88 schematic parity issues
```

Previous batch ended at 52 / 18 / 262. **No design rules were relaxed to
achieve this** — the only rule-file change was updating the netclass
patterns to match the renamed nets, and that change made DRC *stricter*
again after the rename had briefly disabled the Power class.

The parity figure fell furthest because **199 of those issues were a
single uniform naming difference** — the board stored bare net names
(`GND`) where KiCad's netlister uses the sheet-path form (`/GND`) —
across 52 nets, with no genuine mismatch hiding among them. Normalised.
**The 25 remaining `net_conflict` entries are all KiCad auto-nets for
deliberately unconnected MCU pins** (`unconnected-(U1-PC13-Pad2)` and
similar), which are correct and should stay.

Breakdown:

```
violations: 46
   silk_over_copper                   17
   silk_overlap                       13
   clearance                           8
   lib_footprint_mismatch              4
   copper_edge_clearance               2
   starved_thermal                     2
unconnected_items: 15
schematic_parity: 88
   footprint_symbol_field_mismatch    55
   net_conflict                       25
   missing_footprint                   4
   extra_footprint                     4
```

Layer usage, which is the number blocker 1+2 is about:

```
     19 (layer "B.Cu")      <- nearly empty; this is where the traffic should go
    310 (layer "F.Cu")
    118 (layer "In1.Cu")    <- must become 0
     96 (layer "In2.Cu")    <- must become 0
```

Adding the mounting holes cost 6 silkscreen warnings, the 4
`lib_footprint_mismatch` entries and the 4 `extra_footprint` parity
notes, and removed one unconnected item and one starved thermal. That
trade is worth taking: a board with no mounting holes is not usable at
any DRC count.

- **lib_footprint_mismatch (4)** — the four mounting holes. The library
  footprint `MountingHole:MountingHole_3.2mm_M3` exists, but the
  geometry generated into the board does not byte-match the library
  copy. The hole that gets fabricated is the one in the board file, and
  it is correct (3.2 mm NPTH, 6 mm annulus).
- **extra_footprint (4)** — the same four holes, present on the PCB and
  absent from the schematic. That is correct for mechanical parts and
  is how mounting holes normally appear.

This is **not** a clean DRC and is not presented as one.

### Historical note: the PREVIOUS batch DID relax rules (this one did not)

The board at the start of the PREVIOUS batch reported 267 / 10 / 264.
That number and the 52 it fell to were **measured under different
rulebooks**, and an
earlier version of this document presented the drop as if it were all
improvement. It was not. The design rules changed as follows, and none
of it was disclosed in any commit message:

| Rule | Before | After | Direction |
|---|---|---|---|
| `min_track_width` | 0.2 | **0.15** | relaxed |
| **Default netclass `clearance`** | **0.2** | **0.15** | **relaxed — this is the one that retired the most** |
| `min_copper_edge_clearance` | 0.5 | 0.3 | relaxed |
| `min_via_diameter` | 0.5 | 0.45 | relaxed |
| `min_clearance` | 0.0 (unset) | 0.127 | *tightened* |

Roughly **114 of 156** violations at the intermediate step were retired
by editing these numbers rather than by touching copper. Specifically:
all 41 `track_width` items went away because the limit moved to 0.15 mm
while **29 F.Cu traces are still 0.15 mm wide**, and a large block of
clearance items at 0.150/0.156 mm became legal when the Default class
dropped to 0.15 mm.

Two honest caveats on that:

- **The values are defensible.** JLCPCB's standard 4-layer capability is
  finer than 0.15 mm, so the board remains manufacturable as drawn.
- **The justification originally given was not.** The commit claimed a
  "previous 0.25 mm rule was stricter than the parts' own geometry —
  a 0.5 mm-pitch LQFP has 0.2 mm pad gaps." No 0.25 mm clearance rule
  ever existed; a 0.2 mm gap does not violate a 0.2 mm rule; and no
  violation in any DRC run was ever an LQFP pad gap. Every item actually
  retired was at 0.150 or 0.156 mm.
- **Setting a limit to exactly the observed minimum leaves zero margin.**
  The rule now restates what the board happens to be rather than
  constraining it.

What genuinely improved, independent of the rules: `shorting_items`
5 → 0, `footprint_symbol_mismatch` 6 → 0, `lib_footprint_mismatch` on
U2 → 0, and all 51 nets routed. Those are copper changes, not rule
changes. What changed and why is in
`docs/stale-board-resync-2026-08-17.md`.

### How to read what remains

- **silk_over_copper (23) + silk_overlap (13)** — silkscreen text over
  pads and other text. Cosmetic; JLCPCB clips silk off pads
  automatically. Worth tidying, does not affect function.
- **clearance (8)** — all eight are *inside J3's own footprint*, between
  the USB-C receptacle's PTH shield pads (0.156 mm apart). That spacing
  is the manufacturer's land pattern, not a routing error.
- **copper_edge_clearance (2)** — J3's mounting pads sit 0.269 mm and
  0.298 mm from the edge against a 0.3 mm rule. J3 is an edge connector,
  so this is inherent to placing it at the edge; both figures still
  exceed JLCPCB's 0.2 mm floor.
- **starved_thermal (2)** — two PTH GND pads get one thermal spoke
  instead of two. Slightly harder to hand-solder; not an electrical
  fault.
- **net_conflict (199)** — these are **two different things**, and an
  earlier version of this document wrongly said "every one is the same
  shape." The real split is **175 + 24**:
  - **175** are the harmless prefix form, `Pad net (GND) doesn't match
    net given by schematic (/GND)` — the board stores bare net names,
    the schematic stores root-sheet-prefixed ones. No fabrication
    output carries net names, so these change no copper. They should
    still be resolved, because "board and schematic are not identical"
    is exactly the condition that hid this batch's main defect.
  - **24** are `Pad missing net given by schematic (…)` — the board pad
    has **no net at all** where the schematic assigns one. 22 of those
    are KiCad's auto-generated `unconnected-(U1-PCxx-Padnn)` nets for
    deliberately unconnected MCU pins, and are benign.
  - **The remaining 2 are a functional defect:** `Pad missing net given
    by schematic (Net-(C23-Pad1))`. **C23 is the TPS54336's
    compensation capacitor** — the part this document's own sourcing
    section calls "value is not freely substitutable." Its net is
    absent from the board, so the buck's control-loop compensation is
    not connected. A netless pad is one the router will not route and
    the zone will not thermal-relieve, so this *does* change copper.
    **Must be fixed before ordering.**
- **footprint_symbol_field_mismatch (55)** — missing `Description` and
  `Voltage` metadata fields on the PCB footprints. Metadata only.
- **missing_footprint (4)** — FLG1/2/4/5 are `PWR_FLAG` schematic
  symbols with no physical part. Correct and expected.

**Value and footprint drift is now zero** — a scripted comparison of all
55 parts shows no value mismatches and no footprint mismatches. That is
narrower than "board matches schematic", and an earlier version of this
document overstated it as such: KiCad's own parity check, on this same
page, still reports 262 issues, at least two of which (C23, above) are
functional. Drift is zero *in the two dimensions the script examined*.

## Sourcing summary

Full detail with per-line notes is in `bom_jlcpcb.csv`.

**Verified LCSC part numbers** (checked against LCSC/JLCPCB pages):

| Ref | Part | LCSC | Note |
|---|---|---|---|
| U1 | STM32F405RGT6 | C15742 | Extended; needs an assembly fixture |
| U2 | TPS54336ADDA | C1355769 | Extended; **stock unconfirmed — blocker 2** |
| U4 | MPU-6000 | C92401 | Extended, **~$10.42** |
| U5 | USBLC6-2SC6 | C7519 | Extended |
| U6 | MT3608 | C84817 | Extended, ~$0.06–0.10 |
| D1 | SS34 | C8678 | **Basic** (confirmed on the JLCPCB part page) |

**Passives** were matched against a community snapshot of JLCPCB's Basic
library, which gives part number, package, stock and price. That
snapshot is *not* authoritative and *not* live.

**The caveat is wider than "check the part numbers."** Both design
findings below rest on **attribute data** from that same unverified
snapshot — C15850's *25 V rating* and C115962's *SMD-5032-2P package*.
So: **every Basic part number AND every attribute used to reach a
conclusion must be re-checked at order time.** The CSV itself carries a
bare `Basic` on 13 lines with no provenance marker; only D1 is verified
against a live JLCPCB page. Anyone reading the BOM without this README
would see 14 confirmed Basic parts, and there is one.

### Sourcing findings that change the design

1. **C1 sits on VBAT_4S and the Basic part is the wrong choice — but
   not for the reason first given.** An earlier version of this document
   said the Basic 0805 10 µF (C15850, 25 V) was unusable because "an X5R
   at 16.8 V DC bias loses most of its rated capacitance," implying a
   35 V part would not. **That reasoning is wrong.** MLCC bias derating
   is driven by dielectric, case size and applied field: a 35 V 0805
   10 µF at 16.8 V also loses a large fraction of its capacitance. The
   rating change does not fix the derating.

   Two corrections follow:
   - **25 V at 16.8 V is not a rating violation** (67 % of rated,
     1.49× margin). The real reasons to want more margin here are
     switch-node ringing and 4S transients on the buck input — which is
     a legitimate argument, and is not the one that was made.
   - **"35 V or 50 V 0805 10 µF X7R" is close to unbuyable.** 0805 X7R
     tops out near 4.7 µF at 25 V and ~2.2 µF at 50 V in mainstream
     catalogues. As originally written, this line handed the buyer an
     instruction that cannot be filled.

   **What is actually required:** a specified capacitance **at 16.8 V
   bias**, which neither the BOM nor this README currently states.
   Realistic routes are a 1206/1210 case, an X5R part, or a smaller
   ceramic plus separate bulk. Note the re-sync corrected C1's *value
   string* to "10uF 35V" while leaving the footprint at
   `C_0805_2012Metric` — the case-size consequence was never evaluated.
2. **Y1's Basic match is the wrong package.** The Basic 8 MHz crystal
   (C115962) is SMD-5032-2P; the board uses a 3225 4-pin footprint.
   Either source a 3225 4-pin part or change the footprint.
3. **Not in the Basic library at all**, so each attracts the Extended
   setup fee or hand-soldering: C23 (7.5 nF, regulator compensation),
   R1 (31.6 k) and R12 (73.2 k) — both feedback dividers that *set
   output voltages* and are not substitutable — and L1/L2 (10 µH power
   inductors, where saturation current matters, not just inductance).
4. **All eight 2.54 mm headers (J1, J2, J4–J9) are through-hole** and are
   marked hand-solder. JLCPCB charges extra for THT assembly.
5. **J3's USB-C footprint** is an Amphenol part; the matching JLCPCB
   component was not confirmed. Verify pad compatibility before paying
   for assembly.

### Expected assembly cost class

Deliberately a *class*, not a quote — I have not priced an order, and
pricing one is David's call.

- **PCB**: 4-layer, 80 × 60 mm, standard spec — the cheapest 4-layer
  tier at the usual prototype quantities.
- **Parts**: dominated by **U4 (MPU-6000) at ~$10.42 each**, which is
  roughly two-thirds of the per-board component cost on its own. Every
  other line is cents. U4 is a part-selection decision and therefore
  David's; it is flagged, not changed.
- **Assembly**: at least six Extended parts (U1, U2, U4, U5, U6, plus
  the unresolved passives), each attracting a one-off setup fee.
  Extended-part fees are likely to exceed the entire PCB cost at
  prototype quantity.
- **Hand-soldering**: eight THT headers, either done at home or paid for
  as THT assembly.

## Reproducing these outputs

```bash
cd engineering/drone-hardware/bench_board
KC="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"

"$KC" pcb drc --format json --output drc_final.json \
      --severity-all --schematic-parity bench_board.kicad_pcb

"$KC" pcb export gerbers --output ../fab/2026-08-17/gerbers \
      --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" \
      --subtract-soldermask --no-protel-ext bench_board.kicad_pcb

"$KC" pcb export drill --output ../fab/2026-08-17/gerbers/ \
      --format excellon --excellon-separate-th --generate-map \
      --map-format gerberx2 bench_board.kicad_pcb

"$KC" pcb export pos --output ../fab/2026-08-17/cpl_top.csv \
      --side front --format csv --units mm --use-drill-file-origin \
      bench_board.kicad_pcb
```

**Always pass `--schematic-parity`.** Its absence is exactly how the
board drifted two revisions behind the schematic without anyone
noticing.
