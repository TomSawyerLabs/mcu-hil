import sys, olefile, re, glob, os
RT = {1:"COMP",2:"PIN",4:"LABEL",17:"PWRPORT",18:"PORT",15:"SHEETSYM",16:"SHEETENTRY",25:"NETLABEL",28:"TEXTFRAME",31:"SHEETINFO",32:"SHEETNAME",33:"SHEETFILE",34:"DESIGNATOR",41:"PARAM",209:"NOTE",215:"HARNESSCONN",216:"HARNESSENTRY",217:"HARNESSTYPE",218:"SIGNALHARNESS",27:"WIRE",45:"IMPL",44:"IMPLLIST",22:"NOERC",26:"BUS",37:"BUSENTRY",29:"JUNCTION",13:"LINE",14:"RECT",6:"POLYLINE",7:"POLYGON",10:"RRECT",12:"ARC",8:"ELLIPSE",11:"ELLIPARC",30:"IMAGE",39:"TEMPLATE",43:"WARNSIGN",46:"IMPL_PINLIST"}
def records(path):
    ole = olefile.OleFileIO(path)
    data = ole.openstream("FileHeader").read()
    i = 0; out=[]
    while i + 4 <= len(data):
        ln = int.from_bytes(data[i:i+3], "little"); typ = data[i+3]; i += 4
        body = data[i:i+ln]; i += ln
        if typ != 0: out.append({"_bin":True}); continue
        s = body.rstrip(b"\0").decode("latin1")
        d = {}
        for kv in s.split("|"):
            if "=" in kv:
                k, v = kv.split("=", 1); d[k.upper()] = v
        out.append(d)
    return out
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.SchDoc"))):
    print("=" * 20, os.path.basename(f))
    recs = records(f)
    comps = {}
    for idx, r in enumerate(recs[1:]):
        rt = int(r.get("RECORD", -1)) if r.get("RECORD","").lstrip("-").isdigit() else -1
        own = r.get("OWNERINDEX")
        name = RT.get(rt, str(rt))
        if rt == 1:
            comps[idx] = r
            print(f"COMP {r.get('LIBREFERENCE')} | {r.get('COMPONENTDESCRIPTION','')}")
        elif rt == 34:
            print(f"   designator {r.get('TEXT')}")
        elif rt == 41 and own is not None and r.get("NAME","").lower() in ("comment","value","manufacturer part number","manufacturer","lcsc","supplier part number 1","mpn","part number","supplier 1"):
            print(f"   {r.get('NAME')}={r.get('TEXT')}")
        elif rt in (4, 28, 209):
            t = r.get("TEXT","")
            if t and not t.startswith("="): print(f"{name}: {t!r}")
        elif rt in (17, 18, 25, 32, 33, 16, 215, 216, 217):
            print(f"{name}: {r.get('TEXT') or r.get('NAME')} {('harness='+r['HARNESSTYPE']) if 'HARNESSTYPE' in r else ''} {('io='+r['IOTYPE']) if 'IOTYPE' in r else ''}")
