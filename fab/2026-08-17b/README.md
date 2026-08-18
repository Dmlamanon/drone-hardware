---
type: fab-package
status: SUPERSEDED
created: 2026-08-17
tags: [drone, hardware, pcb, fab]
---

# Fab package — bench_board, 2026-08-17**b**

> [!warning] SUPERSEDED 2026-08-18 by `fab/2026-08-17c/` — DO NOT ORDER FROM THIS FOLDER
> 17c closes 11 of the 13 unconnected items, resolves C1/C23/J3, and adds
> the mandatory filled-and-capped via requirement. Use `fab/2026-08-17c/ORDER-SHEET.md`.

**Supersedes `fab/2026-08-17/`**, which predated the mounting-pattern
restoration, the buzzer, and the zone refill, and which is now marked
DO-NOT-ORDER in place.

Regenerated from the board at commit `5d17ea9` (batch 4, after item 3).

---

## Is it ready to order? **No — and one reason is a decision, not a defect**

| gate | state |
|---|---|
| Schematic ERC | **0 errors, 0 warnings** |
| Board DRC | **54 violations** — see the breakdown |
| Unconnected | **13** — all supply pins and the USB-C shield |
| All components present in the CPL | **yes**, verified by diff |
| Copper planes coherent | **yes**, 2 and 1 filled polygons |

**The blocker is the 13 unconnected items.** Every one is on `/3V3` or
`/GND`, and between them they span **15 pads: 8 on U1 (MCU), 3 on U4
(IMU), 4 on J3's USB-C shield**. **An STM32 whose VDD pins are not
connected does not run**, so this cannot be ordered as-is regardless of
how good the rest looks.

(Two of the thirteen are J3 shield-to-shield and touch no chip; they are
still real, and they are still unrouted.)

`docs/manual-fanout-guide-2026-08-17.md` has the measured position: at
0.5 mm pin pitch there is **no legal fanout site** for any of them, so the
fix is to move the neighbouring copper in the interactive router (a few
minutes per pin), or to pay for via-in-pad as a fab option. That is
human work and it is the last thing standing between this and an order.

---

## What changed since `fab/2026-08-17/`

| | old | new |
|---|---|---|
| CPL rows (parts to place) | 55 | **61** |
| DRC violations | 46 | **54** |
| Unconnected | 15 | **13** |
| Parity issues | 88 | **93** |
| In1.Cu `/GND` fill | 2 polygons | 2 polygons |
| In2.Cu `/3V3` fill | 1 polygon | 1 polygon |

### The six components the old package was missing

Verified present by diffing the CPL against the board's own footprint
list, not by looking:

| ref | part | job |
|---|---|---|
| Q1 | AO3400A | buzzer low-side switch |
| R14 | 100 R | gate series |
| R15 | 10 k | gate pull-down |
| D2 | 1N4148W | flyback |
| C27 | 10 µF | local bulk |
| J10 | 2-pin header | buzzer connector |

`cpl_top.csv` holds **61 rows against 61 placeable components — nothing
missing, nothing extra.** The four mounting holes are deliberately
excluded: they are NPTH and telling an assembler to place a hole is how
you get a support ticket.

### The mounting pattern is now the 30.5 mm standard

The four holes are at (24.75, 14.75), (55.25, 14.75), (24.75, 45.25) and
(55.25, 45.25) — exactly 30.5 × 30.5 mm, centred on the board.
`scripts/check_fc_pattern.py` asserts that against the frame's exported
DXF and passes.

### The copper was refilled, correctly

With KiCad's own `ZONE_FILLER` through headless `pcbnew`, **not** the MCP
refill that shattered the planes last batch. Both pours came out with the
same polygon count and the same coverage as the git-stored copper. That
refill is what took DRC from 82 down to 54.

---

## DRC state — verbatim

```
Found 54 violations
Found 13 unconnected items
Found 93 schematic parity issues
```

### The 54, broken down honestly

