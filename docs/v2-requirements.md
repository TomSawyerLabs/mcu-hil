# v2 requirements (draft)

Derived from [v1-review.md](v1-review.md) and the user's answers of 2026-11-11. Items marked **(Q n)**
wait on open question *n* in [plans/v2-design.md](../plans/v2-design.md).

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
  Software-USB testing routes MCU GPIO to a D+/D- pair. A small hub on every board would let hardware and
  software USB run at once, on both CM and HAT. **(Q 2: hub?)**
- **HAT USB:** USB-C as a data link to the Pi through a short loopback cable. It is not a power input.
- **Clock control:** keep GPCLK0 → XTAL1 override per DUT. Consider a programmable clock generator
  (Si5351-class, 3 outputs) for arbitrary and overclock frequencies.
- **More programming interfaces** as DUT families need them: PDI (XMEGA), aWire/JTAG (UC3), UPDI, TPI, debugWIRE.
- **CM carrier:** microSD slot (CM4/CM5 Lite; network boot is the plan, so no storage should be needed),
  Ethernet jack for network boot, and a USB-C port for backup power and rpiboot firmware flashing.
  On CM4 the single USB 2.0 port is shared by the hub and rpiboot, so it needs a USB switch, as the CM4 IO board has.
- **Power input:** USB-C only, plus PoE as an option **(Q 3: how)**. No secondary power inputs anywhere;
  the HAT is powered by the Pi.

## Shared GPIO map constraint

Both variants use the BCM GPIO 0–27 bank. CM4 and CM5 bring all of it out on their two Hirose DF40
100-pin connectors, with the same alt functions as the 40-pin header, so one map serves both. The carrier gets
extra pins (USB, more power control, maybe I2C GPIO expanders) that the HAT lacks. On the HAT the DUT USB goes over a cable.
