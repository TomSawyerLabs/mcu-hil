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
- ISP over Pi SPI0, and UART between Pi and DUT. **This version uses series resistors, not buffers**
  (user, 2026-11-12, see the target voltage section). The Pi lets go of the lines by setting its pins to inputs.
- HWB (DFU entry) control for USB AVRs. **Fix:** move it off GPIO2/3 so I2C1 is free.
- Clock override from GPCLK0 into XTAL1, through a buffer powered from the target rail.
- HAT ID EEPROM with a WP jumper (HAT variant; the carrier gets one too if useful).
- Activity LEDs.

## Fix

- Every resistor value matches its part number, and every part has an LCSC number (the v1 BOM/schematic mismatch).
- No 3.3 V buffer driving 5 V inputs. This version runs the DUT at 3.3 V, so no translation is needed.
  A future 5 V board needs real translators (TXU0304/TXU0202 were the pick, see the parts list).
- No back-powering a switched-off DUT through its I/O pins: series resistors limit it, software keeps the Pi pins
  as inputs while the DUT is off, and pull-ups go to the switched target rail.
- USB-C done properly: 5.1k Rd on any sink port, and no two supplies tied together without an ideal diode.
- No parallel USB connectors stubbing D+/D-.
- Footprints from KiCad's standard library or JLC/EasyEDA, with plated slots where the datasheet asks for them.
  No overlapping alternate footprints (v1's J3/J4).
- Clean DRC/ERC, and JLC's DFM check passing.

## Add

- **Target voltage: 3.3 V for now** (user, 2026-11-12), for every MCU. That matches the Pi's I/O, XMEGA and UC3.
  - The 16U2 at 3.3 V is limited to about 10.7 MHz (linear from 8 MHz at 2.7 V to 16 MHz at 4.5 V,
    datasheet §26.3), so its crystal is **8 MHz**. USB still works, because the PLL takes 8 or 16 MHz.
  - USB at 3.3 V follows the datasheet's fig. 20-6: UVCC, AVCC and VCC all on the 3.3 V rail, 1 µF on UCAP,
    and firmware sets REGCR.REGDIS. The same wiring works at 5 V with the regulator enabled (its reset default).
  - **The DUT rail can still switch to 5 V, for HVPP only** (§25.7.1 requires VCC 4.5–5.5 V). That's part of
    the HV option. Without HV, the rail is fixed at 3.3 V.
  - **No level translators in this version** (user, 2026-11-12): ISP and UART go through 4.7 kΩ series
    resistors. The resistors limit back-feed into an unpowered DUT and the 5 V injection into the Pi during HVPP.
    The clock buffer stays, to drive XTAL1 hard and gate it.
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
  The ISP lines must never touch RESET.
- **VCC for HVPP is 4.5–5.5 V**, so HV mode switches the DUT rail from 3.3 V to 5 V (power mux, Pi-selected,
  3.3 V by default).
- **Entry timing (corrected 2026-11-12):** the 16U2's HVPP entry (§25.7.1) has **no tight window**:
  1. VCC on.
  2. RESET low, and toggle XTAL1 at least 6 times.
  3. Prog_enable = 0000, then wait at least 100 ns.
  4. Apply 12 V to RESET, with no Prog_enable activity for 100 ns.
  5. Wait at least 50 µs.

  The Pi can do all of that from Linux. The 20–60 µs window belongs to ATtiny **HVSP**. A future ATtiny board
  would need a hardware-timed entry (an RC delay from VCC to the 12 V switch). The 16U2 board doesn't.
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
