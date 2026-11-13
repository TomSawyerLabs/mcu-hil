"""Generate the mcu-hil v2 schematics: python -m schgen (run from tools/)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from . import design, symbols
from .core import DesignError, Project

ROOT = Path(__file__).resolve().parents[2]
HW = ROOT / "hw"
LIB = HW / "lib"
CSV = LIB / "cm4-cm5-pins.csv"


def main() -> int:
    symbols.build(LIB / "mcu-hil.kicad_sym", CSV)
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    projects = [
        Project("mcu-hil-carrier", "mcu-hil v2: CM4/CM5 carrier, ATmega16U2",
                design.shared_sheets(carrier=True) + design.sheet_cm(rows) + [design.sheet_carrier_io()],
                [LIB], design.VARIANTS, fp_lib_dir_rel="../lib/mcu-hil.pretty", sym_lib_rel="../lib/mcu-hil.kicad_sym"),
        Project("mcu-hil-hat", "mcu-hil v2: Pi HAT, ATmega16U2",
                design.shared_sheets(carrier=False) + [design.sheet_hat_io()],
                [LIB], design.VARIANTS, fp_lib_dir_rel="../lib/mcu-hil.pretty", sym_lib_rel="../lib/mcu-hil.kicad_sym"),
    ]
    ok = True
    for proj in projects:
        out = HW / ("carrier" if "carrier" in proj.name else "hat")
        try:
            proj.write(out)
            print(f"wrote {out}")
        except DesignError as e:
            ok = False
            print(f"{proj.name}: design errors:\n{e}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
