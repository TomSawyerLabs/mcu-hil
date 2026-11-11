# AVR Tester v2 design

## Goal

Design the next generation of the AVR Test HAT: Raspberry Pi hardware that
connects to, programs and exercises AVR microcontrollers under test. Output is
a KiCad project (or two) that can be ordered fully assembled from JLCPCB and
work on arrival.

## Environment / context

- This repo: `C:\Users\camer\git\Personal Projects\avr-tester-v2` (branch `master`, no remote yet).
- v1 design: `C:\Users\camer\git\Personal Projects\avr-test-hat`
  (remote `https://github.com/TomSawyerLabs/avr-test-hat`).
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

## Plan / steps

1. ~~Import v1 Altium project into KiCad and write up v1's circuits.~~ Done:
   `docs/v1-review.md`, with recovered data in `reference/v1-import/` (reference only).
2. **(current: waiting on the user's answers)** Requirements for v2: draft is in
   `docs/v2-requirements.md`. Finalize it once the open questions below are answered.
3. GPIO map shared by both variants (CM4 vs CM5 differences, HAT 40-pin limits).
4. Part selection with LCSC numbers + stock check (jlcpcb.com parts / JLC API).
5. Schematic (shared sheets for common circuitry, per-variant top sheets).
6. Layout: CM4/CM5 carrier first, then HAT.
7. DRC/ERC, JLC DFM check, BOM/CPL generation, order review with user.

## Findings / gotchas

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
- [ ] v2 requirements: draft in `docs/v2-requirements.md`, waiting on answers to the open questions.

## Open questions for the user

1. **DUT:** what will v2 test? v1 soldered an ATmega16U2 onto the HAT. Is v2 for external
   boards (cable, ISP header, pogo fixture), an on-board chip or socket, or both? Which AVR
   families (USB megaAVR like 16U2/32U4, classic megaAVR, tinyAVR 0/1/2 or AVR Dx over UPDI, XMEGA over PDI)?
   This drives the programming interfaces, connectors and pin count.
2. **Target voltage:** fixed 5 V like v1, switchable 3.3/5 V, or adjustable?
   Recommendation: switchable 3.3/5 V, with level translators referenced to target VCC.
3. **DUT USB on the carrier:** how many DUT USB ports? Per-port VBUS switching ("virtual unplug")?
   CM4 has one USB 2.0 host port, so more than one port means a hub chip. CM5 has more.
   Recommendation: a hub with 2 DUT ports, each with a VBUS load switch.
4. **Measurement:** add DUT current/voltage monitoring (INA226-class)? Recommendation: yes.
5. **microSD:** the request was cut off at "If there is room to support a uSD card on ...".
   Which variant, and for what? Recommendation: on the carrier, wired to the CM's SD
   interface so CM4/CM5 Lite (no eMMC) modules can boot.
6. **Carrier extras:** Ethernet magjack? Power input (USB-C PD, barrel 12 V, PoE)? Form factor or enclosure?
   Recommendation: gigabit Ethernet and 5 V USB-C PD input (CM5 wants 5 V/5 A), sized to fit
   a stock enclosure if you have one in mind.
7. **v1 history:** was v1 ever fabricated? What worked, what didn't, and what got bodged?
8. **GitHub repo:** new repo (e.g. `TomSawyerLabs/avr-tester-v2`), or a v2 folder in the existing
   `TomSawyerLabs/avr-test-hat`? Private or public? (No repo gets created until you answer.)

## Things not to do

- Don't pick parts without an LCSC number or that are out of stock.
- Don't modify the v1 repo (`..\avr-test-hat`); work from a copy.
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
