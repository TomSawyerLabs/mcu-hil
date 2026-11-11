import sys, olefile, struct, json
o = olefile.OleFileIO(sys.argv[1])
U = 2.54e-6  # Altium internal unit (1e-4 mil) -> mm
def textrecs(name):
    d = o.openstream(name).read(); i = 0; out = []
    while i + 4 <= len(d):
        ln = struct.unpack_from("<I", d, i)[0]; i += 4
        s = d[i:i+ln].rstrip(b"\0").decode("latin1"); i += ln
        out.append(dict(kv.split("=",1) for kv in s.split("|") if "=" in kv))
    return out
comps = textrecs("Components6/Data")
des = [c.get("SOURCEDESIGNATOR","?") for c in comps]
d = o.openstream("Pads6/Data").read(); i = 0; pads = []
def sub():
    global i
    ln = struct.unpack_from("<I", d, i)[0]; i += 4; st = i; i += ln; return st, ln
while i < len(d):
    rt = d[i]; i += 1; assert rt == 2, (rt, i)
    st, ln = sub(); name = d[st+1:st+1+d[st]].decode("latin1")
    for _ in range(3): sub()
    st, ln = sub(); p = st
    layer = d[p]; p += 1; flags1 = d[p]; flags2 = d[p+1]; p += 2
    net = struct.unpack_from("<H", d, p)[0]; p += 4
    comp = struct.unpack_from("<H", d, p)[0]; p += 6
    x, y, tx, ty, mx, my, bx, by, hole = struct.unpack_from("<9i", d, p); p += 36
    ts, ms, bs = d[p], d[p+1], d[p+2]; p += 3
    direction = struct.unpack_from("<d", d, p)[0]; p += 8
    plated = d[p] != 0
    st6, ln6 = sub(); holeshape = 0; slot = 0; slotrot = 0
    if ln6 >= 596:
        q = st6 + 29*4*2 + 29 + 1
        holeshape = d[q]; slot = struct.unpack_from("<i", d, q+1)[0]; slotrot = struct.unpack_from("<d", d, q+5)[0]
    pads.append(dict(comp=des[comp] if comp < len(des) else None, name=name, layer=layer, x=x*U, y=y*U,
        size=(round(tx*U,3), round(ty*U,3)), hole=round(hole*U,3), plated=plated, shape=ts,
        holeshape=["round","square","slot"][holeshape] if holeshape < 3 else holeshape, slot=round(slot*U,3), slotrot=slotrot, dir=direction))
th = [p for p in pads if p["hole"] > 0]
print("pads total", len(pads), "with holes", len(th))
for p in th:
    print(f'{p["comp"] or "(free)":6} {p["name"]:6} hole={p["hole"]} {p["holeshape"]}{" slot="+str(p["slot"])+" rot="+str(p["slotrot"]) if p["holeshape"]=="slot" else ""} plated={p["plated"]} pad={p["size"]} shape={p["shape"]}')
json.dump(pads, open(sys.argv[2], "w"), indent=0)
