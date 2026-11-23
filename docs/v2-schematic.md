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

## Population options

Optional blocks are independent on/off options, chosen per build (defined with their rules in
[`hw/options.toml`](../hw/options.toml)): `XTAL` (16 MHz crystal and load caps), `XSW` (Pi-controlled crystal
switch), `CLK` (clock override buffer), `SI` (Si5351 and its buffer), `HV`, and on the carrier `SD` (microSD slot,
its power switch and pull-up; network boot needs no card). There are no KiCad design variants.

Each optional part's `Option` field is a condition: space-separated terms that must all hold. `X` means option X is
on, `!X` means it is off. Examples: the crystal switch is `XSW`, its 0R bypass is `!XSW`, and the XTAL1-side load
cap is `XTAL !XSW`. The schematic's own DNP flags show the build with every option on. For any other mix,
`cd tools && python -m bom carrier --without SD,HV` writes that build's JLC BOM (`--only` picks options the other
way round, `--list` lists them). Rules it enforces: HV needs CLK, XSW needs XTAL.

Each part's `LCSC` field is its preferred JLC part and its `Spec` field says what may replace it when stock runs
short (no Spec: that exact part only). The chosen parts live in `hw/<board>/bom.lock.json`; see the README.

With both clock buffers off (the default) the DUT runs from its crystal; to run from a driven clock, set its fuses
to external clock (and open the crystal switch, if fitted).

HV needs CLK, because HVPP clocks XTAL1 through the GPCLK0 buffer (user OK'd, 2026-11-12).

## Design notes

- **Reset.** A 2N7002 holds RESET low whenever DUT_5V is up, unless the Pi sets GPIO12 high (a second 2N7002 then
  pulls the first one's gate low). The pull-up path is DUT_5V → 1N4148W → 10k → RESET, so 12 V on RESET can't reach DUT_5V. The reset
  LED sits in a parallel branch (LED + 1k) and lights only while RESET is pulled low.
- **12 V.** MT3608 with a 100k/5.1k divider (12.36 V nominal). The AO3401A switch has a 10k/10k gate divider
  (VGS −6 V; its limit is ±12 V). A 1k series resistor into RESET limits fault current; at the 250 µA HVPP
  current it drops 0.25 V, so RESET sees about 11.9–12.4 V (spec 11.5–12.5 V).
- **Crystal and its switch.** The 16 MHz crystal and load caps are option `XTAL`. Its XTAL1 side joins the MCU through
  an SN74LVC1G66 analog switch (option `XSW`, C133643): GPIO23 high opens it, so a driven clock (GPCLK0, Si5351, or the
  HVPP strobe) sees a bare XTAL1. The switch's control is pulled up to DUT_5V (crystal connected by default) and the
  Pi pulls it low through a 2N7002, because the switch's 5 V input-high threshold (3.5 V) is above 3.3 V. The
  switch adds about 5.5 Ω in series with the crystal (ESR is tens of ohms) and about 13 pF on-capacitance. That
  capacitance stands in for the XTAL1-side load cap, so the 12 pF cap there (on the crystal side, option
  `XTAL !XSW`) is fitted only without the switch: CL = 13 × 12 / 25 + ~3 pF stray = 9.2 pF, against the crystal's
  9 pF. Its footprint stays, for tuning on real boards. Without `XSW`, a 0R bypass (option `!XSW`) wires the crystal
  straight to XTAL1 and that cap is fitted.
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

- ~~KiCad ERC~~: clean on both boards (kicad-cli 10.0.6, 2026-11-13), and KiCad's netlists match the generator's.
  View in the browser (KiCanvas, reads `master` on GitHub): [carrier](https://kicanvas.org/?github=https://github.com/TomSawyerLabs/mcu-hil/tree/master/hw/carrier), [HAT](https://kicanvas.org/?github=https://github.com/TomSawyerLabs/mcu-hil/tree/master/hw/hat).
- Tidier sheet layout (the generated placement is functional but sparse).
- HR911130C LED colours, and its footprint against HanRun's drawing.
- The DF40 footprint's pin-1 orientation against the CM4/CM5 mechanical drawings (layout step).
