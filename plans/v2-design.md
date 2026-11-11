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

1. **(current)** Import v1 Altium project into KiCad (scratch copy, not committed
   as the v2 design) and write up v1's circuits: blocks, nets, Pi GPIO map, parts
   used, and what each block is for. Save as `docs/v1-review.md`.
2. Requirements doc for v2: what to keep, drop, add. Bring open questions to the user.
3. GPIO map shared by both variants (CM4 vs CM5 differences, HAT 40-pin limits).
4. Part selection with LCSC numbers + stock check (jlcpcb.com parts / JLC API).
5. Schematic (shared sheets for common circuitry, per-variant top sheets).
6. Layout: CM4/CM5 carrier first, then HAT.
7. DRC/ERC, JLC DFM check, BOM/CPL generation, order review with user.

## Findings / gotchas

- v1 source is Altium, which KiCad imports natively.

## Progress log

- [x] Project dir + repo created, plan seeded (2026-11-11).
- [ ] v1 import and review.
- [ ] v2 requirements.

## Open questions for the user

1. microSD card: the request was cut off at "If there is room to support a uSD
   card on ..." On which variant(s), and for what (CM4/CM5 Lite boot media)?
   Recommendation: carrier board, wired to the CM's SD interface so Lite modules work.
2. GitHub repo: new repo (e.g. under `TomSawyerLabs`), or v2 folder in the existing
   `TomSawyerLabs/avr-test-hat`? Private or public?

## Things not to do

- Don't pick parts without an LCSC number or that are out of stock.
- Don't modify the v1 repo (`..\avr-test-hat`); work from a copy.
