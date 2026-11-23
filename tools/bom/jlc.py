"""JLCPCB's assembly parts library: the search endpoint behind jlcpcb.com/parts (no key needed)."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


@dataclass(frozen=True)
class Component:
    lcsc: str
    model: str
    brand: str
    package: str
    category: str
    library: str          # "Basic", "Preferred" or "Extended": Extended parts cost a loading fee per order
    stock: int
    attrition: int        # JLC's extra parts per order ("lossNumber")
    price: float          # unit price at the smallest quantity, USD
    attributes: dict[str, str]
    describe: str

    @classmethod
    def from_api(cls, c: dict) -> "Component":
        lib = "Basic" if c.get("componentLibraryType") == "base" else (
            "Preferred" if c.get("preferredComponentFlag") else "Extended")
        prices = c.get("componentPrices") or [{}]
        return cls(
            lcsc=c["componentCode"], model=c.get("componentModelEn") or "", brand=c.get("componentBrandEn") or "",
            package=c.get("componentSpecificationEn") or "", category=c.get("firstSortName") or "",
            library=lib, stock=int(c.get("stockCount") or 0), attrition=int(c.get("lossNumber") or 0),
            price=float(prices[0].get("productPrice") or 0),
            attributes={a["attribute_name_en"].strip(): a["attribute_value_name"]
                        for a in c.get("attributes") or [] if a.get("attribute_value_name") not in (None, "-")},
            describe=c.get("describe") or "")


class Jlc:
    def __init__(self):
        self._cache: dict[str, list[Component]] = {}

    def search(self, keyword: str, pages: int = 1, page_size: int = 100, in_stock: bool = False,
               basic_only: bool = False) -> list[Component]:
        key = f"{keyword}|{pages}|{page_size}|{in_stock}|{basic_only}"
        if key not in self._cache:
            out: list[Component] = []
            for page in range(1, pages + 1):
                body = {"keyword": keyword, "currentPage": page, "pageSize": page_size}
                if in_stock:
                    body["stockFlag"] = True
                if basic_only:
                    body["componentLibraryType"] = "base"
                found = _post(body)
                out += [Component.from_api(c) for c in found]
                if len(found) < page_size:
                    break
            self._cache[key] = out
        return self._cache[key]

    def part(self, lcsc: str) -> Component | None:
        return next((c for c in self.search(lcsc, page_size=10) if c.lcsc == lcsc), None)


def _post(body: dict) -> list[dict]:
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("code") not in (200, None):
        raise RuntimeError(f"JLC search failed: {data.get('code')} {data.get('message')}")
    return ((data.get("data") or {}).get("componentPageInfo") or {}).get("list") or []
