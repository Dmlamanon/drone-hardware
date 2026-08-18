---
type: order-sheet
status: READY-TO-ORDER-WITH-CONDITIONS
created: 2026-08-18
tags: [drone, hardware, pcb, fab, jlcpcb, order]
---

# ORDER SHEET — bench_board rev 2026-08-17c, JLCPCB, qty 5

Written for someone who has never ordered a PCB. Follow it top to
bottom. Two conditions are embedded and marked **STOP** — read them
before paying.

Generated from board commit `8b12e0c` (DRC verbatim: **53 violations /
2 unconnected / 93 parity** — see "Honest final state" below for why
that is orderable).

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
> pad); via barrels tangent to pads at U4 pad 11, C24 pad 1, C27 pad 2
> (0.6/0.3 and 0.3/0.15)."*
>
> These positions are measured from the board file
> (`scripts/` geometric audit, 2026-08-18), not inferred from commit
> messages.

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
5. Rows the assembler will NOT place (they show as "no part selected" —
   that is correct, click through it): **J1–J10 (all headers), J3
   (USB-C), BUZZER**. Details below.

## Step 4 — what arrives loose / what David solders

JLCPCB places all 52 SMD parts (12 Extended lines ⇒ 12 × $3 setup fees
are already in the estimate). The following are **hand work**:

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
93 schematic parity issues.**

- **The 2 unconnected items** are U1 pad 48 (a /3V3 supply pin) and U4
  pad 1 (the IMU's grounded CLKIN). In both cases a same-net track stub
  already ends **less than 1 mm from the pad** (0.71 mm and 0.95 mm
  gaps). Five automated attempts to close them regressed the board and
  were reverted by the guard. **The fix is a bench solder-bridge across
  each sub-millimetre gap after the boards arrive** — two joints, five
  minutes, done under magnification. The STM32 runs without pad 48
  bridged (its other VDD pins carry it) but is out of datasheet spec
  until bridged; bridge both before trusting the board.
- **The 53 violations:** 37 silkscreen cosmetics, 8 pre-existing
  clearance reports inside the J3 footprint's own pads, 4 known
  mounting-hole library mismatches, 2 copper-edge (J3's NPTH, 0.27 mm
  against our 0.3 mm rule — JLCPCB's own floor is 0.2 mm, so it
  fabricates fine), 2 starved thermals (J9.1, J3.B1 — solder them with
  a bigger iron tip). None are shorts, crossings, or hole errors.
- **The 93 parity issues** are all metadata/no-net-by-design; itemized
  in `README.md` here.

## Step 6 — cost at qty 5 (estimate; the cart is the truth)

| line | est. USD |
|---|---|
| 4-layer PCB, 80×60, qty 5 | 15–25 |
| **Epoxy filled & capped vias (the mandatory option)** | 30–60 |
| SMT assembly setup + stencil | ~10 |
| 12 Extended-part setup fees | 36 |
| Parts, 5 boards (U4 MPU-6000 ≈$52 and U1 ≈$29 dominate) | ~110 |
| Shipping (economy) | 10–20 |
| **Total, 5 assembled boards** | **≈ $210–260** |

Plus hand-work parts bought separately: Amphenol USB-C ~$2, header
stock ~$3, buzzer ~$1 (Digi-Key/Mouser/AliExpress).

## If anything on this sheet fails

The two **STOP** conditions (via-covering unavailable; U1/U2 stock zero)
go back to the log, not around it. Everything else — a surcharge, a
rotation query from JLCPCB's reviewer, a DFM note about the 0.15 mm
drills — is normal and answerable from this document.
