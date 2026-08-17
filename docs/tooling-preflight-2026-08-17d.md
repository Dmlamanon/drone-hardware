---
type: preflight
status: current
created: 2026-08-17
tags: [stevie, tooling]
---

# Tooling pre-flight — 2026-08-17 (batch 5)

## Working

| Tool | Version | Notes |
|---|---|---|
| gcc (host) | 16.1.0 MinGW-W64 | native tests |
| arm-none-eabi-gcc | 14.2.Rel1 | `make cross`, `make firmware` |
| kicad-cli | 10.0.5 | DRC/ERC, gerbers, exports |
| KiCad headless Python | 3.x + `pcbnew` | `C:\Program Files\KiCad\10.0\bin\python.exe` |
| FreeCAD | 1.1.3 | headless `freecadcmd.exe` — **confirmed for item 6** |
| Python (system) | 3.14.6 | analysis scripts, ground station |

Baseline before any batch-5 work: **43 test binaries + the decoder
cross-check pass**; `cross`, `firmware`, `rc-verify`, `probe-railing`
all pass.

## `freecadcmd` headless — confirmed

`freecadcmd.exe --version` returns `FreeCAD 1.1.3 Revision: 20260725`,
and it has been driving `mechanical/frame-v0/frame_v0.py` end to end all
day (STEP, STL, DXF, SVG exports plus 17 geometry checks). Item 6 has the
interpreter it needs.

**The install path is non-standard and scripts must not assume PATH:**

```
C:\Users\dmlam\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe
```

It also **rejects MSYS-style paths** — pass Windows paths, not
`/c/Users/...`.

## NO SWD TOOLING ON THIS MACHINE — item 1 degrades, and says so

This is the finding that shapes item 1. Every candidate was probed:

| Tool | Result |
|---|---|
| `openocd` | **not found** |
| `st-flash` / `st-info` | **not found** |
| `STM32_Programmer_CLI` | **not found** |
| `dfu-util` | **not found** |
| `pyocd` | **not found** |
| `JLinkExe` | **not found** |

Not merely absent from `PATH` — a directory sweep of `C:\Program Files`
and `C:\Program Files (x86)` for `STMicroelectronics`, `OpenOCD`,
`SEGGER` and `stlink` found **no install at all**.

**And no debug probe is attached.** `Get-PnpDevice` matching
`ST-Link|STLink|J-Link|CMSIS-DAP|DAPLink` returns nothing.

### What that means for item 1, stated plainly

The deliverable is **tooling plus a dry-run mode**, and the live-probe
step is **untestable on this machine today**. Specifically:

- `make flash` can be written, and its command construction can be
  verified, but **it has never moved a byte to silicon** and must not be
  described as though it has.
- `tools/bring-up/smoke.py` can be exercised end to end **against a
  loopback/stub**, which proves the sequencing, the parsing and the
  PASS/FAIL reporting — and proves *nothing* about the hardware.
- Every artifact this batch produces for B1 carries that distinction in
  the artifact itself, not only here.

There is also nothing to be gained by installing OpenOCD now: with no
probe and no board, a successful install would still leave the live path
unexercised, and it would swap an honest "not present" for a misleading
"present but never used."

## CCM SRAM — verified for item 4

Item 4 asks for a crash ring in the F405's CCM bank and says to verify
against the linker script rather than assume. Checked:

```
CCM    (rw)  : ORIGIN = 0x10000000, LENGTH = 64K
.ccmram (NOLOAD) : ALIGN(4) { _sccm = .; *(.ccmram .ccmram.*) _eccm = .; } > CCM
```

Address and size match the task brief and RM0090. The script already
carries the constraint item 4 asks to document:

> CCM IS DELIBERATELY NOT IN THE DEFAULT .data/.bss PATH. […] a
> DMA-visible buffer in CCM is a classic, silent, hard-to-debug STM32F4
> failure. Anything DMA touches must live in SRAM.

So the section is **opt-in only**, via
`__attribute__((section(".ccmram")))`. The crash ring is a good fit
precisely because it is CPU-written and never DMA-touched.

## Not re-checked this batch

Freerouting/Java and the KiCad MCP are untouched — **this batch must not
modify the board**, so neither is on the path. The MCP refill ban from
batch 4 stands regardless.

## Related

- `docs/tooling-preflight-2026-08-17c.md` — batch 4, the blocking-dialog fix
- `scripts/kicad_safe.py` — the standing headless-pcbnew preamble
