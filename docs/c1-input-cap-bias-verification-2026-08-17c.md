---
type: verification
status: verified
created: 2026-08-18
tags: [drone, hardware, bom, capacitor, dc-bias]
---

# C1 input capacitor — capacitance-at-bias verification (order blocker, batch 2026-08-17c item 4)

The BOM note on C1 (`fab/2026-08-17b/bom_jlcpcb.csv`) requires: *"MUST
read the vendor C-vs-Vdc curve and confirm it meets the TPS54336A input
requirement before ordering"* — capacitance **at 16.8 V bias**, not
nameplate. This document is that reading.

## Finding 1: the example part is EOL at Murata

The BOM's example part **GRM32ER71H106KA12L** (10 µF 50 V X7R 1210) is
**absent from Murata's current SimSurfing catalog** (`mlcc.csv` dataset,
25,632 parts, updated 2026-08-17 — checked 2026-08-18). Murata's
catalog now lists **zero** GRM-series 3225/1210 50 V 10 µF in production:
every GRM32/GRJ32 variant of that spec carries status **N (NRND)**.
JLCPCB still stocks the L-suffix part (C77102, 19,671 pcs, $0.37) but
that is last-time stock of a dead part — wrong choice for a board that
may be re-ordered.

## Finding 2: the in-production, in-stock replacement

**Murata GCM32EC71H106KA03** — 10 µF, 50 V, **X7S**, 1210 (3225M),
±10%, automotive AEC-Q200, production status **B (in production)** in
the same catalog. JLCPCB stock: **C126612, 28,306 pcs, $0.30, Extended**.
Same body (3.2×2.5, max 2.7 mm), same 1210 land pattern as the
footprint on the board (`C_1210_3225Metric`). X7S vs X7R: ±22% vs ±15%
over −55…125 °C — accounted for in the stack-up below.

## The vendor curve, as read

Source: Murata PIM characteristics data for `GCM32EC71H106KA03#`
(pimapi.murata.com, C-DC bias / capchange, **25.0 °C, AC 1.0 Vrms**),
retrieved 2026-08-18 via the product detail page's own data feed —
i.e. Murata's published measurement, not a datasheet-class guess.

| Vdc (V) | ΔC (%) | | Vdc (V) | ΔC (%) |
|---|---|---|---|---|
| 0 | 0.0 | | 15.75 | −18.88 |
| 2.5 | +0.99 | | 16.00 | −19.41 |
| 5.0 | −0.94 | | 16.50 | −20.50 |
| 7.5 | −4.03 | | **16.75** | **−21.04** |
| 10.0 | −7.84 | | **17.00** | **−21.59** |
| 12.5 | −12.29 | | 20.0 | −28.32 |
| 15.0 | −17.29 | | 25.0 | −39.47 |

Interpolating at the specified **16.8 V** operating bias:
**ΔC = −21.15 %** → effective capacitance:

- nominal: 10 µF × 0.789 = **7.89 µF**
- worst-case −10 % tolerance: 9 µF × 0.789 = **7.10 µF**
- worst-case tolerance AND X7S temperature corner (−22 %):
  7.10 × 0.78 = **5.54 µF**

## Against the TI requirement

The TPS54336A datasheet (SLVSCH2, *Input Capacitors*) sets no hard
"≥ X µF effective" floor; it states the **typical recommended value is
10 µF** (X5R/X7R, rated above Vin,max) and that *"a smaller value can be
used as long as all other requirements are met"* — the binding
requirements being input ripple voltage (Eq. 17) and RMS ripple current
(Eq. 18). Checking those at the everything-worst-case 5.54 µF, minimum
fsw = 272 kHz (datasheet min for the 336A's 340 kHz nominal):

- **Ripple voltage**, Iout = 3 A (device max, far above this board's
  real 3V3 load): ΔVin ≈ (3 × 0.25)/(5.54 µF × 272 kHz) + 3 A×ESR ≈
  **0.51 V** on 16.8 V (3.0 %) — same class as the datasheet's own
  design example (227 mV on 12 V, 1.9 %), and the input also carries the
  0.1 µF HF decoupler per the schematic. At the board's realistic
  ≤ 1 A: **0.17 V (1.0 %)**.
- **RMS ripple current**: D = 3.3/16.8 = 0.196, Icin,rms =
  Iout×√(D(1−D)) = 3 × 0.397 = **1.19 A** — well inside a 3225 X7S
  50 V part's ripple rating.

**Verdict: PASS.** C1 = **GCM32EC71H106KA03, LCSC C126612** meets the
TPS54336A input requirement at 16.8 V bias with margin at every corner,
using Murata's own published bias curve, and is in production. The
`fab/2026-08-17c` BOM carries this part (Extended — one more
unique-part fee); the superseded 17b BOM is left as-was.

## Note kept for honesty

16.8 V is the specified operating bias (4S max charge, per the BOM
note). The batch-3 loop-gain harness also stress-tested 25.2 V (6S); at
that bias this part reads −39.5 % → 5.4 µF nominal / 3.8 µF at the full
worst-case stack, and a 6S variant of the board should revisit input
bulk capacitance (add a second 10 µF or step up the case size). That is
a v2 note, not a v1 blocker — v1 is specified at 4S.
