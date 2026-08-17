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
> two jobs are **largely independent**. Of the six pads that looked
> immediately fixable, **two were placed this batch** and the other four
> turned out to need the UI as well — because plane coverage under the
> PAD does not imply a feasible location for the VIA beside it.

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

### Which pads can be fixed today — and what a script could actually reach

**Two of the six were placed this batch. Unconnected went 15 → 13.**

An earlier version of this section said "six of fourteen pads have plane
copper underneath, so they can take a fanout via today." That was true of
the **pad** and not of the **via**. A via has to go *beside* the pad, and
beside these pads either the plane is voided or the F.Cu fanout ring is
already congested. Measured, searching 168–396 candidate positions per
pad out to a 5 mm stub at 0.2 mm clearance:

| Pad | Net | Placed? | Why not |
|---|---|---|---|
| **U4.18** | /GND | **YES** — via (50.827, 20.384), 0.95 mm stub | — |
| **U1.32** | /3V3 | **YES** — via (42.393, 36.757), 3.80 mm stub | — |
| U1.13 | /3V3 | no | 101 of 168 near positions blocked by other nets' copper, 61 outside the 3V3 pour |
| U1.19 | /3V3 | no | 115 of 168 outside the 3V3 pour |
| U1.18 | /GND | no | 103 of 168 outside the GND pour |
| U4.11 | /GND | no | 124 of 168 blocked by other nets' copper |

**The U1.32 stub is 3.8 mm, which is long for a supply pin** — roughly
3 nH of added inductance on a VDD feed. It is better than unconnected and
it is flagged rather than hidden; a human in the editor should shorten it
if the plane can be extended nearby.

**Everything remaining needs the UI.** Not because scripting is
forbidden, but because the fix is *move existing copper*, which is a
judgement call about which trace yields — exactly what an interactive
router with live DRC is for and what a coordinate search is not.

> [!info] SUPERSEDED IN PART — 2026-08-17, batch 4 item 2
> The two buzzer items in the list below are **done**: `/BUZZER_GPIO` and
> the `/5V_RX` feed are routed, on B.Cu, and DRC-clean. Unconnected went
> **15 → 13**.
>
> The other thirteen were re-attempted with a checker that tests **both**
> halves of the rule — clear of other-net copper **and** inside the filled
> polygon of the plane carrying that pad's net — plus the fanout stub, not
> just the via. Result: **zero of the eleven MCU/IMU supply pads have a
> legal fanout site within 3 mm**, even at the smallest via this board's
> rules allow (0.50 mm / 0.30 mm drill, 0.10 mm annular).
>
> That is now a measured fact rather than an impression:
> `scripts/place_fanouts.py`. Run it and it prints, pad by pad, that there
> is nowhere to put the via.
>
> **Two earlier "successes" were the checker being wrong, not the board
> being routable.** A first version checked the stub against tracks but
> not against pads, and placed a via for U4.11 whose stub then clipped
> U4's own pad 10 — DRC caught it. With pads included, both placements
> disappear. The number to trust is zero.
>
> The conclusion an earlier version of this guide reached stands, and now
> has evidence: **the remaining work is to MOVE EXISTING COPPER**, which
> is a judgement about which trace yields, and that is what an interactive
> router with live DRC is for. See "What actually remains" at the bottom.

### The 15 items that remain, verbatim from DRC

**Updated 2026-08-17 after the buzzer went on the board (batch F item 5).**
Two items were added by that work and both are ordinary routing rather
than fanout:

```
Pad 41 [/BUZZER_GPIO] of U1  <-> Pad 1 [/BUZZER_GPIO] of R14
Track [/5V_RX] 4.7000 mm     <-> PTH pad 1 [/5V_RX] of J7
```

The first is the one wire that makes the buzzer work at all — until it
exists the annunciator is placed and inert. The second ties the buzzer's
local 5 V cluster (D2/C27/J10) back to the boost rail.

The original thirteen follow.



