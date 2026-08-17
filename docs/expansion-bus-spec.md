# Expansion Bus Spec — 2026-08-16

Platform-revision batch, item 4. Defines one logical expansion connector
for the 5"-class FC board, covering every sensor class the [[Sensor
Expansion Roadmap]] (item 10) recommends as a future add-on, without
committing this batch to any specific part beyond the on-board baro/mag
decided in item 6. Arduino-compatible header **dropped per David** — this
is a bare pin header, not a shield-form-factor connector.

## Per-sensor-class interface research (cited)

| Sensor class | Interface | Example part | Current (active) | Source |
|---|---|---|---|---|
| Optical flow | **SPI** (4-wire, 2MHz) | PMW3901-class | 6–9mA @ 3.3V | [Pimoroni PIM453 datasheet](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/306/PIM453_Web.pdf), [PX4 sensor guide](https://docs.px4.io/main/en/sensor/pmw3901) |
| ToF rangefinder | **I2C** (up to 400kHz, addr 0x29 default, reprogrammable) | VL53L1X-class | 16–18mA measuring, 6µA standby | [ST VL53L1X datasheet](https://www.st.com/resource/en/datasheet/vl53l1x.pdf) |
| Barometer | **I2C or SPI** (both supported natively) | BMP280 / DPS310-class | ~1.5–1.7µA @ 1Hz sampling (DPS310) | [Infineon DPS310 datasheet](https://www.mouser.com/datasheet/2/196/Infineon_DPS310_DataSheet_v01_02_EN-3161788.pdf) |
| Magnetometer | **I2C** | **IST8310 — decided 2026-08-16, drone-firmware batch item 13** (was open "QMC5883L / IST8310-class" as of this doc's original writing) | Sub-mA class, exact figure not independently confirmed this pass — see note below | [IST8310 Datasheet v1.2](https://intofpv.com/attachment.php?aid=8104) (real PDF, fetched and text-extracted for the driver work). Decisive factor: IST8310 has a real, built-in local KiCad symbol (`Sensor_Magnetic:IST8310`); QMC5883L has none (`search_symbols` returns zero results) — same criterion the MPU-6000 IMU pick already used. Full reasoning and the real driver: `engineering/drone-firmware/src/ist8310.h`. |
| GPS | **UART** (NMEA or UBX, 3.3V logic, 9600–460800 baud configurable) | u-blox M8N/M10-class | 20–45mA (varies: ATGM336H 20–25mA, NEO-6M ~45mA, PSM mode ~11mA) | [ATGM336H/NEO-M8N-MOD specs](https://www.robotics.org.za/NEO-M8N-MOD), [NEO-6M tutorial](https://lastminuteengineers.com/neo6m-gps-arduino-tutorial/) |
| Companion computer link | **UART** | (any companion SBC) | Companion computer has its own power path — link is signal-only, not budgeted on this rail | — |

**Why the magnetometer is the highest-value cheap sensor**: this design
currently has **no yaw reference at all** — `imu_fusion.c`'s complementary
filter (see [[Attitude Filter Methods]]) resolves roll/pitch from the
accelerometer but has nothing to correct gyro yaw drift against. A
magnetometer is the cheapest fix (sub-$2 part, I2C, low pin count) and is
the reason it's called out explicitly here rather than left as "just
another I2C device" — see item 6 for why it's placed on-board rather than
left as an expansion option.

## One logical connector — pinout

Physical: 0.1" pin header, acceptable at this board's 8"×4" (203×102mm)
envelope (per next-task.md item 4's explicit sizing note — no need for a
higher-density connector at this scale). Not Arduino-shield-compatible —
a bare header, per David's decision to drop that option.

| Pin | Signal | MCU pin (see [[stm32f405-pin-assignment]]) | Notes |
|---|---|---|---|
| 1 | 3.3V | — | Shared expansion rail — see budget below |
| 2 | GND | — | |
| 3 | SCL (I2C) | PB10 (I2C2_SCL, AF4) | Shared bus — on-board baro+mag, ToF, and any I2C header device all share this |
| 4 | SDA (I2C) | PB11 (I2C2_SDA, AF4) | |
| 5 | SPI_SCK | PB13 (SPI2_SCK, AF5) | Dedicated second SPI instance — SPI1 is fully claimed by the on-board IMU |
| 6 | SPI_MOSI | PB15 (SPI2_MOSI, AF5) | |
| 7 | SPI_MISO | PB14 (SPI2_MISO, AF5) | |
| 8 | SPI_CS1 | PC0 (GPIO, software CS) | e.g. optical flow |
| 9 | SPI_CS2 | PC1 (GPIO, software CS) | e.g. baro, if run in SPI mode instead of I2C |
| 10 | UART_RX (spare) | PC11 (USART3_RX, AF7) | **CHANGED 2026-08-17:** was UART_TX on PC10. PC10 is now the telemetry port (see `rx-power-and-telemetry-port.md`), so USART3 is split by direction: TX out to telemetry, RX in from a forward lidar. Both want 115200. The bus is therefore **RX-only** and cannot carry a bidirectional companion link — see `collision-avoidance-provisioning.md`. |
| 11 | IRQ1 | PC2 (GPIO/EXTI) | Renumbered 2026-08-17 (e.g. VL53L1X data-ready) |
| 12 | IRQ2 | PC3 (GPIO/EXTI) | Renumbered 2026-08-17. Genuinely spare — the TF-Luna free-runs over UART and has no interrupt output |
| 13 | **5V** | — | **NEW 2026-08-17.** Fed from the MT3608 boost added for the receiver. Required because the TF-Luna needs 5V +-0.1V and the bus was 3.3V-only. Budget and the deliberate deviation from "RX alone" are in `collision-avoidance-provisioning.md` |
| 14 | GND | — | **NEW 2026-08-17.** Second return for signal integrity on a 14-way ribbon |

12 signal/power pins total (3.3V, GND, I2C×2, SPI×4, UART×2, IRQ×2) — the
"I2C, SPI+2CS, spare UART, 3.3V, GND, 2 interrupt GPIOs" set called for in
next-task.md item 4, no more.

## Expansion rail current budget vs. the buck

From [[power-verification-4s]] (item 3): the TPS54331DR replacement buck is
rated 3A, with a provisional total board load (FC core + full expansion
headroom) estimated well under 1A. Concrete peripheral-level numbers,
using the cited currents above for a fully-populated header (worst case —
flow + ToF + baro + mag + GPS all present simultaneously, which is more
than any single roadmap stage in [[Sensor Expansion Roadmap]] actually
proposes at once):

| Load | Current |
|---|---|
| FC core (STM32F405 + on-board MPU-6000, carried over from §7 of [[power-verification-4s]]) | 150–200mA |
| On-board baro + mag (item 6, always populated) | <5mA combined (both are sub-mA/low-mA class per the table above) |
| Optical flow (if populated) | 9mA |
| ToF rangefinder (if populated) | 18mA |
| GPS (if populated) | 45mA (worst-case NEO-6M-class figure, not the lower ATGM336H figure) |
| **Worst-case fully-populated total** | **≈230–280mA** |

Against the buck's 3A rating and the 0.16%-ripple/comfortable-thermal
finding in [[power-verification-4s]], **this is not a binding constraint**
— even the worst-case fully-populated expansion header leaves >10× margin
against the regulator. The real constraint at this current level is
connector/trace current rating, not the regulator — not evaluated further
here since worst-case draw (~280mA) is trivial for 0.1" headers and any
reasonable trace width at this board size.

## Related

- [[power-verification-4s]] · [[pin-budget-audit]] (item 5, cross-checks
  every AF mapping this connector implies) · [[stm32f405-pin-assignment]]
  · [[Sensor Expansion Roadmap]] (item 10) · [[Attitude Filter Methods]]
  (why the mag matters)
