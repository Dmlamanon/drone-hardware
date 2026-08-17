> [!warning] SUPERSEDED — moved to docs/superseded/ 2026-08-16 (Cleanup & Consolidation batch)
> **Superseded by:** `docs/power-spice-verification-2026-08-16.md`.
> **Why:** this doc documents replacing `TPS563201` with `TPS54331DR`
> for the 4S revision — but the part actually placed in the schematic
> turned out to be a different IC, `TPS54336ADDA` (found in the Tier 1
> build-out batch). The current doc simulates and verifies the real
> placed part, at both 4S and 6S, with real ngspice data instead of this
> doc's duty-cycle/ripple hand-calculations.
> **Why it's kept, not deleted:** real, methodical hand-calculation work
> (duty cycle across the full voltage range, inductor/ripple sizing,
> thermal bounds) that the current doc's own §4 explicitly cross-checks
> its ngspice results against — the two independent methods agreeing is
> itself a useful confidence signal, only visible by keeping both. The
> note directly below (already present before this archival) documents a
> real, separate finding: two of this doc's own derived values (`R9`,
> `C1` rating) were never actually applied to the schematic and needed
> further revision once they were. Do not use any number below for the
> current design without cross-checking the current doc first.

> [!note] Amended 2026-08-16, "close findings" batch — two values below superseded
> This doc's derived values were never actually applied to the schematic
> (found while resolving the long-outstanding WIP — see
> `schematic-wip-resolution-2026-08-16.md`) and, once applied, two of them
> turned out to need a further revision for real 6S-peak safety: **`R9`
> is now `75.0k`** (not `49.9k` — the 49.9k ratio still over-ranges the
> ADC at true 6S peak, see the resolution doc) and **`C1`'s voltage
> rating is now `35V`** (not `≥25V` — zero margin at 25.2V). `R1`
> (`31.6k`), `L1`, `C2`, and the regulator-swap reasoning below are
> unchanged and were applied as-documented.

# Power System Re-Verification for 4S — 2026-08-16

Platform-revision batch, item 3. The vehicle class changed from 65mm
whoop/2S to a 5"-class quad/4S (see [[log]], [[Build Plan — 3D Printed
Drone with Custom PCB]]). This re-verifies the buck regulator against the
new input range, using real datasheet numbers fetched from TI.com this
batch (not memory), and updates the schematic and firmware accordingly.

## 1. TPS563201 vs 4S — FAILS margin, replace

**Source: `ti.com/product/TPS563201` (TI.com product page, fetched this
batch).** Recommended operating VIN range: **4.5V–17V**. Feedback
reference (VFB): 0.76V. Switching frequency: 580kHz (D-CAP2 adaptive
on-time). Max duty cycle: 80%. Max output current: 3A.

4S pack peak voltage (full charge, 4.20V/cell × 4): **16.8V**.

Margin: 17V − 16.8V = **0.2V (1.2%)**. This is not a workable margin for a
production design:
- A freshly balance-charged pack sits at the 16.8V ceiling by definition,
  not as a rare edge case — this is nominal full-charge behavior, not
  abuse.
- Input-node ringing from PCB trace/connector parasitics, and ESC
  regenerative braking transients feeding back through the shared battery
  bus, both commonly add several hundred mV to a kV spike on top of the
  DC pack voltage in FPV-class systems — well documented in the existing
  [[Micro FC Failure Modes]] research. A 0.2V DC margin leaves no room for
  any of that before exceeding the part's own recommended operating
  ceiling.

**Verdict: marginal-to-failing, replace the regulator.** Not attempting to
run the old part closer to its rated limit — the margin is too thin to
trust on a board that also has no motor current isolating this rail from
transients (FC-only architecture still shares the battery bus with the ESC).

## 2. Replacement selection: TPS54331DR

Searched JLCPCB's parts library for a wide-input buck with comfortable 4S
headroom, same single-stage-to-3.3V architecture (direct buck, no LDO
second stage) as the current design.

**TPS54331DR** — confirmed via TI.com and JLCPCB part lookup this batch:
- **JLCPCB classification: Extended Part** (LCSC `C9865`), package SOIC-8.
- Recommended VIN: **3.5V–28V**; datasheet-stated absolute max 30V.
- Output: adjustable via external feedback divider, **VFB = 0.8V typical**.
- Switching frequency: 570kHz (fixed, not adaptive like the D-CAP2 part it
  replaces — worth knowing since ripple/EMI characteristics shift
  slightly, not evaluated further here).