```
Pad 1 [/3V3] of U1        <-> Pad 64 [/3V3] of U1
Pad 13 [/3V3] of U1       <-> Pad 19 [/3V3] of U1
Pad 13 [/3V3] of U1       <-> Pad 1  [/3V3] of U1
Track [/3V3] 1.4016 mm    <-> Pad 19 [/3V3] of U1
Track [/3V3] 0.7128 mm    <-> Pad 48 [/3V3] of U1
Pad 13 [/3V3] of U4       <-> Pad 48 [/3V3] of U1
Track [/GND] 0.3526 mm    <-> Pad 63 [/GND] of U1
Pad 12 [/GND] of U1       <-> Track [/GND] 0.3526 mm
Pad 18 [/GND] of U1       <-> Pad 2 [/GND] of C17
Pad 1  [/GND] of U4       <-> Track [/GND] 0.9500 mm
Pad 11 [/GND] of U4       <-> Track [/GND] 0.9500 mm
Pad A1 [/GND] of J3       <-> PTH pad B12 [/GND] of J3
PTH pad B1 [/GND] of J3   <-> Pad A12 [/GND] of J3
```

That is **11 distinct pads** (U1: 1, 12, 13, 18, 19, 48, 63, 64; U4: 1,
11, 13) plus J3's four shield pads, spread across 13 ratsnest edges --
plus the two buzzer items above, for 15 in total.

**Do them in this order:**

1. **J3's four (A1, A12, B1, B12).** These are *not* fanout misses — B1
   and B12 are through-hole and their barrels already cross both inner
   layers. They report unconnected because the GND pour does not reach
   them. **Job A fixes these for free**, so do the inner-layer work
   first and re-check before touching them.
2. **U1's four VDD pins (19, 32, 48, 64) and VBAT (1) / VDDA (13).**
   32 is done. The rest want the 3V3 pour extended under the MCU, which
   is the same work as job A.
3. **The GND pins** (U1 12, 18, 63; U4 1, 11) — same story on In1.Cu.
4. **U4 pad 13 (`/3V3`).** Called out separately because it was in the
   pad list and the verbatim DRC block above but in **none** of the three
   ordered steps — step 2 was U1-only and step 3 is GND-only — so anyone
   working this list top-down would have skipped it silently.

**Get the pad names right when working pad-by-pad:** on an LQFP-64
STM32F405, **pad 1 is VBAT** and **pad 13 is VDDA**; the four VDD pins
are **19, 32, 48, 64**. All are tied to /3V3 on this board so the net is
correct, but they are not interchangeable functionally.

---

## Ordering — the honest version

The two jobs are **largely independent**. Do them in whichever order
suits, with one caveat:

1. **The scriptable via work is done** — two placed, unconnected 15 → 13.
   Nothing further can be sited without moving existing copper.
2. **Job A (inner layers) comes next**, and it is now the gating item.
   It extends the pours, which is precisely what the remaining eleven
   pads need, and it fixes J3's four through-hole shield pads for free.
3. **Then finish job B in the UI**, re-checking DRC first — several of
   the remaining edges should disappear once the pours are whole.

The first version of this document mandated a 1–2 hour irreversible
operation *before* any via work, on evidence that turned out to be an
artifact. The corrected ordering above is job-A-first for a different
and real reason: it is what unblocks the rest, not a precondition
invented from a bad measurement.

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

### Partial progress made 2026-08-17 (batch 3) — and what it cost

A per-net attempt was made on the six EMI-critical nets, deleting their
routing entirely and letting Freerouting re-route **only those nets**
against the rest of the board as fixed pre-routed wiring. It works —
Freerouting reported "78 already connected" and touched only the deleted
nets — and it helped, partially:

| Net | Inner segments before | After | F.Cu now |
|---|---:|---:|---:|
| **/HSE_OUT** | 5 | **0 — CLEAN** | 12 |
| /HSE_IN | 5 | 4 | 8 |
| /SW_NODE | 4 | 4 | 4 |
| /VBAT_4S | 9 | 5 | 9 |
| /VFB | 3 | 3 | 5 |
| /VFB_5V | 2 | 2 | 4 |
| **total** | **28** | **18 (−36 %)** | |

