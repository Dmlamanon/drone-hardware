# Bench Board Power Path — Analysis, 2026-08-16

**This is NOT a SPICE simulation, despite being asked for one — tooling
was blocked, documented below rather than faked.** What follows instead
is a hand-calculation analysis against real datasheet parameters,
covering the same questions, clearly labeled as a different (and weaker)
method than actual circuit simulation would have been.

## Why SPICE didn't happen

Checked before attempting to fake a result:

1. **No `ngspice` executable anywhere on this machine.** Not on `PATH`,
   no winget package available. KiCad 10.0 bundles `bin/ngspice.dll` —
   but that's a library linked into Eeschema's own GUI "Simulate" tab
   (a wxWidgets dialog), not a standalone CLI tool, and no MCP tool
   exposes "run a SPICE simulation" — `export_netlist(format=Spice)` can
   *write* a SPICE netlist, but nothing in the current toolset can
   *execute* one.
2. **Neither IC on this board has a real SPICE model in KiCad's bundled
   libraries.** Checked directly: `grep -ic spice` against both
   `Regulator_Switching.kicad_sym` (TPS563201) and
   `Regulator_Linear.kicad_sym` (AMS1117-3.3) returns **0** in each —
   these are schematic-symbol-only definitions (pins + footprint), not
   behavioral models. Even with a working `ngspice`, simulating this
   exact schematic would need TI's real TPS563201 SPICE model and an
   AMS1117 model sourced and correctly attached first — a separate,
   nontrivial task on its own.

Both blockers together mean a genuine SPICE run wasn't a small gap to
paper over. Hand calculation against real datasheet numbers is a weaker
method (no transient/AC behavior, no parasitic-aware ripple prediction)
but still answers the actual engineering questions this was for.

## Datasheet parameters used (cited, not assumed)

**TPS563201** (TI product page, `ti.com/product/TPS563201`):
Vin 4.5-17V, Vout range 0.76-7V, switching frequency 580kHz (typical,
D-CAP2 adaptive on-time — pseudo-fixed, not a hard clock), **max duty
cycle 80%**, max output current 3A, quiescent current 400µA typical,
feedback accuracy ±2% @ 25°C.

