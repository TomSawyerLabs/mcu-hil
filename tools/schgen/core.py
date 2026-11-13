"""Design model and KiCad 10 schematic writer.

A design is a list of sheets. Each sheet holds parts; each part maps its pins to net names.
The writer places parts on a grid and puts a label on every pin end instead of drawing wires:
power nets get power symbols, nets used on one sheet get local labels, and nets used on more
than one sheet get global labels. Unused pins get no-connect flags.
"""

from __future__ import annotations

import json
import math
import uuid as uuidlib
from dataclasses import dataclass, field
from pathlib import Path

from .libsym import LibSymbol, Pin, load_symbol
from .sexpr import Sym, dumps, find

SCH_VERSION = 20260306
GEN_VERSION = "10.0"
GRID = 2.54

# Nets drawn with KiCad power symbols. Everything else gets labels.
POWER_SYMBOLS = {
    "GND": "power:GND",
    "+5V": "power:+5V",
    "+3V3": "power:+3V3",
    "+12V": "power:+12V",
    "+1V8": "power:+1V8",
}

NC = "__NC__"   # map a pin to this to mark it deliberately unconnected


def stable_uuid(*parts: str) -> str:
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, "mcu-hil/" + "/".join(parts)))


@dataclass
class Part:
    lib_id: str
    value: str
    pins: dict[str, str]              # pin number or pin name -> net
    footprint: str = ""
    lcsc: str = ""
    mpn: str = ""
    datasheet: str = ""
    description: str = ""
    ref_prefix: str = ""
    option: str = ""                  # population option: "", "HV" or "CLK"
    dnp: bool = False
    in_bom: bool = True
    on_board: bool = True
    unit: int = 1
    note: str = ""
    key: str = ""                     # stable identity for uuids
    sym: LibSymbol | None = None
    ref: str = ""
    resolved: dict[str, str] = field(default_factory=dict)   # pin number -> net


@dataclass
class Sheet:
    name: str           # file stem
    title: str
    parts: list[Part] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    paper: str = "A3"

    def add(self, part: Part) -> Part:
        if not part.key:
            part.key = f"{self.name}/{len(self.parts)}"
        self.parts.append(part)
        return part


class DesignError(Exception):
    pass


