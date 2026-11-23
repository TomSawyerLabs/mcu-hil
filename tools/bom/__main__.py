"""Make a board's JLC BOM for any mix of population options, from in-stock parts (run from tools/).

  python -m bom carrier --update --qty 10     pick parts for every position, write hw/carrier/bom.lock.json
  python -m bom carrier --without SD,HV       BOM + report for that build, from the lock
  python -m bom carrier --qty 10              ... and re-check the locked parts' stock live
  python -m bom carrier --list                the board's options

Reads the KiCad schematics (not the generator), so it keeps working once the board is hand-edited.
Options and their rules live in hw/options.toml. Each part's "Option" field is a condition: space-separated
terms that must all hold, "X" = option X on, "!X" = option X off. Its "Spec" field says what parts may fill
the position (tools/bom/spec.py); its "LCSC" field is the preferred part.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

from schgen.sexpr import find, find_all, parse

from .jlc import Jlc
from .resolve import ResolveError, lines_of, load_lock, needed, ref_key, resolve, save_lock, stale
from .spec import SpecError

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


def parts(board: str) -> list[dict]:
    project = BOARDS[board]
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
                            "lcsc": props.get("LCSC", ""), "spec": props.get("Spec", ""),
                            "option": props.get("Option", ""), "dnp": str(find(sym, "dnp")[1]) == "yes"})
    return out


def build_name(options: dict[str, dict], on: set[str]) -> str:
    off = [o for o in options if o not in on]
    return "all" if not off else "no-" + "-".join(off)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="python -m bom", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.splitlines()[1:]))
    ap.add_argument("board", choices=sorted(BOARDS))
    ap.add_argument("--without", default="", help="options to leave off, comma-separated (default: all on)")
    ap.add_argument("--only", default=None, help="the options to fit, comma-separated; all others off")
    ap.add_argument("--qty", type=int, help="boards to order: with --update, what the stock must cover "
                                            "(default: the lock's); otherwise re-check the lock's stock live")
    ap.add_argument("--update", action="store_true", help="re-pick parts and rewrite the lock")
    ap.add_argument("--out", type=Path, help="output folder (default hw/<board>/out)")
    ap.add_argument("--list", action="store_true", help="list the board's options and exit")
    a = ap.parse_args()
    split = lambda s: {x.strip().upper() for x in s.split(",") if x.strip()}
    lock_path = HW / a.board / "bom.lock.json"
    try:
        options = load_options(a.board)
        if a.list:
            for k, v in options.items():
                needs = f" (needs {', '.join(v['needs'])})" if v.get("needs") else ""
                print(f"{k:5} {v['description']}{needs}")
            return 0
        on = choose(options, split(a.without), split(a.only) if a.only is not None else None)
        rows = parts(a.board)
        # Every position some build can fit: option-driven parts, plus parts not hand-set DNP.
        lines = lines_of([r for r in rows if r["option"] or not r["dnp"]])
        lock = load_lock(lock_path)
        jlc = Jlc()
        if a.update:
            qty = a.qty or (lock or {}).get("qty")
            if not qty:
                raise BuildError("first --update needs --qty")
            print(f"{a.board}: resolving {len(lines)} lines for {qty} boards")
            lock = resolve(lines, qty, jlc, (lock or {}).get("lines", {}), print)
            save_lock(lock_path, lock)
            print(f"  wrote {lock_path}")
        if lock is None:
            raise BuildError(f"no lock yet: run python -m bom {a.board} --update --qty N")
        if changed := stale(lines, lock):
            raise BuildError("the lock is out of date with the schematic (run --update):\n  " + "\n  ".join(changed))
        fit = [r for r in rows if (fitted(r["option"], on, options) if r["option"] else not r["dnp"])]
        by_line = {(l.spec, l.preferred): lock["lines"][l.key] for l in lines}
        if a.qty and not a.update:
            short = []
            counts: dict[str, int] = defaultdict(int)
            for r in fit:
                counts[(r["spec"], r["lcsc"])] += 1
            for k, n in counts.items():
                e = by_line[k]
                c = jlc.part(e["lcsc"])
                need = needed(n, a.qty, c) if c else 0
                if c is None or c.stock < need:
                    short.append(f"{e['lcsc']} ({', '.join(e['refs'])}): {c.stock if c else 'not found'} in stock, "
                                 f"needs {need}")
            if short:
                raise BuildError(f"locked parts short for {a.qty} boards (run --update --qty {a.qty}):\n  "
                                 + "\n  ".join(short))
            print(f"{a.board}: stock checked live for {a.qty} boards: OK")
    except (BuildError, ResolveError, SpecError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    groups: dict[tuple, list[str]] = defaultdict(list)
    for r in fit:
        e = by_line[(r["spec"], r["lcsc"])]
        groups[(r["value"], r["footprint"].split(":")[-1], e["lcsc"])].append(r["ref"])
    name = build_name(options, on)
    outdir = a.out or HW / a.board / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    bom = outdir / f"{name}-bom.csv"
    with bom.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda g: ref_key(min(g[1], key=ref_key))):
            w.writerow([value, ",".join(sorted(refs, key=ref_key)), fp, lcsc])
    used = {by_line[(r["spec"], r["lcsc"])]["lcsc"]: by_line[(r["spec"], r["lcsc"])] for r in fit}
    subs = sorted({(e["preferred"], e["lcsc"], e["model"], e["reason"]) for e in used.values()
                   if e["lcsc"] != e["preferred"]})
    ext = sorted(e["lcsc"] for e in used.values() if e["library"] == "Extended")
    report = outdir / f"{name}-report.md"
    report.write_text("\n".join([
        f"# {a.board} build: {name}", "",
        f"Options on: {', '.join(o for o in options if o in on) or 'none'}. "
        f"Lock: resolved {lock['updated']} for {lock['qty']} boards.", "",
        f"{len(fit)} parts fitted, {len(groups)} BOM lines, {len(ext)} Extended parts (JLC charges a loading fee "
        "for each).", "",
        "## Substitutions", "",
        *([f"- {p} -> {c} ({m}): {why}" for p, c, m, why in subs] or ["None: every line uses its preferred part."]),
        ""]), encoding="utf-8", newline="\n")
    print(f"{a.board}: options on: {', '.join(o for o in options if o in on) or 'none'}")
    print(f"  {len(fit)} parts fitted ({len(groups)} lines, {len(ext)} Extended), {len(subs)} substitutions")
    print(f"  wrote {bom.resolve()}")
    print(f"  wrote {report.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
