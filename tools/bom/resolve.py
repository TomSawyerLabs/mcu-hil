"""Pick an in-stock JLC part for every BOM line and keep the choices in a lock file.

A line is every position with the same Spec and preferred LCSC number (the schematic's "LCSC" field). The lock
(hw/<board>/bom.lock.json, committed) holds the chosen part per line, so a build is reproducible until someone
re-resolves with --update. Re-resolving keeps a locked choice while it still meets the spec and has the stock.
"""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .jlc import Component, Jlc
from .spec import Spec, SpecError

LIB_RANK = {"Basic": 0, "Preferred": 1, "Extended": 2}
MARGIN = 1.1   # stock must cover the order plus 10%, plus JLC's attrition


class ResolveError(Exception):
    pass


@dataclass
class Line:
    spec: str
    preferred: str
    refs: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.spec} | {self.preferred}"


def needed(per_board: int, qty: int, c: Component) -> int:
    return math.ceil(per_board * qty * MARGIN) + c.attrition


def lines_of(rows: list[dict]) -> list[Line]:
    by: dict[tuple, Line] = {}
    for r in rows:
        if not r["lcsc"]:
            raise ResolveError(f"{r['ref']} has no LCSC number (the preferred part)")
        k = (r["spec"], r["lcsc"])
        by.setdefault(k, Line(r["spec"], r["lcsc"])).refs.append(r["ref"])
    for line in by.values():
        line.refs.sort(key=ref_key)
    return sorted(by.values(), key=lambda l: (l.spec, l.preferred))


def ref_key(ref: str) -> tuple:
    stem = ref.rstrip("0123456789")
    return stem, int(ref[len(stem):] or 0)


def resolve(lines: list[Line], qty: int, jlc: Jlc, locked: dict[str, dict], log) -> dict:
    """Locked choice if still good, else the preferred part, else the best in-stock part meeting the spec.

    JLC is searched for substitutes only when both are unusable (a search takes seconds, a lookup well under one).
    """
    codes = {l.preferred for l in lines} | {e["lcsc"] for e in locked.values()}
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(jlc.part, codes))
    chosen_codes: set[str] = set()
    out: dict[str, dict] = {}
    problems: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for line in lines:
        spec = Spec(line.spec) if line.spec else None
        n = len(line.refs)
        good = lambda c: c is not None and c.stock >= needed(n, qty, c) and (not spec or spec.why_not(c) is None)
        pref = jlc.part(line.preferred)
        if pref is None:
            problems.append(f"{line.key}: preferred part {line.preferred} not found at JLC")
            continue
        if spec and (why := spec.why_not(pref)):
            raise SpecError(f"{', '.join(line.refs)}: preferred part {line.preferred} doesn't meet its own spec "
                            f"{line.spec!r} ({why})")
        old = locked.get(line.key, {}).get("lcsc")
        oc = jlc.part(old) if old else None
        if good(oc):
            pick, reason = oc, locked[line.key]["reason"]
        elif good(pref):
            pick, reason = pref, "preferred"
        elif spec:
            kw = spec.keyword()
            ok = [c for c in jlc.search(kw, pages=2, in_stock=True) + jlc.search(kw, in_stock=True, basic_only=True)
                  if good(c)]
            if not ok:
                problems.append(f"{', '.join(line.refs)} ({line.spec}): nothing in stock for {qty} boards "
                                f"(preferred {line.preferred} has {pref.stock}, needs {needed(n, qty, pref)})")
                continue
            pick = min(ok, key=lambda c: (LIB_RANK[c.library], c.lcsc not in chosen_codes, -c.stock))
            reason = f"preferred {line.preferred} short ({pref.stock} in stock, needs {needed(n, qty, pref)})"
        else:
            problems.append(f"{', '.join(line.refs)} (fixed {line.preferred}, no Spec): {pref.stock} in stock, "
                            f"needs {needed(n, qty, pref)}")
            continue
        if pick.lcsc != old:
            log(f"  {', '.join(line.refs)}: {pick.lcsc} {pick.model} ({pick.library}, {pick.stock} in stock): {reason}")
        chosen_codes.add(pick.lcsc)
        out[line.key] = {"spec": line.spec, "preferred": line.preferred, "lcsc": pick.lcsc, "model": pick.model,
                         "brand": pick.brand, "library": pick.library, "stock": pick.stock, "checked": now,
                         "reason": reason, "refs": line.refs}
    if problems:
        raise ResolveError("can't fill these lines:\n  " + "\n  ".join(problems))
    return {"qty": qty, "updated": now, "lines": out}


def load_lock(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save_lock(path: Path, lock: dict) -> None:
    lock = {**lock, "lines": dict(sorted(lock["lines"].items()))}
    path.write_text(json.dumps(lock, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def stale(lines: list[Line], lock: dict) -> list[str]:
    """Lines whose positions changed since the lock was written."""
    have = lock["lines"]
    out = [f"new or changed: {l.key} ({', '.join(l.refs)})" for l in lines
           if l.key not in have or have[l.key]["refs"] != l.refs]
    keys = {l.key for l in lines}
    out += [f"gone: {k}" for k in have if k not in keys]
    return out
