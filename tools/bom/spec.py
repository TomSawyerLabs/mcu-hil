"""Part specs: what a position must be, written in each symbol's "Spec" field.

  R <value> [<tol>%] <package>           R 10k 1% 0402, R 0 0402 (jumper), R 1 1% 0603
  C <value> <dielectric> <volts>V <pkg>  C 100n X5R+ 16V 0402, C 12p C0G 50V 0402
                                          X5R+ = X5R or better (X6S, X7R, X7S, X8R, C0G); C0G = C0G/NP0 only
  LED <colour> <package>                 LED red 0603
  mpn <part number> [<package>]          mpn 2N7002 SOT-23: that part number from any maker. A suffix after a
                                          separator is allowed (2N7002-7-F, "B5819W SL"); 2N7002K is not.

A part with no Spec is fixed to its LCSC number (stock is still checked).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .jlc import Component

_PREFIX = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1.0, "k": 1e3, "M": 1e6}
_NUM = re.compile(r"^\s*([0-9.]+)\s*([pnuµmkM]?)")
_GRADES = {"X5R+": {"X5R", "X6S", "X7R", "X7S", "X8R", "C0G", "NP0"}, "X7R+": {"X7R", "X7S", "X8R", "C0G", "NP0"},
           "C0G": {"C0G", "NP0"}}
_CATEGORY = {"R": "Chip Resistor - Surface Mount", "C": "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
             "LED": "LED Indication - Discrete"}


class SpecError(ValueError):
    pass


def number(s: str) -> float | None:
    m = _NUM.match(s.replace("Ω", "").replace("R", ""))
    return float(m.group(1)) * _PREFIX[m.group(2)] if m else None


def _pkg(s: str) -> str:
    return s.upper().replace(" ", "")


@dataclass(frozen=True)
class Spec:
    text: str

    def __post_init__(self):
        self.parse()   # fail early on a bad spec

    def parse(self) -> dict:
        t = self.text.split()
        if not t:
            raise SpecError("empty spec")
        kind = t[0]
        try:
            if kind == "R":
                d = {"kind": "R", "value": number(t[1]), "package": t[-1], "tol": None}
                if len(t) == 4:
                    d["tol"] = float(t[2].rstrip("%"))
                elif len(t) != 3:
                    raise IndexError
            elif kind == "C":
                if len(t) != 5 or t[2] not in _GRADES and t[2] not in {"X5R", "X7R"} or not t[3].endswith("V"):
                    raise IndexError
                d = {"kind": "C", "value": number(t[1]), "grade": t[2], "volts": float(t[3][:-1]), "package": t[4]}
            elif kind == "LED":
                if len(t) != 3:
                    raise IndexError
                d = {"kind": "LED", "colour": t[1].lower(), "package": t[2]}
            elif kind == "mpn":
                if len(t) not in (2, 3):
                    raise IndexError
                d = {"kind": "mpn", "mpn": t[1].upper(), "package": t[2] if len(t) == 3 else None}
            else:
                raise SpecError(f"unknown spec kind {kind!r} in {self.text!r}")
        except (IndexError, ValueError, TypeError) as e:
            if isinstance(e, SpecError):
                raise
            raise SpecError(f"can't parse spec {self.text!r} (see tools/bom/spec.py)") from None
        if d.get("value", 0) is None:
            raise SpecError(f"bad value in spec {self.text!r}")
        return d

    def keyword(self) -> str:
        d = self.parse()
        if d["kind"] == "R":
            v = self.text.split()[1]
            return f"{v.rstrip('R') or '0'}Ω {d['package']}"
        if d["kind"] == "C":
            return f"{self.text.split()[1]}F {d['package']}"
        if d["kind"] == "LED":
            return f"LED {d['colour']} {d['package']}"
        return d["mpn"]

    def why_not(self, c: Component) -> str | None:
        """None if the component meets this spec, else the first reason it doesn't."""
        d = self.parse()
        a = c.attributes
        if d.get("package") and _pkg(c.package) != _pkg(d["package"]):
            return f"package {c.package}"
        if d["kind"] in _CATEGORY and c.category != _CATEGORY[d["kind"]]:
            return f"category {c.category}"
        if d["kind"] == "R":
            v = number(a.get("Resistance", ""))
            if v is None or abs(v - d["value"]) > 1e-9 * max(1.0, d["value"]):
                return f"resistance {a.get('Resistance')}"
            if d["tol"] is not None:
                tol = number(a.get("Tolerance", "").lstrip("±").rstrip("%"))
                if tol is None or tol > d["tol"]:
                    return f"tolerance {a.get('Tolerance')}"
        elif d["kind"] == "C":
            v = number(a.get("Capacitance", ""))
            if v is None or abs(v - d["value"]) > 1e-6 * d["value"]:
                return f"capacitance {a.get('Capacitance')}"
            if a.get("Temperature Coefficient") not in _GRADES.get(d["grade"], {d["grade"]}):
                return f"dielectric {a.get('Temperature Coefficient')}"
            volts = number(a.get("Voltage Rating", ""))
            if volts is None or volts < d["volts"]:
                return f"voltage {a.get('Voltage Rating')}"
            if d["grade"] == "C0G":
                tol = number(a.get("Tolerance", "").lstrip("±").rstrip("%"))
                if tol is None or tol > 5:
                    return f"tolerance {a.get('Tolerance')}"
        elif d["kind"] == "LED":
            if a.get("Illumination Color", "").lower() != d["colour"]:
                return f"colour {a.get('Illumination Color')}"
        elif d["kind"] == "mpn":
            m = c.model.upper()
            if not m.startswith(d["mpn"]) or (len(m) > len(d["mpn"]) and m[len(d["mpn"])].isalnum()):
                return f"part number {c.model}"
        return None
