---
type: guide
status: action-required
created: 2026-08-17
tags: [stevie, hardware, pcb, manual-rework]
---

# Manual PCB rework guide — the two blockers a script cannot fix

**Estimated time: 1–2 hours in the KiCad PCB editor. This is a David
task**, or a task for whoever next has KiCad open. Everything else on
the board is done.

Read the ordering section first — **the two jobs are not independent, and
doing them in the wrong order wastes the effort.**

---

## The finding that changes the plan

The previous batch listed "18 unconnected pins, add fanout vias" as a
straightforward hour of work. It is not, and here is the proof.

A fanout via was placed at **(27.90, 26.25)** on net `3V3`, with a stub
to U1 pad 1, and the zones were refilled. DRC still reported the pad as
unconnected. Extracting the actual filled copper from the board file
shows why:

| Zone layer | Filled polygons | Extent |
|---|---|---|
| In1.Cu (GND) | 2 | main plane 2,2–78,58 **+ a 1.4 × 1.2 mm island** |
| In2.Cu (3V3) | 2 | main plane 2,2–78,58 **+ a 5.5 × 0.8 mm island** |

The via landed inside the **5.5 × 0.8 mm island** — a sliver of 3V3
copper cut off from the main pour — not the main plane. It connects to
nothing.

Sampling the planes directly confirms the cause: the point **(40, 30)**,
the middle of the board directly under the MCU, is **not covered by
filled copper on either inner layer.** The pours have been carved away
there by the **118 signal segments on In1.Cu and 96 on In2.Cu** that the
autorouter put through them.

**So: the unconnected pins are downstream of the inner-layer problem.
Adding vias cannot fix them while the planes are fragmented, because
there is often no intact plane under the pin to reach.**

---

## Ordering — do these in this sequence

1. **Fix the inner layers first** (job A below).
2. **Refill zones**, and confirm the two pours are each ONE polygon.
3. **Then** add fanout vias (job B). Most of them may become unnecessary
   once the planes are solid, because the router will have real planes
   to drop onto.

---

## Job A — get the signals off the inner layers

**Goal:** In1.Cu is a solid GND plane and In2.Cu a solid 3V3 plane, with
all signal routing on F.Cu and B.Cu.

**Why this was not done automatically.** Two attempts, both recorded:

- Freerouting v2.3.0 logs `Layer 'In1.Cu' has been automatically
  configured as a dedicated power plane` and then **routes signals on it
  anyway.** The log line is not a guarantee.
- The DSN was hand-edited to declare both inner layers `(type power)`,
  which is the Specctra mechanism for reserving a layer, and Freerouting
  was run directly on it. It **hung**: 16 minutes with completely flat
  memory and no output, and was killed. Constraining a 52-net board to
  two signal layers is a much harder problem and this version does not
  cope.

**The manual procedure:**

1. Open the PCB in KiCad. **Edit → Design Rules → Custom Rules**, and add
   a keepout so future routing cannot re-enter the planes:

   ```
   (rule "no signals on inner planes"
      (constraint disallow track via)
      (condition "A.Layer == 'In1.Cu' || A.Layer == 'In2.Cu'"))
   ```

   The MCP tooling has no keepout support, which is why this step is
   here rather than already applied.

2. **Select → Filter**: tracks only, layers In1.Cu + In2.Cu. Delete them
   (214 segments).
3. **Interactive router**, F.Cu and B.Cu only. **B.Cu is nearly empty —
   19 segments** — so there is a whole layer of space available. This is
   the main reason the job is tractable.
4. Refill zones. Verify each pour is a single polygon (Appearance panel →
   zone display, or re-run the check below).

**Nets that MUST NOT touch an inner layer**, listed because they are the
ones where plane-slicing does real electrical harm rather than just
looking untidy:

