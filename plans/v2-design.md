# AVR Tester v2 design

## Goal

Design the next generation of the AVR Test HAT: Raspberry Pi hardware that
connects to, programs and exercises AVR microcontrollers under test. Output is
a KiCad project (or two) that can be ordered fully assembled from JLCPCB and
work on arrival.

## Environment / context

- This repo: `C:\Users\camer\git\Personal Projects\avr-tester-v2`, remote `origin` =
  https://github.com/TomSawyerLabs/mcu-hil (formerly `avr-test-hat`; GitHub redirects the old URL).
- v1 design: tag `v1` / branch `v1-archive` (`4560cfe`) in this repo's history. Old checkout
  `C:\Users\camer\git\Personal Projects\avr-test-hat` still exists (left untouched; remote works via redirect).
  - v1 is **Altium**, not Ultiboard/Multisim: `HAT/AVR-Tester.PrjPcb`,
    `HAT/AVR Test Hat.PcbDoc`, and sheets `Main`, `AVR`, `Clock Buffer`,
    `EEPROM`, `I2C-PullUps`, `Logic Buffer`, `Power Switch`, `Reset`,
    `RPi-HAT_Conn-EE`, `USB`, `USB-C`, `microUSB` (`.SchDoc`).
  - Simplified block diagram: `Circuits.drawio.svg` in that repo.
  - Pi OS image setup: `OS Image/setup.sh` (uncommitted in v1 checkout).
  - KiCad has a native Altium importer (File > Import > Non-KiCad Project),
    so v1 can be pulled into KiCad directly; NI/Ultiboard conversion is not needed for this.
- NI Multisim/Ultiboard tooling (only relevant if older EW versions turn up):
  `..\ewd` (binary decoder library) and `..\ew-conv` (EW XML -> KiCad converter),
  tracked as their own projects.

## Decisions already made (don't re-ask)

- **KiCad** for v2.
- **JLCPCB assembly**: every part has an LCSC number and is generally in stock
  (prefer JLC Basic parts; Extended is OK when needed). BOM + CPL ready for JLC.
- **Two variants, same GPIO map** where possible: CM4/CM5 carrier and Pi HAT.
  The carrier is the priority (it can have USB connections to the DUT).
  A USB cable between a Pi B and the HAT is an acceptable fallback for the HAT.
- Start from v1's circuits (import the Altium project) rather than redraw from scratch.
- **Why v2 (user, 2026-11-11):** reproducibility, moving to open tools, and a base design
  that new parts can be added to. Likely variants carry other AVRs (e.g. AVR32 UC3, XMEGA),
  each on its own board or a couple sharing one. Pis aren't free, so a board may carry more than one MCU.
- **Architecture: complete boards, no plug-in cards.** Each variant is a whole board
  (a CM carrier or a HAT) with its MCU(s) on it. "The boards are the plug-in cards."
  Variants share a common base design (copied/shared schematic sheets), not a connector.
- **CM carrier size: same outline as the CM4/CM5 module (55 × 40 mm)**, so they stack like the
  Waveshare CM4-NANO carrier.
