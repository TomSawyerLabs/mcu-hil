# v2 part selection (first pass)

The stock numbers are JLCPCB assembly stock, checked **2026-11-11 8:50 PM PST (04:50Z on 11-12)** with
[`tools/jlc_search.py`](../tools/jlc_search.py). That tool uses the same search as jlcpcb.com/parts. Re-run it
before ordering, because stock moves.

**Lib** is JLC's library type. **Basic** parts are always loaded on the machines. **Ext** (extended) parts
each add a one-time loading fee per order (about $3 per unique part). Prices are per unit at qty 1, in USD.

Covers the 16U2 board, both variants (CM carrier and HAT). **The DUT runs at 5 V** (user, 2026-11-12, after a
detour through 3.3 V). Schematic work may still change values;
the passives listed are the common Basic ones.

## Target and its support

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DUT | ATmega16U2-AU (TQFP-32) | C59019 | Ext | **84** | 5.50 | **Thin stock**, see risks. QFN: C507117 (84), C17317 (20). TQFP is easier to probe and rework. |
| DUT crystal | 16 MHz 3225, CL 9 pF (X322516MLB4SI) | C13738 | Basic | 283k | 0.09 | 16 MHz is the 16U2's top speed at 4.5–5.5 V. Load caps 12 pF C1547 (Basic): 2 × (9 pF − ~3 pF stray). |
| USB series R | 22 Ω 0402 | C25092 | Basic | 5.0M | — | 16U2 D+/D- |

## Level translation and clock (Pi 3.3 V ↔ DUT 5 V)

Both translators run their B side from the **switched** DUT rail, so they go Hi-Z with the DUT off (Ioff and
supply isolation), and the Pi never feeds an unpowered DUT.

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| ISP translator | TXU0304PWR (TSSOP-14) | C4364118 | Ext | 4667 | 0.64 | 3 lines Pi→DUT (MOSI, SCK, +1 spare) and 1 line DUT→Pi (MISO). Fixed direction, OE (Hi-Z), Ioff, 1.08–5.5 V each side. UQFN version: C2959768. |
| UART translator | TXU0202DCUR (VSSOP-8) | C5186957 | Ext | 8370 | 0.90 | TX out, RX in, OE, Ioff |
| Clock buffer → XTAL1 (**clock override option**) | SN74LV1T126DBVR (SOT-23-5) | C2440228 | Ext | 8747 | 0.33 | Runs on the DUT rail with TTL-level inputs, so 3.3 V drives it at 5 V. OE (GPIO 18), Ioff. Replaces v1's 74AHCT. Left off in the "no clock override" variant; XTAL1 then sees only the crystal. |
| Clock generator (optional, within the clock option) | Si5351A-B-GTR (MSOP-10) | C504891 | Ext | 12.4k | 1.18 | 3 outputs on I2C. Can be left unfitted; GPCLK0 is still there. |
| Si5351 crystal | 25 MHz 3225, CL 10 pF (NX3225SA) | C448646 | Ext | 6271 | 0.46 | The Si5351 wants an 8/10 pF crystal. The Basic 25 MHz (C9006) is 12 pF. |

Rejected: **SN74AXC4T774** is 3.6 V max, so it can't drive a 5 V AVR. **SN74LVC2T45/LXC2T45** have no OE, so they
can't go Hi-Z. **SN74LVC8T245** has one DIR for all 8 bits, but ISP needs both directions. Plain series resistors
(tried briefly on 2026-11-12) back-feed an unpowered DUT and push 5 V into the Pi's pins.

## Power, switching and measurement

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DUT VCC switch | TPS22918DBVR (SOT-23-6) | C131941 | Ext | 68k | 0.34 | Load switch from 5 V, with set slew and **quick output discharge**, so power cycles are clean. Off by default (GPIO 22). |
| Power meter | INA226AIDGSR (VSSOP-10) | C49851 | Ext | 64.6k | 0.66 | 16-bit. With the 1 Ω shunt: 81.9 mA full scale, 2.5 µA steps. **INA228 went to 0 stock on 2026-11-13** (was 316); it is pin- and footprint-compatible (20-bit, 164 mA / 0.3 µA with this shunt), so it can go back in later. |
| Shunt | 1 Ω 0603 1% | C22936 | Basic | 472k | 0.003 | |
| SD card power (carrier) | TPS22918DBVR (second one) | C131941 | Ext | — | — | Same part as the DUT switch, so no extra loading fee. Switched by the CM's SD_PWR_ON. |

