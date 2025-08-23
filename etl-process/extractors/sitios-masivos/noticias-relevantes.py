# -*- coding: utf-8 -*-
"""
Scrapers de noticias relevantes migrados desde sitios-locales-confiables.py
Incluye utilidades mínimas y dependencias necesarias.
"""
import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
PDF_RE  = re.compile(r"\\.pdf($|\\?)", re.I)
MONTHS_SHORT = "ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic"

def fetch(url: str, method: str = "GET", **kw) -> requests.Response:
    kw.setdefault("headers", HEADERS)
    kw.setdefault("timeout", 25)
    resp = requests.request(method, url, **kw)
    resp.raise_for_status()
    return resp

def soup_of(url: str, **kw) -> BeautifulSoup:
    r = fetch(url, **kw)
    return BeautifulSoup(r.text, "lxml")

def normspace(s: str) -> str:
    return re.sub(r"\\s+", " ", (s or "").strip())

def parse_date_any(s: str) -> Optional[str]:
    if not s:
        return None
    txt = s.strip().lower()
    m = re.search(r"\\b(\\d{1,2})/(\\d{1,2})/(\\d{4})\\b", txt)
    if m:
        d, mth, y = map(int, m.groups())
        if 1 <= mth <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mth:02d}-{d:02d}"
    MONTH_MAP = {
        'ene':1,'enero':1,'feb':2,'febrero':2,'mar':3,'marzo':3,'abr':4,'abril':4,
        'may':5,'mayo':5,'jun':6,'junio':6,'jul':7,'julio':7,'ago':8,'agosto':8,
        'sep':9,'sept':9,'septiembre':9,'oct':10,'octubre':10,'nov':11,'noviembre':11,
        'dic':12,'diciembre':12
    }
    m2 = re.search(r"\\b(\\d{1,2})\\s+([a-záéíóú]+)\\s+(\\d{4})\\b", txt)
    if m2:
        d = int(m2.group(1))
        mon_word = m2.group(2)[:4] if m2.group(2).startswith('sept') else m2.group(2)
        mon_word = mon_word.strip('.').lower()
        mon = MONTH_MAP.get(mon_word)
        if mon:
            y = int(m2.group(3))
            if 1 <= d <= 31:
                return f"{y:04d}-{mon:02d}-{d:02d}"
    return None

def within_range(date_str: Optional[str], since: str, until: str) -> bool:
    if not date_str:
        return True
    return since <= date_str <= until

@dataclass
class Item:
    source: str
    jurisdiction: str
    code: Optional[str]
    title: str
    date: Optional[str]
    url: str
    doc_url: Optional[str]
    raw_text: Optional[str]

def dedup(items: List[Item]) -> List[Item]:
    seen=set(); out=[]
    for it in items:
        k = (it.source, it.code, it.doc_url or it.url)
        if k in seen: continue
        seen.add(k); out.append(it)
    return out

def scrape_eluniversal_tag(since, until) -> List[Item]:
    base = "https://www.eluniversal.com.mx/tag/licitaciones/"
    items=[]; next_url = base
    for _ in range(9):
        s = soup_of(next_url)
        for art in s.select("article a[href], .c-article a[href], .c-list__item a[href], a[href]"):
            href = art["href"]
            if not href.startswith("http"): 
                href = requests.compat.urljoin(base, href)
            title = normspace(art.get_text())
            if not title or len(title) < 20: 
                continue
            parent = art.find_parent()
            date = None
            if parent:
                around = normspace(parent.get_text(" ", strip=True))
                m = re.search(r"\\b(\\d{2}/\\d{2}/\\d{4})\\b", around)
                if m: date = parse_date_any(m.group(1))
            if "licit" in title.lower() or "/licit" in href:
                if within_range(date, since, until):
                    items.append(Item("ElUniversal/Tag", "Nacional", None, title, date, href, None, None))
        nxt = s.find("a", string=re.compile("siguiente", re.I))
        if not nxt: break
        next_url = requests.compat.urljoin(base, nxt.get("href"))
    return dedup(items)

def scrape_elsiglo_obras(since, until) -> List[Item]:
    url = "https://www.elsiglodetorreon.com.mx/noticias/obras-publicas.html"
    s = soup_of(url)
    items=[]
    for c in s.select("article, .c-article, .c-list__item, li, div"):
        title_el = c.find(["h2","h3","a"])
        if not title_el: continue
        title = normspace(title_el.get_text())
        if not title: continue
        text = normspace(c.get_text(" ", strip=True))
        m = re.search(r"\\b(\\d{1,2}\\s+(?:%s)\\s+\\d{4})\\b" % MONTHS_SHORT, text, re.I)
        date = parse_date_any(m.group(1)) if m else None
        a = title_el if title_el.name=="a" else c.find("a", href=True)
        href = a["href"] if (a and a.has_attr("href")) else url
        if not href.startswith("http"): href = requests.compat.urljoin(url, href)
        if within_range(date, since, until):
            items.append(Item("ElSiglo/ObrasPublicas", "Coahuila-Dgo", None, title, date, href, None, None))
    return dedup(items)

if __name__ == "__main__":
    since = "2024-02-01"
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scrapers = [
        ("eluniversal_tag", scrape_eluniversal_tag),
        ("elsiglo_obras", scrape_elsiglo_obras),
    ]
    for name, fn in scrapers:
        try:
            items = fn(since, until)
            print(f"[OK] {name}: {len(items)} items")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