DRC unchanged at 46 / 13 / 88 — no regression, no rules touched.

**Why it did not go further, and what that says about the fix.** Before
the Freerouting attempt, a direct reroute of `/SW_NODE` was tried by
hand: deleting its four In2.Cu segments disconnects U2 pad 3 (the switch
pin) from the L1/C3 chain, and **no direct or single-bend path exists on
either F.Cu or B.Cu** at 0.2 mm clearance. The buck area is congested —
U2, L1, C1 (now a 1210), C2, R1, R11, C23, C24 all crowd it.

**That points at placement, not routing.** In a buck converter the switch
node should be a short, fat, direct connection from the regulator's SW
pin to the inductor. Here it takes a long dogleg through
(17.85, 38.999) and still needs inner-layer hops. **The real fix is to
move L1 adjacent to U2**, which is a placement change and out of scope
for a rerouting pass. Worth doing before this board is taken seriously
as a power design.

### The other 186 segments — counted, and deliberately left

37 non-target nets still use the inner layers (114 on In1.Cu, 90 on
In2.Cu, of which 18 are the target nets above). They are **left in
place**, per the cost-benefit judgement the task allows:

- They are ordinary signals — `/CRSF_RX` (19), `/M1` (8), `/SPI1_MOSI`
  (8), `/USB_DM` (7), the EXP_* bus. Slicing a reference plane with them
  is untidy and does raise EMI, but none carries the dV/dt of `SW_NODE`
  or the impedance sensitivity of the feedback nets.
- Clearing all of them needs the same interactive-router session as job
  A, and doing it piecemeal by script has now been shown to plateau.
- **B.Cu carries only 19 segments.** There is an almost entirely free
  layer to move this traffic onto, which is why the job is tractable for
  a human and why it is worth doing in one pass rather than in fragments.

### Partial progress made 2026-08-17 (batch 3) — and what it cost

A per-net attempt was made on the six EMI-critical nets, deleting their
routing entirely and letting Freerouting re-route **only those nets**
against the rest of the board as fixed pre-routed wiring. It works —
Freerouting reported "78 already connected" and touched only the deleted
nets — and it helped, partially:

| Net | Inner segments before | After | F.Cu now |
|---|---:|---:|---:|
| **/HSE_OUT** | 5 | **0 — CLEAN** | 12 |
| /HSE_IN | 5 | 4 | 8 |
| /SW_NODE | 4 | 4 | 4 |
| /VBAT_4S | 9 | 5 | 9 |
| /VFB | 3 | 3 | 5 |
| /VFB_5V | 2 | 2 | 4 |
| **total** | **28** | **18 (−36 %)** | |

DRC unchanged at 46 / 13 / 88 — no regression, no rules touched.

**Why it did not go further, and what that says about the fix.** Before
the Freerouting attempt, a direct reroute of `/SW_NODE` was tried by
hand: deleting its four In2.Cu segments disconnects U2 pad 3 (the switch
pin) from the L1/C3 chain, and **no direct or single-bend path exists on
either F.Cu or B.Cu** at 0.2 mm clearance. The buck area is congested —
U2, L1, C1 (now a 1210), C2, R1, R11, C23, C24 all crowd it.

**That points at placement, not routing.** In a buck converter the switch
node should be a short, fat, direct connection from the regulator's SW
pin to the inductor. Here it takes a long dogleg through
(17.85, 38.999) and still needs inner-layer hops. **The real fix is to
move L1 adjacent to U2**, which is a placement change and out of scope
for a rerouting pass. Worth doing before this board is taken seriously
as a power design.

### The other 186 segments — counted, and deliberately left

37 non-target nets still use the inner layers (114 on In1.Cu, 90 on
In2.Cu, of which 18 are the target nets above). They are **left in
place**, per the cost-benefit judgement the task allows:

