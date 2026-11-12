# v2 requirements (draft)

Derived from [v1-review.md](v1-review.md) and the user's answers of 2026-11-11.
Decisions and open items live in [plans/v2-design.md](../plans/v2-design.md).

## Purpose

- Reproducible builds with open tools (KiCad, JLCPCB assembly, LCSC parts).
- A base design that new parts can be added to: other AVRs (e.g. AVR32 UC3, XMEGA), each on its own
  board or a couple per board. Pis aren't free, so a board may carry more than one MCU.
- **Complete boards, no plug-in cards.** Each variant is a whole CM carrier or HAT with its MCU(s) on it.
  Variants share schematic sheets, not a connector.
- **CM carrier outline = CM4/CM5 module outline (55 × 40 mm)**, stacking like the Waveshare CM4-NANO.
- The main target is each part's standard, officially supported operating modes.
  Later special boards may push overclocking or power-draw limits.

## Keep from v1 (fixed where noted)

- Pi-controlled DUT power switching, off by default. Separate VCC and USB rails for USB AVRs.
- Reset control: open-drain, asserted by default, plus a reset-state LED.
- ISP over Pi SPI0 through a buffer the Pi can disable, so the Pi lets go of the lines when not programming.
- UART between Pi and DUT, also through a buffer that can be disabled.
- HWB (DFU entry) control for USB AVRs. **Fix:** move it off GPIO2/3 so I2C1 is free.
- Clock override from GPCLK0 into XTAL1, through a buffer powered from the target rail.
- HAT ID EEPROM with a WP jumper (HAT variant; the carrier gets one too if useful).
- Activity LEDs.

## Fix

- Every resistor value matches its part number, and every part has an LCSC number (the v1 BOM/schematic mismatch).
- Level translation in both directions, referenced to the target's VCC (e.g. 74LVC1T45/2T45/8T245-class),
  not a 3.3 V buffer driving 5 V inputs.
- No back-powering a switched-off DUT through its I/O pins: buffers default to Hi-Z, and pull-ups go to the
  switched target rail.
- USB-C done properly: 5.1k Rd on any sink port, and no two supplies tied together without an ideal diode.
- No parallel USB connectors stubbing D+/D-.
- Footprints from KiCad's standard library or JLC/EasyEDA, with plated slots where the datasheet asks for them.
  No overlapping alternate footprints (v1's J3/J4).
- Clean DRC/ERC, and JLC's DFM check passing.

## Add

- **Target voltage:** whatever is easiest per DUT. Each DUT gets the rail its standard operating mode needs
  (5 V for 16U2 at 16 MHz, 3.3 V for XMEGA/UC3). The base supplies 5 V and 3.3 V, and the DUT side picks.
- **Power meter per DUT rail**, sized for AVR currents: from µA in sleep to ~100–200 mA running. Covering that
  range likely takes a high-resolution monitor (INA228-class) or switchable shunts. To be chosen in part selection.
- **DUT USB:** one USB port per MCU, with a current-limited VBUS switch the Pi controls (virtual unplug).
  Software-USB testing routes MCU GPIO to a D+/D- pair.
- **USB switch, no hub:** only one USB path is needed at a time. The host's USB 2.0 port goes through a
  high-speed analog USB switch to one of: USB-C (rpiboot, the default), the MCU's hardware USB, or the
  software-USB pins. Unselected paths are fully disconnected. With two USB MCUs on one board, tests switch
  between them. The same circuit sits on the HAT behind the loopback cable.
- **HAT USB:** USB-C as a data link to the Pi through a short loopback cable. It is not a power input.
- **Clock control:** keep GPCLK0 → XTAL1 override per DUT. Consider a programmable clock generator
  (Si5351-class, 3 outputs) for arbitrary and overclock frequencies.
- **More programming interfaces** as DUT families need them: PDI (XMEGA), aWire/JTAG (UC3), UPDI, TPI, debugWIRE.
- **High-voltage programming** (see below), as a population option.

### High-voltage programming

Needed to recover AVRs whose fuses lock out ISP: RSTDISBL set, SPIEN cleared, or a bad clock fuse.
**It's an optional block.** Builders can leave it off with the KiCad 10 design variant "no HV", which
marks those parts DNP. The board must stay fully safe and working either way.

- **Modes:** HVPP for the 16U2 (and other ATmegas). The same block covers later boards' 12 V needs:
  HVSP (8/14-pin ATtiny, 4 signals), TPI with 12 V on RESET (ATtiny4/5/9/10), and the UPDI 12 V
  enable pulse (tinyAVR 0/1/2). XMEGA and UC3 have no HV mode.
- **12 V source:** a small boost from 5 V (11.5–12.5 V at RESET, a few mA). It's enabled by the Pi and off by default.
- **12 V switch onto RESET:** off by default. With the HV parts left off, RESET works exactly as without HV.
  A solder jumper or 0 Ω also lets a built board disable HV.
- **Protect the RESET net from 12 V:** the open-drain reset FET must be rated well above 12 V (e.g. 2N7002
  at 60 V). The RESET pull-up must not feed 12 V into the DUT rail (a diode in series or a switched pull-up).
  The ISP translator must never touch RESET.
- **Entry timing in hardware:** HVPP entry wants VCC up (above 1.8 V within 20 µs), then 12 V on RESET
  20–60 µs later (16U2 datasheet; re-check during schematic work). So:
  - the Pi arms HV, then switches VCC on, and an RC delay applies 12 V inside the window
  - the VCC switch must be fast in HV mode, so it can't have a slow soft-start there
- **Pins:** 16 HVPP data and control lines through an I2C GPIO expander (Hi-Z by default, no back-powering an off DUT:
  pick a part with Ioff or power it from the DUT rail). XTAL1 is pulsed through the existing clock buffer.
  The pin map is in [v2-pinmap.md](v2-pinmap.md#high-voltage-programming).
- **CM carrier:** microSD slot (CM4/CM5 Lite; network boot is the plan, so no storage should be needed),
  Ethernet jack for network boot, and a USB-C port for backup power and rpiboot firmware flashing.
  On CM4 the single USB 2.0 port is shared by rpiboot and the DUT, which the USB switch above handles.
- **Power input:** USB-C only. No PoE in this version, and no secondary power inputs anywhere;
  the HAT is powered by the Pi.

## Shared GPIO map constraint

Both variants use the BCM GPIO 0–27 bank. CM4 and CM5 bring all of it out on their two Hirose DF40
100-pin connectors, with the same alt functions as the 40-pin header, so one map serves both. The carrier gets
extra pins (USB, more power control, maybe I2C GPIO expanders) that the HAT lacks. On the HAT the DUT USB goes over a cable.
