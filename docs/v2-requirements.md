# v2 requirements (draft, pending user answers)

Derived from [v1-review.md](v1-review.md). Items marked **(Q n)** wait on open question *n* in
[plans/v2-design.md](../plans/v2-design.md).

## Keep from v1 (fixed where noted)

- Pi-controlled DUT power switching, off by default. Separate VCC and USB rails are worth keeping for USB AVRs.
- Reset control: open-drain, asserted by default, plus a reset-state LED. **Fix:** pull up to the switched target VCC, not the always-on 5V.
- ISP over Pi SPI0 through a buffer the Pi can disable, so the Pi lets go of the lines when not programming.
- UART between Pi and DUT, also through a buffer that can be disabled.
- HWB (DFU entry) control for USB AVRs. **Fix:** move it off GPIO2/3 so I2C1 is free.
- Clock override from GPCLK0 into XTAL1, through a buffer powered from the target rail.
- HAT ID EEPROM with a WP jumper (HAT variant; the carrier gets one too if useful).
- Activity LEDs.

## Fix

- Every resistor value matches its part number, and every part has an LCSC number (the v1 BOM/schematic mismatch).
- Real level translation referenced to the target's VCC (e.g. 74LVC1T45/2T45/8T245-class parts), not 3.3 V buffers driving 5 V inputs.
- USB-C done properly: 5.1k Rd on any sink port, no unprotected back-feed of the Pi 5V rail
  (the HAT spec's ideal-diode/back-power protection if the HAT accepts power).
- No parallel USB connectors stubbing D+/D-.
- Footprints from KiCad's standard library or JLC/EasyEDA, with plated slots where the datasheet asks for them.
- Clean DRC/ERC, and JLC's DFM check passing.

## Add (proposed)

- **Carrier (CM4/CM5):** native USB from the CM to the DUT. That needs a USB 2.0 hub if there's more than one DUT port
  or the carrier itself needs USB. Each DUT port gets a VBUS switch with current limit, so the Pi can "unplug" it. **(Q 3)**
- DUT current/voltage monitoring (INA226-class) on the switched rail. **(Q 4)**
- Selectable target voltage (3.3 V / 5 V, maybe adjustable). **(Q 2)**
- Support for more AVR programming interfaces (UPDI, PDI, TPI, debugWIRE) depending on the DUT families. **(Q 1)**
- A breakout of more DUT GPIO to free Pi GPIO, for functional tests. **(Q 1)**
- microSD. **(Q 5)**

## Shared GPIO map constraint

Both variants use the BCM GPIO 0–27 bank. CM4 and CM5 bring all of it out on their two Hirose DF40
100-pin connectors, with the same alt functions as the 40-pin header, so one map serves both. The carrier gets extra pins (USB, more power control,
maybe I2C GPIO expanders) that the HAT lacks, and on the HAT the DUT USB goes over a cable.
