---
type: preflight
status: current
created: 2026-08-17
tags: [stevie, tooling]
---

# Tooling pre-flight — 2026-08-17 (batch 3)

## Working

| Tool | Version | Notes |
|---|---|---|
| gcc (host) | 16.1.0 MinGW-W64 | native tests |
| arm-none-eabi-gcc | 14.2.Rel1 | `make cross`, `make firmware` |
| kicad-cli | 10.0.5 | DRC/ERC, gerbers, exports |
| KiCad MCP | responds | `open_project` OK this session, swig backend |
| Java | OpenJDK 25.0.4 | Freerouting host |
| Freerouting | 2.3.0 | **known limitation carried forward: will not honour `(type power)` layer reservation, and hung 16 min when forced** |

## FreeCAD — the item 6 question, answered

**There is NO freecad MCP.** The only MCP servers this session are kicad,
github, gemini-cli and claude-in-chrome. Searched the deferred tool list
directly; nothing FreeCAD-shaped exists.

**Headless scripting works, and that is the route.**

- Install is in a **non-standard location** — not `C:\Program Files` —
  which is why a naive check would report FreeCAD missing:
  ```
  C:\Users\dmlam\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe
  ```
- **FreeCAD 1.1.3** (libs 1.1.3R20260725).
- Verified this session by actually running geometry rather than just
  launching the binary: created a box and a cylinder, performed a
  **boolean cut** (volume 590.575 mm³, correct), and exported both
  **STEP and STL** successfully.

**One trap worth recording:** FreeCAD will not accept MSYS-style paths.
`Import.export([...], "/tmp/x.step")` fails with
`Step File could not be created` and the script aborts with
`Cannot open file:`. Native Windows paths (`C:\...`) work. Every export
path in the mechanical scripts must therefore be a Windows path, not the
bash-style path the rest of this project uses.

**Conclusion: item 6 proceeds via `freecadcmd.exe <script.py>`.**

## Item 6's stated inputs — two of three do not exist

The brief says: *"Input specs exist: `docs/mechanical-requirements.md` +
the material rules in `docs/cfd-structural-recommendation-2026-08-17.md`
+ the board STEP in `engineering/drone-hardware/mechanical/`."*

Checked directly:

| Input | Status |
|---|---|
| `docs/cfd-structural-recommendation-2026-08-17.md` | **EXISTS** — written last batch, contains the material-independence rules |
| `docs/mechanical-requirements.md` | **DOES NOT EXIST** anywhere in either repo or the vault |
| `engineering/drone-hardware/mechanical/` and a board STEP | **DOES NOT EXIST** — no `mechanical/` directory, and `find` turns up no `.step`/`.stp` anywhere in the repo |

This is the same false-premise shape this project has hit before — the
"cost-cut list" last batch, the "disturbance matrix from the earlier
plan", the "350-class gains already derived". Flagged rather than
silently treated as real prior work.

**Neither absence blocks item 6**, and neither is invented around:

- The **board STEP is generated** this batch with
  `kicad-cli pcb export step`, which is real output from the real board
  rather than a document that was supposed to exist.
- The **mechanical requirements are written** this batch from constraints
  that genuinely do exist and are cited to their sources: the 350 mm
  wheelbase and mass budget from
  `drone-firmware/docs/inertia-estimate-350class-REAL-2026-08-16.md`, the
  30.5 mm FC mount pattern, the 18.9 mm / 8.3 % prop-clearance finding
  from the CFD doc, and the PETG/PA-CF/CF-plate section minimums from the
  same.
