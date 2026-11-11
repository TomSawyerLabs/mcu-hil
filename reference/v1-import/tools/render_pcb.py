"""Render a .kicad_pcb to PNGs with matplotlib, reading the file as text (no KiCad runtime).

usage: python -I render_pcb.py board.kicad_pcb out_prefix   ->  out_prefix-top.png, out_prefix-bottom.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, first, parse  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402

F = float
COL = {"F.Cu": "#c83434", "B.Cu": "#4d7fc4", "F.SilkS": "#f2eda1", "B.SilkS": "#e8b2a7", "Edge.Cuts": "#d0d2cd"}


def lay(n):
    node = first(n, "layer")
    return node[1] if node else None


def xf(fpat, x, y):
    """Footprint-local -> board coordinates (KiCad: y down, angle CCW as seen)."""
    fx, fy = F(fpat[1]), F(fpat[2])
    a = math.radians(F(fpat[3])) if len(fpat) > 3 else 0.0
    return fx + x * math.cos(a) + y * math.sin(a), fy - x * math.sin(a) + y * math.cos(a)


def arc_points(p1, p2, p3, n=40):
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return [p1, p3]
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1, a2, a3 = (math.atan2(y - uy, x - ux) for x, y in (p1, p2, p3))
    tau = 2 * math.pi
    span = (a3 - a1) % tau if (a2 - a1) % tau < (a3 - a1) % tau else -((a1 - a3) % tau)
    return [(ux + r * math.cos(a1 + span * i / n), uy + r * math.sin(a1 + span * i / n)) for i in range(n + 1)]


def render(board, side, path, title):
    cu, silk = side + ".Cu", side + ".SilkS"
    other = ("B" if side == "F" else "F") + ".Cu"
    fig, ax = plt.subplots(figsize=(13, 11), dpi=150)
    bg = "#001023"
    ax.set_facecolor(bg)
    fig.patch.set_facecolor(bg)

    def line(pts, color, lw, z):
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, solid_capstyle="round", zorder=z)

    def geom(n, frame=None):
        t = (lambda p: xf(frame, *p)) if frame else (lambda p: p)
        if n[0].endswith("_line") or n[0] == "segment":
            return [t((F(first(n, "start")[1]), F(first(n, "start")[2]))), t((F(first(n, "end")[1]), F(first(n, "end")[2])))]
        if n[0].endswith("_arc") or n[0] == "arc":
            return arc_points(*[t((F(first(n, k)[1]), F(first(n, k)[2]))) for k in ("start", "mid", "end")])
        return None

    for z in find(board, "zone"):
        for fpoly in find(z, "filled_polygon"):
            if lay(fpoly) not in (cu, other):
                continue
            pts = [(F(p[1]), F(p[2])) for p in first(fpoly, "pts")[1:] if p[0] == "xy"]
            mine = lay(fpoly) == cu
            ax.add_patch(Polygon(pts, closed=True, fc=COL[lay(fpoly)], ec="none", alpha=0.35 if mine else 0.07, zorder=1 if mine else 0))

    for t in find(board, "segment") + find(board, "arc"):
        if lay(t) not in (cu, other):
            continue
        mine = lay(t) == cu
        w = F(first(t, "width")[1]) * 72 / 25.4 * 1.6  # mm -> pt at this figure scale (approx)
        line(geom(t), matplotlib.colors.to_rgba(COL[lay(t)], 1 if mine else 0.18), max(w, 0.3), 3 if mine else 0.5)

    for g in board:
        if isinstance(g, list) and g and g[0] in ("gr_line", "gr_arc") and lay(g) in ("Edge.Cuts", silk):
            line(geom(g), COL[lay(g)], 1.2, 6)

    for fp in find(board, "footprint"):
        at = first(fp, "at")
        for g in fp:
            if not (isinstance(g, list) and g and g[0].startswith("fp_")) or lay(g) not in (silk, "Edge.Cuts"):
                continue
            c = COL[lay(g)]
            if g[0] in ("fp_line", "fp_arc"):
                line(geom(g, at), c, 0.8, 6)
            elif g[0] == "fp_circle":
                ce, e = first(g, "center"), first(g, "end")
                r = math.hypot(F(e[1]) - F(ce[1]), F(e[2]) - F(ce[2]))
                ax.add_patch(Circle(xf(at, F(ce[1]), F(ce[2])), r, fill=False, ec=c, lw=0.8, zorder=6))
            elif g[0] == "fp_poly":
                pts = [xf(at, F(p[1]), F(p[2])) for p in first(g, "pts")[1:] if p[0] == "xy"]
                ax.add_patch(Polygon(pts, closed=True, fill=False, ec=c, lw=0.8, zorder=6))
        for pad in find(fp, "pad"):
            layers = first(pad, "layers")[1:]
            if cu not in layers and "*.Cu" not in layers:
                continue
            pa, sz = first(pad, "at"), first(pad, "size")
            px, py = xf(at, F(pa[1]), F(pa[2]))
            w, h = F(sz[1]), F(sz[2])
            ang = F(pa[3]) if len(pa) > 3 else 0.0
            tr = Affine2D().rotate_deg_around(px, py, -ang) + ax.transData
            c = "#202020" if pad[2] == "np_thru_hole" else "#d4af37"
            if w > 0 and h > 0:
                if pad[3] == "circle":
                    ax.add_patch(Circle((px, py), w / 2, fc=c, ec="none", zorder=7))
                elif pad[3] in ("oval", "roundrect"):
                    r = min(w, h) / 2 if pad[3] == "oval" else min(w, h) * 0.25
                    ax.add_patch(FancyBboxPatch((px - w / 2 + r, py - h / 2 + r), w - 2 * r, h - 2 * r,
                                                boxstyle=f"round,pad={r}", fc=c, ec="none", zorder=7, transform=tr))
                else:
                    ax.add_patch(Rectangle((px - w / 2, py - h / 2), w, h, fc=c, ec="none", zorder=7, transform=tr))
            dr = first(pad, "drill")
            if dr:
                if dr[1] == "oval":
                    dw, dh = F(dr[2]), F(dr[3])
                    r = min(dw, dh) / 2
                    ax.add_patch(FancyBboxPatch((px - dw / 2 + r, py - dh / 2 + r), dw - 2 * r, dh - 2 * r,
                                                boxstyle=f"round,pad={r}", fc="#050505", ec="#999", lw=0.4, zorder=8, transform=tr))
                else:
                    ax.add_patch(Circle((px, py), F(dr[1]) / 2, fc="#050505",
                                        ec="#999" if pad[2] == "np_thru_hole" else "none", lw=0.4, zorder=8))
        ref = next((p for p in find(fp, "property") if p[1] == "Reference"), None)
        if ref and ref[2] and lay(fp) == cu:
            ax.text(F(at[1]), F(at[2]), ref[2], color="white", fontsize=7, ha="center", va="center",
                    zorder=10, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.1", fc=(0, 0, 0, 0.55), ec="none"))

    for v in find(board, "via"):
        a, s, d = first(v, "at"), first(v, "size"), first(v, "drill")
        ax.add_patch(Circle((F(a[1]), F(a[2])), F(s[1]) / 2, fc="#c0c0c0", ec="none", zorder=9))
        ax.add_patch(Circle((F(a[1]), F(a[2])), F(d[1]) / 2, fc="#050505", ec="none", zorder=9))

    edge = [p for g in board if isinstance(g, list) and g and g[0] in ("gr_line", "gr_arc") and lay(g) == "Edge.Cuts"
            for p in geom(g)]
    xs, ys = [p[0] for p in edge], [p[1] for p in edge]
    m = 2
    ax.set_aspect("equal")
    ax.set_xlim((max(xs) + m, min(xs) - m) if side == "B" else (min(xs) - m, max(xs) + m))
    ax.set_ylim(max(ys) + m, min(ys) - m)
    ax.axis("off")
    ax.set_title(title, color="white", fontsize=14)
    fig.savefig(path, bbox_inches="tight", facecolor=bg)
    plt.close(fig)


if __name__ == "__main__":
    brd = parse(open(sys.argv[1], encoding="utf8").read())
    render(brd, "F", sys.argv[2] + "-top.png", "v1 AVR Test HAT: top side")
    render(brd, "B", sys.argv[2] + "-bottom.png", "v1 AVR Test HAT: bottom side (seen from below, mirrored)")
