import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find, first
b = parse(open(sys.argv[1], encoding="utf8").read())
out = []
for fp in find(b, "footprint"):
    ref = next((p[2] for p in find(fp, "property") if p[1] == "Reference"), "")
    at = first(fp, "at")
    for pad in find(fp, "pad"):
        dr = first(pad, "drill")
        if not dr: continue
        sz = first(pad, "size")
        out.append(dict(ref=ref, num=pad[1], type=pad[2], shape=pad[3], drill=dr[1:], size=sz[1:] if sz else None))
for o in out: print(o["ref"] or "(none)", o["num"] or "''", o["type"], o["shape"], "drill", " ".join(map(str, o["drill"])), "size", o["size"])
# board-level holes outside footprints?
print("vias", len(find(b, "via")))
