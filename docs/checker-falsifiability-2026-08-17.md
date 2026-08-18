---
type: audit
status: current
created: 2026-08-17
tags: [stevie, checks, audit]
---

# Checker falsifiability audit — 2026-08-17 (B4)

**Every automated check in this project was deliberately broken once, to
confirm it notices.** Eleven cases, all of them falsifiable.

Run it yourself:

```
python engineering/drone-hardware/scripts/falsifiability_audit.py
```

It exits non-zero if any check survives its own mutation, restores every
file it touches, and verifies the restore rather than assuming it.

## Why this exists

This project's most persistent defect is not broken code. It is **a check
that passes while looking at the wrong thing.** The last two batches
produced seven of them, and every one was green:

| what it claimed | what it actually did |
|---|---|
| the leg meets the material minimum | read `ARM_T`, a variable the leg never uses |
| the gear clears the battery | compared a number against itself |
| the feet are a separate part | tested two constants |
| the board bolts to the frame | never compared the hole to a bolt |
| the buzzer names match the header | compared Python to Python |
| there is no legal fanout site | over-strict in one place, blind in another |
| the crash log never blocks | measured below the clock's resolution |

A checker that cannot fail is worse than no checker, because it launders
a guess into a fact. Hence: break each one on purpose, and keep the
evidence.

## Results

Each row is a real run: the check is executed clean, then with one
deliberate defect, then the file is restored.

| # | check | the defect introduced | clean | mutated | verdict |
|---|---|---|---|---|---|
| 1 | frame leg thickness | `LEG_W` 14 → 0.5 mm | pass | **fail** | falsifiable |
| 2 | frame ground clearance | battery 33.5 → 200 mm | pass | **fail** | falsifiable |
| 3 | flats DXF is sheet-only | `leg_1` added to `SHEET_PARTS` | pass | **fail** | falsifiable |
| 4 | mounting pattern fits an M3 | board drill 3.2 → 2.0 mm | pass | **fail** | falsifiable |
| 5 | mounting DXF is not stale | touch `frame_v0.py` | pass | **fail** | falsifiable |
| 6 | CPL describes the board | drop one component row | pass | **fail** | falsifiable |
| 7 | C/Python buzzer names agree | rename `"lost-model"` | pass | **fail** | falsifiable |
| 8 | crash log reads oldest-first | force `oldest = 0` | pass | **fail** | falsifiable |
| 9 | `hello` reports real versions | hardcode 99 in the response | pass | **fail** | falsifiable |
| 10 | a version drift is caught | `TELEMETRY_VERSION` 6 → 99 | pass | **fail** | falsifiable |
| 11 | a params write reaches the PID | stub out the config request | pass | **fail** | falsifiable |

**11 of 11.** Nothing had to be deleted.

## What the audit found while auditing

> [!warning] Two of these were not falsifiable at first
> **Case 9 could not fail.** The mutation bumped `TELEMETRY_VERSION`, and
> the test compares `hello`'s output against *the same macro `hello`
> reads* — so both sides moved together and the test stayed green. That
> is the identical self-referential shape as the buzzer-name check before
> it was rebuilt, reappearing in a test written the same day, by the same
> hand, that was specifically about not doing this.
>
> Retargeted to hardcode a literal in the response, which is the defect
> the test is actually for. Case 10 was then added to prove the version
> drift *is* guarded — by the decoder cross-check, which carries its own
> independent constant.
>
> **Case 5's baseline was failing, and so were four others**, because the
> harness had two bugs of its own: it used `shell=True` with
> `make x && ./build/x`, which works pasted into bash and silently fails
> under Python on Windows (`shell=True` is cmd.exe); and it restored a
> generator's *source* without regenerating its *exports*, so a mutant's
> DXF was left behind and every later case that read it failed. An audit
> that does not clean up after itself reports other people's checks as
> broken — the same failure class, inside the tool built to hunt it.

## The CPL check did not exist as an artifact

Batch 4 verified the pick-and-place file with a command typed at a shell.
That caught a real defect (six missing components), but a one-off command
cannot be re-run, cannot be audited, and would not have caught the same
mistake in the next package. It is now
`scripts/check_cpl.py`, and it compares **sets, not counts** — six
missing and six spurious would give matching counts and a board nobody
can assemble.

Writing it corrected a claim from batch 4: the fab README said the four
mounting holes "carry `FP_EXCLUDE_FROM_POS_FILES`". They do not — that
string appears nowhere in the board. They simply have no `(attr ...)`
block, and there are exactly 61 footprints with one against 61 CPL rows.
The checker honours both rules so it keeps working if the explicit flag
is ever set.

## Not covered, and why

- **The fanout site search** (`place_fanouts.py`, `why_no_fanout.py`) is
  a search, not a pass/fail gate — there is no exit code to falsify. It
  was audited differently and more harshly in batch 4: two defects were
  found in it by placing a via it proposed and letting DRC judge, which
  is the strongest test available and is recorded in the fanout guide.
- **DRC and ERC** are KiCad's, not ours. Their falsifiability is not
  this project's to assert.

## Standing from now on

This audit is part of the wrap checklist. Every batch that adds an
automated check adds a case here, and the wrap runs the audit. A check
introduced without one is a check nobody has confirmed can fail.

## Related

- `scripts/falsifiability_audit.py` — the audit itself
- `scripts/check_cpl.py` — new this batch
- `docs/manual-fanout-guide-2026-08-17.md` — how the fanout search was audited
