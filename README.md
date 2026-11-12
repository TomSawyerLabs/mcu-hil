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
the [v2 pin map](docs/v2-pinmap.md) and the [parts list](docs/v2-parts.md).

## v1 (AVR Test HAT)

This repo was `avr-test-hat`. The v1 design was an Altium project for a single Pi HAT with an
on-board ATmega16U2. Its files are no longer on `master` but are kept in history:

- Tag [`v1`](https://github.com/TomSawyerLabs/mcu-hil/tree/v1) (also branch
  [`v1-archive`](https://github.com/TomSawyerLabs/mcu-hil/tree/v1-archive)): the Altium project as it was.
- v1's simplified block diagram: [docs/v1-images/Circuits.drawio.svg](docs/v1-images/Circuits.drawio.svg).

v1 credits: [Raspberry Pi HAT Template](https://workspace.circuitmaker.com/Projects/Details/jonaslorander/Raspberry-Pi-HAT-Template)
by [Jonas Lorander](https://workspace.circuitmaker.com/User/Details/jonaslorander), and [SnapEDA](https://www.snapeda.com).