class Project:
    def __init__(self, name: str, title: str, sheets: list[Sheet], lib_dirs: list[Path],
                 variants: dict[str, set[str]], fp_lib_dir_rel: str = "", sym_lib_rel: str = ""):
        self.name = name
        self.title = title
        self.sheets = sheets
        self.lib_dirs = lib_dirs
        self.variants = variants       # variant name -> options left unfitted
        self.fp_lib_dir_rel = fp_lib_dir_rel
        self.sym_lib_rel = sym_lib_rel
        self.root_uuid = stable_uuid(name, "root")
        self._symcache: dict[str, LibSymbol] = {}

    # ---------------------------------------------------------------- resolve
    def sym(self, lib_id: str) -> LibSymbol:
        if lib_id not in self._symcache:
            self._symcache[lib_id] = load_symbol(lib_id, self.lib_dirs)
        return self._symcache[lib_id]

    def resolve(self):
        errors: list[str] = []
        counters: dict[str, int] = {}
        for sh in self.sheets:
            for p in sh.parts:
                p.sym = self.sym(p.lib_id)
                pins = [q for q in p.sym.pins if q.unit in (0, p.unit)]
                by_num = {q.number: q for q in pins}
                by_name: dict[str, list[Pin]] = {}
                for q in pins:
                    by_name.setdefault(q.name, []).append(q)
                p.resolved = {}
                for k, net in p.pins.items():
                    if k in by_num:
                        targets = [by_num[k]]
                    elif k in by_name:
                        targets = by_name[k]
                    else:
                        errors.append(f"{sh.name}: {p.lib_id} ({p.value}) has no pin {k!r}")
                        continue
                    for q in targets:
                        if q.number in p.resolved and p.resolved[q.number] != net:
                            errors.append(f"{sh.name}: {p.value} pin {q.number} mapped twice")
                        p.resolved[q.number] = net
                for q in pins:
                    if q.number not in p.resolved:
                        if q.name.upper() in ("NC", "DNC") or q.etype == "no_connect":
                            p.resolved[q.number] = NC
                        else:
                            errors.append(f"{sh.name}: {p.value} pin {q.number} ({q.name}) not assigned")
                    if q.hidden and q.etype == "power_in":
                        errors.append(f"{sh.name}: {p.lib_id} has hidden power pin {q.number}; not supported")
                prefix = p.ref_prefix or p.sym.prop_value("Reference", "U").rstrip("?")
                counters[prefix] = counters.get(prefix, 0) + 1
                p.ref = f"{prefix}{counters[prefix]}"
        if errors:
            raise DesignError("\n".join(errors))

    def nets(self) -> dict[str, list[tuple[str, Part, str]]]:
        out: dict[str, list] = {}
        for sh in self.sheets:
            for p in sh.parts:
                for num, net in p.resolved.items():
                    if net != NC:
                        out.setdefault(net, []).append((sh.name, p, num))
        return out

    def check(self) -> list[str]:
        problems = []
        for net, conns in sorted(self.nets().items()):
            if len(conns) < 2:
                sh, p, num = conns[0]
                problems.append(f"net {net} has one connection only ({p.ref} pin {num}, sheet {sh})")
        return problems

    # ----------------------------------------------------------------- write
    def write(self, outdir: Path):
        self.resolve()
        problems = self.check()
        if problems:
            raise DesignError("\n".join(problems))
        outdir.mkdir(parents=True, exist_ok=True)
        nets = self.nets()
        global_nets = {n for n, c in nets.items() if len({s for s, _, _ in c}) > 1}
        page = 2
        sheet_nodes = []
        for i, sh in enumerate(self.sheets):
            sheet_uuid = stable_uuid(self.name, "sheet", sh.name)
            text = self._sheet_file(sh, sheet_uuid, global_nets, page)
            (outdir / f"{sh.name}.kicad_sch").write_text(text, encoding="utf-8", newline="\n")
            sheet_nodes.append(self._sheet_symbol(sh, sheet_uuid, i, page))
            page += 1
        root = self._root_file(sheet_nodes)
        (outdir / f"{self.name}.kicad_sch").write_text(root, encoding="utf-8", newline="\n")
        (outdir / f"{self.name}.kicad_pro").write_text(self._project_file(), encoding="utf-8", newline="\n")
        if self.fp_lib_dir_rel:
            (outdir / "fp-lib-table").write_text(
                "(fp_lib_table\n\t(version 7)\n\t(lib (name \"mcu-hil\") (type \"KiCad\") "
                f"(uri \"${{KIPRJMOD}}/{self.fp_lib_dir_rel}\") (options \"\") (descr \"Project footprints\"))\n)\n",
                encoding="utf-8", newline="\n")
        if self.sym_lib_rel:
            (outdir / "sym-lib-table").write_text(
                "(sym_lib_table\n\t(version 7)\n\t(lib (name \"mcu-hil\") (type \"KiCad\") "
                f"(uri \"${{KIPRJMOD}}/{self.sym_lib_rel}\") (options \"\") (descr \"Project symbols\"))\n)\n",
                encoding="utf-8", newline="\n")

    def _project_file(self) -> str:
        pro = {
            "meta": {"filename": f"{self.name}.kicad_pro", "version": 3},
            "schematic": {
                "variants": [{"name": n, "description": "Leaves unfitted: " + ", ".join(sorted(o))}
                             for n, o in self.variants.items()],
            },
            "sheets": [[self.root_uuid, "Root"]] + [
                [stable_uuid(self.name, "sheet", sh.name), sh.title] for sh in self.sheets],
        }
        return json.dumps(pro, indent=2) + "\n"

    def _header(self, sh_uuid: str, title: str, paper: str, page: int):
        return [Sym("kicad_sch"), [Sym("version"), Sym(str(SCH_VERSION))],
                [Sym("generator"), "eeschema"], [Sym("generator_version"), GEN_VERSION],
                [Sym("uuid"), sh_uuid], [Sym("paper"), paper],
                [Sym("title_block"), [Sym("title"), title], [Sym("company"), "TomSawyerLabs mcu-hil"],
                 [Sym("comment"), Sym("1"), "Generated by tools/schgen. Edit the generator, not this file."]]]

    def _root_file(self, sheet_nodes) -> str:
        root = self._header(self.root_uuid, self.title, "A4", 1)
        root.append([Sym("lib_symbols")])
        root += sheet_nodes
        root.append([Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]])
        root.append([Sym("embedded_fonts"), Sym("no")])
        return dumps(root) + "\n"

    def _sheet_symbol(self, sh: Sheet, sheet_uuid: str, index: int, page: int):
        col, row = index % 4, index // 4
        x, y = 20.32 + col * 66.04, 30.48 + row * 30.48
        w, h = 55.88, 15.24
        return [Sym("sheet"), [Sym("at"), x, y], [Sym("size"), w, h],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
                [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("no")],
                [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
                [Sym("fill"), [Sym("color"), 0, 0, 0, 0.0]],
                [Sym("uuid"), sheet_uuid],
                [Sym("property"), "Sheetname", sh.title, [Sym("at"), x, y - 0.7, 0],
                 _effects(justify=["left", "bottom"])],
                [Sym("property"), "Sheetfile", f"{sh.name}.kicad_sch", [Sym("at"), x, y + h + 0.6, 0],
                 _effects(justify=["left", "top"])],
                [Sym("instances"), [Sym("project"), self.name,
                                    [Sym("path"), f"/{self.root_uuid}", [Sym("page"), str(page)]]]]]

    def _sheet_file(self, sh: Sheet, sheet_uuid: str, global_nets: set[str], page: int) -> str:
        node = self._header(sheet_uuid, sh.title, sh.paper, page)
        libs: dict[str, LibSymbol] = {}
        for p in sh.parts:
            libs[p.lib_id] = p.sym
        power_needed = {POWER_SYMBOLS[n] for p in sh.parts for n in p.resolved.values() if n in POWER_SYMBOLS}
        for lid in sorted(power_needed):
            libs[lid] = self.sym(lid)
        node.append([Sym("lib_symbols")] + [libs[k].node for k in sorted(libs)])
        path = f"/{self.root_uuid}/{sheet_uuid}"
        items: list = []
        layout = _Layout(sh.paper)
        pwr_count = [0]
        y_text = 12.7
        for n in sh.notes:
            items.append(_text(n, 15.24, y_text, stable_uuid(self.name, sh.name, "note", n)))
            y_text += 2.54 * (1 + n.count("\n"))
        layout.y = max(layout.y, y_text + 7.62)
        for p in sh.parts:
            items += self._place_part(sh, p, path, layout, global_nets, pwr_count)
        node += items
        node.append([Sym("embedded_fonts"), Sym("no")])
        return dumps(node) + "\n"

    def _place_part(self, sh: Sheet, p: Part, path: str, layout: "_Layout", global_nets, pwr_count):
        sym = p.sym
        x0, y0, x1, y1 = sym.body_bbox(p.unit)
        # Room for labels on each side.
        pins = [q for q in sym.pins if q.unit in (0, p.unit)]
        def lab_len(q):
            net = p.resolved[q.number]
            if net == NC:
                return 2.54
            if net in POWER_SYMBOLS:
                return 7.62
            return 2.54 + 1.0 * len(net) * 1.27 * 0.75 + (3.81 if net in global_nets else 0)
        left = max([lab_len(q) for q in pins if _label_dir(q.angle) == 180] or [0])
        right = max([lab_len(q) for q in pins if _label_dir(q.angle) == 0] or [0])
        up = max([lab_len(q) for q in pins if _label_dir(q.angle) == 90] or [0])
        down = max([lab_len(q) for q in pins if _label_dir(q.angle) == 270] or [0])
        w = (x1 - x0) + left + right + 10.16
        h = (y1 - y0) + up + down + 10.16
        cx, cy = layout.place(w, h)
        # Symbol origin so that the bbox (with label room) starts at cx, cy. Library y is up.
        X = _snap(cx + left + 5.08 - x0)
        Y = _snap(cy + up + 5.08 + y1)
        uid = stable_uuid(self.name, p.key, "sym")
        out = []
        node = [Sym("symbol"), [Sym("lib_id"), p.lib_id], [Sym("at"), X, Y, 0], [Sym("unit"), p.unit],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes" if p.in_bom else "no")],
                [Sym("on_board"), Sym("yes" if p.on_board else "no")], [Sym("dnp"), Sym("yes" if p.dnp else "no")],
                [Sym("uuid"), uid]]
        fields = [("Reference", p.ref, False), ("Value", p.value, False),
                  ("Footprint", p.footprint, True), ("Datasheet", p.datasheet or sym.prop_value("Datasheet"), True),
                  ("Description", p.description or sym.prop_value("Description"), True)]
        extra = [("LCSC", p.lcsc), ("MPN", p.mpn), ("Option", p.option), ("Note", p.note)]
        for k, v in extra:
            if v:
                fields.append((k, v, k != "Option"))
        for i, (k, v, hide) in enumerate(fields):
            lp = sym.props.get(k)
            if lp is not None and find(lp, "at") is not None and k in ("Reference", "Value"):
                at = find(lp, "at")
                fx, fy = X + float(at[1]), Y - float(at[2])
            else:
                fx, fy = X + x0, Y - y0 + 2.54 * (i - 1)
            prop = [Sym("property"), k, v, [Sym("at"), _r(fx), _r(fy), 0]]
            if hide:
                prop.append([Sym("hide"), Sym("yes")])
            prop.append(_effects())
            node.append(prop)
        for q in pins:
            node.append([Sym("pin"), q.number, [Sym("uuid"), stable_uuid(self.name, p.key, "pin", q.number)]])
        inst = [Sym("path"), path, [Sym("reference"), p.ref], [Sym("unit"), p.unit]]
        for vname, unfitted in self.variants.items():
            if p.option and p.option in unfitted and not p.dnp:
                inst.append([Sym("variant"), [Sym("name"), vname], [Sym("dnp"), Sym("yes")]])
        node.append([Sym("instances"), [Sym("project"), self.name, inst]])
        out.append(node)
        # Labels on pin ends. Stacked pins (same point, often hidden) get one label.
        placed: dict[tuple, str] = {}
        for q in sorted(pins, key=lambda q: q.hidden):
            net = p.resolved[q.number]
            px, py = _r(X + q.x), _r(Y - q.y)
            if (px, py) in placed:
                if placed[(px, py)] != net:
                    raise DesignError(f"{p.ref}: stacked pins at one point on nets {placed[(px, py)]} and {net}")
                continue
            placed[(px, py)] = net
            d = _label_dir(q.angle)
            key = f"{p.key}/{q.number}"
            if net == NC:
                out.append([Sym("no_connect"), [Sym("at"), px, py], [Sym("uuid"), stable_uuid(self.name, key, "nc")]])
            elif net in POWER_SYMBOLS:
                pwr_count[0] += 1
                out.append(self._power_symbol(net, px, py, d, sh, key, path))
            elif net in global_nets:
                out.append(_global_label(net, px, py, d, stable_uuid(self.name, key, "gl")))
            else:
                out.append(_label(net, px, py, d, stable_uuid(self.name, key, "l")))
        return out

    def _power_symbol(self, net, px, py, d, sh, key, path):
        lid = POWER_SYMBOLS[net]
        sym = self.sym(lid)
        default = 270 if net == "GND" else 90
        rot = (d - default) % 360
        self._pwr_n = getattr(self, "_pwr_n", 0) + 1
        ref = f"#PWR{self._pwr_n:04d}"
        uid = stable_uuid(self.name, key, "pwr")
        vx, vy = px, py
        off = 5.08
        if d == 270:
            vy += off
        elif d == 90:
            vy -= off
        elif d == 0:
            vx += off + 2.54
        else:
            vx -= off + 2.54
        return [Sym("symbol"), [Sym("lib_id"), lid], [Sym("at"), px, py, rot], [Sym("unit"), 1],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
                [Sym("dnp"), Sym("no")], [Sym("uuid"), uid],
                [Sym("property"), "Reference", ref, [Sym("at"), px, py, 0], [Sym("hide"), Sym("yes")], _effects()],
                [Sym("property"), "Value", net, [Sym("at"), _r(vx), _r(vy), 0], _effects()],
                [Sym("property"), "Footprint", "", [Sym("at"), px, py, 0], [Sym("hide"), Sym("yes")], _effects()],
                [Sym("property"), "Datasheet", "", [Sym("at"), px, py, 0], [Sym("hide"), Sym("yes")], _effects()],
                [Sym("pin"), "1", [Sym("uuid"), stable_uuid(self.name, key, "pwrpin")]],
                [Sym("instances"), [Sym("project"), self.name,
                                    [Sym("path"), path, [Sym("reference"), ref], [Sym("unit"), 1]]]]]


class _Layout:
    """Row-based placement on a sheet."""

    SIZES = {"A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0)}

    def __init__(self, paper: str):
        self.W, self.H = self.SIZES[paper]
        self.margin = 12.7
        self.x = self.margin
        self.y = self.margin + 10.16
        self.row_h = 0.0

    def place(self, w, h):
        if self.x + w > self.W - self.margin and self.x > self.margin:
            self.x = self.margin
            self.y += self.row_h
            self.row_h = 0.0
        pos = (self.x, self.y)
        self.x += w
        self.row_h = max(self.row_h, h)
        return pos


def _label_dir(pin_angle: int) -> int:
    return (pin_angle + 180) % 360


def _snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


def _r(v: float) -> float:
    return round(v, 4)


def _effects(size=1.27, justify=None):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify])
    return e


def _label(net, x, y, d, uid):
    just = ["left", "bottom"] if d in (0, 90) else ["right", "bottom"]
    return [Sym("label"), net, [Sym("at"), x, y, d], _effects(justify=just), [Sym("uuid"), uid]]


def _global_label(net, x, y, d, uid):
    just = ["left"] if d in (0, 90) else ["right"]
    return [Sym("global_label"), net, [Sym("shape"), Sym("bidirectional")], [Sym("at"), x, y, d],
            [Sym("fields_autoplaced"), Sym("yes")], _effects(justify=just), [Sym("uuid"), uid],
            [Sym("property"), "Intersheetrefs", "${INTERSHEET_REFS}", [Sym("at"), x, y, 0],
             [Sym("hide"), Sym("yes")], _effects(justify=just)]]


def _text(s, x, y, uid):
    return [Sym("text"), s, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), x, y, 0],
            _effects(justify=["left", "bottom"]), [Sym("uuid"), uid]]