| type | n | is it a problem? |
|---|---|---|
| `silk_overlap` | 17 | **No.** Reference text overlapping on a dense 80 × 60 board. Board-wide norm; every decoupling cluster is in this list. |
| `silk_over_copper` | 19 | **No.** Same. |
| `silk_edge_clearance` | 1 | **No.** |
| `clearance` | 8 | **Pre-existing, J3 only.** Four pairs of the USB-C connector's own no-net pads against its GND pads, reported twice each. Unchanged since before this batch. |
| `lib_footprint_mismatch` | 4 | **No.** The four mounting holes differ from the library copy. |
| `copper_edge_clearance` | 3 | **Flagged.** J3's NPTH pad against its own GND pads, 0.27–0.33 mm against a 0.5 mm rule. Pre-existing, on the USB-C footprint. Worth a look before a second revision. |
| `starved_thermal` | 2 | **Flagged.** J9 pin 1 (`/3V3`) and J3 pad B1 (`/GND`) get fewer than the required 2 thermal spokes. Solderable, but they will run cool and be slow to heat — mention it to the assembler or widen the spokes. |

**Zero `shorting_items`, zero `tracks_crossing`, zero `solder_mask_bridge`,
zero `hole_clearance`, zero `courtyards_overlap`.**

### The 93 parity issues are all benign, and here is why each is

| type | n | explanation |
|---|---|---|
| `footprint_symbol_field_mismatch` | 61 | Metadata only — `Description` and `Voltage` fields empty on the board side, populated in the schematic. No electrical meaning. |
| `net_conflict` | 24 | KiCad auto-nets for **deliberately unconnected MCU pins**: PC13-15, PA1, PA2, PA3, PC5, PB0-B2, PB12, PC6-C9, PA15, PC12, PD2, PB3-B5, plus U4's AUX I²C pair and U6's NC pin. All correct. |
| `missing_footprint` | 4 | The four `PWR_FLAG` symbols, which correctly have no footprint. |
| `extra_footprint` | 4 | The four mounting holes, which correctly have no schematic symbol. |

> [!note] PA1 and PA3 appear in that unconnected list on purpose
> The firmware allocates **PA1 to GPS_RX** and **PA3 to ESC_TELEM_RX**,
> and both drivers are written and interrupt-driven. Neither pin has a net
> on this board — there is no GPS connector and the ESC telemetry line is
> not brought out. So `hal_gps_read()` reports no fix and
> `esc_telem_count` stays 0 on real hardware. That is the honest state,
> not an oversight, and it is recorded in
> `docs/stm32f405-pin-assignment.md`.
>
> **PA8, the buzzer pin, is NOT in that list** — it is properly connected.

---

## Checklist to order

1. [ ] **Fix the 13 unconnected items.** This is the blocker. See
       `docs/manual-fanout-guide-2026-08-17.md`; budget a few minutes per
       pin in the interactive router, or choose via-in-pad instead.
2. [ ] Re-run `scripts/refill_zones.py` after any copper change, and check
       it still reports 2 and 1 filled polygons.
3. [ ] Re-run DRC and confirm unconnected is **0**.
4. [ ] Re-export this package (the commands are in the batch log).
5. [ ] Decide the **MPU-6000** question — it is 47 % of the component cost
       and it is bottleneck #1 in the final report.
6. [ ] Resolve the `UNRESOLVED-*` rows in `bom_jlcpcb.csv`, in particular
       **C1**, whose specification is *capacitance at 16.8 V bias*, not a
       nameplate voltage. Read the vendor's C-vs-Vdc curve.
7. [ ] Check `copper_edge_clearance` and `starved_thermal` on J3/J9 above.
8. [ ] Build **5, not 1** — ≈$32/board at qty 5 against ≈$60 at qty 1.

---

## Files

| file | what |
|---|---|
| `gerbers/` | 11 layers + PTH/NPTH Excellon drills + map + job file |
| `cpl_top.csv` | 61 placeable parts, mounting holes excluded |
| `cpl_bottom.csv` | empty — nothing is on the back |
| `bom_jlcpcb.csv` | JLCPCB-format BOM, 43 rows, with sourcing notes |
| `bom_from_schematic.csv` | grouped BOM straight from the schematic |
| `drc.json` | the DRC + parity run quoted above |
