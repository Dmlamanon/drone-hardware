---
type: preflight
status: current
created: 2026-08-17
tags: [stevie, tooling]
---

# Tooling pre-flight — 2026-08-17 (batch 6: close the board for order)

## Confirmed working

| Tool | Version | Check |
|---|---|---|
| kicad-cli | **10.0.5** | `version` runs and reports — the guard in item 1 is built on it |
| KiCad headless Python | 10.0.5 pcbnew | imported through `kicad_safe`, asserts confirmed OFF |
| gcc / arm-none-eabi-gcc | 16.1.0 / 14.2.Rel1 | unchanged from batch 5 |
| FreeCAD | 1.1.3 | not on this batch's path (board work only) |

## The `wx.DisableAsserts()` preamble — verified executing, not just present

Every pcbnew-importing script in `scripts/` references `kicad_safe`
(12 of 12, checked by grep), and importing it through KiCad's own
interpreter confirms `_ASSERTS_OFF == True` at runtime. A blocking assert
dialog in an unattended batch is an unbounded hang, and it happened once
(batch 4, `PCB_VIA::GetWidth()`); this is the standing countermeasure.

The scripts this batch will actually drive — `refill_zones.py`,
`place_fanouts.py`, `why_no_fanout.py` — are all covered. Two new scripts
are planned: `board_guard.py` (kicad-cli subprocess only; no pcbnew, no
wx exposure) and whatever edits zone outlines. **If the zone editor
imports pcbnew, `kicad_safe` goes first — but the intended route is
textual edits to `bench_board.kicad_pcb` followed by `refill_zones.py`,
which keeps outline changes deterministic and diffable and stays inside
already-safe code for the pcbnew half.**

## Firmware baseline (this batch must not touch it)

As pushed at the end of batch 5 (`7c3a740`): **46 test binaries + the
decoder cross-check pass**, `cross`/`firmware`/`rc-verify`/`probe-railing`
pass. Item 6 re-runs the whole suite fresh; any delta is a red flag to be
explained, not absorbed.

## Standing constraints carried into this batch

- The MCP zone refill remains banned (it shattered both planes in batch
  3); `refill_zones.py` (pcbnew `ZONE_FILLER`) is the only refill path.
- The routing-attempt ban is **lifted for this batch only, by David**,
  under item 1's guard contract. If the attempt fails, the ban is
  restored in the report.
- Smallest legal fanout via under the **current** design rules: 0.50 mm
  dia / 0.30 mm drill (min_via_diameter 0.45 + min_annular 0.10 +
  min_through_hole 0.30). JLCPCB's published 4–6-layer capability is
  smaller; if that margin matters this batch, the rule change is its own
  guarded, documented step — never a silent edit.
