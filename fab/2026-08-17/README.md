---
type: fab-package
status: NOT-READY-TO-ORDER
created: 2026-08-17
tags: [drone, hardware, pcb, fab]
---

# Fab package — bench_board, 2026-08-17

## Status: **NOT READY TO ORDER**

This is a complete set of fabrication outputs, and it is **not**
orderable. **Four blockers**, stated first because the rest of this
document describes a package that otherwise looks finished.

Ordering is David's call and David's alone. Nothing here has been sent
anywhere.

> [!warning] Much of this section was rewritten after an independent review
> The first version of this document claimed two blockers, called the
> inner layers "solid planes", said all 199 net conflicts were the same
> harmless kind, and presented a 267 → 43 DRC drop as pure improvement.
> A review found all four claims wrong. The corrections are inline
> below and each says what it replaced, rather than being silently
> edited.

---

## Blockers

### 1. Eighteen unconnected items — the board would not work

DRC reports 18 unconnected items. They are not cosmetic. Most are
**U1's 3V3 supply pins (1, 13, 19, 32, 48, 64)** and a set of GND pads
that have no via dropping to the inner planes.

The inner layers carry large GND and 3V3 pours, so a surface pad on
either net generally reaches its net only through a via. Freerouting's
fanout stage left 17 pins unrouted, and those pins therefore float. **An
STM32 with unconnected VDD pins does not run.**

(Two of the unconnected items are **PTH** pads on J3, whose barrels pass
through the inner layers regardless — those are not fanout misses and
have a different cause. One more is **`Pad 7 [VBAT_4S]` of U2**, the
buck's own power input, which is a distinct item on the highest-current
net rather than a 3V3/GND fanout miss.)

Two scripted attempts to close these are recorded as failures rather
than quietly dropped:

| Attempt | Method | Result |
|---|---|---|
| 1 | Via placed at a blind radial offset from each pad | 43 → **235** violations, 58 shorts |
| 2 | Same, plus clearance checks against other nets' pads/tracks/vias | 43 → **387** violations, 89 shorts |

Both were reverted. The second failed because the geometric model
ignored zone fills and drill-to-drill spacing, which KiCad checks and
the script did not.

**Conclusion: this needs manual routing in the KiCad UI against live
DRC.** It is a short job for a human with the board open — add fanout
vias on the MCU's supply pins and the remaining GND pads — and it is
not a job for scripted file surgery. Do not order until DRC reports
zero unconnected items.

### 2. U2 stock is unconfirmed

The main 3.3V buck, **TPS54336ADDA (LCSC C1355769)**, showed as *out of
stock at LCSC* in a search result during sourcing. That was not
confirmed against a live stock figure, because the JLCPCB part pages
render their stock and library-type fields via JavaScript and the
fetched HTML does not contain them.

It has no drop-in alternate on this footprint. **Verify availability
before ordering anything else**, since a substitution changes the
footprint, the feedback divider, and therefore the board.

### 3. Signal traces run through both inner "planes"

97 segments on In1.Cu and 90 on In2.Cu, including `SW_NODE`, `VBAT_4S`,
the crystal and the regulator feedback nets. The GND reference is sliced
by 97 slots. Detail and consequences in the section below. Same class of
work as blocker 1: KiCad UI, restrict the inner layers, re-route onto
F.Cu/B.Cu.

### 4. C23's net is missing from the board

`Pad missing net given by schematic (Net-(C23-Pad1))`, twice. C23 is the
TPS54336's **compensation capacitor**, so the buck's control loop is not
connected. A netless pad is one the router will not route and the zone
will not thermal-relieve. Filed for most of this batch under a heading
that said it affected nothing.

---

## What is in this package

| File | Contents |
|---|---|
| `gerbers/` | 11 layers (F/B copper, In1/In2, paste, silk, mask, Edge.Cuts), Excellon PTH + NPTH drill, drill maps, `.gbrjob` |
| `cpl_top.csv` | Pick-and-place, 55 parts, all top side |
| `cpl_bottom.csv` | Header only — nothing is mounted on the back |
| `bom_jlcpcb.csv` | 37 BOM lines with sourcing notes |

Board: **80 × 60 mm, 4 layers**, 55 components, 509 track segments,
90 vias.

### The inner layers are NOT clean planes — blocker 3

An earlier version of this document, and the batch commits, claimed the
inner layers were "solid planes (In1.Cu = GND, In2.Cu = 3V3), which
Freerouting detected and treated as such." **That is false**, and an
independent review caught it. Freerouting's log does say it configured
both as dedicated power planes, but it then routed signals through them
anyway:

| Layer | Segments | Distinct nets |
|---|---|---|
| F.Cu | 291 | — |
| **In1.Cu** (GND pour) | **97** | **24** |
| **In2.Cu** (3V3 pour) | **90** | **24** |
| B.Cu | 31 | — |

Nets routed *through* the pours include **`SW_NODE`** — the highest
dV/dt node on the board — plus `BOOST_SW`, `VBAT_4S` (on *both* inner
layers), `HSE_OUT` (the crystal), the regulator feedback and
compensation nets `VFB` / `VFB_5V` / `COMP_NODE`, `USB_DM` / `USB_DP`,
`NRST`, and M1–M4.

**Consequence, and it is real:** the GND reference under every F.Cu
signal is sliced by 97 traces. Return current has to detour around the
slots, which is the standard mechanism for EMI and ground bounce — and a
solid reference was the entire reason the pour was added. Burying
`SW_NODE` inside the 3V3 pour is the specific case worth fixing first.

This is precisely what item 5's manual review pass ("ground plane
integrity under MCU, no signal traces splitting the plane") existed to
catch, and that pass was skipped. **It is a third blocker, of the same
kind as the first: work to be done in the KiCad UI, restricting the
inner layers to their pours and re-routing signals onto F.Cu/B.Cu.**

**Mounting holes**: 4 × M3 (3.2 mm NPTH, 6 mm pad) on the standard
**30.5 × 30.5 mm** flight-controller pattern, centred on the board at
(24.75, 14.75), (55.25, 14.75), (24.75, 45.25), (55.25, 45.25). The
board had **none at all** before this batch — it could not have been
bolted to anything. They were added, the board re-routed around them
(still all 51 nets), and they are deliberately excluded from
`cpl_top.csv`, which lists 55 placeable parts and no mechanical holes.

## DRC state — verbatim

```
Found 52 violations
Found 18 unconnected items
Found 262 schematic parity issues
```

Breakdown:

```
violations: 52
   silk_over_copper                   23
   silk_overlap                       13
   clearance                           8
   lib_footprint_mismatch              4
   copper_edge_clearance               2
   starved_thermal                     2
unconnected_items: 18
schematic_parity: 262
   net_conflict                      199
   footprint_symbol_field_mismatch    55
   missing_footprint                   4
   extra_footprint                     4
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

### The 267 → 52 comparison is NOT like-for-like — the rules changed

The board at the start of this session reported 267 / 10 / 264. That
number and this one were **measured under different rulebooks**, and an
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
