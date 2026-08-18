---
type: fab-package
status: SUPERSEDED
created: 2026-08-18
tags: [drone, hardware, pcb, fab]
---

# Fab package — bench_board, 2026-08-17**c**

> [!danger] SUPERSEDED 2026-08-18 by `fab/2026-08-18a/` — DO NOT ORDER FROM THIS FOLDER
> **Why, in one line: this revision wires the buck regulator's EN pin to
> 16.8 V against a 6 V absolute maximum** (found by the datasheet
> verification pass) — an abs-max violation, not a tidy-up. 18a fixes it
> with a pack-UVLO divider and also corrects the MPU-6000 charge-pump
> cap and the crystal load caps.

**Supersedes `fab/2026-08-17b/`** (which is marked superseded in place).
Regenerated 2026-08-18 from the board at commit `8b12e0c`, after batch 6
closed 11 of 13 unconnected pads and resolved all three BOM blockers.

**To order: follow `ORDER-SHEET.md` in this directory.** It contains the
exact options, the mandatory filled-and-capped via requirement, and the
two STOP conditions.

## Gates

| gate | state |
|---|---|
| Schematic ERC | **0 violations** (re-run 2026-08-18 after the C23 edit) |
| Board DRC | **53 violations / 2 unconnected / 93 parity** (verbatim, `drc.json`) |
| CPL vs board | **PASS** — `python scripts/check_cpl.py bench_board/bench_board.kicad_pcb fab/2026-08-17c` (the explicit fab-dir argument matters; the script's default now points here): 61 placeable, 61 rows, same set |
| BOM blockers | **0** — C1, C23, J3 resolved with evidence (see docs/) |
| Guard log | every committed board state has a matching PASS entry |

## What changed since 17b

| | 17b | 17c |
|---|---|---|
| Unconnected | 13 | **2** (bench wire jumpers, 3.9 mm and 7.4 mm — see order sheet) |
| DRC violations | 54 | **53** |
| C23 | 7.5 nF, unsourceable | **8.2 nF, C107032**, chosen by loop-gain study |
| C1 | example part EOL, curve unread | **C126612**, Murata bias curve read at 16.8 V |
| J3 | "verify pad compatibility" | measured: **no stocked substitute; hand-fit Amphenol** |
| Assembly BOM rows without an LCSC # | 8 | **0** (the 10 hand-work J-rows carry none by design, both revisions) |
| Via-in-pad | none | **U1×5, L1×1 in-pad; 2 edge-overlaps + 1 near-tangent — filled & capped mandatory** |

The 93 parity issues are unchanged from 17b and all benign:
61 metadata-field mismatches, 24 KiCad auto-nets for deliberately
unconnected MCU/IMU pins, 4 PWR_FLAGs without footprints, 4 mounting
holes without symbols. The full itemization is in
`fab/2026-08-17b/README.md` and still applies row-for-row.

## Files

| file | what |
|---|---|
| `gerbers/` | 11 layers + PTH/NPTH Excellon + maps + job file |
| `cpl_top.csv` | 61 placeable parts; mounting holes excluded |
| `cpl_bottom.csv` | header only — nothing on the back |
| `bom_jlcpcb.csv` | 43 lines, every assembly line carries an LCSC part |
| `bom_from_schematic.csv` | grouped BOM straight from the schematic (8.2 nF confirmed) |
| `drc.json` | the 53/2/93 run quoted above |
| `ORDER-SHEET.md` | the ordering procedure — start there |

## Reproducing

Same commands as `fab/2026-08-17/README.md` §"Reproducing these
outputs", with `2026-08-17c` as the output folder, plus
`--side back` pos export for `cpl_bottom.csv`. Always pass
`--schematic-parity` to DRC.
