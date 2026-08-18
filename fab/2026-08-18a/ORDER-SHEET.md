---
type: order-sheet
status: READY-TO-ORDER-WITH-CONDITIONS
created: 2026-08-18
tags: [drone, hardware, pcb, fab, jlcpcb, order]
---

# ORDER SHEET — bench_board rev 2026-08-18a, JLCPCB, qty 5

Written for someone who has never ordered a PCB. Follow it top to
bottom. Two conditions are embedded and marked **STOP** — read them
before paying.

Generated from board commit `e06a699` (DRC verbatim: **53 violations /
2 unconnected / 95 parity** — see "Honest final state" below for why
that is orderable). Supersedes rev 2026-08-17c, which carried a
**datasheet absolute-maximum violation** (TPS54336A EN pin at 16.8 V
against a 6 V rating) — fixed this revision with a proper pack-UVLO
divider. Also fixed: the MPU-6000 charge-pump cap (now 2.2 nF/50 V to
GND per its datasheet) and the crystal load caps (33 pF for the 20 pF
crystal).

> [!note] NEW BEHAVIOUR DAVID WILL SEE ON THE BENCH — by design
> The 3.3 V rail now implements **pack undervoltage lockout**. Nominal
> thresholds: start **12.0 V** (3.00 V/cell on 4S), stop **11.0 V**,
> ~1 V hysteresis so it cannot chatter. **The independent review's
> worst-case numbers, using the EN comparator's datasheet LIMITS rather
> than typicals: start may be anywhere in 12.0–13.0 V and stop anywhere
> in 10.1–11.0 V**, part-to-part — the comparator tolerance dominates
> the 1% resistors. Two practical consequences:
> **(1) Bench supplies: set ≥ 13.5 V** — a worst-case part refuses to
> start until ~12.95 V, and a board doing that is working, not broken.
> **(2) This UVLO is brownout protection for the electronics, NOT LiPo
> cell protection** — a worst-case part runs the pack down to
> 2.53 V/cell before cutting off. The firmware's low-battery policy
> remains the actual pack guardian.
> One more line for storage habits: the divider draws a standing
> **~83 µA from the pack whenever one is plugged in** (~62 mAh/month)
> — don't leave a pack connected for storage.

---

## Step 1 — upload the gerbers

1. Go to jlcpcb.com, click **Order now**.
2. Zip the entire `gerbers/` folder in this directory and drop the zip
   into the upload box. JLCPCB reads the board size (80 × 60 mm) and
   layer count (4) automatically — confirm it shows **4 layers**.

## Step 2 — PCB options to click

| option | set it to | why |
|---|---|---|
| Base material | FR-4 | default |
| Layers | **4** | In1=GND plane, In2=3V3 plane |
| Dimensions | 80 × 60 mm | auto-detected |
| PCB Qty | **5** | ≈$32/board at 5 vs ≈$60 at 1 |
| PCB Thickness | 1.6 mm | default |
| PCB Color | any — green is fastest/cheapest | |
| Surface Finish | **LeadFree HASL** (ENIG optional, +≈$15) | LQFP-64 at 0.5 mm pitch assembles fine on HASL |
| Outer Copper Weight | 1 oz | default |
| Inner Copper Weight | 0.5 oz | default |
| Via Covering | **Epoxy Filled & Capped** | **MANDATORY — see the danger box** |
| Min via hole size/diameter | **0.15 mm/0.25 mm** | the board contains 0.15 mm laser-class drills |
| Board Outline Tolerance | ±0.2 mm | default |
| Remove Order Number | "Specify a location" is free | cosmetic |

