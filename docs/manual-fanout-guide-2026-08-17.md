---
type: guide
status: action-required
created: 2026-08-17
updated: 2026-08-17
tags: [stevie, hardware, pcb, manual-rework]
---

# Manual PCB rework guide — the two jobs a script cannot do

**Estimated time: 1–2 hours in the KiCad PCB editor.** Everything else on
the board is done.

> [!warning] This document was substantially wrong and has been rewritten
> The first version claimed the 15 unconnected pins were **blocked
> behind** fixing the inner layers, on the strength of a fanout via that
> "landed on a 5.5 × 0.8 mm isolated island of 3V3 copper."
>
> **That evidence was an artifact of my own probe.** The via was placed
> at (27.90, 26.25), which is **inside the In1.Cu GND pour and outside
> the In2.Cu 3V3 pour** — a 3V3 via dropped into the middle of the ground
> plane, where 3V3 copper does not reach. The zone filler then built a
> small 3V3 puddle around the via itself, and I read that puddle as
> evidence of a shattered plane. With the via removed, **In2.Cu is a
> single filled polygon.** There is no island.
>
> An independent review caught it. The corrected position is below: the
> two jobs are **largely independent**, and six of the fourteen pads can
> be fixed today with no inner-layer work at all.

---

## What the board actually shows

Measured from `bench_board.kicad_pcb` directly, at the current revision:

| Layer | Filled polygons | Coverage of the 2–78 × 2–58 pour area |
|---|---|---|
| **In1.Cu** (GND) | 2 — main pour **+ a 1.36 × 1.17 mm sliver** at (70.33, 26.12) | **76.7 %** |
| **In2.Cu** (3V3) | **1** — main pour only | **73.0 %** |

So the pours are **connected, not fragmented**. What they do have is
**large voids**, notably under U1: the point (40, 30) is uncovered on
both layers. That is a real signal-integrity problem and it is worth
fixing — but it is a *coverage* problem, not a *fragmentation* one, and
it does not block via work.

### Which pads can be fixed today

Plane copper directly beneath each unconnected pad, on the layer that
matters for its net:

| Pad | Net | Plane | Copper underneath? |
|---|---|---|---|
| U1.13, U1.19, U1.32 | /3V3 | In2.Cu | **YES** |
| U1.18, U4.11, U4.18 | /GND | In1.Cu | **YES** |
| U1.1, U1.48, U1.64, U4.13 | /3V3 | In2.Cu | no |
| U1.12, U1.63, U4.1, C17.2 | /GND | In1.Cu | no |

**Six of fourteen can take a fanout via right now.** The other eight sit
over a void and need either the plane extended (job A) or a short trace
to somewhere the plane does reach.

**Note on pad names:** U1 pad 1 is **VBAT** and pad 13 is **VDDA**, not
VDD — the four VDD pins are 19, 32, 48 and 64. All are tied to /3V3 on
this board, so the net is right, but get the names right when working
pad-by-pad.

---

## Ordering — the honest version

The two jobs are **largely independent**. Do them in whichever order
suits, with one caveat:

1. **Job B on the six covered pads can be done immediately** and will
   reduce the unconnected count straight away.
2. **Job A (inner layers) will move copper**, so doing it first may make
   some of the remaining eight pads trivially fixable — and will
   certainly change where their vias should go.
3. So: **do the six now if you want quick progress; do job A before
   attacking the other eight.**

The previous version of this document mandated a 1–2 hour irreversible
operation (delete 214 segments, hand re-route) *before* any via work.
That was not justified.

---

## Job A — get the signals off the inner layers

**Goal:** In1.Cu a solid GND plane and In2.Cu a solid 3V3 plane, with all
signal routing on F.Cu and B.Cu.

**This is worth doing on its own merits**, independent of the unconnected
pins:

- **118 segments on In1.Cu and 96 on In2.Cu** slice the reference planes.
  Return current detours around the slots, which is the standard
  mechanism for EMI and ground bounce.
- **`SW_NODE`, the highest dV/dt node on the board, is routed inside the
  3V3 pour.** That is the single worst case here.
- Fixing it is what closes the voids, which is what makes the remaining
  eight pads straightforward.

**Why it was not done automatically.** Two attempts, both recorded:

- Freerouting v2.3.0 logs `Layer 'In1.Cu' has been automatically
  configured as a dedicated power plane` and then **routes signals on it
  anyway.** The log line is not a guarantee.
