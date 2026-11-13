# v2 schematic

The KiCad 10 schematics for both boards are **generated** from one circuit description:

- [`tools/schgen/design.py`](../tools/schgen/design.py): every sheet, part, value, LCSC number and net.
- `hw/carrier/` (CM4/CM5 carrier) and `hw/hat/` (Pi HAT): the generated KiCad projects. Open
  `mcu-hil-carrier.kicad_pro` or `mcu-hil-hat.kicad_pro`.
- `hw/lib/`: project symbols (`mcu-hil.kicad_sym`, also generated), footprints that KiCad's library lacks
  (`mcu-hil.pretty`, from JLC/EasyEDA), and the CM4/CM5 pin table (`cm4-cm5-pins.csv`).

Regenerate after changing the design (no KiCad needed):

```sh
cd tools
python -m schgen
```

The generator places parts on a grid and connects pins with labels, not wires: power symbols for GND/+5V/+3V3,
local labels for nets on one sheet, global labels for nets that cross sheets, and no-connect flags on unused pins.
It refuses to write a design with an unassigned pin or a net with only one connection. Once the layout starts
being edited by hand in KiCad, the generated files become the source and the generator is retired.

## Sheets

Shared by both boards:

| Sheet | Contents |
| --- | --- |
| `dut` | ATmega16U2 at 5 V and 16 MHz, crystal, decoupling, USB series resistors, software-USB network (PC7/PC4), reset pull-up and reset LED, HWB pull-up, test points on the spare pins |
| `pi_io` | TXU0304 (ISP) and TXU0202 (UART) translators, reset FETs (asserted by default), HWB FET, default pulls |
| `clock` | Two SN74LV1T126 buffers onto XTAL1 (GPCLK0 and Si5351 CLK0), Si5351A with its 25 MHz crystal |
| `dut_power` | TPS22918 DUT power switch, 1 Ω shunt, INA226 power meter |
| `hv` | MT3608 12 V boost, 12 V switch onto RESET, TCA6416A for the 16 HVPP lines |
| `usb` | TS3USB221A switch(es): carrier has two in cascade, HAT has one |

Carrier only: `cm` (the two DF40 connectors) and `carrier_io` (USB-C power and rpiboot, Ethernet MagJack,
microSD with its power switch, rpiboot button, LEDs, mounting holes). HAT only: `hat_io` (40-pin header,
ID EEPROM, USB-C loopback port, LED, mounting holes).

## Population options and variants

Optional parts carry an `Option` field: `CLK` (clock override buffer), `SI` (Si5351 and its buffer) and `HV`.
The KiCad projects define two design variants besides the default (everything fitted):

- **no HV**: HV parts DNP.
- **minimal**: HV, CLK and SI parts DNP.

HV needs CLK, because HVPP clocks XTAL1 through the GPCLK0 buffer (user OK'd, 2026-11-12).

## Design notes

- **Reset.** Q1 (2N7002) holds RESET low whenever DUT_5V is up, unless the Pi sets GPIO12 high (Q2 then pulls Q1's
  gate low). The pull-up path is DUT_5V → 1N4148W → 10k → RESET, so 12 V on RESET can't reach DUT_5V. The reset
  LED sits in a parallel branch (LED + 1k) and lights only while RESET is pulled low.
- **12 V.** MT3608 with a 100k/5.1k divider (12.36 V nominal). The AO3401A switch has a 10k/10k gate divider
  (VGS −6 V; its limit is ±12 V). A 1k series resistor into RESET limits fault current; at the 250 µA HVPP
  current it drops 0.25 V, so RESET sees about 11.9–12.4 V (spec 11.5–12.5 V).
- **TCA6416A power order.** TI recommends VCCP up before VCCI, or SDA can stick low (datasheet §10.1).
  VCCP is on +5V, which always comes up before +3V3. Its ~RESET is pulled up to DUT_5V, so the ports are held as
  inputs (Hi-Z) whenever the DUT is off and can't back-power it.
- **USB.** S0 low = USB-C (rpiboot, CM is a device). S0 high = DUT side, and a 2N7002 grounds USB_OTG_ID so the
  CM becomes the host. S1 picks hardware or software USB. The 16U2 has no VBUS pin, so there is no VBUS switch:
  "unplug" is the USB switch disconnecting D+/D-.
- **Software USB** (V-USB): D+ on PC7 (INT4), D− on PC4, neither used by HVPP. 75 Ω series, 3.6 V zeners, 1.5k
  pull-up on D− (low speed). The TS3USB221A's I/O pins tolerate 5.5 V, so the zeners are for the USB host.
- **CM5 USB-C power.** CM5 pins 94/96 (CC1/CC2) let CM5's PMIC negotiate 5 V/5 A; on CM4 they are ADC inputs with
  100 nF on the module. The carrier leaves them open and fits 5.1k Rd on the USB-C port, which works with both.
  CM5 then runs without 5 A PD.
- **Ethernet.** HR911130C 1:1 MagJack. PHY-side centre taps (P1) to GND through 100 nF; P10 (Bob Smith
  termination, internal cap) to GND. LED pins decoded from JLC's symbol: 14 = LED1 anode, 13 = LED1 cathode,
  11 = LED2 anode, 12 = LED2 cathode. LED1 shows activity (Ethernet_nLED3), LED2 shows speed (Ethernet_nLED2).
  Colours are not confirmed (HanRun's datasheet could not be downloaded).
- **HAT+ rules** (HAT+ specification): only the ID EEPROM and 3.9k pull-ups on ID_SD/ID_SC; EEPROM WP pulled up
  with 1k, with a solder jumper and a test point to write it; the HAT never powers the Pi; the board must be
  safe in STANDBY (5 V up, 3.3 V down), which it is because every enable defaults off.

## Sources

- ATmega16U2: Microchip doc7799 (pin table, §25 HVPP, table 25-9).
- TXU0304, TXU0202, SN74LV1T126, TPS22918, TCA6416A, TS3USB221A, INA226/INA228: TI datasheets.
- CM4 and CM5 datasheets (pinout tables), CM4 IO board datasheet (schematics), HAT+ specification.
- JLC/EasyEDA footprints via `easyeda2kicad` 1.0.1 for TS3USB221A (RSE), HR911130C and the SWPA4030 inductor.

## Still to check

- KiCad ERC, and a visual review of the generated sheets (needs `kicad-cli`; asked before running).
- HR911130C LED colours, and its footprint against HanRun's drawing.
- The DF40 footprint's pin-1 orientation against the CM4/CM5 mechanical drawings (layout step).
