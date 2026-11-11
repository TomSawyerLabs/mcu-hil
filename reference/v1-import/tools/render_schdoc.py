"""Render Altium .SchDoc sheets to PNG with matplotlib (approximate; no Altium or KiCad needed).

usage: python -I render_schdoc.py <dir with .SchDoc> <out dir>
Coordinates are Altium sheet units (10 mil), y up. Primitives owned by components are
stored in absolute sheet coordinates; only the current part / display mode is drawn.
"""
import glob
import math
import os
import sys

import olefile
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle, FancyBboxPatch, Arc  # noqa: E402

INK, WIRE, LABEL, PORT, SHEET = "#7a1e1e", "#1d4fa8", "#0b6b2e", "#7a5b00", "#5a2d82"


def records(path):
    data = olefile.OleFileIO(path).openstream("FileHeader").read()
    i, out = 0, []
    while i + 4 <= len(data):
        ln = int.from_bytes(data[i:i + 3], "little")
        typ = data[i + 3]
        body = data[i + 4:i + 4 + ln]
        i += 4 + ln
        if typ != 0:
            out.append({})
            continue
        d = {}
        for kv in body.rstrip(b"\0").decode("latin1").split("|"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                d[k.upper()] = v
        out.append(d)
    return out


def num(r, k, default=0.0):
    v = r.get(k)
    f = r.get(k + "_FRAC")
    if v is None and f is None:
        return default
    return float(v or 0) + float(f or 0) / 100000.0


def pt(r, prefix="LOCATION"):
    return num(r, prefix + ".X"), num(r, prefix + ".Y")


def plist(r):
    n = int(r.get("LOCATIONCOUNT", 0))
    return [(num(r, f"X{i}"), num(r, f"Y{i}")) for i in range(1, n + 1)]


def text_of(r):
    t = r.get("TEXT", r.get("NAME", ""))
    return t.replace("~1", "\n")


def render(path, outpng):
    recs = records(path)
    body = recs[1:]  # index 0 is the header; OWNERINDEX refers to positions in body
    fig, ax = plt.subplots(figsize=(17, 12), dpi=130)
    fig.patch.set_facecolor("white")
    xs, ys = [], []

    def track(*pts):
        for x, y in pts:
            xs.append(x)
            ys.append(y)

    def visible(r):
        own = r.get("OWNERINDEX")
        if own is None:
            return True
        try:
            o = body[int(own)]
        except (ValueError, IndexError):
            return True
        if o.get("RECORD") != "1":
            return True
        cur = o.get("CURRENTPARTID", "1")
        if r.get("OWNERPARTID", "-1") not in ("-1", cur):
            return False
        return r.get("OWNERPARTDISPLAYMODE", "0") == o.get("DISPLAYMODE", "0")

    for r in body:
        rt = r.get("RECORD")
        if rt is None or not visible(r) or r.get("ISHIDDEN") == "T":
            continue
        rt = int(rt)
        if rt in (27, 26, 6, 218):  # wire, bus, polyline, signal harness
            p = plist(r)
            if len(p) < 2:
                continue
            color = WIRE if rt in (27, 26, 218) else INK
            lw = {27: 1.2, 26: 3, 218: 4, 6: 0.9}[rt]
            ax.plot([a for a, _ in p], [b for _, b in p], color=color, lw=lw, solid_capstyle="round", zorder=3)
            track(*p)
        elif rt == 7:
            p = plist(r)
            if len(p) >= 3:
                ax.add_patch(Polygon(p, closed=True, fc=INK if r.get("ISSOLID") == "T" else "none", ec=INK, lw=0.9, zorder=3))
        elif rt == 13:
            (x1, y1), (x2, y2) = pt(r), pt(r, "CORNER")
            ax.plot([x1, x2], [y1, y2], color=INK, lw=0.9, zorder=3)
            track((x1, y1), (x2, y2))
        elif rt in (14, 10):
            (x1, y1), (x2, y2) = pt(r), pt(r, "CORNER")
            ax.add_patch(Rectangle((min(x1, x2), min(y1, y2)), abs(x2 - x1), abs(y2 - y1),
                                   fc="#fff7cc" if r.get("ISSOLID") == "T" else "none", ec=INK, lw=0.9, zorder=2))
            track((x1, y1), (x2, y2))
        elif rt == 8:
            (x, y) = pt(r)
            rx, ry = num(r, "RADIUS"), num(r, "SECONDARYRADIUS", num(r, "RADIUS"))
            ax.add_patch(Ellipse((x, y), 2 * rx, 2 * ry, fc="none", ec=INK, lw=0.9, zorder=3))
        elif rt in (12, 11):
            (x, y) = pt(r)
            rad = num(r, "RADIUS")
            a1, a2 = num(r, "STARTANGLE"), num(r, "ENDANGLE", 360)
            ax.add_patch(Arc((x, y), 2 * rad, 2 * rad, theta1=a1, theta2=a2, ec=INK, lw=0.9, zorder=3))
        elif rt == 2:  # pin
            (x, y) = pt(r)
            ln = num(r, "PINLENGTH")
            orient = int(r.get("PINCONGLOMERATE", "0")) & 3
            dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][orient]
            ax.plot([x, x + dx * ln], [y, y + dy * ln], color=INK, lw=0.9, zorder=3)
            track((x, y), (x + dx * ln, y + dy * ln))
            name = r.get("NAME", "")
            des = r.get("DESIGNATOR", "")
            rot = 90 if orient in (1, 3) else 0
            if name and r.get("PINCONGLOMERATE") is not None and not (int(r["PINCONGLOMERATE"]) & 0x08 == 0 and False):
                ha = {0: "right", 2: "left"}.get(orient, "center")
                va = {1: "top", 3: "bottom"}.get(orient, "center")
                ax.text(x - dx * 3, y - dy * 3, name.replace("\\", ""), fontsize=5.5, ha=ha if rot == 0 else "center",
                        va=va if rot else "center", rotation=rot, color="#333", zorder=4)
            if des:
                ax.text(x + dx * ln / 2, y + dy * ln / 2 + (2 if rot == 0 else 0), des, fontsize=4.5,
                        ha="center", va="bottom", rotation=rot, color="#777", zorder=4)
        elif rt in (4, 34, 41, 25, 32, 33):  # text-ish
            (x, y) = pt(r)
            t = text_of(r)
            if not t or t.startswith("=") or t == "*":
                continue
            if rt == 41 and r.get("NAME", "") not in ("Comment", "Value"):
                continue
            color = {25: LABEL, 32: SHEET, 33: SHEET, 34: "#000"}.get(rt, "#222")
            size = {34: 6.5, 25: 6.5, 32: 7, 33: 6}.get(rt, 6)
            rot = int(r.get("ORIENTATION", "0")) * 90
            ax.text(x, y, t, fontsize=size, color=color, rotation=rot, ha="left", va="bottom", zorder=5,
                    fontweight="bold" if rt in (34, 32) else "normal")
            track((x, y))
        elif rt == 28 or rt == 209:  # text frame / note
            (x1, y1), (x2, y2) = pt(r), pt(r, "CORNER")
            ax.add_patch(Rectangle((min(x1, x2), min(y1, y2)), abs(x2 - x1), abs(y2 - y1), fc="#fffde8", ec="#bba", lw=0.6, zorder=1))
            ax.text(min(x1, x2) + 3, max(y1, y2) - 3, text_of(r), fontsize=6, va="top", zorder=5, wrap=True)
        elif rt == 17:  # power port
            (x, y) = pt(r)
            o = int(r.get("ORIENTATION", "0"))
            dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][o]
            ax.plot([x, x + dx * 10], [y, y + dy * 10], color=INK, lw=1, zorder=3)
            name = r.get("TEXT", "")
            gnd = "GND" in name.upper()
            ex, ey = x + dx * 10, y + dy * 10
            px, py = -dy, dx
            for k, w in enumerate((8, 5, 2) if gnd else (8,)):
                cx, cy = ex + dx * k * 2.5, ey + dy * k * 2.5
                ax.plot([cx - px * w, cx + px * w], [cy - py * w, cy + py * w], color=INK, lw=1.2, zorder=3)
            if not gnd or r.get("SHOWNETNAME") == "T":
                ax.text(ex + dx * 5, ey + dy * 5, name, fontsize=6, color=INK, ha="center", va="center", zorder=5)
            track((x, y), (ex, ey))
        elif rt == 18:  # port
            (x, y) = pt(r)
            w = num(r, "WIDTH", 50)
            h = num(r, "HEIGHT", 10)
            vertical = r.get("STYLE", "0") in ("4", "5", "6", "7")
            if vertical:
                ax.add_patch(Rectangle((x - h / 2, y), h, w, fc="#ffe9a8", ec=PORT, lw=0.8, zorder=4))
                ax.text(x, y + w / 2, r.get("NAME", ""), fontsize=6, rotation=90, ha="center", va="center", zorder=5)
            else:
                ax.add_patch(Rectangle((x, y - h / 2), w, h, fc="#ffe9a8", ec=PORT, lw=0.8, zorder=4))
                ax.text(x + w / 2, y, r.get("NAME", ""), fontsize=6, ha="center", va="center", zorder=5)
            track((x, y), (x + w, y))
        elif rt == 15:  # sheet symbol
            (x, y) = pt(r)
            w, h = num(r, "XSIZE"), num(r, "YSIZE")
            ax.add_patch(Rectangle((x, y - h), w, h, fc="#f1e8fb", ec=SHEET, lw=1.2, zorder=1))
            track((x, y), (x + w, y - h))
        elif rt == 16:  # sheet entry
            try:
                o = body[int(r["OWNERINDEX"])]
            except (KeyError, ValueError, IndexError):
                continue
            (sx, sy) = pt(o)
            w = num(o, "XSIZE")
            dft = num(r, "DISTANCEFROMTOP") * 10
            side = int(r.get("SIDE", "0"))
            ex, ey = (sx, sy - dft) if side == 0 else (sx + w, sy - dft) if side == 1 else (sx + dft, sy)
            ax.plot([ex], [ey], marker="s", ms=3, color=SHEET, zorder=5)
            ax.text(ex + (4 if side == 0 else -4), ey, r.get("NAME", ""), fontsize=5.5, color=SHEET,
                    ha="left" if side == 0 else "right", va="center", zorder=5)
        elif rt == 215:  # harness connector
            (x, y) = pt(r)
            w, h = num(r, "XSIZE"), num(r, "YSIZE")
            ax.add_patch(Rectangle((x, y - h), w, h, fc="#dfe9ff", ec=WIRE, lw=1, zorder=1))
        elif rt == 29:
            ax.add_patch(Circle(pt(r), 2.2, fc=WIRE, ec="none", zorder=6))

    if xs:
        m = 30
        ax.set_xlim(min(xs) - m, max(xs) + m)
        ax.set_ylim(min(ys) - m, max(ys) + m)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"v1 schematic: {os.path.splitext(os.path.basename(path))[0]} (re-drawn from Altium records; approximate)", fontsize=11)
    fig.savefig(outpng, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, "*.SchDoc"))):
        name = os.path.splitext(os.path.basename(f))[0].replace(" ", "-")
        render(f, os.path.join(dst, f"sch-{name}.png"))
        print("wrote", name)
