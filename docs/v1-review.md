# v1 AVR Test HAT: design review

Source: `C:\Users\camer\git\Personal Projects\avr-test-hat` (Altium; `HAT/AVR-Tester.PrjPcb`),
read from a scratch copy, so the v1 repo was not modified. Reviewed 2026-11-11.

Recovered data lives in [`reference/v1-import/`](../reference/v1-import/):

- `v1.kicad_pcb`: the v1 board imported into KiCad 10.0.6 (`kicad-cli pcb import --format altium`).
  It's reference only, not the v2 design.
- `pcb-netlist.txt`: every footprint, its pad-to-net map, and the full netlist from that board.
- `sch-records.txt`: components, values, ports, net labels and notes parsed from the `.SchDoc` sheets.
- `tools/`: the plain-Python parsers that produced these. They need no KiCad runtime
  (`sexpr.py` + `kpads.py` read `.kicad_pcb` text; `schdoc.py` and `altium_pads.py` read Altium files with `olefile`).

KiCad 10's CLI cannot import Altium *schematics* (only the GUI can), so schematic intent
comes from parsing the `.SchDoc` records directly. Connectivity comes from the board netlist.

## What v1 is

A 65 × 56 mm, 2-layer Raspberry Pi HAT. Its target is an **ATmega16U2 (U1) soldered on the board**,
whose SPI, reset and power rails are also brought out to two 6-pin AVR ISP headers.
The Pi can do all of these to the AVR:

- switch its power: VCC and UVCC separately
- hold it in reset or release it
- set HWB, the DFU bootloader entry pin
- program it over SPI (ISP)
- talk to it over UART
- override its clock with a Pi-generated clock
- see its activity on an LED
- talk to its USB port, but only through an external USB cable from the HAT's USB-C or micro-USB back into a Pi USB port

Nothing on v1 carries an LCSC part number, and the Altium design holds no supplier parameters at all.

## Blocks

| Sheet | Parts | What it does |
| --- | --- | --- |
| `AVR` | U1 ATmega16U2-AU (TQFP-32), X1 16 MHz crystal (ABM3B), C5/C6 12 pF, R3 1k in series with XTAL2, C2/C3 100 nF, C4 1 µF UCAP, R1/R2 22 Ω USB series, C1 10 µF on 5V, J3 (TE 2-1761605-1) and J4 (3M 30306-6002HB) 2×3 ISP headers | The on-board DUT and the ISP headers. J3/J4 share `Device_MISO/MOSI/SCLK`, `Reset` and `VCC` with U1. |
| `Power Switch` (×2: `Power`, `USB`) | Q3 CJ2305 P-FET, Q4 2N7002 driver, R25 gate pull-up, R26 1k load/bleed, R27 gate pull-down | Pi-controlled high-side switches from the Pi 5V: one feeds `VCC` (VCC/AVCC), the other `UVCC` (the USB regulator input). Both are off by default. |
| `Reset` | Q1, Q2 2N7002, R15/R16 1k to 5V, D1 "Not Reset" LED, D2 "Reset active" LED | Non-inverting, open-drain reset control: GPIO13 high → Q2 on → Q1 off → `Reset` pulled to 5V. |
| `Logic Buffer` | U3 74LVC244APW on 3V3, C8, R6–R9 pull-ups, R10–R14 series resistors | Two gated, one-directional buffers between the Pi and the DUT. Bank 1 is UART, enabled by GPIO8. Bank 2 is SPI, enabled by GPIO5. Both are pulled up, so disabled by default. MISO and AVR TX come back through the 5V-tolerant inputs. |
| `Clock Buffer` | U4 74AHCT1G126 on 5V, C9, R28 OE pull-down | Drives the Pi's GPCLK0 (GPIO4) onto XTAL1 at 5V levels when GPIO17 is high. Handy for recovering chips fused to an external clock, or for slow or odd clocks. |
| `EEPROM` + `I2C-PullUps` | U2 CAT24C32 (0x50), J5 WP jumper, R4/R5 pull-ups, C7 | Standard HAT ID EEPROM on ID_SD/ID_SC. Fit J5 to write-protect it. |
| `USB`, `USB-C` (×2), `microUSB` | J6A USB4105 (power in), J6B USB4105 (data), J7 Amphenol 10118193 micro-B, R29/R30 CC resistors | J6A is a **power input**: VBUS goes to the HAT/Pi 5V, and CC1/CC2 have Rd to GND. Its D+/D- are unconnected. J6B and J7 sit **in parallel** on the AVR's USB D+/D-. Neither has VBUS or CC connected. |
| `Main` | D3 Pi activity LED (GPIO26), D4 AVR activity LED (PC7), R19–R22 | The glue: HWB and reset default/control resistor networks. |
| `RPi-HAT_Conn-EE` | J1 Harwin M20-7832046 (2×20 female), J2 Sullins PPPC022LFBN-RC (2×2 female) | Pi header. J2 has **no electrical connections**. It sits where the Pi 3B+/4 PoE header is, so it probably just gives the PoE pins somewhere to go. |

