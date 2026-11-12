"""Search JLCPCB's assembly parts library (the same endpoint as jlcpcb.com/parts) and print stock.

usage: python tools/jlc_search.py [-n N] "keyword" ["keyword" ...]
       python tools/jlc_search.py --codes C59019 C7519 ...      (exact LCSC numbers)

Columns: LCSC code, library (Basic / Pref = preferred extended / Ext), JLC stock, unit price at qty 1 (USD),
model, package, description. Sorted Basic first, then by stock.
"""
import argparse
import json
import sys
import urllib.request

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


def search(keyword, n=8):
    body = json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": max(n, 10)}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return ((data.get("data") or {}).get("componentPageInfo") or {}).get("list") or []


def lib(c):
    if c.get("componentLibraryType") == "base":
        return "Basic"
    return "Pref" if c.get("preferredComponentFlag") else "Ext"


def row(c):
    price = (c.get("componentPrices") or [{}])[0].get("productPrice")
    return (f"{c['componentCode']:<10} {lib(c):<5} {c.get('stockCount', 0):>8} "
            f"{price if price is not None else '-':>8} {c.get('componentModelEn', '')[:28]:<28} "
            f"{(c.get('componentSpecificationEn') or '')[:16]:<16} {(c.get('describe') or '')[:70]}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=6)
    ap.add_argument("--codes", action="store_true", help="treat arguments as exact LCSC codes")
    ap.add_argument("terms", nargs="+")
    a = ap.parse_args()
    for t in a.terms:
        res = search(t, a.n)
        if a.codes:
            res = [c for c in res if c["componentCode"] == t]
        res.sort(key=lambda c: (lib(c) != "Basic", lib(c) != "Pref", -(c.get("stockCount") or 0)))
        print(f"== {t}")
        for c in res[: a.n]:
            print("  " + row(c))
        if not res:
            print("  (no results)")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