- They are ordinary signals — `/CRSF_RX` (19), `/M1` (8), `/SPI1_MOSI`
  (8), `/USB_DM` (7), the EXP_* bus. Slicing a reference plane with them
  is untidy and does raise EMI, but none carries the dV/dt of `SW_NODE`
  or the impedance sensitivity of the feedback nets.
- Clearing all of them needs the same interactive-router session as job
  A, and doing it piecemeal by script has now been shown to plateau.
- **B.Cu carries only 19 segments.** There is an almost entirely free
  layer to move this traffic onto, which is why the job is tractable for
  a human and why it is worth doing in one pass rather than in fragments.

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

---

## What actually remains — 2026-08-17, batch 4

**13 unconnected items, all of them supply pins or the USB-C shield.**

```
Pad 1  [/3V3] of U1  <-> Pad 13 [/3V3] of U1
Pad 13 [/3V3] of U1  <-> Pad 19 [/3V3] of U1
Pad 64 [/3V3] of U1  <-> Pad 1  [/3V3] of U1
Pad 19 [/3V3] of U1  <-> Track [/3V3] 1.4016 mm
Pad 48 [/3V3] of U1  <-> Pad 13 [/3V3] of U4
Track [/3V3] 0.7128 mm <-> Pad 48 [/3V3] of U1
Pad 12 [/GND] of U1  <-> Pad 2 [/GND] of R4
Pad 2  [/GND] of R4  <-> Pad 63 [/GND] of U1
Pad 18 [/GND] of U1  <-> Pad 2 [/GND] of C17
Pad 11 [/GND] of U4  <-> Track [/GND] 0.9500 mm
Track [/GND] 0.9500 mm <-> Pad 1 [/GND] of U4
Pad A12 [/GND] of J3 <-> PTH pad B1  [/GND] of J3
PTH pad B12 [/GND] of J3 <-> Pad A1 [/GND] of J3
```

### Why a script cannot finish these

At **0.5 mm pin pitch** the escape channel between adjacent LQFP-64 pads
is smaller than the smallest legal via this board allows. So a fanout via
cannot sit *between* pins; it has to sit *outside* the pin row, and the
stub reaching it has to cross whatever is already routed there — which,
on the supply pins, is the fanout of the neighbouring signal pins.

Measured, at 0.50 mm via / 0.30 mm drill / 0.20 mm stub / 0.20 mm
clearance, searching every 0.05 mm out to 3 mm: **no site satisfies all
four constraints for any of the eleven pads.**

### The three ways a human can actually fix them, in order of effort

1. ~~**J3's four shield pads (A1, A12, B1, B12) are free** — refilling
   the zones connects them.~~ **TESTED 2026-08-17 AND FALSE.** The zones
   have now been refilled with KiCad's own filler and **all four are still
   unconnected**. This claim had been carried forward from an earlier
   batch and never checked; it is checked now, and it was wrong.

   They still are not ordinary fanout misses — B1 and B12 are
   through-hole and their barrels do cross both inner layers — but the GND
   pour does not reach them even after a correct refill, so they need the
   same treatment as the rest: move copper, or extend the pour boundary in
   the editor.
2. **Move the neighbouring traces.** For each supply pin, drag the one or
   two signal traces that own the escape channel a fraction of a
   millimetre and the via fits. This is the judgement call — which trace
   yields — and it is a few minutes each in the interactive router.
3. **Via-in-pad**, if you would rather not move anything. It is the
   standard answer at this pitch and it is a fab option (filled and
   capped vias), not a layout change. It costs money per board rather
   than time per pin.

### Get the pin names right

On an LQFP-64 STM32F405, **pad 1 is VBAT** and **pad 13 is VDDA**; the
four VDD pins are **19, 32, 48, 64**. Pad 32 is already connected. All are
on `/3V3` so the net is right, but they are not interchangeable
functionally.
