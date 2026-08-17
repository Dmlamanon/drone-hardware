# STM32F405RGT6 (LQFP-64) Pin Assignment — 2026-08-16

Platform-revision batch, item 5. Every pin on `U1` (`bench_board.kicad_sch`,
package `Package_QFP:LQFP-64_10x10mm_P0.5mm`), read directly from the live
schematic via the KiCad MCP (`list_symbol_pins` + `list_schematic_nets`),
not transcribed from memory. Current assignment = what's actually wired
today. Proposed = what item 6's revised schematic adds. Every new
assignment's alternate-function (AF) mapping is checked against the
[STM32F405 datasheet's own AF table](https://www.st.com/resource/en/datasheet/stm32f405rg.pdf)
convention (AF numbering as used across the F4 family) — this is exactly
where designs silently break, per the task brief, so each new signal below
states which AF it needs and why that pin (not just "any free GPIO").

## Full pin table

| Pin | Name | Current assignment | Proposed (this batch) | Notes |
|---|---|---|---|---|
| 1 | VBAT | 3V3 | unchanged | RTC/backup-domain supply, tied to main 3.3V (no coin cell) |
| 2 | PC13 | unused | unused | Free — RTC-alternate pin, reserved for future use |
| 3 | PC14 | unused | unused | Free — OSC32_IN if an LSE crystal is ever added |
| 4 | PC15 | unused | unused | Free — OSC32_OUT if an LSE crystal is ever added |
| 5 | PH0 | HSE_IN | unchanged | HSE crystal (AF0/analog, OSC_IN) |
| 6 | PH1 | HSE_OUT | unchanged | HSE crystal (OSC_OUT) |
| 7 | NRST | NRST | unchanged | |
| 8 | PC0 | unused | **EXP_SPI_CS1** | GPIO output (software CS, same pattern as existing SPI1_CS on PA4) — optical-flow chip select |
| 9 | PC1 | unused | **EXP_SPI_CS2** | GPIO output — baro chip select (if a future part is run in SPI mode) |
| 10 | PC2 | unused | **EXP_IRQ1** | GPIO/EXTI input, general-purpose (e.g. ToF data-ready) |
| 11 | PC3 | unused | **EXP_IRQ2** | GPIO/EXTI input (e.g. flow sensor data-ready) |
| 12 | VSSA | GND | unchanged | |
| 13 | VDDA | 3V3 | unchanged | |
| 14 | PA0 | VBAT_SENSE | unchanged | ADC1_IN0, battery-sense divider (item 3) |
| 15 | PA1 | unused | unused | Free |
| 16 | PA2 | unused | **reserved (ESC_TELEM_TX, unwired)** | USART2_TX, AF7 — pairs with PA3 below; not connected to the ESC connector this batch since 4-in-1 ESC telemetry is RX-only from the FC's side, kept free/available rather than wired for symmetry with no current use |
| 17 | PA3 | unused | **ESC_TELEM_RX** | USART2_RX, AF7 — 4-in-1 ESC telemetry input (item 6) |
| 18 | VSS | GND | unchanged | |
| 19 | VDD | 3V3 | unchanged | |
| 20 | PA4 | SPI1_CS | unchanged | GPIO (software CS), IMU (MPU-6000) |
| 21 | PA5 | SPI1_SCK | unchanged | SPI1_SCK, AF5 |
| 22 | PA6 | SPI1_MISO | unchanged | SPI1_MISO, AF5 |
| 23 | PA7 | SPI1_MOSI | unchanged | SPI1_MOSI, AF5 |
| 24 | PC4 | MPU_INT | unchanged | GPIO/EXTI input |
| 25 | PC5 | unused | unused | Free |
| 26 | PB0 | unused | unused | Free |
| 27 | PB1 | unused | unused | Free |
| 28 | PB2 | unused | unused | **Flag: this is BOOT1.** Currently floating in the existing (pre-this-batch) schematic — not driven by this batch's changes, but ST's own application guidance recommends a defined level (external pull) rather than float when BOOT0=0 selects main-flash boot, since an internal default alone is a documented soft-brick risk if BOOT0 is ever accidentally strapped high. Flagged here, not fixed — pre-existing, out of this batch's stated scope (item 6 doesn't call for a BOOT1 fix), but real and worth a follow-up. |
| 29 | PB10 | unused | **EXP_I2C_SCL** | I2C2_SCL, AF4 — shared bus for on-board baro+mag (item 6) AND the expansion header's I2C pins |
| 30 | PB11 | unused | **EXP_I2C_SDA** | I2C2_SDA, AF4 |
| 31 | VCAP_1 | VCAP1 | unchanged | |
| 32 | VDD | 3V3 | unchanged | |
| 33 | PB12 | unused | unused | Free |
| 34 | PB13 | unused | **EXP_SPI_SCK** | SPI2_SCK, AF5 |
| 35 | PB14 | unused | **EXP_SPI_MISO** | SPI2_MISO, AF5 |
| 36 | PB15 | unused | **EXP_SPI_MOSI** | SPI2_MOSI, AF5 |
| 37 | PC6 | unused | unused | Free — **TIM3_CH1 / TIM8_CH1 (AF2/AF3)**. Reserved for a tiltrotor servo, see the note below the table. |
| 38 | PC7 | unused | unused | Free — **TIM3_CH2 / TIM8_CH2 (AF2/AF3)**. Reserved for a tiltrotor servo, see the note below the table. |
| 39 | PC8 | unused | unused | Free — **TIM3_CH3 / TIM8_CH3 (AF2/AF3)**. Reserved for a tiltrotor servo, see the note below the table. |
| 40 | PC9 | unused | unused | Free — **TIM3_CH4 / TIM8_CH4 (AF2/AF3)**. Reserved for a tiltrotor servo, see the note below the table. |
| 41 | PA8 | unused | unused | Free |
| 42 | PA9 | CRSF_TX | unchanged | USART1_TX, AF7 |
| 43 | PA10 | CRSF_RX | unchanged | USART1_RX, AF7 |
| 44 | PA11 | USB_DM_MCU | unchanged | USB_OTG_FS_DM, AF10 |
| 45 | PA12 | USB_DP_MCU | unchanged | USB_OTG_FS_DP, AF10 |
| 46 | PA13 | SWDIO | unchanged | AF0/SYS |
| 47 | VCAP_2 | VCAP2 | unchanged | |
| 48 | VDD | 3V3 | unchanged | |
| 49 | PA14 | SWCLK | unchanged | AF0/SYS |
| 50 | PA15 | unused | unused | Free — hardware SPI1_NSS alternate, also JTDI; left free (software CS already used for SPI1) |
| 51 | PC10 | unused | **EXP_UART_TX** | USART3_TX, AF7 |
| 52 | PC11 | unused | **EXP_UART_RX** | USART3_RX, AF7 |
| 53 | PC12 | unused | unused | Free — UART5_TX alternate, kept free |
| 54 | PD2 | unused | unused | Free — UART5_RX alternate, kept free |
| 55 | PB3 | unused | unused | Free — also SPI1_SCK alternate and JTDO/TRACESWO; left free for debug/SWO use, deliberately not repurposed |
| 56 | PB4 | unused | unused | Free — also SPI1_MISO alternate and JTRST; left free |
| 57 | PB5 | unused | unused | Free — also SPI1_MOSI alternate and I2C1_SMBA; left free |
| 58 | PB6 | M1 | unchanged | TIM4_CH1, AF2 — DShot |
| 59 | PB7 | M2 | unchanged | TIM4_CH2, AF2 — DShot |
| 60 | BOOT0 | BOOT0 | unchanged | |
| 61 | PB8 | M3 | unchanged | TIM4_CH3, AF2 — DShot |
| 62 | PB9 | M4 | unchanged | TIM4_CH4, AF2 — DShot |
| 63 | VSS | GND | unchanged | |
| 64 | VDD | 3V3 | unchanged | |