## v1 Pi GPIO map

| BCM GPIO | Header pin | Pi alt function | v1 use |
| --- | --- | --- | --- |
| 0 / 1 | 27 / 28 | ID_SD / ID_SC | HAT ID EEPROM U2 |
| 2 | 3 | SDA1 | HWB control (4.7k into HWB / PD7) |
| 3 | 5 | SCL1 | HWB default (4.7k to GPIO2) |
| 4 | 7 | GPCLK0 | Clock override signal → U4 → XTAL1 |
| 5 | 29 | — | SPI buffer disable (U3 2OE, pulled up) |
| 8 | 24 | SPI0_CE0 | UART buffer disable (U3 1OE, pulled up) |
| 9 / 10 / 11 | 21 / 19 / 23 | SPI0 MISO / MOSI / SCLK | ISP to DUT via U3 (PB3 / PB2 / PB1) |
| 13 | 33 | PWM1 | Reset control (high = released) |
| 14 / 15 | 8 / 10 | UART0 TXD / RXD | DUT RXD1 / TXD1 (PD2 / PD3) via U3 |
| 17 | 11 | — | Clock override enable (U4 OE, pulled down) |
| 18 | 12 | PCM_CLK / PWM0 | AVR UVCC enable (pulled down) |
| 19 | 35 | — | Reset default (4.7k to GND, 4.7k to GPIO13) |
| 26 | 37 | — | Pi activity LED D3 (active high) |
| 27 | 13 | — | AVR VCC enable (pulled down) |
| 6, 7, 12, 16, 20–25 | | | Unused |

DUT pins reachable from the Pi: RESET, XTAL1, PD2/RXD1, PD3/TXD1, PD7/HWB, PB1–PB3 (ISP), PC7 (LED only)
and USB D+/D- (via a cable). The other 16U2 I/O (PB0, PB4–PB7, PC2, PC4–PC6, PD0, PD1, PD4–PD6) aren't connected.

## Problems found in v1

These shape the v2 requirements.

