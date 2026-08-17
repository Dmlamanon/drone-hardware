---
type: incident
status: resolved
created: 2026-08-17
tags: [drone, hardware, pcb, drift, incident]
---

# The board was two revisions behind the schematic

**Found:** 2026-08-17, by running DRC with `--schematic-parity` for the
first time, immediately after a 20-minute autoroute.

**Severity:** would have produced a non-functional board if fabricated.

## What was wrong

The schematic had been through a 2S → 4S redesign. The PCB had not.
Nothing ever re-synced the two, and nothing had checked.

| Ref | Board carried | Schematic specified |
|---|---|---|
| U2 | TPS563201, **SOT-23-6, 6 pads** | TPS54336ADDA, **SOIC-8-1EP, 8 pins + thermal pad** |
| J1 | BATT_**2S** | BATT_**4S** |
| R1 | 33.2k | 31.6k |
| R9 | 20.0k | 75.0k |
| C1 | 10uF (unrated) | 10uF **35V** |

R1 and R9 are not incidental: R1 is the buck feedback divider that sets
the 3.3V rail, and R9 is the battery-sense divider. The board encoded a
**different regulator, in a different package, at a different output
voltage, fed from a different battery**.

## How it showed up

The first DRC after routing reported 267 violations, 10 unconnected and
264 schematic-parity issues. The parity report was the one that
mattered — the plain violation list looked like ordinary routing noise.

The tell was in `shorting_items`: all five landed on a U2 pad.

```
Items shorting two nets (nets VBAT_4S and SW_NODE)
     Pad 2 [VBAT_4S] of U2 on F.Cu
     Track [SW_NODE] on F.Cu, length 0.1203 mm
```

The router was connecting a SOIC-8 netlist to SOT-23-6 pad numbers. Pad
2 is VBAT on one package and the switch node on the other, so the
"shorts" were the netlist and the land pattern disagreeing about what
each pin *is*. That is not a routing defect; it is the board and the
schematic describing different circuits.

A second, older artifact turned up in the same pass: the exported
`.dsn` still carried a `VBAT_2S` net in its class list and wiring
section, which Freerouting warned about and discarded. The PCB and
schematic had no such net. It was residue from the same 2S era.

## The trap in the fix

The obvious repair — point U2's footprint field at the right library
footprint — is wrong, and it made things worse before it made them
better.

`edit_component` changes the footprint *name*. It does not swap the
*pads*. After that edit U2 read `SOIC-8-1EP_3.9x4.9mm...` in every
listing and BOM while still carrying six SOT-23-6 lands. The board was
just as wrong and no longer said so: the earlier
`footprint_symbol_mismatch` disappeared, and the only remaining trace
was a single `lib_footprint_mismatch` line.

The real fix was to delete U2 and re-place it from the library, which
yields the correct 13-pad geometry (8 signal + thermal EP + 4 EP
stitching pads), then re-sync nets and re-route.

**Rule going forward: a footprint change means delete-and-replace, then
verify the pad count.** Never trust the footprint field alone.

## What else the pass corrected

- **J9** (14-pin expansion header) overhung the right board edge by
  12.8 mm. Moved to x=43, validated with `check_courtyard_overlaps`
  before committing — 0 overlaps, 0 boundary violations.
- **In2.Cu had no pour.** On a 4-layer board running a 3A switcher,
  both inner layers should be planes. Added a 3V3 pour; Freerouting
  then auto-detected *both* inner layers as dedicated power planes, and
  routed 45 nets where the previous run managed 19.
- **No netclass existed.** Everything, including VBAT_4S and GND, was
  routed at 0.2 mm. Added a `Power` class (0.6 mm track, 0.8/0.4 via)
  covering VBAT_4S, 3V3, 5V_RX, GND, SW_NODE, BOOST_SW.

## Why this is the same failure as the firmware ones

This project has now hit duplication drift six times — the torque
clamps, the mixer geometry, the gain defaults, the test literals, the
ground-station decoder, and now the board. The shape is always
identical: **two artifacts describe one thing, and only one of them gets
updated.**

The firmware fixes all took the same form — make the second artifact
*derive from* the first rather than restate it (`params_defaults()` as
the single source of gains, `plant.h` shared rather than copied,
`nmea.c` compiled directly by the beacon, the Python decoder
cross-validated against the compiled C encoder).

The hardware equivalent is that **`--schematic-parity` has to run every
time, not once**. It is the only check that compares the two artifacts,
and it had never been run on this board. It is now part of the fab
gate.

## Verification

See `fab/2026-08-17/README.md` for the DRC state after this work, given
verbatim. The board still has open items; they are listed there rather
than summarised away.