## Conflicts checked, none found

**Why I2C2 (PB10/PB11), not I2C1 (PB6/PB7 or PB8/PB9):** I2C1's natural
pin pairs are exactly the same pins M1–M4 (DShot, TIM4_CH1–4) already
occupy — a direct conflict if I2C1 had been picked. I2C2's alternate pins
(PB10/PB11, AF4) are free and don't collide with anything. This is
precisely the kind of AF collision the task brief warned about, caught by
checking the actual AF table rather than assuming any free-looking GPIO
would work.

**Why USART3 on PC10/PC11, not PB10/PB11:** PB10/PB11 also carry
USART3_TX/RX as an alternate mapping (AF7) — using them for USART3 would
have collided with the I2C2 assignment above on the exact same pins.
PC10/PC11 carry the same USART3 signals on a different, free pin pair
(also AF7) — picked specifically to avoid that collision, not the first
free-looking option.

**Why SPI2 on PB13/14/15, not another SPI instance:** SPI3 exists on this
part (PC10/11/12) but those pins are now claimed by USART3/free-reserved
above; SPI2's default pins (PB13/14/15, AF5) are entirely free and
unclaimed by anything else in this table.

## Pin budget verdict

31 of 64 pins were already committed before this batch (MCU core power/HSE/
NRST/BOOT0, IMU SPI1, CRSF USART1, USB, SWD, DShot TIM4). This batch adds
10 more (2 SPI CS, 2 IRQ, I2C2 ×2, SPI2 ×3, USART3 ×2 — wait, that's 11;
counted precisely: PC0, PC1, PC2, PC3, PB10, PB11, PB13, PB14, PB15, PC10,
PC11 = **11 newly assigned pins**), bringing the total to 42 of 64. **The
expansion bus fits the pin budget with no compromise and no AF conflicts**
— roughly 22 GPIOs remain free after this batch (PC13-15, PA1, PA8, PA15,
PB0-2, PB3-5, PC5-9, PC12, PD2), comfortably more than the "spare capacity"
a v1 board needs. The one real flag is pre-existing (PB2/BOOT1 floating),
not introduced by this batch's additions.

