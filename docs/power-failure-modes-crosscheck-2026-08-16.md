> [!warning] STALE — describes a superseded power architecture, found and flagged 2026-08-16 during this batch's own independent review
> This entire document's substantive findings (not just the path
> references, already fixed) analyze the **original 2-stage 2S design**
> — switching buck (`TPS563201`) dropping to 5V, then an LDO (`AMS1117-
> 3.3`) dropping 5V→3.3V. **Neither part exists on the current board.**
> The actual current design is a single-stage buck (`TPS54336ADDA`)
> direct to 3.3V, no LDO, no 5V rail at all — confirmed directly against
> `bench_board.kicad_sch`'s real placed components (only one regulator
> `lib_id` instance exists) and `docs/schematic-wip-resolution-2026-08-16.md`.
> **The "Linear regulator thermal failure" finding below is now moot**
> (there is no linear regulator); **the "5V regulator failure" and
> "brownout" findings below describe a rail and a duty-cycle-margin
> problem specific to the wrong part** (`TPS563201`'s 570kHz/80%-duty
> figures, not `TPS54336ADDA`'s real 340kHz behavior, already
> re-verified for real in `docs/power-spice-verification-2026-08-16.md`).
> **Kept in place rather than moved to `docs/superseded/`** — this
> wasn't one of the three doc-pairs this batch's item 4 was scoped to
> archive, and a full re-analysis against the current single-stage
> topology is real, separate work, not a quick fix. Treat every finding
> below as historical reasoning about a retired design, not a current
> risk assessment, until that re-analysis happens.

# Power Stage vs. Known Micro-FC Failure Modes — 2026-08-16

Cross-checking the bench board's power design (schematic + the hand-
calculation analysis in `docs/superseded/power-simulation-2026-08-16.md`) against
`.raw/micro-fc-failure-modes.md`. For each failure mode relevant to the
power stage: does this design address it, and if not, what would.

## Power-rail failures

**Blown capacitor disabling the entire rail (AIO blast-radius risk).**
Partially addressed by architecture, not eliminated. This board is
explicitly *not* an AIO — the power section (buck, LDO) is on its own
discrete nets, separable from the MCU/IMU beyond the shared 3.3V/5V
rails themselves. A blown cap still takes down whatever's downstream of
*it specifically* (e.g. `C2` failing shorted kills the whole 5V rail —
both the LDO's input and the CRSF header's 5V pin) — the two-board
strategy limits blast radius between *boards*, not within this one
board's own power tree. Nothing further addresses this; noted as a
real, if unremarkable, residual risk common to any single-rail design.

**Bricked bootloader from an interrupted flash / power dip mid-flash.**
Not a circuit-design question — this is a flashing-procedure risk
(stable USB power during flashing, don't flash on a marginal battery).
The schematic doesn't need to "address" this in hardware; noted so it
isn't mistaken for a gap.

**5V regulator failure (dead regulator / downstream short).**
Partially addressed: TPS563201 has datasheet-specified cycle-by-cycle
overcurrent limiting *and* hiccup-mode overcurrent protection (TI
product page) — a downstream short doesn't just cook the regulator
silently, the IC's own protection limits sustained damage. Per-VDD-pin
decoupling (already in the schematic, per the KiCad bench-board build)
is the standard mitigation for the *symptom* side (rail noise/instability
under transient load), not the fault itself.

**Linear regulator thermal failure.** **Already addressed by the
architecture, not just tolerated.** The research source itself makes
this connection explicitly: keeping the switching buck (TPS563201) doing
the large 2S→5V drop, so the LDO (AMS1117-3.3) only has to drop
5V→3.3V — a small differential — is exactly the mitigation it names, and
exactly what this schematic already does. Confirmed quantitatively in
`docs/superseded/power-simulation-2026-08-16.md` §3: ~5°C rise above ambient at the
estimated real load, comfortable margin to the SOT-223 package's thermal
limits.

**Burnt MOSFET.** Doesn't directly apply the same way — the buck's FETs
are integrated inside the TPS563201 package (synchronous buck), not
discrete external MOSFETs a tech could visually/olfactorily diagnose the
same way. The IC itself could still fail thermally or short internally;
no discrete-MOSFET-specific mitigation is relevant here to begin with.

**Brownout (voltage sag under load, connector/battery current capacity).**
**This is the same failure mode `docs/superseded/power-simulation-2026-08-16.md`
already found a real margin problem for, from the opposite direction.**
That analysis showed the buck's 80% max duty cycle caps regulation at
Vin≥6.25V — a battery sagging under load into the 6.0-6.25V range (a real
brownout, not a hypothetical) would trigger *exactly* the dropout already
flagged there. This isn't two separate findings — it's one finding,
reachable either by asking "what happens at low battery" (the power
analysis) or "what does a brownout look like" (this failure-mode
research). Mitigation is the same either way: verify real-world battery
sag under this board's actual load stays above ~6.25V-plus-margin, or
revisit the buck's input voltage headroom before trusting it near end-
of-pack.

## Not power-stage, noted for completeness

- **Cold/cracked IMU solder joints post-crash** — already cross-referenced
  in `b1-bench-verification-procedure.md` as a failure mode that can look
  like a sign-convention bug during bring-up. Not a power-stage item.
- **Vibration-fatigued wire joints** — assembly/soldering practice, not a
  schematic concern; relevant specifically to `J1`'s (battery input)
  leads if hand-wired rather than connectorized. Worth remembering during
  actual board assembly, not something this schematic controls.
- **ESC/motor desync** — no motors or ESCs exist on this board's power
  path (bench board, not the flight board) — explicitly out of scope,
  not force-fit into a connection that isn't there.

## Summary

One real, actionable finding, reachable from either document: **the buck
regulator's duty-cycle margin at low battery voltage is the single power-
stage risk this cross-check and the SPICE-blocked hand analysis both
converge on.** Everything else in the failure-mode research either doesn't
apply to this board's actual topology (AIO blast radius, discrete
MOSFETs, ESC desync) or is already addressed by a design choice already
made for other reasons (switching-before-linear regulation, per-pin
decoupling).
