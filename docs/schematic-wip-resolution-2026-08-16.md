# Schematic WIP Resolution — 2026-08-16

Item 1 of the "close findings" batch: `bench_board.kicad_sch` had an
uncommitted diff sitting outside any task's scope for two batches running
(flagged in `wiki/hot.md`/`wiki/log.md` both times). Instructed to review
it properly this time — read the actual diff, don't assume it's correct —
and either commit it clean or fix it. **It was not clean.** Real defects
found, fixed here, all re-verified against a clean ERC before committing.

## What the WIP actually contained (read directly, not assumed)

`git diff --stat` showed 489 insertions/195 deletions, but only **one**
new component type (`lib_id`) was ever added: `TPS54336ADDA` (the
regulator swap already known from last batch — see
`power-spice-verification-2026-08-16.md`). Everything else in the diff
was net-label churn from that one swap (`SW_NODE`, `VBST_NODE`, etc.) and
a `VBAT_2S`→`VBAT_4S`-adjacent rename. **The two "proposed" docs sitting
alongside it (`expansion-bus-spec.md`, `stm32f405-pin-assignment.md`)
describe an on-board magnetometer/barometer, an expansion header, and ESC
telemetry wiring that were never actually applied to the schematic** —
confirmed by the same `lib_id` check (nothing else new) and by
`list_schematic_nets` showing no I2C2/SPI2/USART3 nets exist at all.
Those two docs are real, honest planning documents (both correctly say
"Current assignment: unused" / "Proposed" throughout) — not wrong, just
not yet executed. Feeds directly into item 4's hardware check below.

## Real defects found and fixed

**1. `R1` (feedback top resistor) was still the old 2S value.** Schematic
had `33.2k` (0.76V-VFB-era); the 4S doc had already derived `31.6k` for
the 0.8V-VFB parts (`TPS54331DR` and, coincidentally, the actually-placed
`TPS54336A` — both use VFB=0.8V) but that value was never pushed to the
schematic. With the old value, `Vout = 0.8×(1+33.2/10) = 3.456V` — a real
4.7% output-voltage error, not a rounding nit. **Fixed: `R1` → `31.6k`.**

**2. `R9`/`R10` (battery-sense divider) were still the old 2S values —
this one is a safety issue, not just a stale number.** Schematic had
`R9=20.0k`/`R10=10.0k` (÷3.0 ratio, sized for 2S). The 4S doc's own
derived `R9=49.9k` was never pushed either. Worse: **even the documented
4S-era value doesn't work for this batch's actual scope.** At true 6S
peak (25.2V), `R9=20.0k` puts **8.4V** on the STM32's ADC pin (would very
likely damage it) and even the "correct" `R9=49.9k` puts **4.207V** on a
3.3V-rail ADC pin — both over `VDDA`, both wrong for a board this batch's
own SPICE work just confirmed is genuinely 6S-capable at the regulator.
**Fixed: `R9` → `75.0k`, recomputed for 6S-peak headroom, not just
matching the already-written-but-unapplied 4S number.** New ratio
`(75.0+10.0)/10.0 = 8.5`: `25.2V/8.5 = 2.965V` at 6S peak (comfortable
under 3.3V), `16.8V/8.5 = 1.976V` at 4S peak — both safely inside the
ADC's usable range. Firmware (`MAIN_LOOP_BATTERY_SENSE_SCALE`,
`hal_stub.c`'s default, every hardcoded value in `test_battery_sense.c`)
updated to match and re-verified passing — see `drone-firmware` commit
`cc91462`. **This is scope beyond literally "commit what the doc already
says" — justified because leaving a known-wrong-for-6S carryover in place
while this whole batch is about verifying 6S would have been dishonest,
not conservative.**

**3. `J1` was never renamed.** The 4S doc's own summary table says
`BATT_2S` → `BATT_4S`; the schematic still said `BATT_2S`. Cosmetic
(doesn't affect ERC/function) but real — a mislabeled connector on a
board that's actually rated well past 2S. **Fixed: `J1` → `BATT_4S`.**

**4. `U2` had no footprint assigned.** Confirmed via
`get_schematic_component` directly (`Footprint: ""`), not inferred.
**Fixed:** assigned `Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.81mm`
— TI's own datasheet states the physical package as "SO PowerPAD,
4.89mm × 3.90mm" (`tps54336a.pdf`, fetched and text-extracted directly
this batch — see the SPICE doc's §6 for how), matching this KiCad
footprint's body size. **Flagged, not fully closed:** the datasheet's
exact exposed-pad mechanical dimensions weren't cleanly extractable from
the PDF's vector mechanical-drawing page (text-only extraction doesn't
capture drawn dimensions) — cross-check the exact EP size against TI's
mechanical drawing before fab, same category of "verify at BOM/fab time"
flag this project already uses elsewhere.

**5. `COMP`/`SS` pins were wired to nothing.** Covered in full in
`power-spice-verification-2026-08-16.md` §6 — no compensation network or
soft-start capacitor physically existed on the schematic at all. Real
components now placed and wired: `R11`=2kΩ + `C23`=7.5nF (compensation,
COMP→GND, AC-verified this batch, ~44kHz crossover, no instability at
either 4S or 6S) and `C24`=10nF (soft-start, SS→GND, sized via the
datasheet's own `Css = Tss·ISS/VREF` equation for a ~3.5ms soft-start
time: `3.5ms × 2.3µA / 0.8V ≈ 10nF`, matching TI's own worked example
value in `tps54336a.pdf` §8.2.4.2.2).

## Item 2: `C1` voltage rating

The 4S doc flagged `C1` needing "a physical part rated ≥25V" — sized for
4S headroom, **zero margin at true 25.2V 6S peak.** Bumped to the next
standard rating up: `C1` Value → `10uF 35V`, added an explicit `Voltage`
property (`35V`) so this is a real, BOM-exportable field now, not just a
prose note that "isn't verifiable at symbol level" (the 4S doc's own
phrase — this closes that specific gap: the rating is now on the
component itself).

## Verification before commit

- `run_erc`: **0 errors, 0 warnings** (started at 2 warnings from the
  original WIP's dangling `COMP_NODE`/`SS_NODE` labels; picked up 5 more
  transient warnings while wiring the new parts off-grid, all resolved —
  see the session's own grid-alignment fix, not left as noise).
- `list_schematic_nets`: confirmed `COMP_NODE` and `SS_NODE` both went
  from 1-pin (dangling) to 2-pin (real connections); `GND` grew from 42
  to 44 pins (the two new ground returns).
- `check_placement_clearance`: 2 pre-existing PCB-side text-overlap
  warnings (`U2`/`C1`, `R9`/`R10`) — confirmed these are **PCB silkscreen
  positions**, unrelated to and unmoved by any schematic-side edit this
  batch (the PCB has never been re-synced from this schematic revision at
  all — that's a separate, not-yet-attempted step, same as it's been
  since the 158-DRC-violation state logged previously). Not this batch's
  scope; flagged, not fixed.

## What this does NOT close

- **PCB sync/DRC/routing** — the board hasn't been re-synced from this
  schematic revision at all. Last known PCB state is still the
  158-violation, not-DRC-clean state from the platform-revision batch.
  A new `sync_schematic_to_board` + DRC pass is real, separate work.
- **Magnetometer / expansion header / ESC telemetry** — per the finding
  above, none of this was ever applied to the schematic despite being
  documented as "proposed." See item 4's write-up (vault log) for the
  explicit decision not to silently add it mid-batch.
- **Footprint EP dimension cross-check** — flagged above, needs the real
  TI mechanical drawing, not this batch's text-only PDF extraction.
