---
type: design-review
status: complete
created: 2026-08-18
tags: [drone, hardware, pcb, review, kicad-happy, pre-order]
---

# bench_board — kicad-happy full design review, 2026-08-18 (pre-order)

Independent tool-based review with the kicad-happy suite (v2.1.0),
run against the board at commit `8278577` — the exact revision
`fab/2026-08-17c/` was generated from. Report-only; the board was not
modified. Scope requested: schematic, PCB layout, EMC pre-compliance,
derating, manufacturing readiness, with a clear order/hold verdict.

## VERDICT: **ORDER AS-IS — with one BOM-value change recommended first**

Nothing order-blocking was found that the project's own reviews missed.
One new finding is worth acting on **because the fix is free right now
and costs a respin later**: the chosen crystal (Y1 = C115962) is a
**20 pF-load part, but the board fits 10 pF load caps** (effective
CL ≈ 8 pF). The board will still work — the resulting ~200–350 ppm
frequency error is inside USB FS tolerance (±2500 ppm) and irrelevant
to UART — but it is out of the crystal's spec, and the fix is a
BOM-only value change (C17/C18: 10 pF → 33 pF, same 0402 footprint,
Basic-library part) with zero copper edits. Change it in
`fab/2026-08-17c/bom_jlcpcb.csv` before uploading, or order as-is and
accept the offset knowingly.

Everything else new is either a triaged analyzer false positive
(§False positives — including one that initially looked like a
board-killer), a known-and-accepted item restated by the tools, or a
v2-grade improvement.

---

## Analyzers run (coverage disclosure)

| analyzer | run | result |
|---|---|---|
| `analyze_schematic.py` | ✔ | 61 components, 55 nets parsed; findings below |
| `analyze_pcb.py --full --proximity` | ✔ | 61 footprints, 587 segments, 113 vias, 2 zones |
| `cross_analysis.py` | ✔ | 15 findings (all one family, see §Known) |
| `analyze_emc.py` (emc skill) | ✔ | 108 findings: 58 error / 32 warning / 18 info |
| SPICE (`simulate_subcircuits.py`, ngspice) | ✔ | **15/15 subcircuits PASS** |
| `analyze_thermal.py` | ✔ | 0 findings, score 100/100 |
| `analyze_gerbers.py` on `fab/2026-08-17c/gerbers` | ✔ | all 11 layers + PTH/NPTH present; 2 triaged warnings |
| Datasheet sync | ✘ skipped | no `datasheets/` dir, no distributor API keys; see Verification basis |
| Lifecycle audit | ✘ skipped | schematic symbols carry 1/41 MPNs (sourcing lives in the fab BOM CSV, not symbol properties); stock on the two thin lines (U1, U2) was live-verified 2026-08-17 in the project's own BOM work |
| Prior-run delta | n/a | first kicad-happy run on this project; prior human reviews (batch-6 independent review, same day) were read and are cross-referenced below |

**Verification basis.** With no datasheet cache, analyzer findings are
*consistency* checks unless stated otherwise. Where this report makes a
correctness claim it cites external evidence explicitly: the crystal
finding is backed by the distributor's published spec for C115962
(X50328MSB2GI: "20pF 8MHz ±10ppm"); C1's bias-derating and C23's
loop-gain evidence come from the project's own committed verification
docs, which the batch-6 independent review reproduced number-for-number.
Pin-level pinout verification against manufacturer PDFs was **not**
performed here — noted as a review limit. Mitigation: this design's
pinouts have survived ERC=0, DRC parity checking (93 issues, all
itemized as benign), and two prior independent reviews; residual risk
concentrates in library-symbol-vs-real-part mismatches, which no
consistency check can catch.

---

## Findings, ranked

### ORDER-BLOCKING

**None.**

### RECOMMENDED BEFORE ORDER (free at order time, costly later)

**1. Crystal load-capacitance mismatch — Y1 vs C17/C18.**
Y1 is LCSC **C115962** (Yangxing X50328MSB2GI, 8 MHz, **CL = 20 pF**,
±10 ppm). The board fits C17 = C18 = 10 pF, giving effective
CL = 10/2 + ~3 pF stray ≈ **8 pF**. A 20 pF crystal run at 8 pF
oscillates reliably but **high** — order of +200–350 ppm. Impact:
USB FS needs ±2500 ppm (fine), UART needs ±2 % (fine), so this is not
a blocker; it is an out-of-spec operating point with a zero-cost fix
available only until the order is placed: change the **BOM value** of
C17/C18 to 33 pF (CL = 16.5 + 3 ≈ 19.5 pF ✔; 0402 33 pF is a
Basic-library part). No copper edit; the SPICE crystal check
(`load_capacitance_pF: 8.0`, PASS against the *schematic's* declared
value) confirms the analyzer and schematic agree — the mismatch is
between the schematic's cap choice and the real part's spec, exactly
the class of bug consistency checks cannot see.
*Alternative: order as-is and note the offset in the bring-up runbook
(measure MCO output on first power-on).*

