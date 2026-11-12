# v2 part selection (first pass)

The stock numbers are JLCPCB assembly stock, checked **2026-11-11 8:50 PM PST (04:50Z on 11-12)** with
[`tools/jlc_search.py`](../tools/jlc_search.py). That tool uses the same search as jlcpcb.com/parts. Re-run it
before ordering, because stock moves.

**Lib** is JLC's library type. **Basic** parts are always loaded on the machines. **Ext** (extended) parts
each add a one-time loading fee per order (about $3 per unique part). Prices are per unit at qty 1, in USD.

Covers the 16U2 board, both variants (CM carrier and HAT). **The DUT runs at 3.3 V** (user, 2026-11-12),
and switches to 5 V only for HVPP. Schematic work may still change values;
the passives listed are the common Basic ones.

## Target and its support

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DUT | ATmega16U2-AU (TQFP-32) | C59019 | Ext | **84** | 5.50 | **Thin stock**, see risks. QFN: C507117 (84), C17317 (20). TQFP is easier to probe and rework. |
| DUT crystal | **8 MHz** 3225, CL 12 pF (1C208000BC0R) | C57131 | Ext | 20.9k | 0.42 | 3.3 V operation caps the 16U2 at about 10.7 MHz. Load caps 18 pF C1549 (Basic). No Basic 8 MHz 3225 exists. (16 MHz Basic C13738 if a board runs at 5 V.) |
| USB series R | 22 Ω 0402 | C25092 | Basic | 5.0M | — | 16U2 D+/D- |

## Pi ↔ DUT signals and clock

**No level translators in this version** (user, 2026-11-12). ISP (SCK, MOSI, MISO) and UART (TX, RX) run
straight from the Pi to the DUT through **4.7 kΩ series resistors** (C25900, Basic). Both sides are 3.3 V.
The resistors limit current when one side is unpowered or at 5 V (HVPP), see risk 6.

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| ISP and UART series R | 4.7 kΩ 0402 ×5 | C25900 | Basic | — | — | The value can change per line at schematic time (1k–4.7k). 4.7k with ~15 pF is ~70 ns, fine for ISP SCK up to 1–2 MHz (8 MHz DUT clock / 4 = 2 MHz max). |
| Clock buffer → XTAL1 | SN74LV1T126DBVR (SOT-23-5) | C2440228 | Ext | 8747 | 0.33 | Kept: drives XTAL1 hard enough to override the crystal, and GPIO 18 gates it. Runs on the DUT rail with TTL-level inputs, so 3.3 V drives it at 5 V. OE, Ioff. Replaces v1's 74AHCT (5 V only). |
| Clock generator (optional) | Si5351A-B-GTR (MSOP-10) | C504891 | Ext | 12.4k | 1.18 | 3 outputs on I2C. Can be left unfitted; GPCLK0 is still there. |
| Si5351 crystal | 25 MHz 3225, CL 10 pF (NX3225SA) | C448646 | Ext | 6271 | 0.46 | The Si5351 wants an 8/10 pF crystal. The Basic 25 MHz (C9006) is 12 pF. |

If translators come back in a later version (5 V DUTs, real Hi-Z), the pick was **TXU0304PWR** C4364118 (ISP, 3 out
and 1 in) and **TXU0202DCUR** C5186957 (UART): fixed direction, OE, Ioff, 1.08–5.5 V. Rejected then:
**SN74AXC4T774** is 3.6 V max. **SN74LVC2T45/LXC2T45** have no OE. **SN74LVC8T245** has one DIR for all 8 bits.

## Power, switching and measurement

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DUT VCC switch | TPS22918DBVR (SOT-23-6) | C131941 | Ext | 68k | 0.34 | Load switch with set slew and **quick output discharge**, so power cycles are clean. Off by default. The 16U2's HVPP has no tight timing, so the switch doesn't need to be fast. |
| DUT rail select 3.3 / 5 V (HV option) | TPS2116DRLR (SOT-583) | C3235557 | Ext | 65.1k | 0.38 | Power mux, Pi-selected, 3.3 V by default. Feeds the TPS22918. The "no HV" variant replaces it with a 0 Ω link to 3.3 V. |
| DUT USB VBUS switch | SY6280AAC (SOT-23-5) | C55136 | Ext | 97.9k | 0.09 | Current limit set by resistor, active-high enable |
| Power meter | INA228AIDGSR (VSSOP-10) | C2887910 | Ext | **316** | 6.78 | 20-bit. 0.5 Ω shunt: ±163.84 mV range → 200 mA full scale with ~0.6 µA steps, ±40.96 mV range → ~80 mA with ~0.16 µA steps. |
| (alt) power meter | INA226AIDGSR | C49851 | Ext | 53k | 0.66 | 16-bit, ~6 µA steps with the same shunt. Fallback if the INA228 runs out. |
| Shunt | 0.5 Ω 0603 1% 100 ppm | C414986 | Ext | 10.9k | 0.04 | |
| 3.3 V rail (DUT + board logic) | ME6211C33M5G-N (SOT-23-5) | C82942 | Ext | 315k | 0.06 | 500 mA LDO from 5 V |

