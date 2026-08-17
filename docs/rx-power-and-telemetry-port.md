# RX power rail + telemetry port — 2026-08-17

Executes the lead decisions: a dedicated 5 V supply for the receiver
alone, and a telemetry header on the board edge.

## The boost IC: MT3608 (LCSC C84817)

| Property | Value | Source |
|---|---|---|
| Topology | Boost (step-up), current-mode, 1.2 MHz fixed | LCSC product page |
| Input range | **2 V – 24 V** | LCSC product page |
| Output | 0.6 V – 28 V, adjustable via feedback divider | LCSC product page |
| Switch current limit | 4 A internal | LCSC product page |
| Quiescent current | **100 µA (PFM)**, 1.6 mA typical | LCSC product page |
| Package | SOT-23-6 | LCSC / JLCPCB |
| JLCPCB library | **Extended** (not Basic) — attracts a setup fee | JLCPCB part page C84817 |
| Stock | 162,224 | LCSC, checked 2026-08-17 |
| Unit price | $0.1143 @1+, $0.0995 @1000+ | LCSC |
| KiCad symbol | `Regulator_Switching:MT3608` — **native, no library work** | local symbol search |

Selection criteria were the same ones that picked the MPU-6000 and the
IST8310: a real KiCad symbol must already exist, and the part must be
orderable at JLCPCB. Both verified rather than assumed.

## Input side: 3.3 V, not battery — and the datasheet decides it

The task allowed either. **The MT3608's 24 V absolute input maximum
settles it: this board is 6S-rated, and 6S peak is 25.2 V.** Feeding it
from the battery would exceed the part's input rating by 1.2 V at a full
6S charge — not a margin question, a destroyed-part question.

So the input is the existing 3.3 V rail, which is what makes this a
genuine *boost* rather than a second buck.

Secondary reasons, all pointing the same way:

- **No new high-voltage switching node.** The layout rules already
  require the buck kept away from the IMU. A second battery-side switcher
  would add a second aggressor near a sensor that has to resolve
  milli-g. A 3.3 V-input boost is a far quieter neighbour.
- **Efficiency cost is negligible.** Double conversion runs ~76 %
  end-to-end versus ~90 % for a direct battery buck. At 100 mA × 5 V =
  0.5 W that is ~0.1 W. Irrelevant against four motors.
- **Load on the 3.3 V rail is comfortable.** 100 mA at 5 V ≈ 160 mA drawn
  from 3.3 V after losses. The TPS54336A supplying it is a 3 A part.

### A note on the stated rationale

The lead decision cited "the industry-standard whoop answer" from the
shopping-list research. That research is for **1S whoops**, where the
battery is 3.7 V and boosting to 5 V is the only option. This vehicle is
4S/350 mm class, where the battery is *above* 5 V and the same conclusion
would normally imply a buck.

The conclusion still holds here — but for a different reason than the
one cited: not "1S needs a boost", but "the 3.3 V rail is the only input
this part can legally take on a 6S-rated board". Recorded because a
future reader checking the whoop reference would find it doesn't apply
to this airframe, and should not conclude the part choice is wrong.

## Feedback divider

MT3608 regulates FB to 0.6 V, so `Vout = 0.6 × (1 + R12/R13)`.

```
R12 = 73.2 kΩ (E96)   R13 = 10.0 kΩ
Vout = 0.6 × (1 + 7.32) = 4.992 V
```

Within 0.2 % of 5.00 V using standard values. Receivers tolerate
4.75–5.25 V comfortably; this sits mid-band.

## Supporting parts

| Ref | Value | Why |
|---|---|---|
| L2 | 10 µH, 1210 | Same footprint and value as L1 — **one fewer distinct BOM line**. At 1.2 MHz, 3.3→5 V, ripple ≈ 0.09 A, comfortably inside the 4 A limit |
| C25 | 10 µF 16 V 0805 | Input bulk |
| C26 | 22 µF 16 V 0805 | Output bulk — boosts have discontinuous output current, so output capacitance matters more than input |
| D1 | SS34 Schottky, SMA | Catch diode. The MT3608 is **non-synchronous**, so an external diode is mandatory, not optional |

## RX data: 3.3 V logic on a 5 V-powered receiver

CRSF data stays on the existing `CRSF_TX`/`CRSF_RX` nets at **3.3 V
logic**, unchanged. The receiver takes 5 V for *power* and 3.3 V for
*signalling* — which is the standard ELRS arrangement.

Verification, per the task's instruction to cite a vendor page:
**RadioMaster's ER-series receiver documentation specifies a 5 V input
supply while the UART signalling is 3.3 V-level**, which is why ELRS
receivers are routinely wired to 3.3 V flight-controller UARTs while
being powered from a 5 V BEC.

> **Confidence note, stated rather than glossed.** This was checked
> against vendor documentation for the receiver *class*, not against the
> specific unit David will buy — no receiver has been selected yet (it is
> a David-only purchasing decision). **Confirm the exact model's logic
> level before first power-on**; it is one line in that model's manual,
> and it is on the bring-up runbook's Stage 7 checklist.

This is precisely the ambiguity the lead decision set out to kill with
hardware: whatever the receiver wants for power, the board now supplies a
proper 5 V rail for it instead of hoping 3.3 V is enough.

## Connectors added

| Ref | Pins | Net assignment |
|---|---|---|
| **J7** | 2 | `5V_RX`, `GND` — dedicated receiver power pair, per the lead decision |
| **J8** | 3 | `TELEM_TX`, `GND`, `3V3` — telemetry header, board edge |

`TELEM_TX` lands on **PC10 = USART3_TX**, exactly as
`stm32f405-pin-assignment.md` already allocated. No pin reassignment was
needed; the plan had the port reserved and this connects it.

This closes re-evaluation finding §5.2, which flagged that the firmware
had a complete telemetry output path with **no port on the board**. It
now has one.

## ERC

Verbatim, from an independent `kicad-cli` run (not the MCP wrapper):

```
ERC report (2026-08-17T08:42:40, Encoding UTF8)
 ** ERC messages: 0  Errors 0  Warnings 0
```

One real defect surfaced getting there and is worth recording: **PC10
carried a stale `no_connect` flag** from when it was an unused pin. Net
labels alone would not have removed it, and the result — a pin marked
"deliberately unconnected" while actually driving a header — is exactly
the class of thing that reaches fabrication silently. ERC caught it;
the flag was removed.
