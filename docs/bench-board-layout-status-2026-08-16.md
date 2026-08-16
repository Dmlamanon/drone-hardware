# Bench Board PCB Layout — Status, 2026-08-16

**Not DRC-clean, and not fully routed — reporting honestly rather than
overstating.** No fab files produced, matching the instruction to review
the layout first. What follows is exactly where it stands.

## What's done

- **4-layer stackup**: `F.Cu` / `In1.Cu` / `In2.Cu` / `B.Cu`, added to
  what was previously a 2-layer board.
- **`In1.Cu` is a dedicated ground plane** — a solid GND copper pour
  covering the board interior, per the explicit layout-rules requirement.
- **80×60mm rounded-rectangle outline** — generous, explicitly not whoop
  dimensions (a real whoop board is ~20-30mm); matches the Build Plan's
  bench-board intent (prove the copper, give firmware real hardware to
  run on — this board never flies).
- **All 42 footprints placed, verified 0 courtyard overlaps and 0
  board-boundary violations** (`check_courtyard_overlaps`, confirmed
  before applying). Key placement decisions, checked against
  [[PCB Layout Rules for Flight Controllers]]:
  - **IMU (`U4`, MPU-6000) placed ~41mm from the switching regulator
    (`U2`, TPS563201)** — computed directly from final coordinates
    (U4 at 48,22mm; U2 at 14,45mm), comfortably satisfying "don't place
    it near the switching regulator."
  - MCU (`U1`) and IMU (`U4`) placed close to each other for a short SPI
    run (see routing section — length target mostly met, not fully).
  - Auto-placement (force-directed clustering, `suggest_placement`)
    pulled each IC's own decoupling caps and feedback-divider resistors
    tight against it, matching "every IC power pin gets 100nF within
    3mm."

## What's NOT done, and why

**No autorouter was available.** Checked before attempting manual
routing of all 35 nets: no Java runtime, no `freerouting.jar`, no Docker
— `check_freerouting` confirmed `"ready": false` on every front.

**Manual routing was attempted for the most safety/signal-critical nets
(SPI bus to the IMU, core power chain) and then reverted.** Direct
point-to-point traces on `U1`'s 0.5mm-pitch LQFP-64 pads produced real
short-circuit DRC errors (`SPI1_SCK` shorting `SPI1_MISO`, `MPU_INT`
shorting `SPI1_MOSI`) — fine-pitch packages need actual escape routing
(fan-out away from the package before running to the destination), not
straight lines, and doing that properly by hand for 5+ nets was beyond
what this pass could responsibly complete. **Rather than save a board
file with hidden short circuits, those traces were deleted.** The board
as saved has placement and the ground plane, but the SPI bus, power
chain, and every other net remain unrouted (ratsnest/airwires only).

**DRC is not clean: 106 violations remain (63 errors, 43 warnings),
entirely placement/footprint-driven, not routing-driven** (re-confirmed
after deleting the problem traces — the same 106 remained before and
after a placement-margin adjustment, ruling out simple repacking as the
fix):

| Type | Count | Severity | Real cause |
|---|---|---|---|
| `clearance` | 60 | error | **Overwhelmingly clustered at `J3`** (the USB-C receptacle, Amphenol 12401548E4-2A) — pad-to-pad spacing of 0.15-0.16mm against this board's default 0.2mm clearance rule. This is very likely intrinsic to the connector's real pin pitch, not a placement mistake — fine-pitch USB-C footprints routinely need a relaxed clearance rule (many fabs, including JLCPCB, support 0.09-0.1mm minimum) rather than a placement fix. Flagged for a design-rule decision, not something more shuffling would resolve. |
| `copper_edge_clearance` | 3 | error | A part sits closer to the board edge (`Edge.Cuts`) than the clearance rule allows — likely `J3` or `J1`, both placed near board edges by design (they're edge connectors). |
| `silk_over_copper` | 28 | warning | Reference-designator silkscreen text overlapping copper/pads — cosmetic, common with auto-placed text, fixable by nudging field label positions (not attempted this pass). |
| `silk_overlap` | 15 | warning | Silkscreen-vs-silkscreen overlap between adjacent parts — same category, cosmetic. |

## Honest bottom line

This is a **placement-and-stackup pass, not a routed board** — the
explicit "DRC clean" bar was not met, and saying otherwise would be worse
than saying so plainly. What exists now (verified-overlap-free placement
respecting the IMU/switcher separation rule, a real 4-layer stackup with
a dedicated ground plane) is real progress and a reasonable starting
point. What's missing (all actual copper routing, the USB-C clearance
rule decision, silkscreen cleanup) is real remaining work, most of which
needs either a working autorouter or manual routing in the KiCad GUI by
someone who can iterate visually — both more suited to a human pass than
continuing to guess at it through blind point-to-point API calls.
