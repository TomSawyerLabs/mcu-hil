"""Load symbols from KiCad .kicad_sym libraries and expose their pins and geometry."""

from __future__ import annotations

import copy
import math
import os
from dataclasses import dataclass
from pathlib import Path

from .sexpr import Sym, find, find_all, parse

KICAD_SYMBOL_DIR = Path(os.environ.get(
    "KICAD10_SYMBOL_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\symbols"))

_lib_cache: dict[Path, list] = {}


@dataclass
class Pin:
    number: str
    name: str
    etype: str      # power_in, input, output, bidirectional, passive, ...
    x: float        # connection point, library coordinates (y up)
    y: float
    angle: int      # direction the pin line runs from the connection point toward the body
    length: float
    unit: int       # 0 = common to all units
    hidden: bool


class LibSymbol:
    """A flattened library symbol, ready to embed in a schematic's lib_symbols."""

    def __init__(self, lib: str, name: str, node: list):
        self.lib = lib
        self.name = name
        self.node = node            # (symbol "lib:name" ...) with sub-units named name_U_B
        self.pins: list[Pin] = []
        self.props: dict[str, list] = {}
        self._index()

    @property
    def lib_id(self) -> str:
        return f"{self.lib}:{self.name}"

    def _index(self):
        for p in find_all(self.node, "property"):
            self.props[p[1]] = p
        for sub in find_all(self.node, "symbol"):
            unit, body = _unit_of(sub[1])
            if body not in (0, 1):
                continue
            for pin in find_all(sub, "pin"):
                at = find(pin, "at")
                name = find(pin, "name")
                num = find(pin, "number")
                length = find(pin, "length")
                hidden = any(c == "hide" or (isinstance(c, list) and c[:2] == ["hide", "yes"])
                             for c in pin)
                self.pins.append(Pin(str(num[1]), str(name[1]), str(pin[1]), float(at[1]), float(at[2]),
                                     int(float(at[3])) if len(at) > 3 else 0,
                                     float(length[1]) if length else 0.0, unit, hidden))

    @property
    def units(self) -> list[int]:
        us = sorted({p.unit for p in self.pins if p.unit})
        return us or [1]

    def prop_value(self, key: str, default: str = "") -> str:
        p = self.props.get(key)
        return str(p[2]) if p else default

    def is_power(self) -> bool:
        return find(self.node, "power") is not None

    def body_bbox(self, unit: int = 1):
        """Bounding box of graphics and pins for one unit, library coordinates."""
        xs, ys = [], []
        for sub in find_all(self.node, "symbol"):
            u, body = _unit_of(sub[1])
            if body not in (0, 1) or u not in (0, unit):
                continue
            for g in sub:
                if not isinstance(g, list):
                    continue
                for key in ("start", "end", "at", "center", "mid"):
                    for c in find_all(g, key):
                        xs.append(float(c[1]))
                        ys.append(float(c[2]))
                pts = find(g, "pts")
                if pts:
                    for xy in find_all(pts, "xy"):
                        xs.append(float(xy[1]))
                        ys.append(float(xy[2]))
                if g[0] == "pin":
                    at = find(g, "at")
                    ln = find(g, "length")
                    a = math.radians(float(at[3]) if len(at) > 3 else 0)
                    L = float(ln[1]) if ln else 0
                    xs += [float(at[1]), float(at[1]) + L * math.cos(a)]
                    ys += [float(at[2]), float(at[2]) + L * math.sin(a)]
        if not xs:
            return (-2.54, -2.54, 2.54, 2.54)
        return (min(xs), min(ys), max(xs), max(ys))


def _unit_of(subname: str):
    parts = subname.rsplit("_", 2)
    return int(parts[-2]), int(parts[-1])


def _load_lib(path: Path) -> list:
    if path not in _lib_cache:
        _lib_cache[path] = parse(path.read_text(encoding="utf-8"))
    return _lib_cache[path]


def _raw_symbol(libnode: list, name: str):
    for s in find_all(libnode, "symbol"):
        if s[1] == name:
            return s
    return None


def load_symbol(lib_id: str, extra_dirs: list[Path] = ()) -> LibSymbol:
    """Load `Lib:Name`, flattening `extends`, from the KiCad library dir or a project lib dir."""
    lib, name = lib_id.split(":", 1)
    path = None
    for d in [*extra_dirs, KICAD_SYMBOL_DIR]:
        cand = Path(d) / f"{lib}.kicad_sym"
        if cand.exists():
            path = cand
            break
    if path is None:
        raise FileNotFoundError(f"symbol library {lib}.kicad_sym not found")
    libnode = _load_lib(path)
    raw = _raw_symbol(libnode, name)
    if raw is None:
        raise KeyError(f"{lib_id} not in {path}")
    node = copy.deepcopy(raw)
    ext = find(node, "extends")
    if ext is not None:
        parent = copy.deepcopy(_raw_symbol(libnode, str(ext[1])))
        if parent is None:
            raise KeyError(f"{lib_id} extends missing {ext[1]}")
        pname = str(ext[1])
        child_props = {p[1]: p for p in find_all(node, "property")}
        flat = [Sym("symbol"), name]
        for c in parent[2:]:
            if isinstance(c, list) and c and c[0] == "property" and c[1] in child_props:
                flat.append(child_props.pop(c[1]))
            elif isinstance(c, list) and c and c[0] == "symbol":
                sub = copy.deepcopy(c)
                sub[1] = name + sub[1][len(pname):]
                flat.append(sub)
            else:
                flat.append(c)
        # Child-only properties go before the unit sub-symbols.
        insert_at = next(i for i, c in enumerate(flat) if isinstance(c, list) and c and c[0] == "symbol")
        for p in child_props.values():
            flat.insert(insert_at, p)
            insert_at += 1
        node = flat
    node[1] = f"{lib}:{name}"
    return LibSymbol(lib, name, node)