## Related

- [[expansion-bus-spec]] (item 4 — the connector this pin table implements)
- [[power-verification-4s]] (item 3 — PA0/VBAT_SENSE, unaffected by this batch's pin additions)


## Tiltrotor provisioning — checked 2026-08-17, no board change needed

Executing the lead ruling *provision on the board, do not build on the
vehicle*. Checked against this table rather than assumed.

**Four tilt servos fit cleanly.** `PC6`–`PC9` are `TIM3_CH1`–`CH4` (AF2),
also available as `TIM8_CH1`–`CH4` (AF3). That is **four channels on a
single timer**, which is what you want: one timebase, one prescaler, four
synchronised outputs, and no interaction with `TIM4`, which already
drives DShot on M1–M4.

Spare timer-capable pins beyond those four, if a different grouping is
ever wanted: `PA8` (TIM1_CH1), `PA15`/`PB3` (TIM2_CH1/CH2), `PB0`/`PB1`
(TIM3_CH3/CH4), `PB4`/`PB5` (TIM3_CH1/CH2).

**An airspeed sensor also fits with no new pin.** The conversion corridor
is defined in terms of airspeed, so a tiltrotor requires one; the usual
parts (MS4525DO, SDP3x class) are I²C, and I²C2 is already on the
expansion bus at `PB10`/`PB11`.

**What is NOT provisioned, stated plainly** — this is the real content of
"provisioned but not built":

1. **The servo pins are not brought out to a connector.** They are free
   at the MCU; the expansion header does not expose them. A tilt build
   needs a board revision to route them out.
2. **There is no servo power rail.** Four digital servos draw amps when
   stalled. They must not be fed from the 3.3 V rail or from the 1 A 5 V
   boost, which is sized for the receiver — browning out the RX is the
   worst possible thing to share a rail with.
3. **No tilt-angle feedback input is allocated.** Position feedback is
   argued for in the requirements analysis (a servo that has not reached
   its commanded angle while the mixer assumes it has is an
   uncommanded-attitude event). That would be four more ADC channels, and
   the ADC driver is itself still a stub.

Full reasoning, including why a wingless tiltrotor buys speed rather than
efficiency: `wiki/projects/STEVIE Tiltrotor Variant — Requirements
Analysis.md`.