- Max output current: 3A.
- **High-side switch RDS(on): 80mΩ typical** (TI.com search result,
  Mouser-hosted datasheet mirror).
- **Non-synchronous**: integrates the high-side FET only; needs an
  external catch (Schottky) diode, which the TPS563201 (fully
  synchronous) did not. **This is a real schematic change, not just a
  part swap** — a diode footprint is being added.

Margin at 4S peak: 28V − 16.8V = **11.2V (67%)**. Comfortable, not marginal,
even accounting for the ringing/transient concern in §1.

## 3. Feedback divider recompute (VFB changes 0.76V → 0.8V)

Existing schematic (TPS563201): R1=33.2k (top), R2=10.0k (bottom) →
`Vout = 0.76×(1+33.2/10) = 3.28V`.

New part's VFB is different (0.8V, not 0.76V) — the divider must be
recomputed, not carried over:

`Vout = VFB × (1 + R1/R2)`, target 3.3V, VFB=0.8V:
`1 + R1/R2 = 3.3/0.8 = 4.125` → `R1/R2 = 3.125`.

Keeping R2 = 10.0k (unchanged, standard value already in use elsewhere on
this board for the battery-sense divider's bottom leg too): `R1 = 31.25k`
→ nearest standard 1% (E96) value **31.6k**.

Check: `Vout = 0.8×(1+31.6/10) = 0.8×4.16 = 3.328V` (+0.85% vs. 3.3V
nominal — well inside the part's feedback accuracy, not flagged).

## 4. Duty cycle across the 4S range

Non-synchronous topology: duty cycle includes the catch diode's forward
drop, unlike the old synchronous part. Using a standard Schottky drop
`Vd ≈ 0.5V` (SS34-class, generic — exact diode MPN is a BOM-selection task,
not decided here): `D ≈ (Vout + Vd) / Vin`.

Floor and ceiling use the same 3.0V/cell-floor / 4.2V/cell-peak convention
the 2S design used (2S doc: "6.0V floor" = 3.0V/cell × 2):

| Vin | Condition | D | vs. limits |
|---|---|---|---|
| 16.8V | 4S full charge (4.2V/cell) | 22.6% | fine |
| 14.8V | 4S nominal (3.7V/cell) | 25.7% | fine |
| 12.0V | 4S floor (3.0V/cell) | 31.7% | fine |

All three points are far from both the part's minimum on-time floor
(roughly 5.7% duty at 570kHz for a ~100ns min on-time) and any practical
maximum-duty ceiling — no dropout risk anywhere in the 4S range, unlike
the prior 2S/TPS563201 finding that flagged exactly this kind of
low-battery dropout.

## 5. Inductor and output ripple

Target ripple current ≈30% of a generously-budgeted 1.5A design load
(actual expected load is much lower — see §7):

`L = (Vin−Vout)×D / (Fsw×ΔI_L)`, evaluated at nominal 14.8V:
`L = (14.8−3.3)×0.257 / (570kHz×0.45A) = 2.96 / 256,500 ≈ 10.0µH`.

**This lands on the same 10µH already in the schematic (`L1`).** That's a
coincidence of the arithmetic, not a reused derivation — the old 10µH was
sized for the 2S/TPS563201 design point (different Vin range, different
Fsw, synchronous topology, no diode-drop term). Re-verified independently
here for the new part and happens to land on the same nominal value.
**Keeping `L1` = 10µH**, but flagging that the physical part's current
rating/saturation current still needs to be checked against a real MPN at
BOM time — the schematic-symbol level (`Device:L`) doesn't carry that.

Ripple current at the three range points (same formula):
- 16.8V: ΔI_L ≈ 0.54A
- 14.8V: ΔI_L ≈ 0.52A
- 12.0V: ΔI_L ≈ 0.48A

Output voltage ripple, keeping `C2` = 22µF (unchanged):
`ΔV ≈ ΔI_L / (8×Fsw×Cout) = 0.54 / (8×570kHz×22µF) ≈ 5.3mV` — **0.16% of
3.3V, comfortable, not flagged.**

`C1` (buck Cin, 10µF, unchanged value) needs a physical part rated ≥25V
for 4S headroom — not verifiable at symbol level, flagged for BOM
selection alongside the inductor.

## 6. Thermal

**Real limitation, stated plainly (same category as the prior batch's
SPICE-blocked finding): exact switching-loss and package θJA figures
could not be extracted from TI's own datasheet PDF this batch** — every
`WebFetch` attempt against the TI-hosted PDF returned binary/compressed
stream data instead of readable text (tried the direct TI.com lit link and
an Octopart mirror; the `Read` tool's PDF path also failed, no
`pdftoppm`/poppler installed on this machine to render pages). This is a
tooling gap, not a skipped step.

What's calculable without those figures — conduction loss only, a real
lower bound, using the 80mΩ RDS(on) figure that WAS obtained (TI.com
search result):

`P_cond = I_out² × R_DS(on) × D`. At a generously-budgeted 1A load,
nominal 14.8V (D=0.257): `P_cond = 1² × 0.08 × 0.257 ≈ 20.6mW`. Even at
the widest duty point (12.0V floor, D=0.317): `≈25.4mW`. Both trivial.

Switching losses aren't captured by this bound and are real (typically the
dominant loss term in a part like this at these frequencies) — the
conduction-only figure is a floor, not a full estimate. Given the floor
itself is two orders of magnitude below any concerning number, and actual
load (§7) is well under the 1A used here, **thermal risk is assessed as
low, but not to the same rigor as a real efficiency-curve-based estimate
would give.** Recommend a bench thermal check at Stage 4 bring-up rather
than treating this as fully closed.

Catch-diode dissipation (off-chip, separate thermal path): `P = I_out ×
V_f × (1−D) ≈ 1A × 0.5V × 0.74 ≈ 0.37W` at nominal — real, but in a
diode package (SMA/SOD-123 class), not the regulator IC. Needs a real part
with adequate power rating at BOM time; not sized further here.

## 7. Expansion-rail current budget

Full peripheral-by-peripheral budget with cited currents is item 4's job
([[expansion-bus-spec]]); provisional total for sizing purposes here:

- FC core (STM32F405 + MPU-6000 active): **150–200mA**, carried over from
  the prior 2S power-simulation doc's estimate (rough, not independently
  re-verified this pass — same caveat that doc already stated).
  Sub-250g/motor-current considerations don't change this figure — it's
  unrelated to vehicle class.