> [!danger] VIA-IN-PAD IS A MANUFACTURING REQUIREMENT, NOT AN OPTION
> This revision closed supply pins with vias placed **inside solder
> pads**. An unfilled via inside a pad wicks solder paste down the
> barrel during reflow and produces a starved or open joint — on the
> processor's own supply pins, the worst place on the board for it.
>
> **You MUST select Via Covering = "Epoxy Filled & Capped".** If the
> option is greyed out, refused for this board, or missing for 4-layer:
> **STOP. Do not order. Tell Claude/the log — that changes the whole
> approach.** (Verified 2026-08-18 against JLCPCB's published
> capabilities: epoxy filled & capped is offered on 4-layer boards as a
> paid option, supported hole range 0.15–0.55 mm; every in-pad drill on
> this board is 0.15–0.40 mm, inside the range. It is free only on
> 6-layer and up, so expect a surcharge here — community reports put it
> around US$30–60 at prototype quantity. If the surcharge shocks you,
> a 6-layer upgrade gets the fill free and is occasionally net-cheaper —
> compare both carts before deciding.)
>
> In the order remarks, paste this line so the fab knows which pads are
> affected:
> *"Via-in-pad (filled & capped required): U1 pads 12, 13, 18, 19, 63
> (0.3/0.15 mm vias fully inside pads); L1 pad 1 (0.6/0.4 mm via inside
> pad); R16 pad 2 (0.6/0.3 mm via-in-pad — 0.22 mm of the 0.30 mm drill
> sits inside the pad copper, the deepest overlap on the board; added
> 2026-08-18 with the EN fix); via barrels overlapping pad edges at U4
> pad 11 (0.3/0.15, 0.075 mm penetration) and C27 pad 2 (0.6/0.3,
> 0.178 mm penetration). One near-tangent worth the same treatment: a
> 0.6/0.4 via clears C2 pad 1 by only 0.014 mm — inside
> mask-registration tolerance, so please fill/cap it too."*
>
> These positions are measured from the board file (geometric audit,
> re-derived independently by this batch's reviewer with exact
> roundrect pad geometry, 2026-08-18), not inferred from commit
> messages. The reviewer's re-derivation removed one false positive
> (C24 pad 1 — its nearest via clears by 0.153 mm) and confirmed
> nothing is missing from the list.

## Step 3 — SMT assembly options

