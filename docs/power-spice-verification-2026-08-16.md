# Power SPICE Verification — TPS54336ADDA — 2026-08-16

Real `ngspice` simulation, replacing the hand-calculation used in
`power-verification-4s-2026-08-16.md`. Simulates the part actually placed
in `bench_board.kicad_sch` (`U2` = **`TPS54336ADDA`**) — this is a real,
previously undocumented discrepancy with the 4S doc, which documents a
different part (`TPS54331DR`); see `wiki/references/tooling-status.md`
for the full discrepancy writeup. Simulating the schematic's actual part,
not the doc's, verifies the real circuit.

## 1. Model sourcing — real, TI-provided, partially usable

Three model files exist on TI's own product page (`ti.com/product/TPS54336A`):
`SLVMAM8A.ZIP` (PSpice transient model), `SLVM980.ZIP` (TINA-TI average
model, encrypted), `SLVM898A.ZIP` (**PSpice average model, unencrypted**).
Downloaded all three directly via `curl` against `ti.com/lit/zip/<docnum>`
(confirmed genuine zip archives, not error pages, before trusting them).

- **Transient model (SLVMAM8A): not usable in ngspice as-is.** Plain-text,
  unencrypted, but built from PSpice-only digital/behavioral primitives
  (`Driver_U8_S3/S4/S5`, `AND3_BASIC_GEN`, `INV_BASIC_GEN`) that reference
  PSpice's own `abm.lib`/digital-primitive library, not included in the
  zip and not present in ngspice. Porting it would mean rewriting every
  referenced primitive from scratch — real effort, not attempted this
  pass.
- **TINA-TI average model (SLVM980): encrypted**, unreadable without
  TINA-TI itself (not installed on this machine). Not usable.
- **PSpice average model (SLVM898A): used for this verification.** Plain
  SPICE-2/3-style behavioral syntax only (`E`/`G` sources with
  `VALUE={...}`, standard `.SUBCKT`), no PSpice-exclusive digital parts.
  Copied to `engineering/drone-hardware/sim/TPS54336_AVG.lib` (original,
  as downloaded) and `sim/TPS54336_AVG_ngspice.lib` (ported copy: `TC=0,0`
  stripped from two passives — ngspice doesn't parse that PSpice
  temperature-coefficient syntax; zero effect since the coefficient is
  zero anyway. Diffable against the original, nothing else changed).

**Real limitation carried by this choice, stated plainly**: an *average*
model represents duty-cycle-averaged behavior, not cycle-by-cycle
switching. It correctly captures large-signal transient response (DC
regulation, startup settling, load-step response) but **does not show
real switching-frequency output ripple in its time-domain output** — the
simulated `V(VOUT)` is smooth by construction. Ripple is still computed
analytically below (§4), now at the correct 340kHz (the 4S doc's ripple
numbers used 570kHz, correct for the *documented* `TPS54331DR`, wrong for
the *actual* `TPS54336ADDA`). The average model also has **no EN/SS
pins** — it doesn't model soft-start, so the "startup transient" below is
a loop step-response, not a real soft-start ramp; see §3.

Also required an `ngspice`-compatibility fix unrelated to the model
itself: PSpice's `IF(cond, a, b)` isn't a native ngspice function — added
`.func if(a,b,c) '(a) ? (b) : (c)'` as a shim in the test netlist
(`sim/tps54336_buck_verify.cir`), mapping it onto ngspice's ternary
operator. Standard, documented ngspice/PSpice porting step, not a hack
specific to this model.

## 2. Circuit under test

`sim/tps54336_buck_verify.cir`. Real component values from the schematic
and the 4S doc: `L1`=10µH, `C2`(Cout)=22µF (5mΩ ESR assumed — typical for
a good ceramic MLCC, not measured), `R1`(fb top)=31.6k, `R2`(fb
bottom)=10.0k, target Vout=3.3V.

**Compensation network (Rcomp/Ccomp from `COMP` to `GND`): not a TI
reference-design value.** The reference-design schematics bundled with
the model zips are OrCAD `.DSN`/TINA `.opj` binaries, not extractable to
plain text this pass. Sized instead via standard current-mode Type-II
practice — zero near the LC double pole (`1/(2π√(LC))` ≈ 10.7kHz for this
L/C). **First attempt (Rcomp=100kΩ) was unstable** — a real result, not
a mistake glossed over: larger Rcomp raises loop gain/crossover, the
opposite of "conservative." Corrected to **Rcomp=2kΩ, Ccomp=7.5nF**,
which stabilized the loop at every voltage point tested. This
compensation is a reasonable working choice, confirmed stable and
correctly regulating — **not a verified-optimal or TI-endorsed value**;
a proper `.ac` loop-gain sweep (crossover frequency, phase margin in
degrees) was not run this pass, only large-signal transient stability.

