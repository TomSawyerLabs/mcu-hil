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
- ISP over Pi SPI0 through a translator the Pi can disable, so the Pi lets go of the lines when not programming.
- UART between Pi and DUT, also through a translator that can be disabled.
- HWB (DFU entry) control for USB AVRs. **Fix:** move it off GPIO2/3 so I2C1 is free.
- Clock override from GPCLK0 into XTAL1, through a buffer powered from the target rail. **Optional** (user,
  2026-11-12): a "no clock override" build leaves the buffer off.
- HAT ID EEPROM with a WP jumper (HAT variant; the carrier gets one too if useful).
- Activity LEDs.

## Fix

- Every resistor value matches its part number, and every part has an LCSC number (the v1 BOM/schematic mismatch).
- Level translation in both directions, referenced to the target's VCC (TXU0304/TXU0202),
  not a 3.3 V buffer driving 5 V inputs.
- No back-powering a switched-off DUT through its I/O pins: translators default to Hi-Z, their DUT side runs from
  the switched rail (Ioff), and pull-ups go to the switched target rail.
- USB-C done properly: 5.1k Rd on any sink port, and no two supplies tied together without an ideal diode.
- No parallel USB connectors stubbing D+/D-.
- Footprints from KiCad's standard library or JLC/EasyEDA, with plated slots where the datasheet asks for them.
  No overlapping alternate footprints (v1's J3/J4).
- Clean DRC/ERC, and JLC's DFM check passing.

## Add

- **Target voltage: 5 V** (user, 2026-11-12). Every classic AVR needs 5 V for HV programming anyway (see below),
  so the DUT rail is a fixed 5 V behind a load switch (TPS22918), with no 3.3/5 V mux.
  - The 16U2 runs at 16 MHz, its full speed at 4.5–5.5 V.
  - USB uses the 16U2's internal 3.3 V regulator (its reset default), with 1 µF on UCAP.
  - Level translators (TXU0304 for ISP, TXU0202 for UART) between the Pi's 3.3 V and the DUT's 5 V.
  - A short detour on 2026-11-12 tried 3.3 V (8 MHz, series resistors instead of translators). It was dropped
    because HVPP needs 5 V regardless.
- **Power meter per DUT rail**, sized for AVR currents: from µA in sleep to tens of mA running. The 16U2 board uses an
  INA226 (16-bit) with a 1 Ω shunt: 81.9 mA full scale, 2.5 µA steps. INA228 (20-bit) is a drop-in upgrade when in stock.
- **DUT USB:** one USB port per MCU. Virtual unplug is the USB switch (it disconnects D+/D-). MCUs with a VBUS pin
  also get a current-limited VBUS switch; the 16U2 has no VBUS pin, so its board has none.
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
  The ISP lines must never touch RESET.
- **VCC for HVPP is 4.5–5.5 V.** The DUT rail is always 5 V, so HV mode needs no extra supply switching.
- **Which AVRs need 5 V VCC for HV** (checked 2026-11-12):
  - Classic ATmega HVPP (16U2: §25.7.1, Table 26-9 "VCC = 5V ± 10%") and classic ATtiny HVSP
    (ATtiny25/45/85 DS2586: "Apply 4.5 - 5.5V between VCC and GND", then 12 V 20–60 µs later): **yes**.
  - ATtiny4/5/9/10 (TPI): their NVM can only be programmed at 5 V at all, HV or not (datasheet and errata).
  - tinyAVR 0/1/2 UPDI HV (ATtiny1614 DS40002204A §33.3.2.1.3): **no**. A 12 V pulse on RESET (≥11.5 V,
    100 µs–1 ms) at any operating VDD; no VDD condition is stated.
  - AVR DA/DB have a dedicated UPDI pin, so no HV. Newer DD/EA-class parts use a lower HV level; check per part.
  - XMEGA and UC3 have no HV mode.
  That's why the DUT rail is 5 V.
- **Entry timing (corrected 2026-11-12):** the 16U2's HVPP entry (§25.7.1) has **no tight window**:
  1. VCC on.
  2. RESET low, and toggle XTAL1 at least 6 times.
  3. Prog_enable = 0000, then wait at least 100 ns.
  4. Apply 12 V to RESET, with no Prog_enable activity for 100 ns.
  5. Wait at least 50 µs.

  The Pi can do all of that from Linux. The 20–60 µs window belongs to ATtiny **HVSP**. A future ATtiny board
  would need a hardware-timed entry (an RC delay from VCC to the 12 V switch). The 16U2 board doesn't.
- **Pins:** 16 HVPP data and control lines through an I2C GPIO expander (Hi-Z by default, no back-powering an off DUT:
  pick a part with Ioff or power it from the DUT rail). XTAL1 is pulsed through the clock buffer, so **the HV option
  needs the clock-override buffer fitted** (the Si5351 stays optional).
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
