# Buzzer annunciator — PA8, low-side switch

**2026-08-17, Batch F item 5.** First item off the expansion catalog. A $3
part that protects the whole vehicle: a quad that goes down in tall grass
is invisible from ten metres and silent, and the only thing that changes
that is a noise it makes by itself.

Firmware side: `engineering/drone-firmware/src/buzzer.h` (patterns,
priority) and `hal_buzzer_set()`. This document is the circuit.

---

## The circuit

```
                  5V_RX  ──┬──────────────┬─── J10.1  (BUZZER +)
                           │              │
                          C27           D2 (K)
                        10uF 16V       1N4148W
                          0805          SOD-123
                           │              │(A)
                          GND             ├─── J10.2  (BUZZER −)
                                          │
   PA8 ──[ R14 100R ]──┬── G   Q1 AO3400A │
                       │      SOT-23      │
                  [ R15 10k ]   D ────────┘
                       │        S
                      GND      GND
```

| Ref | Part | Package | Job |
|---|---|---|---|
| Q1 | **AO3400A** | SOT-23 | Low-side switch. 30 V, 5.7 A, R<sub>DS(on)</sub> ~28 mΩ at V<sub>GS</sub>=4.5 V and specified down to 2.5 V |
| R14 | 100 R | 0402 | Gate series — damps the gate ring, limits the MCU pin's peak current into C<sub>iss</sub> |
| R15 | 10 k | 0402 | Gate pull-down — holds the FET off while PA8 is a floating input (reset, boot, SWD halt) |
| D2 | **1N4148W** | SOD-123 | Flyback across the buzzer |
| C27 | 10 µF 16 V | 0805 | Local bulk at the connector |
| J10 | 2-pin 2.54 mm header | — | Buzzer connector, `BUZZER` |

### Why a MOSFET at all

An F4 GPIO is rated **25 mA absolute maximum**. A 12 mm magnetic buzzer
draws **30–90 mA**. Driving one from a bare pin is not marginal, it is
out of spec, and the failure is a damaged port rather than a quiet
buzzer. The AO3400A is deliberate overkill — at this current it is a
closed switch with a ~3 mV drop — and it costs the same as the parts that
would have been marginal. The 2N7002 that KiCad offers first is rated
115 mA continuous, which is *inside* the buzzer's range, not above it.

### Why a flyback diode when the buzzer might be piezo

D2 does nothing at all for a piezo (capacitive) buzzer, and saves the FET
for a magnetic (inductive) one. It costs two cents. Fitting it is what
makes the board **buzzer-type-independent** — the same reasoning the
frame requirement uses about material. Leaving it out would silently
restrict which $3 part you are allowed to plug in.

### Why the local bulk cap

The buzzer runs off `5V_RX`, the MT3608 boost rail that also feeds the
receiver and expansion pin 13. The measured budget in
`collision-avoidance-provisioning.md` is ~170 mA average against a 4 A
switch limit, so **average current is not the concern** — the concern is
that a buzzer is a *pulsed* load stepping 90 mA on and off next to the RC
receiver's supply. C27 puts that step on a local cap instead of on the
shared rail. During a lost-model tone the link is already gone so it
would not matter; during a low-battery chirp the link is live and it
would.

### Why PA8

PA8 was free, and it is **TIM1_CH1 (AF1)** — verified against the
STM32F405RGTx symbol's own pin data, not assumed. TIM1 is unused on this
board (DShot is on TIM4). So the pin works as a plain GPIO today and
leaves a passive buzzer with real tones available later **with no board
change**. Several plain GPIOs were also free; none of them would have
left that option open.

PA8 previously carried a no-connect flag in the schematic, which is why
ERC flagged it the moment the net was attached. The flag is removed.

---

## Layout

