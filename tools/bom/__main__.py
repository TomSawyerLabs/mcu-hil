"""Make a board's JLC BOM for any mix of population options: python -m bom carrier --without SD,HV (from tools/).

Reads the KiCad schematics (not the generator), so it keeps working once the board is hand-edited. Options and
their rules live in hw/options.toml. Each part's "Option" field is a condition: space-separated terms that must
all hold, "X" = option X on, "!X" = option X off.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

from schgen.sexpr import find, find_all, parse

ROOT = Path(__file__).resolve().parents[2]
HW = ROOT / "hw"
BOARDS = {"carrier": "mcu-hil-carrier", "hat": "mcu-hil-hat"}


class BuildError(Exception):
    pass


def load_options(board: str) -> dict[str, dict]:
    raw = tomllib.loads((HW / "options.toml").read_text(encoding="utf-8"))["options"]
    return {k: v for k, v in raw.items() if board in v.get("boards", [board])}


def choose(options: dict[str, dict], without: set[str], with_: set[str] | None) -> set[str]:
    unknown = (without | (with_ or set())) - set(options)
    if unknown:
        raise BuildError(f"unknown option(s) for this board: {', '.join(sorted(unknown))} "
                         f"(have {', '.join(options)})")
    on = (set(with_) if with_ is not None else set(options)) - without
    for name in sorted(on):
        missing = set(options[name].get("needs", [])) - on
        if missing:
            raise BuildError(f"{name} needs {', '.join(sorted(missing))}")
    return on


def fitted(condition: str, on: set[str], options: dict[str, dict]) -> bool:
    for term in condition.split():
        name = term.removeprefix("!")
        if name not in options:
            raise BuildError(f"Option field names unknown option {name!r}")
        if (name in on) == term.startswith("!"):
            return False
    return True


def parts(board: str, project: str) -> list[dict]:
    out = []
    for sch in sorted((HW / board).glob("*.kicad_sch")):
        for sym in find_all(parse(sch.read_text(encoding="utf-8")), "symbol"):
            lib_id = find(sym, "lib_id")
            if not lib_id or str(lib_id[1]).startswith("power:"):
                continue
            if str(find(sym, "in_bom")[1]) != "yes" or str(find(sym, "on_board")[1]) != "yes":
                continue
            props = {str(p[1]): str(p[2]) for p in find_all(sym, "property")}
            refs = [find(path, "reference")[1]
                    for proj in find_all(find(sym, "instances"), "project") if proj[1] == project
                    for path in find_all(proj, "path")]
            for ref in refs or [props["Reference"]]:
                out.append({"ref": str(ref), "value": props.get("Value", ""), "footprint": props.get("Footprint", ""),
                            "lcsc": props.get("LCSC", ""), "option": props.get("Option", ""),
                            "dnp": str(find(sym, "dnp")[1]) == "yes", "sheet": sch.name})
    return out


def build_name(options: dict[str, dict], on: set[str]) -> str:
    off = [o for o in options if o not in on]
    return "all" if not off else "no-" + "-".join(off)


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m bom", description=__doc__.splitlines()[0])
    ap.add_argument("board", choices=sorted(BOARDS))
    ap.add_argument("--without", default="", help="options to leave off, comma-separated (default: all on)")
    ap.add_argument("--only", default=None, help="the options to fit, comma-separated; all others off")
    ap.add_argument("--out", type=Path, help="output CSV (default hw/<board>/out/<build>-bom.csv)")
    ap.add_argument("--list", action="store_true", help="list the board's options and exit")
    a = ap.parse_args()
    split = lambda s: {x.strip().upper() for x in s.split(",") if x.strip()}
    try:
        options = load_options(a.board)
        if a.list:
            for k, v in options.items():
                needs = f" (needs {', '.join(v['needs'])})" if v.get("needs") else ""
                print(f"{k:5} {v['description']}{needs}")
            return 0
        on = choose(options, split(a.without), split(a.only) if a.only is not None else None)
        rows = parts(a.board, BOARDS[a.board])
        fit, dnp = [], []
        for r in rows:
            # Hand-set DNP with no option stays DNP; option-driven parts follow the chosen options.
            ok = fitted(r["option"], on, options) if r["option"] else not r["dnp"]
            (fit if ok else dnp).append(r)
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    missing = [r["ref"] for r in fit if not r["lcsc"]]
    groups: dict[tuple, list[str]] = defaultdict(list)
    for r in fit:
        groups[(r["value"], r["footprint"].split(":")[-1], r["lcsc"])].append(r["ref"])
    out = a.out or HW / a.board / "out" / f"{build_name(options, on)}-bom.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    key = lambda ref: (ref.rstrip("0123456789"), int(ref[len(ref.rstrip("0123456789")):] or 0))
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda g: key(min(g[1], key=key))):
            w.writerow([value, ",".join(sorted(refs, key=key)), fp, lcsc])
    print(f"{a.board}: options on: {', '.join(o for o in options if o in on) or 'none'}")
    print(f"  {len(fit)} parts fitted ({len(groups)} lines), {len(dnp)} not fitted")
    print(f"  wrote {out.relative_to(ROOT)}")
    if missing:
        print(f"error: fitted parts with no LCSC number: {', '.join(sorted(missing, key=key))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