- **Power input:** no secondary power input. CM carrier: USB-C (power + rpiboot).
  **No PoE in this version** (user, 2026-11-11: skip it; it didn't fit at 55 × 40 mm anyway).
  Plain RJ45 magjack. HAT: powered by the Pi only. Its USB-C is a **data**
  connection to the Pi through a short loopback cable, so the HAT never back-feeds the Pi's 5 V.
- **Target voltage:** whatever is easiest to run. The main target is each part's standard,
  officially supported operating modes. Special boards may later push overclocking or power-draw limits.
- **Power meter:** yes, sized for the currents an AVR draws.
- **DUT USB:** one port per DUT is enough, with per-port power control (virtual unplug).
  Software-USB testing goes to the **MCU's** GPIO (confirmed: we test the MCU, not the Pi).
  On a single-MCU board, MCU GPIO can be routed to a USB D+/D- pair.
- **USB switch, not a hub** (user, 2026-11-11: "we only need one path at a time"). The host's one
  USB 2.0 port goes through a high-speed analog USB switch (TS3USB221-class, HS-rated because the
  rpiboot path runs at 480 Mbps) to exactly one of: USB-C (rpiboot), the MCU's hardware USB, or the
  software-USB pin pair. Unselected paths are disconnected, so no D+/D- stubs. The switch selects
  USB-C by default (pulled, so it's right before the CM boots). Accepted cost: on a board with
  two USB MCUs, only one enumerates at a time, and tests switch between them. Same circuit on the HAT
  behind the loopback cable.
- **Clock:** the Pi can optionally drive the DUT clock directly (v1's GPCLK0 override, kept and
  possibly extended with a programmable clock generator).
- **CM boards:** a microSD slot on the carrier. Network boot is the plan, so CM4/CM5 Lite with no
  storage *should* work. A USB-C port is required, for backup power and firmware flashing (rpiboot).
  Network boot implies an Ethernet jack.
- **v1 history:** a v1 was built, PCB dated 2023-01-10. Its USB-C footprints J6A/J6B are **not populated**,
  and J6B is an alternate footprint for J7 micro-USB, which is fitted (user, 2026-11-11).
  The Altium files were committed 2023-01-14 (tag `v1`), so they very likely match the built board.
- **DUT voltage: 5 V, fixed** (user, 2026-11-12, final: "power the chips at 5V"). Reason: every classic AVR
  needs VCC 4.5–5.5 V for HV programming. 16U2 at 16 MHz (C13738, Basic). TPS22918 load switch, no 3.3/5 V mux.
  (Same day, the design briefly went to 3.3 V with series resistors instead of translators. Both reverted.)
- **Level translators are in** (user, 2026-11-12): TXU0304 (ISP) and TXU0202 (UART), enables on GPIO 16/17.
- **Clock override is optional** (user, 2026-11-12): a "no clock override" variant leaves the SN74LV1T126 off.
  The HV option depends on it (HVPP pulses XTAL1 through it, for entry and as the load strobe, Table 25-12).
  User OK'd sharing the one buffer (2026-11-12), rather than a second buffer in the HV block.
- **High-voltage programming: required, as an optional block** (user, 2026-11-11): builders can
  leave it out (KiCad 10 variant with those parts DNP). It covers HVPP for the 16U2 and the 12 V needs of
  later boards (HVSP, TPI, UPDI). Details are in `docs/v2-requirements.md`.
- **SPI without CS** (user asked how): `dtoverlay=spi0-0cs` plus avrdude `linuxspi` with reset on a GPIO.
  ISP needs no CS.
- **Pin map:** v2 gets a new map, with no v1 compatibility needed. Sharing it between the CM and HAT
  variants is low priority ("only if easy"). It is easy, so the draft shares it.
- **Repo:** rename the existing `TomSawyerLabs/avr-test-hat` to **`TomSawyerLabs/mcu-hil`**
  (picked 2026-11-11; the name was free), make an archive branch `v1-archive` and a tag `v1` of the
  old version, and do the v2 rewrite there (not in a new repo). **Delete the Altium files from
  `master`** (they stay in git history), and link the `v1` tag from the README.

## Plan / steps

1. ~~Import v1 Altium project into KiCad and write up v1's circuits.~~ Done:
   `docs/v1-review.md`, with recovered data in `reference/v1-import/` (reference only).
2. ~~Requirements for v2~~: `docs/v2-requirements.md`, all questions answered (2026-11-11).
2b. ~~Repo move to `mcu-hil`~~: done 2026-11-11 with the user's yes. Merge `05395e7` (unrelated
   histories, so v1's history is kept), Altium removal `ec8def9`, pushed to `master` as a fast-forward
   (no force). `v1-archive` branch + annotated `v1` tag at `4560cfe`. Description updated.
   The repo is public with no committed workflows, so pushes start no paid CI.
3. ~~GPIO map~~: draft in `docs/v2-pinmap.md` (2026-11-11). User: sharing it between variants is low
   priority and a new v2 map is fine. Sharing turned out free, since GPIO 0–27 match on CM4/CM5/header.
4. ~~Part selection~~ (user: "parts seem fine", 2026-11-13). LCSC numbers + stock check:
   `docs/v2-parts.md`. Stock comes from `tools/jlc_search.py` (JLC's own parts-search endpoint,
   `selectSmtComponentList`; no account or key needed).
5. **(current, started 2026-11-13)** Schematic (shared sheets for common circuitry, per-variant top sheets).
   Approach:
   - **Generated by a Python script** (`tools/schgen/`), from one circuit description that both variants share.
     The script writes `.kicad_sch` files for `hw/carrier/` and `hw/hat/`. It places symbols on a grid and
     joins pins with net labels, not drawn wires. That keeps the output reproducible and diffable while the
     design still changes. Once the user starts hand-editing in KiCad, the generated files become the source and
     the generator is retired.
   - Symbols and footprints come from KiCad 10's standard libraries (embedded in each schematic, as KiCad does).
     Parts missing there come from JLC/EasyEDA via `easyeda2kicad`, into a project library `hw/lib/`.
     Their pin numbers are checked against the datasheets.
   - Sheets: DUT (16U2), Pi↔DUT I/O (translators, reset, HWB), clock (optional), DUT power + meter,
     HV (optional), USB switch. Variant-only sheets: CM connectors, Ethernet, microSD, USB-C power (carrier);
     40-pin header, ID EEPROM, USB-C loopback (HAT).
   - Checks: my own netlist check in the generator. KiCad's ERC needs the user's OK to run `kicad-cli`.
   - **Status (2026-11-13):** first full draft generated for both boards (`hw/carrier`, `hw/hat`; notes in
     `docs/v2-schematic.md`). Next: KiCad ERC + PDF export (waiting on the user's OK to run `kicad-cli`), then review.
6. Layout: CM4/CM5 carrier first, then HAT.
7. DRC/ERC, JLC DFM check, BOM/CPL generation, order review with user.

## Findings / gotchas

- Part selection (2026-11-11):
  - **SN74AXC4T774 is 3.6 V max**, so it's unusable for 5 V AVRs. LVC2T45/LXC2T45 have no OE.
    LVC8T245 has a single DIR for all bits. The fit is TI **TXU0304 / TXU0202**: fixed direction, OE, Ioff, 1.08–5.5 V.
  - **ATmega16U2 stock at JLC is thin** (84 TQFP), and so is the whole xU2 family.
  - **DF40HC(3.0) (3 mm stack) has 4 in stock.** Plan on DF40C (1.5 mm), which means the CM covers the whole top side.
  - **Correction (2026-11-12):** the 16U2's HVPP entry has no 20–60 µs window. That window is ATtiny HVSP.
    16U2 HVPP: VCC 4.5–5.5 V, XTAL1 ×6, Prog_enable 0000, then 12 V (datasheet doc7799 §25.7.1). Linux can sequence it.
  - **HVPP needs VCC 4.5–5.5 V**, not just 12 V on RESET: §25.7.1 step 1 and Table 26-9 ("VCC = 5V ± 10%").
    The user asked whether 5 V is needed (2026-11-12); the answer is yes by spec. HVPP at 3.3 V is outside the spec.
  - Checked across families (details in `docs/v2-requirements.md`): classic ATmega HVPP and ATtiny HVSP need 5 V.
    ATtiny4/5/9/10 need 5 V for any programming. tinyAVR 0/1/2 UPDI HV works at any VDD.
  - Schematic work (2026-11-13):
    - **INA228 went to 0 stock** at JLC (all variants; INA229/INA238 too). INA226 fitted (same pinout and footprint).
      Shunt raised to 1 Ω (Basic C22936): 81.9 mA full scale, 2.5 µA steps.
    - **The 16U2 has no VBUS pin**, so the SY6280 VBUS switch was dropped. Virtual unplug = USB switch.
    - **TCA6416A wants VCCP up before VCCI** (TI §10.1), or SDA can stick low and hang the I2C bus. VCCP on +5V,
      ~RESET pulled up to DUT_5V (ports held Hi-Z while the DUT is off).
    - **CM5 pins 94/96 are USB-C CC1/CC2** for its PMIC's 5 A PD; on CM4 they're ADC inputs with 100 nF. Left open,
      with 5.1k Rd on the carrier's USB-C (works with both; CM5 runs without 5 A PD).
    - CM USB_OTG_ID: internal pull-up = device; grounded = host. Driven from USB_S0 through a 2N7002.
    - HAT+ spec: 3.9k pull-ups on ID_SD/ID_SC only; EEPROM WP 1k pull-up; must be safe in STANDBY (5 V without 3.3 V).
    - LCSC's datasheet links need a browser (curl gets an HTML shell). `easyeda2kicad` fetches JLC symbols and
      footprints directly; used for TS3USB221A (RSE), HR911130C and the SWPA4030 inductor. HR911130C LED pins were
      decoded from the JLC symbol's drawing.
    - KiCad 10 schematic format: version 20260306. Variants live in each symbol instance:
      `(path ... (reference ..) (unit 1) (variant (name "no HV") (dnp yes)))`, and in the project file under
      `schematic.variants` (from KiCad's `sch_io_kicad_sexpr.cpp` and `schematic_settings.cpp`, 10.0 branch).
    - KiCad 10 ships a CM5 carrier demo (`demos/cm5_minima`, CERN-OHL-S). Used only as a reference, nothing copied.
    - Two research subagents died on API auth errors (HTTP 403); the work was redone inline.
  - `tools/jlc_search.py` needs `sys.stdout.reconfigure(encoding="utf-8")` on Windows, because descriptions contain ℃.

- v1 source is Altium. KiCad 10.0.6 `kicad-cli pcb import --format altium` imports the
  **board** (69 footprints, 155 vias, nets intact). The CLI **cannot** import Altium
  schematics (`kicad-cli sch export … Main.SchDoc` → "Failed to load schematic"); only the GUI can.
  Schematic intent was recovered by parsing `.SchDoc` OLE records with olefile
  (`reference/v1-import/tools/schdoc.py`).
- **Popups (corrected; the user reproduced them on a hidden desktop):** the modal boxes
  came from KiCad's Python `pcbnew.LoadBoard()`, which turns every parser warning into a
  modal wx dialog ("Invalid zero-sized pad pinned to 1µm … line 437"). `kicad-cli pcb import`
  printed the same warnings to the console and raised **no** dialog. This plan first
  blamed the CLI import, wrongly.
  - Fix for KiCad Python: `import wx; wx.Log.SetActiveTarget(wx.LogStderr())` before
    loading. Verified to raise no dialog.
  - Root cause: KiCad's Altium importer writes the 4 mounting-hole NPTH pads as `(size 0 0)`
    (they are 0 × 0 in Altium too), so every later load of `v1.kicad_pcb` warns about them.
- Hole cross-check (Altium `Pads6`/`Vias6` vs imported `.kicad_pcb`): 82 drilled pads and 155 vias,
  all matching in size and plating. No hole was dropped. The only hole oddity is the 4 zero-size
  mounting-hole pads (2.75 mm NPTH) above. J7's plated slots came through as oval drills. D1–D4 lost unsupported polygon graphics (not holes).
- Altium internal units are 1e-4 mil (2.54e-6 mm). An off-by-10 here first made the drills look 10× too big.
- The v1 BOM is wrong in places: resistor `Comment`/part numbers disagree with `Value` (e.g. USB-C
  CC resistors are 1k parts but should be 5.1k). Don't reuse v1 part numbers blindly.
- v1 has no LCSC numbers or supplier fields anywhere.
- v1's DUT was an on-board ATmega16U2, with the same ISP lines also on two 2×3 headers.

## Progress log

- [x] Project dir + repo created, plan seeded (2026-11-11).
- [x] v1 import and review: `docs/v1-review.md` (2026-11-11).
- [x] v1 board and schematic images: `docs/v1-images/` (rendered from files, no KiCad runtime).
- [x] v2 requirements: `docs/v2-requirements.md`, open questions answered (2026-11-11).
- [x] Repo move local prep: branch `mcu-hil-merge` (merge, Altium removal, new README).
- [x] Repo move GitHub steps (2026-11-11): renamed to https://github.com/TomSawyerLabs/mcu-hil,
      `v1-archive` branch and annotated `v1` tag at `4560cfe`, `master` fast-forwarded to the merged history,
      description updated. Local `master` tracks `origin/master`.
- [x] v2 pin map draft: `docs/v2-pinmap.md` (shared by CM and HAT; all defaults set by external resistors).
- [x] v1 review corrected: J6A/J6B not populated, J6B is an alternate for J7 (verified in the board file).
- [x] Part selection, first pass: `docs/v2-parts.md` (stock as of 2026-11-11 8:50 PM PST).
- [x] DUT at 5 V with translators, load switch, optional clock override and optional HV (user, 2026-11-12).
- [x] User review of the parts list ("parts seem fine", 2026-11-13).
- [x] Schematic generator (`tools/schgen/`) and first full draft of both boards (2026-11-13).
- [ ] KiCad ERC and PDF review of the generated schematics (needs OK to run `kicad-cli`).
- [ ] User review of the schematic.
- [ ] Fit check: CM connectors, RJ45, USB-C, microSD, MCU, USB switch and power meter on 55 × 40 mm (likely both sides).

## Open questions for the user

1. **OK to run `kicad-cli`** (ERC + PDF export of the generated schematics, hidden window)? Asked 2026-11-13.
2. ~~Parts list review~~ (approved 2026-11-13). Was: (`docs/v2-parts.md`), including accepting the thin 16U2 stock (84 at JLC).

Answered 2026-11-11: name `mcu-hil`, USB switch instead of a hub, no PoE in this version,
repo move approved (done), and the built v1 has USB-C. Answered 2026-11-12: DUT at 5 V, translators in, clock override and HV both optional.

## Things not to do

- Don't pick parts without an LCSC number or that are out of stock.
- Don't modify the v1 repo (`..\avr-test-hat`) beyond the agreed rename/archive/rewrite steps,
  and don't touch its uncommitted `.github/` and `OS Image/` files (not this thread's).
- **Don't run KiCad's runtime (kicad-cli or KiCad's Python) without asking first.**
  KiCad's Python (`pcbnew.LoadBoard` etc.) turns parser warnings into modal wx dialogs
  that land on the user's screen and block until dismissed. That happened ~16 times on
  2026-11-11 around 12:20–12:22 AM PST (08:20–08:22Z). Default to reading
  `.kicad_pcb`/`.kicad_sch` as S-expression text and Altium files with olefile.
  If the runtime is truly needed, ask first, then use **both** of these:
  1. `import wx; wx.Log.SetActiveTarget(wx.LogStderr())` before any load (KiCad Python).
  2. The hidden-desktop harness, which reports any windows it creates:
     `C:\Users\camer\AppData\Local\Temp\claude\0205f6f58e3459de\7d71a0b8-4c7a-477c-a12b-b9f1ae632030\scratchpad\kicad-popup\hidden-run.ps1`.
     It's a backstop, not a replacement for the LogStderr fix.
- Don't re-run the Altium PCB import; reuse `reference/v1-import/v1.kicad_pcb`.
