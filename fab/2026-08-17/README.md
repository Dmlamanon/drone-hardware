---
type: fab-package
status: NOT-READY-TO-ORDER
created: 2026-08-17
tags: [drone, hardware, pcb, fab]
---

# Fab package — bench_board, 2026-08-17

## Status: **NOT READY TO ORDER**

This is a complete, self-consistent set of fabrication outputs, and it
is **not** orderable yet. Two blockers are listed below. They are stated
first because the rest of this document describes a package that
otherwise looks finished.

Ordering is David's call and David's alone. Nothing here has been sent
anywhere.

---

## Blockers

### 1. Nineteen unconnected items — the board would not work

DRC reports 19 unconnected items. They are not cosmetic. Most are
**U1's 3V3 supply pins (1, 13, 19, 32, 48, 64)** and a set of GND pads
that have no via dropping to the inner planes.

The inner layers are solid planes (In1.Cu = GND, In2.Cu = 3V3), so a
surface pad on either net is connected *only* through a via.
Freerouting's fanout stage left 17 pins unrouted, and those pins
therefore float. **An STM32 with unconnected VDD pins does not run.**

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

---

## What is in this package

| File | Contents |
|---|---|
| `gerbers/` | 11 layers (F/B copper, In1/In2, paste, silk, mask, Edge.Cuts), Excellon PTH + NPTH drill, drill maps, `.gbrjob` |
| `cpl_top.csv` | Pick-and-place, 55 parts, all top side |
| `cpl_bottom.csv` | Header only — nothing is mounted on the back |
| `bom_jlcpcb.csv` | 38 BOM lines with sourcing notes |

Board: **80 × 60 mm, 4 layers**, 55 components, 498 tracks, 89 vias.
Inner layers are both planes (GND and 3V3), which Freerouting detected
and treated as such.

## DRC state — verbatim

```
Found 43 violations
Found 19 unconnected items
Found 258 schematic parity issues
```

Breakdown:

```
violations: 43
   silk_over_copper                   17
   silk_overlap                       13
   clearance                           8
   starved_thermal                     3
   copper_edge_clearance               2
unconnected_items: 19
schematic_parity: 258
   net_conflict                      199
   footprint_symbol_field_mismatch    55
   missing_footprint                   4
```

This is **not** a clean DRC and is not presented as one. For contrast,
the same board at the start of this session reported 267 / 10 / 264,
with five genuine shorts. What changed is in
`docs/stale-board-resync-2026-08-17.md`.

### How to read what remains

- **silk_over_copper (17) + silk_overlap (13)** — silkscreen text over
  pads and other text. Cosmetic; JLCPCB clips silk off pads
  automatically. Worth tidying, does not affect function.
- **clearance (8)** — all eight are *inside J3's own footprint*, between
  the USB-C receptacle's PTH shield pads (0.156 mm apart). That spacing
  is the manufacturer's land pattern, not a routing error.
- **copper_edge_clearance (2)** — J3's mounting pads sit 0.269 mm and
  0.298 mm from the edge against a 0.3 mm rule. J3 is an edge connector,
  so this is inherent to placing it at the edge; both figures still
  exceed JLCPCB's 0.2 mm floor.
- **starved_thermal (3)** — three PTH GND pads (J3, J4, J5) get one
  thermal spoke instead of two. Slightly harder to hand-solder; not an
  electrical fault.
- **net_conflict (199)** — every one is the same shape: `Pad net (GND)
  doesn't match net given by schematic (/GND)`. The board stores bare
  net names, the schematic stores root-sheet-prefixed ones. It affects
  no fabrication output — gerbers carry no net names — but it does mean
  KiCad itself does not consider board and schematic identical, so it
  should be resolved rather than lived with.
- **footprint_symbol_field_mismatch (55)** — missing `Description` and
  `Voltage` metadata fields on the PCB footprints. Metadata only.
- **missing_footprint (4)** — FLG1/2/4/5 are `PWR_FLAG` schematic
  symbols with no physical part. Correct and expected.

**Board-vs-schematic drift is now zero**: a scripted comparison of all
55 parts shows no value mismatches and no footprint mismatches.

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
snapshot is *not* authoritative and *not* live — **every Basic part
number in the BOM must be re-checked at order time.**

### Sourcing findings that change the design

1. **C1 must be ≥35 V and the Basic part is not.** C1 sits on VBAT_4S
   (16.8 V at full charge). The Basic 0805 10 µF (C15850) is rated
   25 V, and an X5R MLCC at 16.8 V DC bias loses most of its rated
   capacitance. Substituting it would quietly shrink the input bulk
   capacitance. The schematic's "10uF 35V" is correct and must be
   honoured with an Extended part.
2. **Y1's Basic match is the wrong package.** The Basic 8 MHz crystal
   (C115962) is SMD-5032-2P; the board uses a 3225 4-pin footprint.
   Either source a 3225 4-pin part or change the footprint.
3. **Not in the Basic library at all**, so each attracts the Extended
   setup fee or hand-soldering: C23 (7.5 nF, regulator compensation),
   R1 (31.6 k) and R12 (73.2 k) — both feedback dividers that *set
   output voltages* and are not substitutable — and L1/L2 (10 µH power
   inductors, where saturation current matters, not just inductance).
4. **All nine 2.54 mm headers (J1, J2, J4–J9) are through-hole** and are
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
- **Hand-soldering**: nine THT headers, either done at home or paid for
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