| Net | Currently on | Why it matters |
|---|---|---|
| `/SW_NODE` | In2.Cu, 4 seg | Highest dV/dt node on the board. Burying it inside the 3V3 plane couples switching noise directly into the supply. |
| `/BOOST_SW` | In1.Cu, 2 seg | Same, for the 5 V boost. |
| `/VBAT_4S` | In1.Cu 5 seg, In2.Cu 4 seg | High current, and it is splitting *both* planes. |
| `/HSE_IN`, `/HSE_OUT` | In1 5, In2 5 | Crystal. Wants a quiet local ground reference, which is exactly what a sliced plane is not. |
| `/VFB`, `/VFB_5V` | In1 3, In2 2 | Regulator feedback. High-impedance nodes next to a switcher. |
| `/COMP_NODE`, `/COMP_RC` | In2.Cu 2 seg | Loop compensation, same reasoning. |
| `/SS_NODE` | In1.Cu 2 seg | Soft-start timing. |

### Verifying job A

```bash
cd engineering/drone-hardware/bench_board
grep -A6 '^\t(segment' bench_board.kicad_pcb | grep -o '(layer "[^"]*"' | sort | uniq -c
```

**Target: zero lines for In1.Cu and In2.Cu.** Current state:

```
     19 (layer "B.Cu"
    310 (layer "F.Cu"
    118 (layer "In1.Cu")     <- must become 0
     96 (layer "In2.Cu")     <- must become 0
```

---

## Job B — the 15 unconnected pins

Do this **after** job A, and re-run DRC first: some of these will already
be gone.

The pins, with exact pad coordinates. All are surface pads that need a
via down to their plane.

### 3V3 (7 pads) — the critical ones, these are the MCU's supply pins

| Ref | Pad | X (mm) | Y (mm) | Note |
|---|---|---|---|---|
| U1 | 1 | 29.325 | 26.250 | VDD |
| U1 | 13 | — | — | VDD, left side |
| U1 | 19 | — | — | VDD, bottom |
| U1 | 32 | — | — | VDD, bottom |
| U1 | 48 | — | — | VDD, right |
| U1 | 64 | — | — | VDD, top |
| U4 | 13 | — | — | IMU supply |

Only pad 1's coordinate is given as measured; the rest are read straight
off the board in the editor by clicking the pad, and are deliberately not
transcribed here — a stale coordinate in a document is worse than no
coordinate, and job A will move things anyway.

**An STM32 with unconnected VDD pins does not run.** These are the
must-fix items.

### GND (8 pads)

U1 pads 12, 18, 63; U4 pads 1, 11, 18; C17 pad 2; and J3 pads A1, A12,
B1, B12.

**J3's are different and are NOT fanout misses:** B1 and B12 are
**through-hole** shield pads whose barrels already pass through both
inner layers. They report unconnected because the GND pour does not reach
them, not because they lack a via. Job A should fix them for free.

### Technique

- Via 0.6 mm / 0.3 mm drill (the board default), placed just outside the
  pad row, with a short 0.2 mm stub on F.Cu.
- **Refill zones after each via** and re-check, or the ratsnest will lie
  to you — this is exactly what made the first attempt look like it had
  failed.
- **Do not batch.** Two scripted attempts at batch placement in the
  previous batch turned 43 violations into 235 and then 387, because a
  geometric clearance model that ignores zone fills and drill-to-drill
  spacing is not a substitute for KiCad's own DRC.

---

## Definition of done

```bash
KC="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
"$KC" pcb drc --format json --output drc.json --severity-all \
      --schematic-parity bench_board.kicad_pcb
```

- **Unconnected items: 0.** Non-negotiable before ordering.
- **In1.Cu / In2.Cu segment count: 0.**
- Violations: the residual set should be silkscreen only (see the fab
  README for why the J3 clearance and mounting-hole entries are
  expected).
- Parity: 88 currently, and the 25 remaining `net_conflict` entries are
  all KiCad auto-nets for deliberately-unconnected MCU pins
  (`unconnected-(U1-PC13-Pad2)` and similar). Those are correct and
  should stay.