**AMS1117-3.3** (Advanced Monolithic Systems datasheet, cross-checked via
LCSC/handsontec mirrors): dropout voltage **1.2V typical / 1.3V max @
1A**, quiescent current 5-11mA @ (Vin−Vout)=1.5V, thermal resistance
**15°C/W** (SOT-223 package — matches this schematic's chosen footprint).

Schematic values used (from `bench_board.kicad_sch`): `L1`=2.2µH,
`C1`(buck Cin)=10µF, `C2`(buck Cout)=22µF, `R1`/`R2`(feedback
divider)=40.2k/7.32k, `C4`(LDO Cin)=10µF, `C5`(LDO Cout)=22µF.

## 1. Buck: 2S input (6.0-8.4V) → 5V

**Finding — marginal, flagged clearly: the buck cannot maintain 5V
regulation across the full stated 2S input range.**

Required duty cycle `D = Vout/Vin` (ideal, before conduction losses,
which only make real D *higher*):

| Vin | Required D | Vs. 80% max |
|---|---|---|
| 8.4V (full charge) | 59.5% | fine |
| 7.4V (nominal) | 67.6% | fine |
| 6.6V (2S @ 3.3V/cell, a common LVC threshold) | 75.8% | fine, tight |
| **6.25V** | **80.0%** | **at the limit** |
| **6.0V (2S @ 3.0V/cell, a real low-battery condition)** | **83.3%** | **exceeds max — regulation fails** |

At the datasheet's 80% max duty cycle, the lowest input voltage that can
still deliver a full 5V output is `Vout / D_max = 5 / 0.80 = 6.25V`.
Below that — which is inside this board's own stated 6.0-8.4V design
range, not an edge case outside it — the buck **drops out of regulation**
and the 5V rail sags. Real (non-ideal) duty cycle requirements are always
somewhat higher than this ideal calculation (conduction losses in the
FETs, inductor DCR, etc.), so the real dropout point is if anything
slightly *above* 6.25V, not below — this isn't a worst-case-only concern.

**Why this matters beyond the buck itself**: the LDO's input comes from
this rail, not the battery directly (§2) — so this same low-battery
condition degrades both regulators together, not independently.

## 2. Buck ripple and load-step (qualitative, at nominal 7.4V)

Inductor ripple current: `ΔI_L = (Vin−Vout)·D / (L·Fsw) = (7.4−5)·0.676 / (2.2µH·580kHz) ≈ 1.27A` peak-to-peak.

Output voltage ripple (capacitive term, ESR of a decent ceramic Cout
assumed small enough to not dominate):
`ΔV ≈ ΔI_L / (8·Fsw·Cout) = 1.27 / (8·580kHz·22µF) ≈ 12mV` — about 0.25%
of the 5V rail. Comfortable, not flagged.

1.27A ripple relative to this board's actual expected load (an STM32F405
+ MPU-6000 + CRSF/DShot signal headers — no motors on this power rail,
they're a separate, unbuilt topic) is large enough that the converter
will likely spend meaningful time in discontinuous conduction mode at
light load. That's D-CAP2's normal, by-design light-load behavior, not a
fault — not flagged as marginal, just noted so it isn't mistaken for an
anomaly if seen on a real scope trace later.

Load-step response: not analyzable by hand with any real confidence
(depends on control-loop compensation internal to the IC, not something
a static calculation captures) — this is exactly the category of
question actual SPICE (or bench measurement) is for for and hand
calculation genuinely can't answer. Left open, not guessed at.

## 3. LDO: 5V → 3.3V dropout margin and dissipation

**Dropout margin**: at a healthy 5.0V input, margin to the AMS1117's
1.2V typical (1.3V max) dropout requirement is `5.0 − 3.3 = 1.7V` —
comfortable. **But per §1, once the buck's own output sags below its
regulated 5V** (starting around Vin≈6.25V on the battery side), that
margin shrinks correspondingly — the two findings compound, they aren't
independent.

**Dissipation**: `P = (Vin−Vout) × Iload = 1.7V × Iload`. Estimated
actual 3.3V-rail load (STM32F405 active + MPU-6000 active — both rough
estimates, not independently re-verified datasheet figures for this
specific pass, flagged as such) ≈150-200mA → **P ≈ 0.3-0.35W**. Against
the SOT-223 package's 15°C/W thermal resistance: **~5°C rise above
ambient** — comfortable, not flagged. Even at the LDO's full 1A rating
(well above this board's actual load), dissipation would be 1.7W →
~26°C rise — still generally fine, included only as a bound, not because
the real load approaches it.

## 4. Inrush at battery connect

Low risk, **specifically because the input capacitance is small**, not
because of any explicit inrush-limiting component (none exists on this
board — no NTC thermistor, no soft-start input stage beyond whatever the
TPS563201 itself integrates internally). Stored energy in `C1` (10µF) at
full charge: `E = ½CV² = ½ × 10µF × 8.4² ≈ 0.35mJ` — trivial. If a much
larger bulk input cap were ever added in a future revision, this
conclusion would need revisiting; as designed, it's fine.

## 5. Battery-sense divider and ADC scaling

**Cannot be analyzed — it doesn't exist in the current schematic.**
Checked the actual component list in `bench_board.kicad_sch`: there is
**no battery-voltage-sense resistor divider anywhere on this board**, and
no MCU ADC pin is connected to one. This is a real gap in the design as
built, not a finding about an existing circuit's accuracy — flagging it
plainly rather than analyzing something that isn't there. Not added here
either: per this batch's own scope (PCB layout next, "no fab files, I
review the layout first"), adding a new circuit mid-analysis wasn't this
task's call to make unilaterally — flagging it for a decision instead.

## Summary — what's actually marginal

| Item | Status |
|---|---|
| Buck duty-cycle margin at low battery (≤6.25V) | **Marginal — regulation fails inside the board's own 6.0-8.4V stated range** |
| Buck output ripple (nominal Vin) | Fine (~12mV, 0.25%) |
| LDO dropout margin (nominal Vin) | Fine (1.7V margin vs. 1.3V max dropout) |
| LDO dropout margin (low battery) | **Degrades together with the buck finding above** |
| LDO thermal dissipation | Fine (~5°C rise at estimated real load) |
| Inrush at battery connect | Fine (small input cap, low stored energy) |
| Battery-sense/ADC scaling | **Not present in the design — can't analyze, can only flag** |

Two real, non-cosmetic findings here: the buck's low-battery duty-cycle
margin, and the missing battery-sense circuit. Neither is a "SPICE would
have caught something hand-calculation couldn't" situation — both are
visible from datasheet numbers and the schematic's actual component list.
