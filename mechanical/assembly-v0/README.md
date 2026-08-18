---
type: mechanical
status: current
created: 2026-08-17
tags: [stevie, mechanical, assembly]
---

# Assembly v0 — every component, in position

```
python ../../scripts/run_freecad_check.py assembly_v0.py build-report-assembly.txt
```

Run it through the wrapper, **not** `freecadcmd assembly_v0.py` directly —
see the warning at the bottom of this file.

## What it answers

Two questions nothing in this project could answer before.

**Does it all actually fit?** Frame, board, battery, ESC stack, motors,
prop discs, receiver, antenna keep-out, buzzer and the expansion-header
access volume have only ever existed as separate numbers in separate
documents. Numbers do not collide; solids do. There are seven checks and
they can fail — proven, not asserted: growing the ESC until it occupies
the receiver's space is a case in the standing falsifiability audit.

**What does it weigh, and where is the mass?** →
`docs/assembly-mass-cg-2026-08-17.md`, which this script generates rather
than anyone transcribing.

## It does not touch the board

Zero edits to `bench_board.kicad_pcb` and zero to the fab package. The
board enters this model **read-only**, as `mechanical/bench_board.step`.

That turned out to matter: the STEP is **80 × 60 × 11.5 mm**, and the
placeholder envelope in the component table was 1.6 mm — the bare PCB.
11.5 mm is the board *with its connectors*, which are exactly the parts a
clearance check is about. The real bounding box now drives the
clearances; the envelope is only a fallback, and if the STEP is missing
the script says so instead of quietly substituting a flat rectangle.

## Parameters are imported, not copied

Frame geometry comes from `../frame-v0/frame_params.py` — the same module
`frame_v0.py` uses. Extracting that module is what made "import, don't
copy" real: a second copy of the wheelbase or the 30.5 mm mount pitch
would be a second thing to update, which is this project's most repeated
defect.

The board-to-frame alignment is not re-derived here either. It **calls**
`scripts/check_fc_pattern.py`, so this fails if that fails — including
for reasons added to it later that this file knows nothing about.

## Provenance, per component

Every dimension carries where it came from, in the re-eval's classes:
`DATASHEET`, `RETAIL-LISTING`, `OWN-MODEL`, `ESTIMATE`, `MEASURED`.

**`MEASURED` appears nowhere, because it would not be true of a single
number here.** The receiver, antenna, buzzer and their placements are
envelopes for parts nobody has chosen: they reserve space, they do not
describe hardware. The expansion access volume carries **mass 0** on
purpose — reserving space must not inflate the AUW.

## Outputs

| file | what |
|---|---|
| `stevie-assembly-v0.step` | full assembly, all bodies |
| `stevie-assembly-v0.stl` | assembly mesh |
| `assembly-v0-plan-2026-08-17.svg` | plan view with prop discs and the CG marked |
| `assembly-v0-exploded-2026-08-17.svg` | exploded elevation — the stack, which is where the clearances live |
| `build-report-assembly.txt` | the run's own numbers and check results |
| `../../docs/assembly-mass-cg-2026-08-17.md` | generated mass/CG/inertia derivation |

## What this is not

- **Not a stress model.** Nothing here computes a load, a deflection or a
  margin. `cfd-structural-recommendation-2026-08-17.md` remains the only
  structural input, and it is a recommendation, not an analysis.
- **Not a wiring model.** Cable routing, connector orientation and strain
  relief are absent; `wiring` appears in the mass rollup as a 35 g
  estimate and nowhere else.
- **Not evidence that it assembles.** Bounding boxes clear each other.
  Whether a human can get a driver onto a bolt is a different question,
  and this cannot answer it.

> [!warning] Never run this with bare `freecadcmd`
> **`freecadcmd` exits 0 for a script that fails to parse.** Verified on
> 1.1.3 — and found here, by a real typo that reported success for three
> runs in a row while the script had never executed a line. The exports
> on disk were from an earlier run and looked current.
>
> `scripts/run_freecad_check.py` takes the verdict from the artifact
> instead: it deletes the build report, runs the script, and requires the
> report to exist and to end with the script's own `RESULT:` line. Use it
> for `frame_v0.py` too.

## Related

- `../frame-v0/README.md` — the frame, and what v0.1 still is not
- `../frame-v0/frame_params.py` — the shared parameter definition
- `docs/checker-falsifiability-2026-08-17.md` — how these checks are audited
- `docs/fable-reeval-2026-08-16.md` — the provenance table and the chain
