"""Build simple rectangular KiCad symbols from pin tables, for parts missing from KiCad's libraries.

Pin tuples are (number, name, electrical_type). A `None` entry leaves a one-pitch gap.
"""

from __future__ import annotations

from pathlib import Path

from .sexpr import Sym, dumps

PITCH = 2.54
PIN_LEN = 2.54


def _effects(hide=False, justify=None):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]
    if justify:
        e.append([Sym("justify"), Sym(justify)])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


def _prop(k, v, x, y, hide=False, justify=None):
    return [Sym("property"), k, v, [Sym("at"), x, y, 0], _effects(hide, justify)]


def _pin(num, name, etype, x, y, angle):
    return [Sym("pin"), Sym(etype), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), PIN_LEN],
            [Sym("name"), name, _effects()], [Sym("number"), num, _effects()]]


def make_symbol(name: str, ref: str, *, left=(), right=(), top=(), bottom=(),
                footprint: str = "", datasheet: str = "", description: str = "",
                keywords: str = "", min_width: float = 10.16):
    """Return a (symbol ...) node for a single-unit rectangular part."""
    left, right, top, bottom = list(left), list(right), list(top), list(bottom)
    longest = max([len(p[1]) for p in left + right if p] or [1])
    w = max(min_width, PITCH * round((longest * 2 * 0.8 * 1.27 + 5.08) / PITCH),
            PITCH * (max(len(top), len(bottom)) + 1))
    w = PITCH * round(w / PITCH / 2) * 2          # even number of pitches, so the centre stays on grid
    rows = max(len(left), len(right), 1)
    h = PITCH * (rows + 1)
    if h % (2 * PITCH):
        h += PITCH
    x0, x1 = -w / 2, w / 2
    y1, y0 = h / 2, -h / 2
    body = [Sym("rectangle"), [Sym("start"), x0, y1], [Sym("end"), x1, y0],
            [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
            [Sym("fill"), [Sym("type"), Sym("background")]]]
    pins = []
    for i, p in enumerate(left):
        if p:
            pins.append(_pin(p[0], p[1], p[2], x0 - PIN_LEN, y1 - PITCH * (i + 1), 0))
    for i, p in enumerate(right):
        if p:
            pins.append(_pin(p[0], p[1], p[2], x1 + PIN_LEN, y1 - PITCH * (i + 1), 180))
    for i, p in enumerate(top):
        if p:
            x = -PITCH * (len(top) - 1) / 2 + PITCH * i
            pins.append(_pin(p[0], p[1], p[2], round(x / PITCH) * PITCH, y1 + PIN_LEN, 270))
    for i, p in enumerate(bottom):
        if p:
            x = -PITCH * (len(bottom) - 1) / 2 + PITCH * i
            pins.append(_pin(p[0], p[1], p[2], round(x / PITCH) * PITCH, y0 - PIN_LEN, 90))
    node = [Sym("symbol"), name,
            [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", ref, x0, y1 + 1.27 + (PIN_LEN if top else 0), justify="left"),
            _prop("Value", name, x0, y0 - 1.27 - (PIN_LEN if bottom else 0), justify="left"),
            _prop("Footprint", footprint, 0, 0, hide=True),
            _prop("Datasheet", datasheet, 0, 0, hide=True),
            _prop("Description", description, 0, 0, hide=True)]
    if keywords:
        node.append(_prop("ki_keywords", keywords, 0, 0, hide=True))
    node.append([Sym("symbol"), f"{name}_0_1", body])
    node.append([Sym("symbol"), f"{name}_1_1"] + pins)
    return node


def write_library(path: Path, symbols: list):
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), Sym("20251024")],
           [Sym("generator"), "mcu-hil-schgen"], [Sym("generator_version"), "10.0"]] + symbols
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(lib) + "\n", encoding="utf-8", newline="\n")
