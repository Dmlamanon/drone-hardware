---
type: verification
status: complete
created: 2026-08-18
tags: [drone, hardware, pcb, datasheets, pinout, derating, lifecycle, pre-order]
---

# bench_board — datasheet-backed verification, 2026-08-18 (pre-order)

Closes the gap every prior review disclosed: no check against
manufacturer part documents had ever been run. Manufacturer PDFs were
downloaded into `datasheets/` (kept untracked — regenerable), and the
schematic/PCB pin data was compared against them pin by pin. Report
only; no board files touched. **Reviewed on the corrected premise that
this board IS the flight board** (Build Plan line 41; the stale
"never flies" paragraph is fixed as part of this pass — see the end).

## VERDICT: **HOLD THE ORDER — one datasheet violation needs a decision first**

Pinouts are clean: **every pin of every reviewed IC matches its
manufacturer document — zero swapped pins anywhere.** But the pass
found one absolute-maximum violation wired in copper, and one required
external component wrong on three axes. Ranked:

**BLOCKER — U2 (TPS54336A) EN pin: 16.8 V applied to a 6 V-abs-max
pin.** The schematic ties EN (pin 7) directly to VBAT_4S — the same
copper as VIN. TI's abs-max table (SLVSCD5D §6.1, p.4): **EN −0.3 to
6 V**, EN source current characterized only to 100 µA. The datasheet's
sanctioned usages (§7.3.3, p.12): **float EN** (internal pull-up
enables), open-drain drive, or a resistor divider from VIN for external
UVLO (Figure 15) — never a direct VIN tie. At 4S the pin sits at
~2.8× abs-max continuously whenever a battery is plugged in (4.2× at
the project's 25.2 V stress corner), with the internal ~6 V clamp
eating the difference at uncontrolled current. Failure mode is EN
clamp/latch-up damage → the 3.3 V rail — the whole aircraft — dead or
intermittent. This is in copper, so no BOM edit fixes it. Options,
honestly ranked:
1. **Fix the board first (recommended).** Smallest edit: disconnect EN
   from VBAT_4S and leave it floating — datasheet-sanctioned, zero new
   parts. Better for a battery vehicle: the Figure-15 two-resistor
   divider, which also gives a clean ~12 V pack-undervoltage lockout
   instead of brownout cycling. Either is a one-net change under the
   board guard, then regenerate the fab package (2026-08-18a). Days,
   not weeks; the order sheet's STOP philosophy exists for exactly this.
2. Order anyway + rework on arrival: lift U2 pin 7 on each of the 5
   boards (floating = enabled, in-spec). Works, but hand-rework on the
   regulator of every board, forever documented as the reason boards
   differ from their files.

**FIX IN THE BOM BEFORE UPLOAD (free now, not later) — U4 (MPU-6000)
charge-pump capacitor C20 is wrong three ways.** PS-MPU-6000A §7.3
(Bill of Materials for External Components): *"Charge Pump Capacitor
(Pin 20): Ceramic, X7R, **2.2 nF** ±10%, **50 V**"*, returned to GND in
the typical operating circuit. The board has **C20 = 100 nF** (folded
into the generic decoupling group, LCSC C1525, **16 V**), returned to
**3V3**, not GND. Abs-max on CPOUT is 30 V (§6.4) — the pump runs well
above VDD, which is why InvenSense demands a 50 V part; a 16 V 0402
across CPOUT sees a sustained over-rating, and 45× the specified
capacitance slows the MEMS drive pump's start. On the gyro the
aircraft depends on. What's fixable where: **value and rating are a
BOM edit** — split C20 out of the 100 nF row and fit a 2.2 nF ≥50 V
0402 X7R; the wrong return node (3V3 instead of GND) is copper — with
the correct 2.2 nF/50 V part the residual (pump ripple into a
heavily-decoupled rail) is modest; put the GND return on the v2 list.
If the EN fix already forces a board edit, fix this net at the same
time.

**ALREADY PENDING, NOW MANUFACTURER-CONFIRMED — Y1 load caps.** The
Yangxing spec sheet for X50328MSB2GI (YSX530GA series) states **Load
Capacitance: 20 pF** — confirming yesterday's distributor-listing
finding at the document level the review asked for. C17/C18 = 10 pF
gives CL ≈ 8 pF → ~+200–350 ppm. The 10 pF → **33 pF** BOM change
stands, now on manufacturer evidence. (Same sheet: ESR max 60–80 Ω for
8–12 MHz — the SPICE harness's 30 Ω assumption was optimistic but
non-load-bearing.)

Everything else verified clean. If the EN decision is "fix the board,"
bundle all three (EN, C20 net, and nothing else) into one guarded edit
batch and regenerate the fab package; if it's "order and lift pin 7,"
make the two BOM edits (C20 → 2.2 nF/50 V; C17/C18 → 33 pF) in
`fab/2026-08-17c/bom_jlcpcb.csv` before upload.

---

## Pinout verification — the check that motivated this pass

Method: schematic pin-to-net data (analyzer JSON, cross-checked to PCB
pad nets) diffed against manufacturer pin tables, pin by pin.

| Ref | Part | Document | Result |
|---|---|---|---|
| U1 | STM32F405RGT6 (LQFP64) | ST DS8626 Rev (Table 7, p.47ff) **+ ST's official machine-readable pin database** (`STM32_open_pin_data/mcu/STM32F405RGTx.xml`, DBVersion 3.0) | **64/64 match, 0 mismatches** (XML); 52/64 additionally corroborated in the PDF table text — the other 12 rows are PDF text-extraction artifacts (column drift), not design mismatches. A first-pass text parse *appeared* to show pin 19=PA4; the official XML settles it: 19=VDD, 20=PA4, exactly as the schematic has it |
| U2 | TPS54336ADDA (SO PowerPAD-8) | TI SLVSCD5D, Table 1 (p.3) | **9/9 match incl. thermal pad→GND.** Worth recording: the reviewer's prior expectation (TPS54331 order: 3=EN, 7=GND, 8=PH) was **wrong** — the 336A DDA package is 3=PH, 4=GND, 7=EN, 8=SS, and the schematic used the right one. The datasheet check vindicated the schematic |
| U4 | MPU-6000 (QFN-24) | PS-MPU-6000A Rev 3.4 (§6 pin table, §7.3 BoM) | **All 13 connected pins match.** SPI directions correct (SDO→MISO, SDI←MOSI, SCLK←SCK, /CS←PA4). CLKIN and FSYNC grounded per "connect to GND if unused." RESV pins 19/21/22 ("do not connect") verified **unconnected on the PCB** pad-net data. AUX_DA/AUX_CL floating (acceptable, master unused) |
| U5 | USBLC6-2SC6 (SOT-23-6) | UMW datasheet (pin-identical clone; see gaps) | **6/6 match**: 1=I/O1, 2=GND, 3=I/O2, 4=I/O2, 5=VBUS, 6=I/O1; D− through 1/6, D+ through 3/4, pass-through pairing correct |
| U6 | MT3608 (SOT-23-6) | Aerosemi datasheet (pin description, p.2) | **6/6 match.** EN tied to IN(3V3): *explicitly sanctioned* — "When not used, connect EN to the input supply for automatic startup." The contrast with U2's EN is the lesson of this whole pass: same wiring pattern, one part permits it, one forbids it |

## Derating vs datasheet limits (operating point → limit)

| Point | Actual | Limit (doc) | Margin |
|---|---|---|---|
| U2 VIN | 16.8 V (25.2 V 6S corner) | 4.5–28 V rec., 30 V abs (SLVSCD5D §6.1/6.3) | ✔ (6S corner 10% under rec. max — thin but inside) |
| **U2 EN** | **16.8 V** | **6 V abs-max** | **✘ VIOLATION — the blocker** |
| U2 BOOT-PH | 0.1 µF C3 across BOOT-PH | 7.5 V abs; 0.1 µF per §8 | ✔ |
| U1 VDD/VBAT | 3.3 V | 1.8–3.6 V | ✔ |
| U1 VCAP_1/2 | 2.2 µF (C11/C12) | 2.2 µF required (DS8626 §3.17/Table 16) | ✔ |
| U4 VDD | 3.3 V | 2.375–3.46 V op., 6 V abs | ✔ |
| U4 REGOUT | 100 nF→GND (C19) | 0.1 µF (§7.3) | ✔ |
| **U4 CPOUT** | **100 nF 16 V → 3V3 (C20)** | **2.2 nF 50 V → GND (§7.3); CPOUT 30 V abs** | **✘ value 45×, rating exceeded, wrong return** |
| U5 VBUS | USB 5 V (clamp-only rail) | 5.25 V op. | ✔ |
| U6 IN/EN | 3.3 V | 26 V abs | ✔ |
| U6 SW | 5 V rail + diode | 30 V abs, 28 V swing | ✔ |
| Y1 drive/load | CL fitted 8 pF | **CL spec 20 pF** | ✘ off-spec (pending 33 pF BOM fix) |
| C1 bias | 16.8 V | verified 2026-08-18 (own doc, reviewer-reproduced) | ✔ |
| C2/C25/C26 | 3.3/5 V on 25 V parts | — | ✔ |
| SS34 (D1) | 16.8 V reverse | 40 V | ✔ |
| AO3400A (Q1) | 5 V switched | 30 V, 5.7 A | ✔ |

## Lifecycle per MPN

| Part | Status | Evidence / note |
|---|---|---|
| STM32F405RGT6 | **Active** — "product in full production," DS8626 Rev 12 dated March 2026 | **Stock alarm:** three sources three numbers — JLCPCB parts index **29**, LCSC retail page **297**, yesterday's check 264. The order sheet's stock-STOP is load-bearing; check the live number in the assembly-matching screen, not any cached one |
| MPU-6000 | **Discontinued at TDK InvenSense** (long-EOL line; no current manufacturer product page) — China distributor stock only, consistent with its price premium | Already David's explicit keep-for-v1 decision (2026-08-17). v2's ICM-42688-P plan is also the lifecycle fix |
| TPS54336ADDA | Active (TI still publishes SLVSCD5D; product page not re-verified) | 245 units at last live check — thin, existing STOP covers it |
| MT3608 | Active, massively stocked | |
| USBLC6-2SC6 (C7519) | Active | **Confirm manufacturer at part matching**: C7519 is listed as ST, but pin-identical clones (UMW etc.) circulate under the same MPN; any of them works electrically (pinout verified), the BOM just shouldn't silently ship a clone if ST was specified |
| X50328MSB2GI | Active (YXC current series) | |
| MTQH322510S100MBT | Unknown — **no datasheet found** (see gaps) | Stays a "David sanity-checks" line, as the BOM already says |

## What this pass could not verify (honest gaps)

- **L1/L2 (MTQH322510S100MBT):** no manufacturer datasheet located
  anywhere; Isat 2.2 A remains a parametric-listing figure. If a
  documented-alternative matters, Sunlord/Cjiang molded 3225 parts with
  published curves exist at similar spec.
- **J3 (Amphenol 12401548E4):** drawing not fetched; footprint
  compatibility was already established geometrically against the
  assembler's own footprint DB (2026-08-18 doc), which is the stronger
  check for the ordering question.
- **U5 document provenance:** verification used a pin-identical clone
  manufacturer's datasheet (UMW) because ST's site refuses automated
  download; the pinout is the industry-standard USBLC6-2SC6 arrangement.
- **DS8626 Table 7 text extraction** is partially mangled by pdftotext
  (12 of 64 rows); ST's official pin XML — machine-readable,
  maintained by ST for CubeMX — was used as the authoritative
  cross-check and agrees with the schematic on all 64.
- Passive-level datasheets (individual R/C) were not pulled except
  where an IC's application table dictates the value — that's where
  the two real findings came from.

## Files

`datasheets/` now holds: DS8626 (STM32F405, 6.1 MB), PS-MPU-6000A
Rev 3.4, TI SLVSCD5D (TPS54335A/336A), Aerosemi MT3608, UMW
USBLC6-2SC6, YXC X50328MSB2GI spec, ST's STM32F405RGTx.xml pin data,
plus extracted text. Left untracked by git (regenerable; sources cited
above).

## Premise correction executed with this pass

`projects/Build Plan — 3D Printed Drone with Custom PCB.md` line 93's
stale two-board narrative ("…and it never flies") contradicted the
Locked Configuration's one-board decision (line 41) and had already
steered at least three reviews into "fine for a bench board"
triage — documented in `FLIGHT-RISK-REVIEW.md`. The paragraph is now
replaced with a visible correction note; the surviving guidance
(generous outline, 4-layer, ground-plane rules) is retained. This
report was written flight-board-first throughout.
