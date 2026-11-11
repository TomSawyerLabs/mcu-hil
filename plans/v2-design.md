# AVR Tester v2 design

## Goal

Design the next generation of the AVR Test HAT: Raspberry Pi hardware that
connects to, programs and exercises AVR microcontrollers under test. Output is
a KiCad project (or two) that can be ordered fully assembled from JLCPCB and
work on arrival.

## Environment / context

- This repo: `C:\Users\camer\git\Personal Projects\avr-tester-v2`. Remote `v1` =
  `https://github.com/TomSawyerLabs/avr-test-hat.git` (fetch only so far; becomes `origin` →
  `mcu-hil` after the rename). Repo-move work is on local branch `mcu-hil-merge` (step 2b).
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
- **v1 history:** a v1 was built, but it may not match the Altium files. Whether it has USB-C is
  unconfirmed (the user will check the board edge).
- **Repo:** rename the existing `TomSawyerLabs/avr-test-hat` to **`TomSawyerLabs/mcu-hil`**
  (picked 2026-11-11; the name was free), make an archive branch `v1-archive` and a tag `v1` of the
  old version, and do the v2 rewrite there (not in a new repo). **Delete the Altium files from
  `master`** (they stay in git history), and link the `v1` tag from the README.

## Plan / steps

1. ~~Import v1 Altium project into KiCad and write up v1's circuits.~~ Done:
   `docs/v1-review.md`, with recovered data in `reference/v1-import/` (reference only).
2. ~~Requirements for v2~~: `docs/v2-requirements.md`, all questions answered (2026-11-11).
2b. **(current: waiting on the user's yes for the GitHub steps)** Repo move to `mcu-hil`.
   Local prep is done: in this repo, remote `v1` = the GitHub repo, and local branch
   `mcu-hil-merge` holds the merge (`05395e7`, unrelated histories, README rewritten), then
   Altium removal (`ec8def9`) and a `.gitignore` commit. Its first parent is our `master`, second is
   v1 `4560cfe`, so pushing it to GitHub `master` is a **fast-forward** (no force).
   GitHub steps, each needing its own yes:
   1. `gh repo rename mcu-hil -R TomSawyerLabs/avr-test-hat --yes` (GitHub redirects the old URL).
   2. `git push v1 4560cfe:refs/heads/v1-archive` and `git tag -a v1 4560cfe -m "v1: Altium AVR Test HAT"`
      then `git push v1 refs/tags/v1`.
   3. `git push v1 mcu-hil-merge:master` (fast-forward), then locally rename remote `v1` → `origin`
      with URL `https://github.com/TomSawyerLabs/mcu-hil.git`, fast-forward local `master`,
      delete `mcu-hil-merge`.
   4. `gh repo edit TomSawyerLabs/mcu-hil --description "..."` (new description).
   The v1 checkout `..\avr-test-hat` is left alone (its remote keeps working through the redirect).
   The repo is public with no committed workflows, so pushes start no paid CI.
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
- [x] v1 board and schematic images: `docs/v1-images/` (rendered from files, no KiCad runtime).
- [x] v2 requirements: `docs/v2-requirements.md`, open questions answered (2026-11-11).
- [x] Repo move local prep: branch `mcu-hil-merge` (merge, Altium removal, new README).
- [ ] Repo move GitHub steps (rename, `v1-archive` + `v1`, push `master`), waiting on the user's yes.
- [ ] Fit check: CM connectors, RJ45, USB-C, microSD, MCU, USB switch and power meter on 55 × 40 mm (likely both sides).

## Open questions for the user

1. **Go-ahead for the repo-move GitHub steps** listed in step 2b (each needs a yes).
2. Whether the built v1 board has USB-C (user checks the board edge 2026-11-12).

Answered 2026-11-11: name `mcu-hil`; USB switch instead of a hub; no PoE this version.

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