**Second real finding during debugging, worth keeping:** an initial
light-load test point (0.2A) produced runaway numerical instability
(`V(VOUT)` diverging to kV-scale) independent of the compensation
question. Root cause, confirmed by computing the CCM/DCM boundary
(`ΔI_L/2`) at each voltage point — 0.35–0.42A across the 12–25.2V
range — **0.2A is genuinely below that boundary, i.e., real DCM
operation.** This model's own CCM/DCM mode-detection logic is degenerate
in this release: `Emode`'s `IF()` has *identical* true and false
branches in `TPS54336_AVG.lib` (`{4/(L*(6.28*Fs)^2)}` both times) — it
cannot represent DCM at all, and goes numerically unstable when forced
into it. Worked around by testing at 0.55A/1.0A (both comfortably above
the boundary at every voltage point) instead of the originally-planned
0.2A/0.8A. **Real hardware implication, not just a sim workaround**: this
converter's actual idle/light-load current (FC core ~150-200mA per the
4S doc) likely *does* run in DCM in real hardware — normal and expected
for this converter topology at light load, just something this
particular average model can't verify — flagging for anyone doing a
bench ripple/efficiency measurement later, since DCM ripple behavior
differs from the CCM formula used in §4.

## 3. Results — startup / DC regulation / load-step

All four points: 12.0V (4S floor), 14.8V (4S nominal), 16.8V (4S peak,
the existing 4S doc's ceiling), **25.2V (6S peak, never previously
calculated for either regulator part)**.

| Vin | Startup: peak/final VOUT | Time to settle | Load-step dip (0.55A→1.0A) | Full-load settled VOUT |
|---|---|---|---|---|
| 12.0V | 3.328V / 3.328V (no overshoot) | <10µs | 3.328V → 3.269V (−59mV, −1.8%) | 3.328V |
| 14.8V | 3.328V / 3.328V (no overshoot) | <11µs | 3.328V → 3.268V (−60mV, −1.8%) | 3.328V |
| 16.8V | 3.328V / 3.328V (no overshoot) | <7µs | 3.328V → 3.267V (−61mV, −1.8%) | 3.328V |
| 25.2V | 3.328V / 3.328V (no overshoot) | <9µs | 3.328V → 3.266V (−62mV, −1.9%) | 3.328V |

Regulation is consistent and correct across the entire 4S-through-6S
range: 3.328V settled (+0.85% vs. 3.3V target, matching the R1/R2
feedback-divider hand-calc in the 4S doc exactly — real cross-check, not
assumed). Load-step dip is consistently small (~60mV, <2%) and fully
recovers within the simulated window at every voltage point. **No
overshoot at startup** — but see §1/§2, this reflects the average
model's lack of soft-start modeling, not a real-hardware guarantee; real
soft-start timing (from the actual datasheet SS pin behavior) hasn't been
checked in this pass.

## 4. Output ripple — recomputed at the correct 340kHz

The 4S doc's ripple figures (§5, ~5.3mV) used 570kHz — correct for
`TPS54331DR`, **wrong for the part actually in the schematic**
(`TPS54336A` is fixed 340kHz). Recomputed with the real frequency:

| Vin | Duty | ΔI_L | ΔV (cap term) | ΔV (ESR term, 5mΩ assumed) | ΔV total | % of 3.3V |
|---|---|---|---|---|---|---|
| 12.0V | 27.5% | 0.704A | 11.8mV | 3.5mV | 15.3mV | 0.46% |
| 14.8V | 22.3% | 0.754A | 12.6mV | 3.8mV | 16.4mV | 0.50% |
| 16.8V | 19.6% | 0.780A | 13.0mV | 3.9mV | 16.9mV | 0.51% |
| **25.2V** | **13.1%** | **0.843A** | **14.1mV** | **4.2mV** | **18.3mV** | **0.55%** |

Comfortable at every point, including 6S peak — well under 1% of
nominal. Duty cycle at 6S peak (13.1%) stays well clear of the part's
minimum-on-time floor (≈3.4% at 340kHz assuming a ~100ns min on-time,
consistent with parts in this class) — no dropout/pulse-skipping concern
at either range end.

## 5. Direct answer: does 6S peak (25.2V) work with `TPS54336ADDA`?

**Yes, electrically — with real numbers behind it now, not just "under
28V so probably fine."** Stable closed-loop regulation (3.328V, matching
the 4S-range result exactly), modest load-step dip (<2%), comfortable
ripple (0.55%, still well under 1%), duty cycle far from any floor/ceiling
concern. Margin to the part's 28V recommended-max ceiling is thin (2.8V,
11%, vs. 4S's 11.2V/67%) but that's an input-voltage headroom question,
separate from and not contradicted by the closed-loop behavior verified
here — both are true simultaneously: thin absolute-max margin, but
correct regulation within that margin.