### MEDIUM (bench-acceptable; put on the v2 list)

**2. U2 (TPS54336A) PowerPAD has zero thermal vias** (`TV-001`,
0 of ≥5 expected). The exposed pad lands on F.Cu copper only. At this
board's real ≤1 A load, dissipation ≈ 0.2–0.3 W → ΔTj ≈ +10–15 °C:
fine, and consistent with the thermal analyzer's clean score. At the
device's 3 A rating it would not be fine (~0.8 W into a pad with no
via path to the GND plane). The order sheet's process (filled/capped
vias) would have made in-pad thermal vias free of paste-wicking risk —
worth 4–6 vias under U2 in the v2 spin.

**3. Boost-converter hot loop (U6/L2/C26) is large** (`SW-003` error;
`SW-001` U6 harmonics land in the 30–88 MHz band). Same family as the
accepted /SW_NODE finding: switching-loop geometry on a fixed layout.
Bench board ≠ EMC test article; record for v2 (tight C-U-L triangle,
input cap adjacent to U6 pin 4/5). Companion note: **L1 is ~11 mm from
Y1** (`ML-001`) and its BOM candidate's shielding is unstated — the
chosen MTQH322510S100MBT is a **molded (shielded-construction)** part,
which mitigates this; keep molded/shielded as a hard requirement if
David substitutes.

**4. IPC Class 2 annular-ring nonconformance on the 0.30/0.15 mm vias**
(`DFM-001`/`DFM-002`: 0.075 mm ring vs 0.125 mm IPC Class 2 / 0.10 mm
"advanced" heuristic). This is a *reliability class* note, not a
manufacturability stop: JLCPCB's published 4-layer floor is
0.25/0.15 mm (0.05 mm ring) and the order sheet already forces the
0.15/0.25 mm process option. Hobby-grade acceptance is reasonable;
just know these eight vias are below IPC Class 2 and live on the MCU's
supply pads — if a board fails weirdly after thermal cycling, look here
first. (The 0.15 mm drill also triggers the "advanced process"
surcharge already priced into the order sheet.)

### LOW / informational

