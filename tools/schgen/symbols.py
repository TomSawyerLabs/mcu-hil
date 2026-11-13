"""Project symbols for parts that KiCad's standard libraries lack.

Pin tables come from the manufacturers' datasheets (checked 2026-11-13):
- TXU0304 (TI SCES919, table 6-1, PW package) and TXU0202 (TI, table 6-1, DCU package).
- TCA6416A (TI SCPS194F, figure 5-2, RTW package).
- TS3USB221A (TI, table 4-1, RSE package).
- HR911130C (HanRun): pin functions decoded from JLC/EasyEDA's symbol for C50933, see docs/v2-schematic.md.
- Raspberry Pi CM4/CM5 connectors: hw/lib/cm4-cm5-pins.csv, from the CM4 and CM5 datasheets' pinout tables.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .symbuilder import make_symbol, write_library

LIB = "mcu-hil"
P, I, O, B, PW, PO, NCT = "passive", "input", "output", "bidirectional", "power_in", "power_out", "no_connect"


def txu0304():
    return make_symbol(
        "TXU0304", "U",
        left=[("1", "VCCA", PW), ("8", "OE", I), None, ("2", "A1", I), ("3", "A2", I), ("4", "A3", I),
              ("5", "A4", O), None, ("6", "NC", NCT), ("9", "NC", NCT)],
        right=[("14", "VCCB", PW), None, None, ("13", "B1", O), ("12", "B2", O), ("11", "B3", O),
               ("10", "B4", I), None, None, ("7", "GND", PW)],
        footprint="Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        datasheet="https://www.ti.com/lit/ds/symlink/txu0304.pdf",
        description="4-bit fixed-direction level translator, 3 A->B and 1 B->A, OE active high, Ioff",
        keywords="level translator")


def txu0202():
    return make_symbol(
        "TXU0202", "U",
        left=[("3", "VCCA", PW), ("6", "OE", I), None, ("5", "A1", I), ("4", "A2", O)],
        right=[("7", "VCCB", PW), None, None, ("8", "B1", O), ("1", "B2", I), None, ("2", "GND", PW)],
        footprint="Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
        datasheet="https://www.ti.com/lit/ds/symlink/txu0202.pdf",
        description="2-bit fixed-direction level translator, 1 A->B and 1 B->A, OE active high, Ioff",
        keywords="level translator")


def tca6416a_rtw():
    ports0 = [(str(1 + i), f"P0{i}", B) for i in range(8)]
    ports1 = [(str(10 + i), f"P1{i}", B) for i in range(8)]
    return make_symbol(
        "TCA6416A_RTW", "U",
        left=[("23", "VCCI", PW), ("21", "VCCP", PW), None, ("19", "SCL", I), ("20", "SDA", B),
              ("22", "~{INT}", "open_collector"), ("24", "~{RESET}", I), ("18", "ADDR", I), None,
              ("9", "GND", PW), ("25", "EP", P)],
        right=ports0 + [None] + ports1,
        footprint="Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
        datasheet="https://www.ti.com/lit/ds/symlink/tca6416a.pdf",
        description="16-bit I2C GPIO expander, separate VCCI (I2C) and VCCP (ports) supplies, WQFN-24",
        keywords="I2C GPIO expander")


def ts3usb221a():
    return make_symbol(
        "TS3USB221A", "U",
        left=[("10", "VCC", PW), ("9", "S", I), ("6", "~{OE}", I), None, ("8", "D+", B), ("7", "D-", B), None,
              ("5", "GND", PW)],
        right=[("1", "1D+", B), ("2", "1D-", B), None, ("3", "2D+", B), ("4", "2D-", B)],
        footprint=f"{LIB}:TI_RSE_UQFN-10_1.5x2mm_P0.5mm",
        datasheet="https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf",
        description="USB 2.0 high-speed 2:1 switch. S low: D=1D, S high: D=2D, ~OE high: all off",
        keywords="USB switch mux")


def hr911130c():
    return make_symbol(
        "HR911130C", "J",
        left=[("P2", "MDI0+", P), ("P3", "MDI0-", P), ("P4", "MDI1+", P), ("P7", "MDI1-", P),
              ("P5", "MDI2+", P), ("P6", "MDI2-", P), ("P8", "MDI3+", P), ("P9", "MDI3-", P), None,
              ("P1", "TCT", P), ("P10", "CHS_GND", P)],
        right=[("14", "LED1_A", P), ("13", "LED1_K", P), ("11", "LED2_A", P), ("12", "LED2_K", P), None,
               None, None, None, None, ("SHIELD0", "SHIELD", P), ("SHIELD1", "SHIELD", P)],
        footprint=f"{LIB}:RJ45_HanRun_HR911130C",
        datasheet="https://lcsc.com/product-detail/RJ45-Transformer_HR911130C_C50933.html",
        description="Gigabit RJ45 MagJack with LEDs. TCT = PHY-side centre taps (all four, tied inside); "
                    "CHS_GND = Bob Smith termination (via internal cap)",
        keywords="RJ45 magjack ethernet")


def cm_connectors(csv_path: Path):
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    syms = []
    for conn, label in (("J1A", "A"), ("J1B", "B")):
        pins = [r for r in rows if r["connector"] == conn]
        left, right = [], []
        for r in sorted(pins, key=lambda r: int(r["pin"])):
            n = int(r["pin"])
            name = r["cm4_name"]
            if r["cm5_name"] and r["cm5_name"] != name and not _same_power(name, r["cm5_name"]):
                name = f"{name}/{r['cm5_name']}"
            name = name.replace(" (Input)", "").replace(" (Output)", "")
            etype = _cm_type(name)
            (left if n % 2 else right).append((str(n), name, etype))
        syms.append(make_symbol(
            f"CM4_CM5_{conn}", "J",
            left=left, right=right, min_width=40.64,
            footprint="Connector_Hirose_DF40:Hirose_DF40C-100DS-0.4V_2x50_P0.4mm",
            datasheet="https://datasheets.raspberrypi.com/cm4/cm4-datasheet.pdf",
            description=f"Raspberry Pi Compute Module 4/5 connector {label} (module pins "
                        f"{'1-100' if label == 'A' else '101-200'}). Pin names: CM4 name, then /CM5 name if different",
            keywords="Raspberry Pi CM4 CM5 compute module"))
    return syms


def _same_power(a: str, b: str) -> bool:
    strip = lambda s: s.replace("+", "").replace("CM4_", "").replace("CM5_", "").strip()
    return strip(a) == strip(b)


def _cm_type(name: str) -> str:
    if name == "GND":
        return PW
    if name.startswith("+5V") or name.startswith("5V"):
        return PW
    if name.startswith("CM4_3.3V") or name.startswith("CM4_1.8V"):
        return PO
    return P


def build(out_lib: Path, csv_path: Path):
    symbols = [txu0304(), txu0202(), tca6416a_rtw(), ts3usb221a(), hr911130c(), *cm_connectors(csv_path)]
    write_library(out_lib, symbols)
    return symbols
