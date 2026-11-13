"""Minimal S-expression reader/writer for KiCad files.

Atoms are kept as `Sym` (bare words and numbers) or `str` (quoted strings), so a file can be
read and written back without changing which atoms were quoted.
"""

from __future__ import annotations

import re


class Sym(str):
    """A bare (unquoted) atom: a keyword, number or bool."""


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text: str):
    """Parse one S-expression (a KiCad file) into nested lists."""
    stack: list[list] = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"bad token at {pos}: {text[pos:pos + 40]!r}")
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(_unescape(m.group(3)))
        elif m.group(4) is not None:
            stack[-1].append(Sym(m.group(4)))
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def _unescape(s: str) -> str:
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def fmt_atom(a) -> str:
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, bool):
        return "yes" if a else "no"
    if isinstance(a, (int, float)):
        return fmt_num(a)
    if isinstance(a, str):
        return f'"{_escape(a)}"'
    raise TypeError(f"not an atom: {a!r}")


def fmt_num(x: float) -> str:
    if isinstance(x, int):
        return str(x)
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# Lists whose children all stay on one line, as KiCad writes them.
_INLINE = {"at", "xy", "size", "start", "end", "mid", "center", "offset", "color", "width", "type",
           "length", "number", "name", "font", "justify", "hide", "uuid", "unit", "lib_id", "thickness",
           "version", "generator", "generator_version", "paper", "page", "reference", "in_bom",
           "on_board", "dnp", "exclude_from_sim", "in_pos_files", "fields_autoplaced", "radius",
           "shape", "bold", "italic", "embedded_fonts", "body_style", "pin_numbers", "power",
           "duplicate_pin_numbers_are_jumpers", "do_not_autoplace", "show_name", "path_short"}


def dumps(node, indent: int = 0) -> str:
    """Write nested lists as KiCad-style text (tabs, one list per line)."""
    if not isinstance(node, list):
        return fmt_atom(node)
    head = node[0] if node else None
    atoms_only = all(not isinstance(c, list) for c in node)
    if atoms_only or (isinstance(head, str) and head in _INLINE and _flat_ok(node)):
        return "(" + " ".join(dumps(c) for c in node) + ")"
    tab = "\t" * (indent + 1)
    parts = []
    line = "(" + " ".join(dumps(c) for c in _leading_atoms(node))
    rest = node[len(_leading_atoms(node)):]
    for c in rest:
        if isinstance(c, list):
            parts.append("\n" + tab + dumps(c, indent + 1))
        else:
            parts.append(" " + fmt_atom(c))
    return line + "".join(parts) + "\n" + "\t" * indent + ")"


def _leading_atoms(node):
    out = []
    for c in node:
        if isinstance(c, list):
            break
        out.append(c)
    return out


def _flat_ok(node) -> bool:
    return all(not isinstance(c, list) or all(not isinstance(cc, list) for cc in c) for c in node)


def find(node, key):
    """First child list whose head is `key`."""
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def find_all(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]