| option | set it to |
|---|---|
| PCB Assembly | **ON** |
| Assembly side | **Top** only (the back is empty) |
| PCBA Qty | **5** (assembling only 2 saves ≈$25 in parts if you want spares-as-bare-boards) |
| Tooling holes | Added by JLCPCB (they may add edge rails — accept) |
| Confirm Parts Placement | **Yes** (free review of rotations; the LQFP and QFN rotations are worth the day's delay) |

3. Upload `bom_jlcpcb.csv` as the BOM and `cpl_top.csv` as the CPL.
4. In the parts-matching screen, every row with an LCSC number should
   match automatically. **Re-verify live stock on two thin lines:**
   U1 STM32F405RGT6 (C15742 — 264 in stock at last check) and U2
   TPS54336ADDA (C1355769 — 245). If either shows zero: **STOP** — there
   is no drop-in alternate on these footprints; wait for restock or
   source the chips yourself and switch to consignment.
   Also re-verify **R16's 182 k (C11481)** — a brand-new Extended part
   whose stock reads inconsistently across sources (19k vs 335 units);
   if thin, the drop-in alternate is C327365 (Yageo RC0402FR-07182KL,
   1%, same value/size).
   Two more verify-before-paying checks from the BOM's own notes:
   **L1/L2 (C17701247)** is a candidate David sanity-checks — the
   saturation math is in the BOM row, and the caveat is that a full
   1 A receiver load thins L2's headroom; and **Y1 (C115962)** came
   from a community snapshot — confirm it against the live JLCPCB
   part page during matching.
5. Rows the assembler will NOT place (they show as "no part selected" —
   that is correct, click through it): **J1–J10 (all headers), J3
   (USB-C), BUZZER**. Details below.

## Step 4 — what arrives loose / what David solders

JLCPCB places all 53 SMD parts (13 Extended part numbers ⇒ 13 × $3
setup fees are already in the estimate; L1/L2 share one part number).
New this revision: R16/R17 (the EN UVLO divider) and C20's corrected
2.2 nF/50 V part. The following are **hand work**:

**The nine through-hole headers** (2.54 mm pitch — buy any standard pin
header stock and cut to length; ~30 min total soldering):

| ref | pins | connects to |
|---|---|---|
| J1 | 2 | 4S battery input (VBAT_4S + GND) — power in |
| J2 | 2 | BOOT0 jumper — short to enter the STM32 bootloader |
| J4 | 4 | CRSF UART — the RC receiver (ELRS/Crossfire) |
| J5 | 5 | DShot motor signals M1–M4 + GND, to the 4-in-1 ESC |
| J6 | 5 | SWD — programming/debug (ST-Link) |
| J7 | 2 | 5 V receiver power (from the MT3608 boost rail) |
| J8 | 3 | Telemetry UART TX |
| J9 | 14 | Expansion bus (spare MCU pins broken out) |
| J10 | 2 | Buzzer (drive comes from Q1; buzzer itself is flying-lead) |

**J3, the USB-C receptacle — hand-fitted, and here is the honest
reason:** no JLCPCB-stocked USB-C is pad-compatible with this Amphenol
footprint. That is a measured result, not a guess — every stocked
candidate family was pulled from the assembler's own footprint database
and diffed against the board's pad table
(`docs/j3-usbc-substitute-verification-2026-08-17c.md`). Buy **Amphenol
12401548E4#2A** from Digi-Key or Mouser (~US$2). Soldering just the
through-hole B row and shield legs gives a mechanically sound, working
USB 2.0 port; drag-soldering the 0.5 mm SMT A row adds the flipped-plug
contact redundancy. Until it is fitted, the board has no USB — SWD (J6)
still programs it.

## Step 5 — honest final state (what you are ordering)

DRC verbatim, this exact package: **53 violations, 2 unconnected items,
95 schematic parity issues.** (Parity is +2 vs the last revision:
the two new UVLO resistors carry the same benign empty-metadata-field
mismatch as the other 61 components.)

- **The 2 unconnected items** are U1 pad 48 (a /3V3 supply pin) and U4
  pad 1 (the IMU's grounded CLKIN). Five automated attempts to close
  them regressed the board and were reverted by the guard, so they are
  **bench wire jumpers after the boards arrive** — measured from the
  board file (an earlier draft of this sheet called them
  "sub-millimetre solder bridges"; that misread the DRC's track-length
  field and was caught by the independent review — the real distances
  are below):
  - **U4 pad 1 → U4 pad 18**: both /GND, both at the same height on
    the QFN, **3.9 mm apart in a straight line**. One short bare wire
    lying flat between the two pin lands, or tack to the /GND track
    stub that already ends at pad 18. QFN perimeter pads are fine work
    — magnification and a fine tip.
  - **U1 pad 48 → C21 pad 1**: both /3V3, **9.2 mm apart**. A thin
    insulated wire (30 AWG wire-wrap) from the LQFP pin 48 lead to the
    3V3 terminal of cap C21 at (45.6, 34.0). Budget 15–30 minutes for
    the pair, not five. *(Earlier revisions named C20 pad 2 as the
    target — this batch re-routed C20's return to GND per the MPU-6000
    datasheet, so C20 is no longer a 3V3 point. C21 pad 1 is the
    nearest 3V3 pad now.)*

  The STM32 runs without pad 48 jumpered (its other VDD pins carry it)
  but is out of datasheet spec until jumpered; do both before trusting
  the board.
- **The 53 violations:** 37 silkscreen cosmetics, 8 pre-existing
  clearance reports inside the J3 footprint's own pads, 4 known
  mounting-hole library mismatches, 2 copper-edge (J3's NPTH, 0.269 and
  0.298 mm against our 0.3 mm rule — JLCPCB's own floor is 0.2 mm, so it
  fabricates fine), 2 starved thermals (J9.1, J3.B1 — solder them with
  a bigger iron tip). None are shorts, crossings, or hole errors.
- **The 95 parity issues** (93 baseline + the two new UVLO resistors'
  empty Description fields) are all metadata/no-net-by-design; itemized
  in `README.md` here.

## Step 6 — cost at qty 5 (estimate; the cart is the truth)

| line | est. USD |
|---|---|
| 4-layer PCB, 80×60, qty 5 | 15–25 |
| **Epoxy filled & capped vias (the mandatory option)** | 30–60 |
| SMT assembly setup + stencil | ~10 |
| 13 Extended-part setup fees | 39 |
| Parts, 5 boards (U4 MPU-6000 ≈$52 and U1 ≈$29 dominate) | ~110 |
| Shipping (economy) | 10–20 |
| **Total, 5 assembled boards** | **≈ $215–265** |

Plus hand-work parts bought separately: Amphenol USB-C ~$2, header
stock ~$3, buzzer ~$1 (Digi-Key/Mouser/AliExpress).

## If anything on this sheet fails

The two **STOP** conditions (via-covering unavailable; U1/U2 stock zero)
go back to the log, not around it. Everything else — a surcharge, a
rotation query from JLCPCB's reviewer, a DFM note about the 0.15 mm
drills — is normal and answerable from this document.