Placed in the gap between J5 (DShot header) and J6 (SWD header), the
bottom-centre of the board — deliberately clear of the three areas where
the outstanding routing work is (U1's fanout, U4's pads, J3's shield).

| Ref | Position (mm) | Rotation |
|---|---|---|
| R14 | 47.00, 51.00 | 0 |
| R15 | 47.00, 54.50 | 0 |
| Q1 | 51.00, 51.50 | 0 |
| D2 | 51.00, 54.80 | 0 |
| C27 | 49.35, 58.00 | 180 |
| J10 | 55.00, 58.00 | 90 |

### The mistake worth recording

The first placement put Q1 and C27 **on top of a 15.7 mm NRST track**
running diagonally from J6 pin 4 at (62.00, 54.62) to (50.91, 43.53).
DRC caught it as `shorting_items` between `/NRST` and `/BUZZER_SW`.

The region had been chosen by reading the component list and finding a
gap between J5 and J6 — and a component list says **nothing about routed
copper**. `check_placement_clearance` does not catch it either: it
classifies body, courtyard, keepout and silk overlap, not tracks.

The fix is a checker that reads the board file and measures every new pad
against every existing segment and via on the layers that pad occupies:
`scripts/padclear.py`. Two things it caught afterwards that would
otherwise have shipped:

- A `/BUZZER_SW` diagonal passing **0.011 mm** from J10's `/5V_RX` pad.
- A GND stitching via sited **outside the GND pour** — the pour stops at
  y≈58.0 near x=48, and a via at (48.0, 58.45) would have connected to
  nothing. This is the same class of error as the fanout-via blocker
  earlier in this project, and the same fix applies: **point-in-polygon
  against the actual `filled_polygon` geometry**, not against the zone
  outline and not by eye.

That checker had a bug of its own on first use — it applied KiCad's
rotation with the wrong sign, so J10's pad 2 was checked at x=52.46 when
it is really at x=57.54. A rotated footprint was therefore being
"verified" at mirrored coordinates. Corrected; the sign convention is
now stated in the file.

---

## What is routed and what is not

**Routed and verified** (`padclear.py`: every pad ≥ 0.20 mm from
other-net copper):

- `/BUZZER_GATE` — R14.2 → Q1.G, R15.1 → R14.2
- `/BUZZER_SW` — Q1.D → D2.A → J10.2 (routed as an L, not a diagonal,
  to clear J10's 5 V pad)
- `/5V_RX` local — D2.K → C27.1 → J10.1
- `/GND` local — R15.2 → Q1.S with a stitching via at (50.0625, 53.60),
  and C27.2 with a via at (47.80, 57.40). Both via sites verified inside
  the In1.Cu GND pour with ≥ 0.60 mm margin.

**Not routed, and this is the honest remaining list:**

1. **`/BUZZER_GPIO` — U1 pad 41 → R14.1.** ~20 mm across the board
   through the busiest area. This is real routing work, not a fanout
   stub, and it belongs with the other 13 outstanding items in
   `manual-fanout-guide-2026-08-17.md`.
2. **The `/5V_RX` feed.** The local cluster (D2/C27/J10) is tied together
   but not yet tied back to the boost rail at J7. Same category.

Until (1) is routed **the buzzer cannot be driven at all** — the pin is
allocated, the parts are placed, the local wiring is done, and the one
wire from the MCU is missing. Said plainly so nobody reads "buzzer added"
as "buzzer works".

---

## DRC, and a zone-fill warning that matters

Measured with `kicad-cli pcb drc --severity-all` (KiCad 10.0), which is
the authority here — see the note below about the SWIG backend.

| | baseline (HEAD) | after this item | delta |
|---|---|---|---|
| violations | 46 | 64 | +18 |
| unconnected | 13 | 15 | +2 |

The +2 unconnected are exactly the two items listed above. Of the +18
violations, **+12 are `clearance`/`hole_clearance` between the new pads
and the stored zone fill**, and they are all one thing:

> **The stored zone fill predates these six footprints and must be
> regenerated before Gerber export.** Open the board in KiCad and run
> Edit → Fill All Zones. The fill has no antipads for J10's two
> through-holes or the two new GND vias, which is precisely what those 12
> violations say.

The rest: +1 `copper_edge_clearance` is J3's USB-C shield (pre-existing
area, unrelated), +4 silk overlaps. Silkscreen overlap is this board's
norm rather than a new defect — the whole board has 75 reference-text
overlaps and every decoupling cluster is in that list.

### Do not use the MCP's `refill_zones`

It was tried. Measuring HEAD and the result the same way, **In1.Cu went
from 2 filled polygons to 19 and In2.Cu from 1 to 22** — the SWIG filler
shattered both planes into islands, and DRC then reported 41
`isolated_copper` and 17 `via_dangling`. That fill was discarded and the
known-good geometry restored from git.

A stale fill fails loudly (12 obvious DRC errors that force a refill). A
fragmented fill fails quietly and would ship. The loud one was chosen
deliberately.

### Two other things `sync_schematic_to_board` did

Both found by comparing against git, both repaired:

1. **It stripped the leading `/` from every net name** — 860 references.
   This board's netclass patterns are `/VBAT_4S`, `/3V3`, `/5V_RX`,
   `/GND`, `/SW_NODE`, `/BOOST_SW`, so unprefixed names match **nothing**
   and every power net silently falls back to the Default netclass. This
   is the second time a net rename has quietly disabled the Power
   netclass on this board. Prefixes restored.
2. A `delete_trace` call with both `net` and `position` set **ignored the
   position and bulk-deleted all 14 `/5V_RX` traces.** The 13 original
   ones were restored from `HEAD`. If you only want one segment gone,
   pass `position` alone.

---

## Related

- [[stm32f405-pin-assignment]] — PA8 row
- [[manual-fanout-guide-2026-08-17]] — where the two unrouted nets belong
- [[collision-avoidance-provisioning]] — the 5 V rail budget C27 sits on
- [[extended-part-audit-2026-08-17]] — Q1/D2 are Extended parts, $3 setup each
