---
type: analysis
status: current
created: 2026-08-17
tags: [stevie, hardware, sourcing, cost]
---

# U2 stock + Extended-fee audit — 2026-08-17

Two questions, one pass: is the main regulator actually buyable, and how
many of the per-part setup fees can be removed without compromising the
design.

## 1. U2 IS IN STOCK — the previous batch's bottleneck #1 was wrong

**TPS54336ADDA, LCSC C1355769 — 245 in stock, ships now.**

| Qty | Unit price |
|---|---|
| 1+ | $1.0689 |
| 10+ | $0.8633 |
| 30+ | $0.7605 |
| 100+ | $0.6593 |
| 1000+ | $0.5663 |

The previous batch listed "U2 may be out of stock" as the single top
bottleneck. **That was wrong.** It came from a search-result snippet
rather than the part page, and the part page — fetched directly this
time — shows stock. The lesson is the one this project keeps relearning:
a snippet is not a source.

**One real caveat remains: 245 units is a thin buffer** for a part with
no drop-in alternate on this footprint. It is fine for a prototype run of
5, and it is not something to rely on for a production batch without
checking again.

## 2. Extended-part audit

JLCPCB charges a one-off setup fee per Extended part. The BOM had six or
more. Each was checked for a Basic substitute that does not compromise
the design.

| Ref | Part | Status | Verdict |
|---|---|---|---|
| **Y1** | 8 MHz crystal | **Extended → BASIC** | **Fee removed.** See below. |
| U1 | STM32F405RGT6 | Extended | **Mandatory.** No Basic MCU is this MCU. |
| U2 | TPS54336ADDA | Extended | **Mandatory.** No Basic part on this footprint; substituting changes the feedback network and the board. |
| U4 | MPU-6000 | Extended, ~$10.42 | **Cannot be swapped for the cheap option — see the analysis below.** Part selection is David's. |
| U5 | USBLC6-2SC6 | Extended per our data | **Verify live.** Widely reported as Basic on JLCPCB; our Basic snapshot is only 692 entries and clearly incomplete. Worth one page check — it may be a free fee. |
| U6 | MT3608 | Extended | Mandatory for the 5 V boost; ~$0.06–0.10 part cost, so the fee dominates it. |
| C1 | 10 µF 50 V 1210 | Extended | **Mandatory.** No 1210 case appears in the Basic library at all, and the case size is the point (see the DC-bias reasoning). |
| C23 | 7.5 nF | Extended | **Not substitutable.** Regulator loop compensation. |
| R1, R12 | 31.6 k, 73.2 k | Extended | **Not substitutable.** These are the feedback dividers that set the 3.3 V and 5 V rails. Changing them changes the output voltage. |
| L1, L2 | 10 µH | Extended | **Not substitutable on inductance alone.** Saturation current and DCR decide whether a buck inductor works; the Basic library carries no 10 µH power inductor anyway. |
| J3 | USB-C | Unresolved | Footprint is an Amphenol part; the matching JLCPCB component is still unconfirmed. |

### Fee delta achieved this batch: one

**Y1 moved from Extended to Basic**, and it came free with a fix that was
needed anyway. The board carried a **4-pin 3225** crystal footprint under
a **2-pin** schematic symbol — which is why Y1's pads 3 and 4 showed up
as permanently unmatched in every sync. The only 8 MHz part in the Basic
library (C115962) is a 2-pin SMD-5032. Re-footprinting to
`Crystal_SMD_5032-2Pin_5.0x3.2mm` fixed the pad mismatch *and* removed a
setup fee.

That is the only safe removal. Everything else is either the specific
functional part or a value that sets a voltage.

### The honest limit on this audit

Basic/Extended classification here came from a **community GitHub
snapshot** of JLCPCB's Basic library — 692 entries, not authoritative,
not live. It has no 1210 capacitors, no power inductors and no USBLC6,
which is more likely incompleteness than genuine absence. **Every
classification in this table must be re-checked against live JLCPCB
pages at order time.** The one figure verified against a live page is
U2's stock, above, plus D1 (C8678, confirmed Basic) from the previous
batch.

## 3. U4 (MPU-6000) — why the obvious saving is not available

At **~$10.42** the IMU is **47 %** of per-board component cost ($22.20 —
see the budget doc, which computes the same figure). An earlier version
of this line said "two-thirds", which did not match the budget written
in the same batch; 47 % is the arithmetic.
The obvious move is the MPU-6050 at a fraction of the price. **It is not
a drop-in**, for two concrete reasons:

1. **The MPU-6050 is I²C-only.** The MPU-6000 supports both SPI and I²C;
   the 6050 dropped SPI. This firmware's driver
   (`engineering/drone-firmware/src/mpu6000.c`) talks over **SPI1**, and
   the board routes it that way. Swapping the part means rewriting the
   driver and re-routing the sensor.
2. **The pinout differs on the pins that matter — but not the way an
   earlier version of this document said.** It claimed the 6050 has a
   separate `VLOGIC` where the 6000 has a single `VDD`; that is wrong.
   Both are QFN-24 4×4, share one datasheet, and both have a separate
   I/O supply on pin 8 — InvenSense simply calls it `VDDIO` on the 6000
   and `VLOGIC` on the 6050. The real differences are pin 9 (AD0/SDO vs
   AD0), pin 22 (`/CS` vs NC) and pins 23/24 (SCLK/SDI vs SCL/SDA) —
   i.e. exactly the SPI pins. Reason 1 is correct and sufficient on its
   own.

A performance argument is often made here — that I²C cannot sustain an
8 kHz gyro update — and **it does not apply to this vehicle**. STEVIE's
loop runs at **2 kHz** (`MAIN_LOOP_TICK_US = 500`), and a 6-byte read
over 400 kHz I²C takes roughly 225 µs, giving about a 4.4 kHz ceiling.
That is comfortably above what this firmware asks for. The argument is a
real one for 8 kHz racing firmware and it should not be used to defend
this BOM line.

**If cost matters more than the existing driver**, the honest options are
SPI-capable and still cheaper — the MPU-6500 or ICM-42688 class of part.
Both need a new driver and a datasheet pass, so it is a real piece of
work, not a BOM edit. **This is a David decision** (part selection), and
it is presented here as a costed choice rather than made unilaterally.

## Bottom line

- **U2 is buyable.** Bottleneck #1 is cleared, with a note that 245 units
  is thin.
- **One setup fee removed** (Y1), as a side effect of fixing a real
  footprint defect.
- **No other Extended line has a *confirmed* Basic substitute.** Note
  the careful wording: R1/R12/C23/L1/L2 are constrained by their VALUE,
  not by being a specific manufacturer's part — any Basic-library 0402
  1% part at the same value is a drop-in. What is unknown is whether
  such an MPN exists in the Basic library, and this audit cannot tell,
  because its snapshot is 692 entries and admittedly incomplete. That is
  a gap in the data, not a proven blocker.
- **The largest single cost, U4, is a design decision with a driver
  attached**, not a sourcing choice.