**5. No fiducials** (`FD-001`, 52 SMD parts, finest pitch 0.30 mm
pads): JLCPCB adds panel rails and fiducials for assembly orders;
board-level fiducials are best practice for v2 but not required for
this order.
**6. VBUS is clamp-only and undecoupled** (`UC-001`, `DC-002` "no cap
near U5"): USB_VBUS goes only to J3 and U5.5 (USBLC6 clamp rail) —
the board is battery-powered and VBUS feeds nothing. A 100 nF at U5.5
would be a nicety for ESD return; harmless to omit.
**7. Test-point coverage 0 %** (`TE-001`): the nine headers (SWD,
expansion, UARTs, DShot) *are* the test access; acceptable by design.
**8. 24 passives flagged 0402 tombstoning-risk "medium"** (`TB-001`):
generic 0402 note; JLCPCB's process handles 0402 routinely. The
"Confirm Parts Placement = Yes" option in the order sheet is the right
mitigation.
**9. Decoupling distance notes** (`DC-001` C near U4 "moderately far",
`DC-003` C1 far from its via): layout-quality observations on a fixed
layout; U4's local 100 nF cluster exists and SPICE PDN checks pass.
**10. Derating sweep** (requested explicitly): C1 was the only
at-risk part and its 16.8 V-bias verification is already committed and
independently reproduced (5.54 µF worst-case ≥ requirement). C2/C25/C26
(25 V parts on 3.3/5 V rails), C13 (50 V on comp node), C14/C24
(50 V), R9/R10 divider (16.8 V across 85 k → 3.3 mW, 0402-safe): all
comfortable. Inner-layer 0.5 oz planes at ≤1 A: fine. No new derating
findings.

---

## False positives triaged (do NOT act on these)

**A. "GND plane split: 6 islands / the seven closed pads are isolated
single-pad islands" (`PS-002` error + `connectivity_graph`).** This
was the scariest output of the run — it claims the pads this batch
closed (U1.12/13/18/19/63/64, U4.11) have no copper path to their
planes, which would mean a dead MCU and a wasted order. **It is false,
and I proved it against the raw board file:** each closure is a chain
(in-pad via → B.Cu leg → landing via → plane), and point-in-polygon
tests on the actual `filled_polygon` data show the landings inside the
plane fills — e.g. U1.13's leg lands on a 0.5/0.3 via at
(30.53, 32.25) **inside the In2 /3V3 fill**, and U1.12's B.Cu chain
reaches a 0.5/0.3 via at (27.43, 33.35) **inside the In1 /GND fill**
(the same chain also picks up U1.18, matching the commit history).
The plugin's union-find drops track-to-via joins whose endpoints are
off-center — this board deliberately ignores KiCad's
"track endpoint not centered on via" check, so several joins are
off-center but physically overlapping. KiCad's own connectivity engine
(the authority — it computes real copper) reports exactly the 2 known
unconnected items, verified hash-for-hash across 13 commits by the
board guard. Conclusion: modeling artifact, not a defect.

**B. Gerber "misalignment: width varies 8.2 mm across copper/edge
layers" (`GR-002`).** The analyzer compares content bounding boxes.
Copper legitimately stays ~4 mm inside the Edge.Cuts outline on this
board (80×60 outline vs ~72×52 copper extents), and F.Paste is smaller
still because THT pads carry no paste. All 11 expected layers plus
both drill files are present and consistent. Nothing is misaligned.

**C. "J10 is 0.23 mm from board edge" (`PM-002` error).** That is the
*courtyard*-to-edge distance. J10's copper is 1.15 mm from the edge
(DRC's copper-edge check, rule 0.3 mm, is clean here), and J10 is a
hand-soldered THT header — a courtyard nicking the edge band has no
assembly consequence for this order.

**D. "Circular enable dependency U6 → U6" (`PS-001`), "5V_RX /
VBAT_SENSE has no declared source" (`RS-001`).** MT3608's EN is tied
to its own input rail (normal always-on wiring) and the "undeclared
source" nets are PWR_FLAG bookkeeping patterns; ERC is 0.

**E. "USB differential pair crosses plane gap" and friends
(`RP-002` on /USB_DM_MCU, /USB_DP_MCU, /SWCLK, SPI/I2C nets;
`GP-001` ×50; `RP-001` stitching).** Real physics, but not new: this
is the known, accepted, documented top-v2 item (214 signal segments on
the inner layers; /SW_NODE inside the 3V3 pour). The EMC tools restate
it 80+ ways. Nothing here changes the order decision for a bench
board; all of it folds into v2 item 1.

---

## What verified clean (positive findings)

- **SPICE, 15/15 PASS with ngspice** on real netlists: buck feedback
  divider R1/R2 → 0.793 V vs TPS54336A's 0.8 V reference (Vout
  3.33 V ✔); boost divider R12/R13 → 0.601 V vs MT3608's 0.6 V
  (5.0 V ✔); battery-sense divider R9/R10 ratio ✔; both RC filters at
  computed cutoffs ✔; buzzer FET switch ✔; PDN impedance of all four
  decoupling clusters ✔; inrush on both rails (0.13/0.19 A) benign ✔.
- **Thermal: 0 findings at 25 °C ambient** (score 100/100),
  independently consistent with my hand-check of U2 above.
- **Gerber package complete**: 11/11 layers, separate PTH/NPTH
  Excellon, drill maps, job file; drill classes match the board file.
- **Zone fills are current** (fill data present and matching DRC) —
  the copper-presence analysis ran on real fills, not stale ones.
- **Placement/DFM**: no courtyard overlaps flagged beyond the known J3
  internals; no silk-over-pad findings on paste-critical parts; SMD is
  single-sided (cheapest assembly path), 61/61 CPL match re-confirmed.
- The two batch-6-review corrections (bench-jumper distances, via-in-pad
  list) held up under this independent toolchain: the 6 untented
  via-in-pad detections (`VP-001`: U1 ×5 + L1.1) match the order
  sheet's mandatory filled-and-capped list exactly.

## Review limits

No manufacturer-PDF pinout verification (no datasheet cache; the two
prior independent reviews and ERC/DRC parity are the compensating
controls). Lifecycle audit skipped (MPNs live in the fab CSV, not
symbol properties — U1/U2 stock was live-checked yesterday and the
order sheet re-checks at matching time). EMC findings are
pre-compliance heuristics, not chamber results. The crystal finding's
CL value comes from the distributor's parametric listing, not the
manufacturer PDF — confirm on the Yangxing datasheet at part matching
if you change C17/C18 (the order sheet already tells you to verify Y1
against the live JLCPCB page).

## Bottom line, restated

**Order as-is is defensible today.** The one thing I would change
first is a BOM value, not copper: **C17/C18 10 pF → 33 pF** to match
the 20 pF crystal actually being placed. Add U2 thermal vias, the
boost hot loop, fiducials, and the IPC Class 2 annular note to the v2
list beside the existing inner-layer item. Every alarming-looking
tool output beyond that was traced to ground truth and dismissed with
evidence, most importantly the false "isolated pad islands" claim —
the batch-6 closures are physically connected copper.
