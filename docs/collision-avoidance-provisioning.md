# Collision-avoidance provisioning — 2026-08-17

Audit of whether the expansion bus can actually carry the two sensors the
lead decision calls for, **checked against the real pin budget and the
real datasheets rather than from memory**, plus the schematic changes
needed to make it true.

Lead decision being executed: collision avoidance = ground-station
separation (software, later) + expansion-bus ranging sensors. **No new
compute on the board.**

## Verdict

**Both sensors fit — but only after resolving two real conflicts found by
this audit.** Neither would have survived to fabrication silently; both
are fixed in the schematic now.

## The two sensors

| | Downward ToF | Forward lidar |
|---|---|---|
| Part | **VL53L1X** (ST) | **TF-Luna** (Benewake) |
| Interface | I²C, addr **0x29** (reprogrammable) | **UART** default, 115200 baud (I²C selectable) |
| Range | ~30 mm – 4 m | 0.2 – 8 m |
| Field of view | ~27° cone (default ROI) | **2°** |
| Supply | 2.6–3.5 V → **3.3 V** | **5 V ±0.1 V**, LVTTL 3.3 V logic |
| Current | 16–18 mA measuring, 6 µA standby | ≤70 mA avg, **150 mA peak** |
| Price | **$14.95** (Adafruit breakout, DigiKey) | **$28.90** (Seeed Studio) |
| Source | [ST VL53L1X datasheet](https://www.st.com/resource/en/datasheet/vl53l1x.pdf) | [TF-Luna manual](https://files.seeedstudio.com/wiki/Grove-TF_Mini_LiDAR/res/SJ-PM-TF-Luna-A03-Product-Manual.pdf) |

**Combined sensor cost: ~$43.85** plus wiring.

## Conflict 1 — PC10 was double-allocated (found, resolved)

`stm32f405-pin-assignment.md` and `expansion-bus-spec.md` both allocate
**PC10 (USART3_TX)**: the pin doc as the telemetry port, the bus spec as
expansion pin 10 "UART_TX (spare)". Item 1 of this batch wired the
telemetry header to PC10, which made the collision concrete.

**Resolution: split USART3 by direction.** This works because both users
are unidirectional, in opposite directions:

| Direction | Pin | User | Rate |
|---|---|---|---|
| TX | PC10 | Telemetry out to the ground station | 115200 |
| RX | PC11 | TF-Luna in | 115200 |

USART3 is full-duplex, so TX and RX are independent hardware. They share
one baud-rate register — and **both want 115200 anyway**, which is the
firmware's existing `TELEM_BAUD` and the TF-Luna's factory default. That
is a genuine fit, not a compromise squeezed to work.

**What it costs:** the expansion bus loses its *bidirectional* spare
UART; it is now RX-only. That forecloses a companion-computer link on
this header. Acceptable, and consistent with the Build Plan, which puts
the companion computer at Stage 8 and states tracking moves to a ground
station in v1. **If a bidirectional companion link is ever wanted, this
is the decision to revisit** — it would need a different pin pair, and
PA9 (USART1_TX, currently unused because CRSF is RX-only) is the obvious
candidate.

## Conflict 2 — the TF-Luna needs 5 V; the bus only had 3.3 V (found, resolved)

The expansion header as specified carries **3.3 V only**. The TF-Luna
requires **5 V ±0.1 V** — a tight tolerance, and 3.3 V is nowhere near
it. As specified, the forward lidar simply could not be powered.

**Resolution: expansion pin 13 = 5 V**, fed from the new MT3608 rail
added in item 1.

### Power budget for that decision

| Load | Current @5 V |
|---|---|
| Receiver | ~100 mA (assumed; no RX selected yet) |
| TF-Luna average | 70 mA |
| **Total average** | **~170 mA** |
| TF-Luna peak (transient) | +80 mA over average |

Against the MT3608's 4 A switch limit this is not close to binding. On
the input side, 170 mA at 5 V ≈ 0.85 W, ≈ **300 mA drawn from 3.3 V**
after boost losses — comfortable for the TPS54336A (3 A). C26's 22 µF
output capacitance covers the 150 mA peaks.

### A deliberate deviation from the lead decision, flagged

The lead decision said the 5 V rail was "for the receiver **alone**".
Extending it to the expansion header is a change. The reasoning: the
decision's stated *purpose* was to kill the 3.3 V-supply question with
hardware, and the forward lidar has exactly the same problem. Leaving the
rail RX-only would mean item 2's own sensor cannot be powered.

Recorded here rather than made silently. If David wants the rails
genuinely separate, pin 13 can be depopulated — it is one header pin, not
a design change.

## No I²C address conflict

Checked, all three devices that could share I²C2:

| Device | 7-bit address | Source |
|---|---|---|
| IST8310 magnetometer | **0x0E** (CAD0/CAD1 floating) | datasheet §6.1.1 |
| VL53L1X ToF | **0x29** | ST datasheet |
| TF-Luna *(if run in I²C mode)* | 0x10 | Benewake manual |

All distinct. **No I²C mux is needed** — the task allowed a mux footprint
if required, and it is not. Worth noting the VL53L1X's address is
reprogrammable at runtime, so even a future second ToF is solvable in
firmware rather than hardware.

## Interrupt lines

Both sensors get one, as the task required:

| Line | MCU pin | Intended use |
|---|---|---|
| IRQ1 | PC2 | VL53L1X data-ready (GPIO1) |
| IRQ2 | PC3 | Spare / TF-Luna, though it has no interrupt output — it free-runs at its frame rate |

The TF-Luna does not actually need an interrupt; it streams continuously
over UART. IRQ2 therefore stays genuinely spare, which is the honest
description rather than claiming it is allocated.

## Final expansion header (J9, 14-pin)

| Pin | Signal | MCU | Changed? |
|---|---|---|---|
| 1 | 3V3 | — | |
| 2 | GND | — | |
| 3 | I2C_SCL | PB10 | |
| 4 | I2C_SDA | PB11 | |
| 5 | SPI_SCK | PB13 | |
| 6 | SPI_MOSI | PB15 | |
| 7 | SPI_MISO | PB14 | |
| 8 | SPI_CS1 | PC0 | |
| 9 | SPI_CS2 | PC1 | |
| 10 | **UART_RX** | PC11 | **was TX+RX; now RX only** |
| 11 | IRQ1 | PC2 | |
| 12 | IRQ2 | PC3 | |
| 13 | **5V** | — | **new** |
| 14 | GND | — | **new** (second return, for signal integrity on a 14-way ribbon) |

## What each sensor actually buys — and the honesty about cones

### Downward ToF (VL53L1X) → landing assist, altitude hold

A ~27° cone looking down at a floor is a genuinely easy problem: the
target is large, flat, perpendicular, and close. This is the sensor that
works well.

**Enables:** precision landing flare, low-altitude hold, ground-proximity
awareness. **Limits:** 4 m ceiling, and it is confused by grass, water,
and direct sunlight — all documented ToF weaknesses, none of them
surprising.

### Forward lidar (TF-Luna) → "brake wall", *not* obstacle avoidance

**The 2° field of view is the single most important number in this
document, and it needs stating bluntly: at 8 m, a 2° cone is about 28 cm
across.** That is a pencil beam. It will reliably detect a wall it is
pointed squarely at. It will **not** see:

- a door frame, pole, tree trunk or wire even slightly off-axis
- anything the vehicle is drifting sideways toward
- anything above or below the beam
- a wall approached at a shallow angle (the beam skips off it)

So this sensor supports a **forward brake wall** — "stop advancing when
something is straight ahead" — and it must not be described as collision
avoidance. Real avoidance needs either multiple beams, a wide-FOV depth
sensor, or vision, none of which are in this design and none of which the
"no new compute on the board" constraint permits.

**Enables:** a firmware limiter that clamps forward pitch when the
straight-ahead range drops below a threshold (item 3 of this batch,
`src/obstacle_brake.c`). That is a real, useful safety net for flying
toward a wall — and it is the honest extent of it.

## What is *not* provisioned

- **Sideways and rearward**: nothing. The vehicle is blind in every
  direction but down and dead-ahead.
- **Drone-to-drone separation**: deliberately not a sensor problem here —
  it is the ground station's job, per the lead decision. Design note:
  `wiki/projects/Ground Station Separation Design.md`.
- **Neither sensor is on the BOM.** Both are expansion-header
  peripherals; the board provisions for them and does not carry them.

## ERC

Verbatim, independent `kicad-cli` run after both conflicts were resolved
and J9 was added:

```
 ** ERC messages: 0  Errors 0  Warnings 0
```

Ten stale `no_connect` flags had to be cleared in the process — every
MCU pin the expansion header now uses was previously marked
"deliberately unconnected". Same class of latent defect as the PC10 flag
found in item 1, and the same reason it matters: a pin cannot be both
intentionally unconnected and driving a header.
