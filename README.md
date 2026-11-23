# mcu-hil

Hardware-in-the-loop boards for testing software against real microcontrollers.
A Raspberry Pi (Compute Module or standard Pi) powers, programs, clocks, resets and talks to
the microcontroller(s) on the board, so tests run against real silicon in a repeatable way.

AVRs come first (starting with the ATmega16U2 from v1). Other families (XMEGA, AVR32 UC3, and
more later) get their own boards built from the same base design.

## Variants

Each variant is a complete board with its MCU(s) on it. They share schematic sheets and one GPIO map.

- **CM4/CM5 carrier** (primary): same 55 × 40 mm outline as the Compute Module, so they stack.
  USB-C for power and rpiboot, Ethernet for network boot, microSD.
- **Pi HAT**: for 40-pin Raspberry Pi boards. Powered by the Pi; its USB-C is a data link back to
  the Pi through a short loopback cable.

Designed in KiCad. Every part has an LCSC part number and is chosen to be in stock, so boards can be
ordered fully assembled from JLCPCB.

## Status

v2 is being designed. See [plans/v2-design.md](plans/v2-design.md), the
[v1 design review](docs/v1-review.md), the [v2 requirements draft](docs/v2-requirements.md),
the [v2 pin map](docs/v2-pinmap.md), the [parts list](docs/v2-parts.md) and the
[schematic notes](docs/v2-schematic.md).

The KiCad 10 projects are in `hw/carrier/` and `hw/hat/`. Their schematics are generated from
[`tools/schgen/design.py`](tools/schgen/design.py) (`cd tools && python -m schgen`).

Optional blocks (crystal, crystal switch, clock override, Si5351, HV programming, microSD) are independent
on/off options, listed in [`hw/options.toml`](hw/options.toml). Make the JLC BOM for any mix with
`cd tools && python -m bom carrier --without SD,HV` (`--list` shows the options). It writes
`hw/<board>/out/<build>-bom.csv` and a report.

Parts come from a committed lock, `hw/<board>/bom.lock.json`. `python -m bom <board> --update --qty N` re-picks
parts that are short for N boards: each symbol's `LCSC` field is the preferred part, and its `Spec` field
(`R 10k 1% 0402`, `C 100n X5R+ 16V 0402`, `mpn 2N7002 SOT-23`, ...) says what may replace it. `--qty N` without
`--update` re-checks the locked parts' stock live.
View them in the browser with KiCanvas: [carrier](https://kicanvas.org/?github=https://github.com/TomSawyerLabs/mcu-hil/tree/master/hw/carrier), [HAT](https://kicanvas.org/?github=https://github.com/TomSawyerLabs/mcu-hil/tree/master/hw/hat).

## v1 (AVR Test HAT)

This repo was `avr-test-hat`. The v1 design was an Altium project for a single Pi HAT with an
on-board ATmega16U2. Its files are no longer on `master` but are kept in history:

- Tag [`v1`](https://github.com/TomSawyerLabs/mcu-hil/tree/v1) (also branch
  [`v1-archive`](https://github.com/TomSawyerLabs/mcu-hil/tree/v1-archive)): the Altium project as it was.
- v1's simplified block diagram: [docs/v1-images/Circuits.drawio.svg](docs/v1-images/Circuits.drawio.svg).

v1 credits: [Raspberry Pi HAT Template](https://workspace.circuitmaker.com/Projects/Details/jonaslorander/Raspberry-Pi-HAT-Template)
by [Jonas Lorander](https://workspace.circuitmaker.com/User/Details/jonaslorander), and [SnapEDA](https://www.snapeda.com).
