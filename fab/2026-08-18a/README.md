---
type: fab-package
status: READY-TO-ORDER-WITH-CONDITIONS
created: 2026-08-18
tags: [drone, hardware, pcb, fab]
---

# Fab package — bench_board, 2026-08-18**a**

**Supersedes `fab/2026-08-17c/` — that revision carries an absolute-
maximum violation (TPS54336A EN pin at 16.8 V against a 6 V rating) and
must not be uploaded.** Also fixed here: the MPU-6000 charge-pump cap
(2.2 nF / 50 V / returned to GND per PS-MPU-6000A §7.3) and the crystal
load caps (33 pF for the manufacturer-confirmed 20 pF crystal).

Generated 2026-08-18 from board commit `e06a699` (batch 7).

**To order: follow `ORDER-SHEET.md` here.** New behaviour: the 3.3 V
rail implements pack UVLO — start 12.01 V typ (12.0–13.0 V across the
EN comparator's datasheet limits), stop 11.01 V typ (10.1–11.0 V
worst-case), ~1 V hysteresis (TI Figure-15 divider, R16 = 182k /
R17 = 20k; EN sits at 1.74 V at 16.8 V input, 2.58 V at the 6S corner,
2.62 V at worst-case tolerance — never above 2.7 V against the 6 V
abs-max). Not LiPo cell protection — see the order sheet's note.

## Gates

| gate | state |
|---|---|
| Schematic ERC | **0 violations** (re-run after every edit this batch) |
| Board DRC | **53 violations / 2 unconnected / 95 parity** (verbatim, `drc.json`) |
| CPL vs board | **PASS** — `python scripts/check_cpl.py` (default now points here): 63 placeable, 63 rows, same set |
| BOM | every assembly row carries an LCSC part; 13 Extended numbers |
| Guard | every board-touching commit carries a matching measured entry, hash-for-hash (reviewer-verified). Honest caveat: the item-1 commit's own entry is a FAIL (parity 93→95) followed by a re-baseline in the same commit — the +2 was verified to be exactly the two new footprints' empty-Description mismatches, argued in that commit's message rather than hidden |

## What changed since 17c

| | 17c | 18a |
|---|---|---|
| U2 EN | tied to VBAT_4S (16.8 V on a 6 V-abs-max pin) | **Figure-15 UVLO divider** — EN ≤ 2.58 V at every corner, pack UVLO 12.0/11.0 V |
| C20 (MPU-6000 CPOUT) | 100 nF / 16 V / returned to 3V3 | **2.2 nF / 50 V (C106861) / returned to GND** |
| C17/C18 | 10 pF (CL ≈ 8 pF vs 20 pF spec) | **33 pF (C1562, Basic)** — CL ≈ 19.5 pF |
| Components | 61 | **63** (R16/R17 added) |
| DRC | 53/2/93 | **53/2/95** (+2 = new parts' benign metadata-field parity) |
| U1.48 bench-jumper target | C20 pad 2 | **C21 pad 1** (C20 is GND now) |
| Via-in-pad list | U1×5, L1.1, +2 overlaps +1 near-tangent | **+ R16 pad 2** (EN via at pad edge) |

The 93 baseline parity issues are unchanged and itemized in
`fab/2026-08-17b/README.md`; the +2 are `footprint_symbol_field_mismatch`
on R16/R17, same class as the existing 61.

## Files

| file | what |
|---|---|
| `gerbers/` | 11 layers + PTH/NPTH Excellon + maps + job file |
| `cpl_top.csv` | 63 placeable parts; mounting holes excluded |
| `cpl_bottom.csv` | header only — nothing on the back |
| `bom_jlcpcb.csv` | 46 lines, 13 Extended part numbers |
| `bom_from_schematic.csv` | grouped BOM straight from the schematic |
| `drc.json` | the 53/2/95 run quoted above |
| `ORDER-SHEET.md` | the ordering procedure — start there |

## Reproducing

Same commands as `fab/2026-08-17/README.md` §"Reproducing these
outputs" with this folder as output. Always pass `--schematic-parity`.
