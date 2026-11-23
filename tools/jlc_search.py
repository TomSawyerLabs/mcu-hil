"""Search JLCPCB's assembly parts library (the same endpoint as jlcpcb.com/parts) and print stock.

usage: python tools/jlc_search.py [-n N] "keyword" ["keyword" ...]
       python tools/jlc_search.py --codes C59019 C7519 ...      (exact LCSC numbers)

Columns: LCSC code, library (Basic / Pref = preferred extended / Ext), JLC stock, unit price at qty 1 (USD),
model, package, description. Sorted Basic first, then by stock.
"""
import argparse
import sys

from bom.jlc import Jlc

SHORT = {"Basic": "Basic", "Preferred": "Pref", "Extended": "Ext"}


def row(c):
    return (f"{c.lcsc:<10} {SHORT[c.library]:<5} {c.stock:>8} {c.price:>8} {c.model[:28]:<28} "
            f"{c.package[:16]:<16} {c.describe[:70]}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=6)
    ap.add_argument("--codes", action="store_true", help="treat arguments as exact LCSC codes")
    ap.add_argument("terms", nargs="+")
    a = ap.parse_args()
    jlc = Jlc()
    for t in a.terms:
        res = jlc.search(t, page_size=max(a.n, 10))
        if a.codes:
            res = [c for c in res if c.lcsc == t]
        res.sort(key=lambda c: (c.library != "Basic", c.library != "Preferred", -c.stock))
        print(f"== {t}")
        for c in res[: a.n]:
            print("  " + row(c))
        if not res:
            print("  (no results)")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