- The DSN was hand-edited to declare both inner layers `(type power)` —
  the Specctra mechanism for reserving a layer — and Freerouting was run
  directly on it. It **hung**: 16 minutes, flat memory, no output, killed.

**Procedure:**

1. **Edit → Design Rules → Custom Rules**, add a keepout so routing
   cannot re-enter the planes:

   ```
   (rule "no signals on inner planes"
      (constraint disallow track via)
      (condition "A.Layer == 'In1.Cu' || A.Layer == 'In2.Cu'"))
   ```

2. **Select → Filter**: tracks only, layers In1.Cu + In2.Cu. Delete
   (214 segments).
3. **Interactive router**, F.Cu and B.Cu only. **B.Cu carries only 19
   segments** — there is a nearly empty layer to move the traffic onto.
   This is the main reason the job is tractable.
4. Refill zones.

**Nets that must not touch an inner layer**, in priority order:

| Net | Currently on | Why |
|---|---|---|
| `/SW_NODE` | In2.Cu, 4 seg | Highest dV/dt node; couples switching noise into the 3V3 plane |
| `/BOOST_SW` | In1.Cu, 2 seg | Same, for the 5 V boost |
| `/VBAT_4S` | In1 5, In2 4 | High current, splitting *both* planes |
| `/HSE_IN`, `/HSE_OUT` | In1 5, In2 5 | Crystal; wants a quiet reference |
| `/VFB`, `/VFB_5V` | In1 3, In2 2 | High-impedance regulator feedback next to a switcher |
| `/COMP_NODE`, `/COMP_RC` | In2.Cu 2 seg | Loop compensation |
| `/SS_NODE` | In1.Cu 2 seg | Soft-start timing |

### Verifying job A

```bash
cd engineering/drone-hardware/bench_board
grep -A6 '^\t(segment' bench_board.kicad_pcb | grep -o '(layer "[^"]*"' | sort | uniq -c
```

Target: **zero** for In1.Cu and In2.Cu. Current:

```
     19 (layer "B.Cu"
    310 (layer "F.Cu"
    118 (layer "In1.Cu")    <- must become 0
     96 (layer "In2.Cu")    <- must become 0
```

**Do not use "each pour is one polygon" as the acceptance test.** In2.Cu
already satisfies that today, so it cannot detect the condition. Use the
segment count above, and check coverage under U1 visually.

---

## Job B — the 15 unconnected items

KiCad reports **15 unconnected *items*** — ratsnest edges, not pads. They
span **14 distinct pads** plus J3, because several pads appear in more
than one edge. Counting pads and counting items gives different numbers;
both are below so they can be reconciled.

**Start with the six that have plane copper underneath** (table above):
U1.13, U1.19, U1.32, U1.18, U4.11, U4.18.

**J3's four (A1, A12, B1, B12) are different.** B1 and B12 are
**through-hole** shield pads whose barrels already pass through both
inner layers. They report unconnected because the GND pour does not reach
them — job A fixes them, not a via.

### Technique

- Via 0.6 mm / 0.3 mm drill (board default), just outside the pad row,
  short 0.2 mm stub on F.Cu.
- **Check the plane actually covers the via location before placing it.**
  That is the mistake this document originally enshrined. In the editor:
  switch to the inner layer and look, or use the coverage script in the
  batch scratch notes.
- **Refill zones after each via** and re-check — otherwise the ratsnest
  lies to you.
- **Do not batch.** Two scripted attempts in an earlier batch turned 43
  violations into 235 and then 387, because a geometric clearance model
  that ignores zone fills and drill-to-hole spacing is not a substitute
  for KiCad's own DRC.

---

## Definition of done

```bash
KC="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
"$KC" pcb drc --format json --output drc.json --severity-all \
      --schematic-parity bench_board.kicad_pcb
```

- **Unconnected items: 0.** Non-negotiable before ordering.
- **In1.Cu / In2.Cu segment count: 0.**
- Violations: expect the residual to be **silkscreen (30) plus J3's
  footprint-internal clearance (8) and edge clearance (2), plus 4
  mounting-hole library mismatches and 2 starved thermals**. One of those
  thermals is `Zone [/3V3] on In2.Cu` ↔ `PTH pad 1 [/3V3] of J9` — a real
  single-spoke connection on a power pin, worth widening while you are in
  there.
- Parity: 88, of which the 25 remaining `net_conflict` entries are all
  KiCad auto-nets for deliberately unconnected MCU pins
  (`unconnected-(U1-PC13-Pad2)`), which are correct and should stay.
