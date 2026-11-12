# v2 Pi GPIO map (draft)

A new map for v2. It does **not** try to match v1 ([v1 map](v1-review.md#v1-pi-gpio-map)).

The CM carrier and the HAT use the same map, which costs nothing. CM4 and CM5 bring out all of BCM GPIO 0–27 on
their DF40 connectors, with the same alt functions as the Pi's 40-pin header. Pi 4/CM4 (BCM2711) and
Pi 5/CM5 (RP1) agree on everything below. Sharing is a nice-to-have, though. If a variant ever needs a
different pin, it gets one.

This is a single-MCU board. Per-DUT signals for a board with more MCUs are covered at the end.

## Rules

- **Every default is set by an external resistor.** The board never relies on the SoC's pulls, which differ by
  bank and by chip and only take effect once the SoC is running. Before boot and with the Pi off, every
  DUT-side signal is in its safe state: power off, buffers Hi-Z, reset asserted.
- Enables are **active-high with pull-downs**, on GPIO 9–27. The SoC's own power-on pulls are down on that bank,
  so they agree with the external ones.
- I2C1 (GPIO 2/3) stays I2C. v1 used it for HWB.
- SPI0 runs without chip selects (`dtoverlay=spi0-0cs`). ISP doesn't use CS, since RESET is a separate pin.
  That frees GPIO 7/8 as plain GPIOs.

## Map

| BCM | Header pin | Alt function | v2 use | Default (external) |
| --- | --- | --- | --- | --- |
| 0 / 1 | 27 / 28 | ID_SD / ID_SC | HAT ID EEPROM (HAT). Reserved on the carrier. | — |
| 2 / 3 | 3 / 5 | SDA1 / SCL1 | I2C bus: power meter, clock generator if fitted, I/O expander if needed | pull-ups |
| 4 | 7 | GPCLK0 | Clock out → clock buffer → DUT XTAL1 | — |
| 5, 6 | 29, 31 | — | Spare | — |
| 7, 8 | 26, 24 | (SPI0 CE1/CE0) | Spare (no CS with `spi0-0cs`) | — |
| 9 / 10 / 11 | 21 / 19 / 23 | SPI0 MISO / MOSI / SCLK | ISP through the level translator | — |
| 12 | 32 | — | DUT reset release (high = released) | pull-down → **reset asserted** |
| 13 | 33 | — | HWB assert (high = HWB pulled low → DFU on next reset) | pull-down → released |
| 14 / 15 | 8 / 10 | UART0 TXD / RXD | DUT UART through the level translator | — |
| 16 | 36 | — | ISP translator enable | pull-down → Hi-Z |
| 17 | 11 | — | UART translator enable | pull-down → Hi-Z |
| 18 | 12 | — | Clock override enable (drive XTAL1) | pull-down → off |
| 19 | 35 | — | Power meter ALERT (input, open-drain from the meter) | pull-up |
| 20 / 21 | 38 / 40 | — | USB switch select S0 / S1 | pull-downs → USB-C (rpiboot) on the carrier |
| 22 | 15 | — | DUT VCC enable | pull-down → off |
| 23 | 16 | — | DUT USB VBUS enable (virtual plug) | pull-down → off |
| 24 | 18 | — | Status LED | — |
| 25, 26, 27 | 22, 37, 13 | — | Spare | — |

That leaves 7 spare GPIOs (5, 6, 7, 8, 25, 26, 27), plus I2C for anything slow.

### Notes

- **USB switch select:** carrier: 00 = USB-C (rpiboot), 01 = MCU hardware USB, 10 = software-USB pins.
  On the HAT, S0 alone picks between hardware and software USB on the loopback cable, and S1 is unused.
  The carrier default has to be USB-C, because rpiboot happens before Linux can drive any pin.
- **Reset:** open-drain to the DUT. The Pi only lets it go. The pull-up is to the switched DUT rail, so a DUT that's
  powered off isn't back-fed (an AVR's RESET has no clamp anyway).
- **Clock:** if the programmable clock generator goes in (Si5351-class on I2C), it feeds the same buffer as
  GPCLK0 does. GPIO 18 still gates it.
- **To check during part selection:** GPCLK0 on GPIO4 under RP1 (Pi 5/CM5). I expect it's there, as on BCM2711.

## Spare pins and future programming interfaces

- **UPDI / TPI / PDI / debugWIRE** run over one or two wires. They can reuse UART0 (UPDI, debugWIRE as
  half-duplex UART) or spare GPIOs (PDI clock and data, TPI), each through a level translator.
- **Multi-MCU boards:** each extra DUT needs its own reset, VCC enable, VBUS enable, HWB and translator
  enables (about 6 slow signals). Put them on an I2C GPIO expander (TCA9535-class) and keep the fast or
  shared lines (SPI, UART, clock) on Pi GPIO, muxed by the translator enables.
