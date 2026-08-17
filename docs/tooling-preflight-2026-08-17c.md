---
type: preflight
status: current
created: 2026-08-17
tags: [stevie, tooling]
---

# Tooling pre-flight — 2026-08-17 (batch 4)

## Working

| Tool | Version | Notes |
|---|---|---|
| gcc (host) | 16.1.0 MinGW-W64 | native tests |
| arm-none-eabi-gcc | 14.2.Rel1 | `make cross`, `make firmware` |
| kicad-cli | 10.0.5 | DRC/ERC, gerbers, exports, `--schematic-parity` |
| KiCad MCP | responds | swig backend |
| FreeCAD | 1.1.3 | headless `freecadcmd.exe`, non-standard install path |
| Python (system) | 3.14.6 | analysis scripts |
| Java | OpenJDK 25.0.4 | Freerouting host |

## NEW THIS BATCH — headless `pcbnew` Python is available, and it is the item-3 route

Item 3 asks for a zone-fill path that is **not** the MCP's, because that
one shattered both planes (In1.Cu 2 → 19 filled polygons, In2.Cu 1 → 22).

**KiCad ships its own Python interpreter with the `pcbnew` module bound:**

```
C:\Program Files\KiCad\10.0\bin\python.exe
>>> import pcbnew; pcbnew.GetBuildVersion()   ->  '10.0.5'
>>> hasattr(pcbnew, 'ZONE_FILLER')            ->  True
>>> hasattr(pcbnew, 'LoadBoard')              ->  True
```

Verified this session by actually loading the real board, not just by
importing the module: 65 footprints, and the zones enumerate correctly.

This is a genuinely different code path from the MCP's — it is KiCad's
own in-tree filler, invoked through KiCad's own interpreter, rather than
whatever the MCP server wraps. Whether it produces the same fragmentation
is the open question item 3 exists to answer, and the answer is measured
rather than assumed.

## A counting correction that matters for item 3

Earlier batches said this board has **3 zones**. It has **2 copper
pours**. The third `(zone ...)` block in the file is a **keepout inside a
footprint** (F.Cu, carries `(keepout ...)`, no net, no fill), which is
why `pcbnew`'s `board.Zones()` returns 2 and a naive regex over the file
returns 3.

The fragment-count baseline for item 3 is therefore, from the
git-committed copper:

| pour | layer | filled polygons |
|---|---|---|
| `/GND` | In1.Cu | **2** |
| `/3V3` | In2.Cu | **1** |

Anything above those numbers after a refill is fragmentation, and the
comparison must use the *same* measurement on both sides — the last batch
established that the hard way, when a "281 violations" baseline turned
out to be an artifact of running DRC on a board extracted without its
`.kicad_pro`.

## Ground station (item 7)

`engineering/drone-firmware/tools/ground-station/` exists with `gs.py`,
`telemetry_frame.py`, `params_cli.py`, `plot_session.py` and
`test_decoder.py`.

**Confirmed working this session by running it, not by noting it exists:**
the cross-validation that keeps the Python decoder byte-identical to the C
encoder is `tools/ground-station/test_decoder.py`. It compiles the real
`src/telemetry.c`, has it encode, and decodes in Python. Currently passing,
including the check `python encode() is byte-identical to C's`.

**It lives outside `test/`, so `make test` does not run it.** Item 7
requires extending it for any frame change, which means invoking it
explicitly (`python test_decoder.py` from that directory) in addition to
`make test`. If it ever reports "SKIPPED: no C compiler", the
cross-validation did not actually happen and the run proves nothing.

## Item 1's inputs both exist

- Board mounting holes: `MH1`–`MH4` in `bench_board.kicad_pcb`.
- Frame pattern: `FC_MOUNT = 30.5` in
  `mechanical/frame-v0/frame_v0.py`, and the exported
  `stevie-frame-v0-flats-petg.dxf`.

Item 1 requires extracting **both** from the actual files and asserting
they match — so the DXF must be parsed, not the script's constant read.
DXF export is confirmed working (97 KB written last batch).

## Carried forward

- **Freerouting 2.3.0** will not honour `(type power)` layer reservation
  and hung 16 minutes when forced. Unchanged.
- **FreeCAD rejects MSYS-style paths.** Every export path must be a
  native Windows path.
- **Do not use the MCP `refill_zones`.** Documented failure, item 3 says
  so explicitly.
- **`delete_trace` with both `net` and `position`** ignores the position
  and bulk-deletes the whole net. Pass one or the other.
- **`sync_schematic_to_board` strips the leading `/` from net names**,
  which disables this board's Power netclass. Re-check after any sync.
