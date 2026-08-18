---
type: verification
status: verified
created: 2026-08-18
tags: [drone, hardware, bom, usb-c, footprint]
---

# J3 USB-C receptacle — JLCPCB substitute search (order blocker, batch 2026-08-17c item 4)

The BOM note on J3 requires: *"Exact JLCPCB equivalent for this Amphenol
footprint not confirmed — verify pad compatibility before ordering
assembly."* This document is that verification. **Verdict: no
JLCPCB-stocked USB-C receptacle is pad-compatible. J3 is hand-fitted.**

## Method

`scripts/j3_footprint_compare.py` pulls each candidate's EasyEDA
footprint — the geometry JLCPCB assembly itself references — via the
public API and normalizes its pad table to the board footprint's frame
(A-row centre origin, +t toward the B-row, +a along the row). The
reference below is the **actual pad table extracted from
`bench_board.kicad_pcb`** (footprint
`USB_C_Receptacle_Amphenol_12401548E4-2A` at (74, 30) rot 90), not the
KiCad library copy.

Reference (board), normalized:

| feature | position | geometry |
|---|---|---|
| A-row | t=0, a=±0.25…±2.75 | 12 SMD 0.30×0.70, pitch 0.5, span 5.50 |
| B-row col 1 | t=1.310, a=±0.4, ±1.2, ±2.8 | PTH pad 0.65, drill 0.40 |
| B-row col 2 | t=2.010, a=±0.8, ±1.6, ±2.4 | PTH pad 0.65, drill 0.40 |
| shield near | t=1.910, a=±4.130 | oval pad 0.8×1.4, slot 0.5×1.1 |
| shield rear | t=7.860, a=±4.490 | oval pad 0.8×1.4, slot 0.5×1.1 |
| pegs | t=0.660, a=−3.600 / +3.600 | NPTH round 0.65 / slot 0.95×0.65 |

## Candidates measured (2026-08-18)

**Hybrid SMT-A + DIP-B family** — TYPE-C 24P QCHT C456013 (40k stock),
TYPE-C 24P QCHT 143 C5156604 (14.7k), HRO TYPE-C-31-M-04 C129018
(4.6k). Correct topology (12 SMD A-row span 5.50 + 12 staggered
0.40-drill B pins + shield slots), but a systematically different
standard:

- B-row columns at **t=1.21/1.91** vs the board's 1.31/2.01 — all 12
  pins 0.10 mm off in the same direction, more than the insertion
  clearance of a B pin in a 0.40 mm hole.
- Near shield legs at t=1.81–1.93 (C456013's need 0.6×1.2 slots — the
  board's are 0.5×1.1, legs do not insert).
- **Rear shield legs at t=6.20–6.32 vs the board's slots at t=7.860.**
  The shell is 1.55–1.66 mm shorter; the rear legs land on bare board
  with no hole. The part physically cannot seat flush. Disqualifying on
  its own, regardless of pin fit.

**Amphenol siblings stocked at JLCPCB** — 12401832E4#2A C464604 (4.5k),
12401610E4#2A C5119948 (4.2k). Same shell family — C5119948's four
shield slots match the board **exactly** (0.5×1.1 slots, a=±4.130/±4.490,
row spacing 5.950) — but both are the **dual-SMT** variant: the B row is
12 SMD feet in a straight 0.5-pitch row at t=1.70, not through-pins.
Those feet land across the board's open staggered 0.40 mm B-row holes
with only partial edge contact on the 0.65 annulars — joints would starve
into open barrels. C464604 additionally needs 0.7×1.3 shield slots.
Not assemblable on this footprint.

**Exact part** — Amphenol 12401548E4 (any suffix): zero hits in the
JLCPCB catalog (searched "12401548", "12401548E4").

## Consequence — what hand-fitting J3 costs

- The genuine **Amphenol 12401548E4#2A** is stocked at Digi-Key/Mouser
  (~US$1.5–2.5 single-qty). David solders it: the 12 B pins and 4 shield
  legs are through-hole (easy); the 12-pad 0.5 mm-pitch SMT A-row is the
  hard part — flux + drag soldering, or accept A-row unsoldered.
- **Function while J3 is unfitted or A-row-unfitted:** the board's USB
  port is dead or USB-2.0-only until fitted. In a USB-C receptacle the
  USB 2.0 function (power, CC resistors, D+/D−) rides on the B through
  pins plus the A-row's duplicated D+/D− — a hybrid receptacle carries
  VBUS/GND/CC/SBU on both rows' pins, so soldering only the through-hole
  B row plus shield yields a mechanically sound, USB-2.0-functional
  port; the A-row duplicates contacts for the flipped-plug orientation
  and full current rating. Practical floor: **solder B row + shield,
  port works; drag-solder the A row for full-spec contact redundancy.**
- JLCPCB assembly simply skips J3 (no fee, one less Extended part); it
  ships nothing — David orders the Amphenol part separately.

This closes the third of the three item-4 blockers. BOM row in
`fab/2026-08-17c` marks J3 `HAND-FIT (Amphenol 12401548E4#2A, Digi-Key/
Mouser)`.