## High-voltage programming (optional block, "no HV" variant leaves these unfitted)

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 12 V boost | MT3608 (SOT-23-6) | C84817 | Ext | 26.1k | 0.10 | Pi-enabled, off by default |
| Boost inductor | 10 µH 4×4 mm (SWPA4030S100MT) | C38117 | Ext | 44.3k | 0.06 | |
| Boost diode | B5819W (SOD-123) | C8598 | Basic | 377k | 0.03 | |
| 12 V → RESET switch | AO3401A + 2N7002 | C15127 + C8545 | Basic | 1.6M / 6.1M | 0.08 | Pi-driven (GPIO 25). An RC-timed entry is only needed on future ATtiny (HVSP) boards. |
| Pull-up isolation | 1N4148W | C81598 | Basic | 3.4M | 0.01 | Stops 12 V on RESET from back-feeding the DUT rail |
| HVPP I/O (16 lines) | TCA6416ARTWR (WQFN-24) | C182336 | Ext | 33k | 0.82 | Separate supplies for the I2C side and the port side, so it level-shifts by itself. Ports run from the DUT rail. TSSOP: C130203 (2152). |

## USB

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| USB path switch | TS3USB221ARSER (UQFN-10) | C128396 | Ext | 101k | 0.24 | HS-rated 2:1. Two in cascade on the carrier (USB-C / MCU HW / software USB), one on the HAT. |
| USB-C receptacle | HRO TYPE-C-31-M-12 (16-pin, USB 2.0) | C165948 | Ext | 282k | 0.19 | Carrier: power and rpiboot. HAT: data loopback. 5.1 kΩ Rd C25905 (Basic) ×2 on each. |
| ESD | USBLC6-2SC6 (ST) | C7519 | Ext | 21.9k | 0.16 | One per external USB connector |

## CM carrier only

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| CM connectors | Hirose DF40C-100DS-0.4V(51) | C597931 | Ext | 1193 | 0.97 | ×2. 1.5 mm stack height. The 3 mm version DF40HC(3.0) has only 4 in stock. |
| Ethernet | HanRun HR911130C (gigabit magjack, LEDs) | C50933 | Ext | 7694 | 2.86 | 10/100 alternative: HR911105A C12074 (50.6k) |
| microSD | Hirose DM3AT-SF-PEJM5 | C114218 | Ext | 14.8k | 1.39 | Same family the Pi uses |
| rpiboot button | TS-1187A-B-A-B | C318884 | Basic | 829k | 0.02 | nRPIBOOT |

## HAT only

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 40-pin header | 2×20 female 2.54 mm, 8.5 mm | C5124634 | Ext | 7422 | 0.33 | |
| ID EEPROM | ST M24C32-RMN6TP (SOIC-8) | C79920 | Ext | 7148 | 0.39 | HAT spec's 24C32-class part, write-protect jumper |

## Common small parts (Basic unless noted)

- 10 kΩ C25744, 5.1 kΩ C25905, 4.7 kΩ C25900, 1 kΩ C11702, 120 Ω C25079, 100 Ω C25076, 22 Ω C25092 (all 0402).
- 100 nF C1525, 1 µF C52923 (0402); 10 µF C19702, 1 µF 50 V C15849 (0603); 12 pF C1547, 22 pF C1555, 100 pF C1546.
- 2N7002 C8545, AO3401A C15127, 1N4148W C81598, B5819W C8598.
- LEDs 0603: red KT-0603R C2286 (Basic). Green KT-0603G C12624 (Ext, 296k). Blue KT-0603B C2288 (Ext).

## Risks and notes

1. **ATmega16U2 stock is thin:** 84 TQFP at JLC (plus 84 + 20 QFN), and the whole xU2 family is similar
   (32U2: 55, 8U2: 16). That's enough for a few boards, but it can run out. Options if it does: JLC's
   global-sourcing pre-order (it showed 81 more pre-orderable), or consigned parts.
2. **Extended parts:** about 23 unique extended parts, so roughly $75 of loading fees per order. Fine for
   prototypes. Later, swap to Basic parts where one fits.
3. **Fit (CM carrier):** with a 1.5 mm stack, the module covers the whole top side, so nearly all parts go on
   the bottom. Through-hole pins (RJ45, USB-C shell) poke into the CM side and have to land where the module's
   underside is clear. The layout fit check needs the CM4/CM5 keep-out drawings. If it doesn't fit, the fallback
   is the 3 mm connector, which has no stock now.
4. **INA228 stock** (316) is fine for prototypes. The fallback is the INA226 (lower resolution). Check its pinout before relying on that.
5. **To verify in datasheets during schematic work:** SN74LV1T126 V_IH at 5 V
   (should be TTL-level); TCA6416A port behaviour when VCCP is off; the 16U2's HVPP pin mapping
   (Table 25-11); GPCLK0 on GPIO4 under RP1; TPS2116 switchover behaviour (no back-feed from 5 V into 3.3 V).
   Already checked in the 16U2 datasheet: the speed grade at 3.3 V, 3.3 V USB wiring (fig. 20-6), and HVPP entry (§25.7.1).
6. **Series resistors instead of translators.** What the software has to do instead:
   - **DUT off:** keep the Pi's ISP and UART pins as inputs. A Pi pin driven high into an unpowered DUT feeds it
     through its clamp diode: about 0.6 mA per pin at 4.7k, enough to half-power it and to skew the power meter.
     SPI0 and UART0 drive their pins whenever they're in their alt function, so switch the pins back to inputs
     (pinctrl) when not in use.
   - **HVPP at 5 V:** the DUT's PB1–PB3 (ISP pins) are HVPP data lines, and the DUT drives them at 5 V on reads.
     PD2/PD3 (UART pins) are HVPP OE/WR, driven at 5 V by the expander. Each one pushes about 0.3 mA through
     4.7k into the Pi's clamp diode. That's small, but the Pi doesn't specify an injection limit, so keep these at
     4.7k, not 1k.