- Expansion bus headroom (baro + mag always-populated per item 6, plus
  optional flow/ToF/GPS on headers): budgeted generously at **300–500mA**
  pending item 4's real per-part numbers.

**Provisional total: well under 1A**, against a 3A-rated regulator with
11.2V of input-voltage margin already established in §2. No expansion-rail
current-budget concern from the regulator's own rating — the constraint,
if any, will be trace width/connector current rating, not the IC.

## 8. Summary — what changed and why

| Item | Old (2S) | New (4S) |
|---|---|---|
| Regulator | TPS563201 (synchronous) | **TPS54331DR (non-synchronous, +external catch diode)** |
| VFB | 0.76V | 0.8V |
| R1 (feedback top) | 33.2k | **31.6k** |
| R2 (feedback bottom) | 10.0k | 10.0k (unchanged) |
| L1 | 10µH | 10µH (unchanged value — independently re-derived, coincidence) |
| C1 / C2 | 10µF / 22µF | unchanged values; C1 needs ≥25V-rated physical part at BOM time |
| Duty cycle range | 59.5–83.3% (2S, includes a dropout finding) | **22.6–31.7% (4S, no dropout anywhere in range)** |
| Battery connector | `J1` "BATT_2S" | **rename to "BATT_4S"** (item 6) |
| Battery-sense divider | R9=20.0k/R10=10.0k, ÷3.0 | **R9=49.9k/R10=10.0k, ÷5.99** (firmware constant updated to match, see below) |

Firmware: `MAIN_LOOP_BATTERY_SENSE_SCALE` (3.0f → **5.99f**) and
`MAIN_LOOP_BATTERY_LOW_VOLTAGE` (7.0f → **14.0f**, same 3.5V/cell
low-voltage-warning convention as the 2S design, just ×4S) both updated in
`engineering/drone-firmware/src/main_loop.h`, with matching updates to
`hal_stub.c`'s default battery-pin voltage and every hardcoded voltage in
`test/test_battery_sense.c`. `make test` (18/18 binaries) and `make cross`
both re-verified clean after the change — see [[log]].

Schematic changes (R1, L1 unchanged/re-verified, R9/R10 changed, new
diode, `J1` rename) are applied in item 6, not this document — this
document is the calculation basis for those edits, and is written first
per the batch's own instructions so the schematic edit has a paper trail
to point back to.