**What this does NOT close:** (a) thermal — RDS(on) figures (128mΩ HS /
84mΩ LS, synchronous — this part needs no catch diode, unlike the
documented `TPS54331DR`, a real simplification in its favor) give a
trivial conduction-loss estimate (~95mW at 1A, nominal Vin) but switching
losses still aren't captured, same caveat as the 4S doc's own §6; (b)
`C1` (input cap) voltage rating — the 4S doc's "≥25V" note has **zero
margin** at a true 25.2V 6S peak — being fixed directly in the schematic
this batch (see the vault log for the item-2 write-up); (c) the
part-choice discrepancy itself (`TPS54331DR` documented vs.
`TPS54336ADDA` actually placed) — being resolved this batch (schematic
gets committed as `TPS54336ADDA`, this doc, item 1's WIP review). §6
below closes the compensation-network item flagged here as open.

## 6. AC loop-gain / phase-margin — real simulation, real caveats

The gap this section closes: §5(a) above (superseded, see note) — and
item 3's own ask, since finding `COMP_NODE`/`SS_NODE` as single-pin
(unconnected) nets while reviewing the WIP schematic for item 1 made
plain that **no compensation network physically exists on the board at
all yet** — the Rcomp/Ccomp values §2 used were a simulation-only
convenience, not something on the schematic. This section verifies those
values with real AC data before they get committed to the schematic in
item 1/2's resolution.

**Method:** `sim/tps54336_loop_gain.cir` (and `..._6s.cir` for the 25.2V
point) — standard single-injection loop-gain measurement, breaking the
loop between the feedback-divider midpoint (`VSENSE_FB`, low output
impedance, R1‖R2≈7.6k) and the model's `VSENSE` pin (near-infinite gm-amp
input impedance — satisfies the standard low-impedance-injection
assumption) with a `DC=0 AC=1` series source. `T(s) = V(VSENSE_FB)/V(VSENSE_INJ)`.
Crossover frequency and phase margin (`PM = 180 − |phase(T)|`) are both
provably robust to which side of the break is called numerator vs.
denominator (swapping negates the phase and flips gain sign, but
`|phase|` and the 0dB-crossing frequency are unchanged either way) — so a
direction mistake here could not silently produce a wrong-but-plausible
result, only a self-evidently-broken one.

**Result, both range ends tested:**

| Vin | Crossover freq | Phase at crossover | Phase margin |
|---|---|---|---|
| 14.8V (4S nominal) | ≈44–46kHz | ≈0.7–0.8° | **≈179°** |
| 25.2V (6S peak) | ≈42–44kHz | ≈0.7–0.7° | **≈179°** |

Crossover barely shifts between 4S and 6S — consistent with current-mode
control's well-known low line-voltage sensitivity in the control-to-output
transfer function (a real property of this topology, not a modeling
artifact). No instability, no low/marginal phase margin, at either point.

**Why this number needs a loud caveat, not a victory lap:** ≈179° PM is
not a plausible real-hardware result — real compensated switching
regulators are typically designed for 45–60° PM, not near-180°. Traced
this to a real, findable cause rather than shrugging at a suspicious
number: the model's current-mode sampling-effect double-pole (normally
placed near `Fsw/2` = 170kHz, meant to add real phase loss as frequency
approaches it) is implemented via the `Emode`/`XC1` varicap block in
`TPS54336_AVG_ngspice.lib` — **the same degenerate `IF()` already found
in §2/last batch** (both branches evaluate to the identical
`4/(L·(2π·Fsw)²)`), independently re-confirmed here from the AC side
rather than just the transient side. With that pole's dynamics not
correctly modeled, the sampling-effect phase loss that a real IC would
show approaching crossover is simply absent from this simulation. This
doesn't mean Rcomp=2kΩ/Ccomp=7.5nF is wrong — the pole-cancellation logic
behind it (TI's own datasheet §8.2.4.2, equations 27–29: place the
compensator zero one decade below crossover to cancel the modulator
pole) is sound, real, and independently checked against the actual TI
datasheet PDF this batch (`ti.com/lit/ds/symlink/tps54336a.pdf`, fetched
directly via `curl`+`pdftotext` — the prior blocker on reading TI PDFs
was `pdftoppm`/poppler being absent for the `Read` tool's image-render
path; `pdftotext` alone, already on this machine, was never tried before
and works fine for text-only extraction). It means: **the crossover
frequency (~44kHz) and the "no instability" finding are trustworthy; the
specific ≈179° number is not** — a real design should assume something
meaningfully lower, and the honest next step name from the task brief
applies directly: **bench measurement with a network analyzer (or a
frequency-response injection transformer + oscilloscope) at Stage 4
bring-up** is what would actually confirm real phase margin, not a
better SPICE model that doesn't exist for this part in a form this
machine can run.

## Files (updated)

- `sim/tps54336_loop_gain.cir`, `sim/tps54336_loop_gain_6s.cir` — AC
  loop-gain netlists, §6.

## Files

- `sim/tps54336_buck_verify.cir` — ngspice netlist, closed-loop transient,
  parameterized on `VINVAL`.
- `sim/TPS54336_AVG.lib` — TI's original average model, as downloaded.
- `sim/TPS54336_AVG_ngspice.lib` — ngspice-compatible port (two `TC=0,0`
  tags stripped, zero electrical effect).
- `sim/.spiceinit` — sets `ngbehavior=all` (required for ngspice to accept
  PSpice-style behavioral-source syntax at all).