1. **Resistor BOM disagrees with the schematic.** Each resistor's `Value` parameter
   (the designer's intent) differs from its `Comment`/library part (what the BOM and PCB carry):
   - R29/R30 USB-C CC pull-downs: Value 5.1k, part **1k**. With 1k Rd, a USB-C source sees Ra (an accessory), not a sink, so C-to-C power input would never turn on.
   - R4/R5 ID EEPROM pull-ups: Value 3.9k, part 1k.
   - R6–R9, R19–R22, R27, R28: Value 4.7k, part 1k.
   - R10–R14: Value 220 Ω, parts 1k (R10, R12) and 120 Ω (R11, R13, R14).
2. **5 V levels into the AVR come from a 3.3 V buffer.** U3 (LVC244 on 3V3) drives MOSI, SCLK and RXD into a 5V AVR
   whose V_IH is 0.6·VCC = 3.0 V. That's marginal, and worse through the 220 Ω series resistors. The clock path does this right (AHCT at 5V).
3. **Back-powering.** J6A feeds VBUS straight onto the Pi's 5V header pins with no ideal diode or
   protection, which the HAT spec requires when a HAT supplies power. The reset pull-up R16 and the Q1 gate pull-up R15
   go to the always-on 5V, not to the switched AVR VCC, so a powered-off DUT gets fed through its RESET pin.
4. **USB to the DUT.** J6B (USB-C) has no CC Rd, so C-to-C cables won't attach; only A-to-C cables work.
   J6B and J7 hang in parallel on the same D+/D-, which leaves a stub. VBUS from the host isn't used at all.
5. **I2C1 is lost.** GPIO2/3 drive HWB. The Pi's 1.8k on-board pull-ups on those pins set the HWB default.
6. **SPI0_CE0 (GPIO8) is used as a plain GPIO** (UART buffer enable), so the kernel spidev chip select has to be disabled or moved.
7. **Footprints.** The J6A/J6B USB4105 shell tabs are SMD oval pads with unplated 0.61 mm holes, not the
   plated slots in GCT's recommended footprint, so they're mechanically weak. All parts are on the bottom
   layer apart from J4.
8. **DRC was not clean.** The PcbDoc stores unresolved violations: 6 short-circuit, 7 hole-to-hole
   ("Pad/Via Touching Holes"), 13 clearance and 2 net-antennae. I don't know whether v1 was ever fabricated.

## Import fidelity: holes and pads

Holes and drills were compared one-to-one between the Altium `Pads6`/`Vias6` streams
(parsed with olefile; Altium's unit is 1e-4 mil = 2.54e-6 mm) and the imported `v1.kicad_pcb` (parsed as text):

| Item | Altium | KiCad import | Result |
| --- | --- | --- | --- |
| Drilled pads | 82 | 82 | All match |
| J1 40-pin, J4 ISP | 1.02 mm PTH | 1.02 mm PTH | Match |
| J2 PoE header | 1.07 mm PTH | 1.07 mm PTH | Match |
| J3 ISP | 0.89 mm PTH | 0.89 mm PTH | Match |
| J7 micro-USB shell (S5, S6) | plated slot 0.5 × 1.2 mm | oval drill 1.2 × 0.5 mm, plated | Match |
| J6A/J6B USB-C pegs | 2 × 0.66 mm NPTH each | same | Match |
| J6A/J6B USB-C shell holes | 8 × 0.61 mm NPTH each (2 per shell pad) | same, as unnamed NPTH pads | Match. The footprint itself is the problem (see #7). |
| Mounting holes | 4 × 2.75 mm NPTH, **pad size 0 × 0**, mask margin 3.1 mm, at (3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5) | 4 footprints with no reference, each one zero-size NPTH pad | Drill and position match the HAT spec. KiCad pins the zero-size pads to 1 µm, which caused the "Invalid zero-sized pad" warnings. |
| Vias | 155: 113 × 0.5/0.25, 24 × 0.504/0.25, 18 × 0.7/0.3 mm | identical | Match |

So **no hole was dropped or resized.** The "Invalid zero-sized pad pinned to 1µm" warnings come from the
4 mounting-hole NPTH pads, which the importer writes as `(size 0 0)`. KiCad warns about them every time the
board loads. (kicad-cli prints these warnings to the console. KiCad's Python `pcbnew.LoadBoard()` shows them
as modal dialogs unless `wx.Log.SetActiveTarget(wx.LogStderr())` is set first.)
Other import losses, none of which are holes:

- D1–D4 footprints contain an Altium polygon "kind 4" that KiCad doesn't support, so some silkscreen/fab graphics were dropped.
- Altium's unused internal-plane layers weren't mapped. The board is 2-layer, so no copper was lost.
- The Altium `Value`/`Comment` mismatch (#1) carries into KiCad: footprint values are the `Comment` strings.