Dropped during schematic work (2026-11-13): the **SY6280 VBUS switch** (the 16U2 has no VBUS pin; virtual unplug is
the USB switch) and the **ME6211 LDO** (3.3 V comes from the Pi or the CM, which also sets the GPIO level).

## High-voltage programming (optional block, "no HV" variant leaves these unfitted)

The HV option also needs the clock-override buffer (SN74LV1T126) fitted, because HVPP pulses XTAL1 through it.

| Function | Part | LCSC | Lib | Stock | $ | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 12 V boost | MT3608 (SOT-23-6) | C84817 | Ext | 26.1k | 0.10 | Pi-enabled, off by default |
| Boost inductor | 10 µH 4×4 mm (SWPA4030S100MT) | C38117 | Ext | 44.3k | 0.06 | |
| Boost diode | B5819W (SOD-123) | C8598 | Basic | 377k | 0.03 | |
| 12 V → RESET switch | AO3401A + 2N7002 | C15127 + C8545 | Basic | 1.6M / 6.1M | 0.08 | Pi-driven (GPIO 25). An RC-timed entry is only needed on future ATtiny (HVSP) boards. |
| Pull-up isolation | 1N4148W | C81598 | Basic | 3.4M | 0.01 | Stops 12 V on RESET from back-feeding the DUT rail. Fitted on every board (part of the reset pull-up path). |
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
| CM connectors | Hirose DF40C-100DS-0.4V(51) | C597931 | Ext | 174 (2026-11-13) | 0.97 | ×2. 1.5 mm stack height. The 3 mm version DF40HC(3.0) has only 4 in stock. |
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
- 75 Ω C25133, 3.9 kΩ C51721 (JLC "Preferred": no loading fee), 470 Ω C25117, 1.5 kΩ C25867, 1 Ω 0603 C22936.
- 1 nF C1523, 10 µF 25 V 0805 C15850, 22 µF 25 V 0805 C45783.
- 2N7002 C8545, AO3401A C15127, 1N4148W C81598, B5819W C8598. Zener BZT52C3V6 C173412 (Ext, software USB).
- LEDs 0603: all red KT-0603R C2286 (Basic), to avoid two loading fees. Green C12624 and blue C2288 are Ext.
- Second SN74LV1T126 for the Si5351 path (same part, no extra fee).

## Risks and notes

1. **ATmega16U2 stock is thin:** 84 TQFP at JLC (plus 84 + 20 QFN), and the whole xU2 family is similar
   (32U2: 55, 8U2: 16). That's enough for a few boards, but it can run out. Options if it does: JLC's
   global-sourcing pre-order (it showed 81 more pre-orderable), or consigned parts.
2. **Extended parts:** about 24 unique extended parts, so roughly $75 of loading fees per order. Fine for
   prototypes. Later, swap to Basic parts where one fits.
3. **Fit (CM carrier):** with a 1.5 mm stack, the module covers the whole top side, so nearly all parts go on
   the bottom. Through-hole pins (RJ45, USB-C shell) poke into the CM side and have to land where the module's
   underside is clear. The layout fit check needs the CM4/CM5 keep-out drawings. If it doesn't fit, the fallback
   is the 3 mm connector, which has no stock now.
4. **INA228 is out of stock** (2026-11-13), so the INA226 is fitted. Pinouts match (checked: KiCad symbols and TI tables).
5. **To verify in datasheets during schematic work:** the TXU0304 direction pin-out; SN74LV1T126 V_IH at 5 V
   (should be TTL-level); TCA6416A port behaviour when VCCP is off; GPCLK0 on GPIO4 under RP1.
   Already checked in the 16U2 datasheet: HVPP entry (§25.7.1, VCC 4.5–5.5 V) and the HVPP pin mapping
   (Table 25-9: PB0–7 data, PD1 RDY/BSY, PD2 OE, PD3 WR, PD4 BS1, PD5 XA0, PD6 XA1, PD7 PAGEL, PC6 BS2).
