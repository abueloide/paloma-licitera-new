# -*- coding: utf-8 -*-
"""
Scrapers locales confiables migrados desde PruebaUnoGPT.py
Incluye dependencias mínimas y utilidades necesarias para funcionar de forma independiente.
"""

import re
import requests
from requests.exceptions import SSLError, RequestException
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, timezone
import os
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Config y utilidades ---
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/124 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
PDF_RE  = re.compile(r"\\.pdf($|\\?)", re.I)
CODE_RE = re.compile(r"\\b(?:SPFA|LPN|LP|LPE|LPI|LA|IA|AC|DGAS|SAF|GEP|GESAL|PLEJ|SCEM|SMOV|ADQ|LPNSC|LPLSC|HCES|SACMEX|SOBSE|LES|LO|LPEJ|LPE\\-|DGAP|PJENL|ASCM|LPEF|LPEM)[A-Z0-9/\\-\\._]*\\b", re.I)
MONTHS_SHORT = "ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic"

# --- Red y parseo ---
def fetch(url: str, method: str = "GET", **kw) -> requests.Response:
    kw.setdefault("headers", HEADERS)
    kw.setdefault("timeout", 25)
    try:
        resp = requests.request(method, url, **kw)
        resp.raise_for_status()
        return resp
    except SSLError:
        if url.startswith("https://"):
            url_http = "http://" + url[len("https://"):]
            try:
                resp = requests.request(method, url_http, **kw)
                resp.raise_for_status()
                return resp
            except Exception:
                pass
        kw_loose = dict(kw)
        kw_loose["verify"] = False
        resp = requests.request(method, url, **kw_loose)
        resp.raise_for_status()
        return resp
    except RequestException:
        kw_loose = dict(kw)
        kw_loose["verify"] = False
        resp = requests.request(method, url, **kw_loose)
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

# --- Modelo de salida ---
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

# --- Scrapers especializados migrados ---
def scrape_puebla_conv_obra(since, until) -> List[Item]:
    base = "https://licitaciones.puebla.gob.mx/index.php/obra-publica-1/convocatorias-obra-publica"
    s = soup_of(base)
    items=[]
    for blk in s.select("article, .item-page, .blog, .item, .entry, div, li, p"):
        txt = normspace(blk.get_text(" ", strip=True))
        if not txt: continue
        codes = CODE_RE.findall(txt)
        pdfs = []
        for a in blk.select("a[href]"):
            href = a.get("href","")
            if PDF_RE.search(href):
                href = href if href.startswith("http") else requests.compat.urljoin(base, href)
                pdfs.append(href)
        if not (codes or pdfs): 
            continue
        code  = max(codes, key=len) if codes else None
        title = (code + " - " if code else "") + txt[:180]
        doc   = pdfs[0] if pdfs else None
        if within_range(None, since, until):
            items.append(Item("Puebla/Conv-Obra", "Puebla", code, title, None, base, doc, txt))
    return dedup(items)

def scrape_jalisco_tree(since, until) -> List[Item]:
    url = "https://compras.jalisco.gob.mx/requisition/tree"
    s = soup_of(url)
    items=[]
    for li in s.select("li, .list-group-item, .media, div, a"):
        txt = normspace(li.get_text(" ", strip=True))
        if not txt: continue
        if not (("licit" in txt.lower()) or ("requisición" in txt.lower()) or ("lpn" in txt.lower())):
            continue
        a_tags = li.select("a[href]") if hasattr(li, "select") else []
        if not a_tags: 
            if li.name == "a" and li.has_attr("href"):
                a_tags = [li]
            else:
                continue
        anchors = {normspace(a.get_text() or ""): a["href"] for a in a_tags if a.has_attr("href")}
        vm = anchors.get("Ver más") or anchors.get("Ver mas")
        bs = anchors.get("Bases")
        vm = vm if (vm and vm.startswith("http")) else (requests.compat.urljoin(url, vm) if vm else None)
        bs = bs if (bs and bs.startswith("http")) else (requests.compat.urljoin(url, bs) if bs else None)
        m  = re.search(r"\\b(LPN\\s*\\d+/\\d{4})\\b", txt)
        code = m.group(1) if m else (max(CODE_RE.findall(txt), key=len) if CODE_RE.findall(txt) else None)
        if within_range(None, since, until):
            items.append(Item("Jalisco/Compras-Tree", "Jalisco", code, txt[:220], None, vm or url, bs, txt))
    return dedup(items)

def scrape_cdmx_finanzas(since, until) -> List[Item]:
    base = "https://www.finanzas.cdmx.gob.mx/notificaciones/licitaciones"
    soup = soup_of(base)
    items=[]
    for a in soup.select("a[href]"):
        label = normspace(a.get_text())
        if "licit" in label.lower() or "consolidad" in label.lower() or "nacionales" in label.lower():
            href = a["href"]; href = href if href.startswith("http") else requests.compat.urljoin(base, href)
            items.append(Item("CDMX/Finanzas/Index", "CDMX", None, label, None, base, href, None))
    try:
        consol = "https://www.finanzas.cdmx.gob.mx/notificaciones/licitaciones-consolidadas"
        s2 = soup_of(consol)
        for blk in s2.select("section, article, div"):
            txt = normspace(blk.get_text(" ", strip=True))
            if not txt: continue
            codes = CODE_RE.findall(txt)
            for a in blk.select("a[href]"):
                href = a["href"]; href = href if href.startswith("http") else requests.compat.urljoin(consol, href)
                if "acta" in a.get_text().lower() or "bases" in a.get_text().lower() or PDF_RE.search(href):
                    if within_range(None, since, until):
                        items.append(Item("CDMX/Finanzas/Consolidadas", "CDMX",
                                          max(codes, key=len) if codes else None,
                                          txt[:220], None, consol, href, txt))
    except Exception:
        pass
    return dedup(items)

def scrape_cdmx_salud(since, until) -> List[Item]:
    base = "https://www.salud.cdmx.gob.mx/convocatorias/licitaciones"
    soup = soup_of(base)
    items=[]
    for card in soup.select("article, .card, .views-row, li, div"):
        txt = normspace(card.get_text(" ", strip=True))
        if not txt or ("licitación" not in txt.lower() and not CODE_RE.search(txt)): 
            continue
        title_el = card.find(["h2","h3","h4"])
        title = normspace(title_el.get_text()) if title_el else txt[:120]
        m_date = re.search(r"Vigencia\\s+del\\s+(.+?)\\s+al\\s+(.+)", txt, re.I)
        date = parse_date_any(m_date.group(1)) if m_date else None
        code = max(CODE_RE.findall(txt), key=len) if CODE_RE.findall(txt) else None
        a = card.find("a", href=True)
        href = (a["href"] if a else base)
        href = href if href.startswith("http") else requests.compat.urljoin(base, href)
        if within_range(date, since, until):
            items.append(Item("CDMX/Salud", "CDMX", code, title, date, base, href, txt))
    return dedup(items)

def scrape_veracruz_siop(since, until) -> List[Item]:
    root = "https://www.veracruz.gob.mx/infraestructura/adquisiciones-estatales-2025/"
    s = soup_of(root)
    items=[]
    for blk in s.select("article, .entry, .post, li, p, div"):
        txt = normspace(blk.get_text(" ", strip=True))
        if not txt: continue
        if not ("licit" in txt.lower() or "adquis" in txt.lower() or CODE_RE.search(txt)):
            continue
        pdfs = []
        for a in blk.select("a[href]"):
            href = a["href"]
            href = href if href.startswith("http") else requests.compat.urljoin(root, href)
            if PDF_RE.search(href) or "licit" in href.lower() or "adqui" in href.lower():
                pdfs.append(href)
        if not pdfs and not CODE_RE.search(txt):
            continue
        code = max(CODE_RE.findall(txt), key=len) if CODE_RE.findall(txt) else None
        if within_range(None, since, until):
            items.append(Item("Veracruz/SIOP", "Veracruz", code, txt[:220], None, root, (pdfs[0] if pdfs else None), txt))
    return dedup(items)

# --- Scrapers de noticias relevantes migrados ---
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

def scrape_bcs_compranet(since, until) -> List[Item]:
    url = "http://compranet.bcs.gob.mx/app/portal"
    try:
        s = soup_of(url)
    except Exception:
        s = soup_of("http://compranet.bcs.gob.mx/")
    items=[]
    for a in s.select("a[href]"):
        label = normspace(a.get_text())
        href = a["href"]; href = href if href.startswith("http") else requests.compat.urljoin(url, href)
        if any(k in (label.lower() + href.lower()) for k in ["licit", "convoc", "compras", "portal"]):
            items.append(Item("BCS/CompraNet", "BCS", None, label or "Licitaciones BCS", None, url, href, None))
    return dedup(items)

def scrape_cea_bcs(since, until) -> List[Item]:
    url = "https://cea.bcs.gob.mx/licitaciones/"
    s = soup_of(url)
    items=[]
    for blk in s.select("article, .entry, .post, li, p, div"):
        txt = normspace(blk.get_text(" ", strip=True))
        if not txt: continue
        if not ("licit" in txt.lower() or CODE_RE.search(txt)):
            continue
        pdfs = []
        for a in blk.select("a[href]"):
            href = a["href"]; href = href if href.startswith("http") else requests.compat.urljoin(url, href)
            if PDF_RE.search(href):
                pdfs.append(href)
        code = max(CODE_RE.findall(txt), key=len) if CODE_RE.findall(txt) else None
        title = (code + " - " if code else "") + txt[:180]
        # Agrega un item por cada PDF encontrado, o uno por bloque si no hay PDF
        if pdfs:
            for pdf in pdfs:
                if within_range(None, since, until):
                    items.append(Item("BCS/CEA", "BCS", code, title, None, url, pdf, txt))
        else:
            if within_range(None, since, until):
                items.append(Item("BCS/CEA", "BCS", code, title, None, url, None, txt))
    return dedup(items)

def scrape_ags_estatales(since, until) -> List[Item]:
    url = "https://egobierno2.aguascalientes.gob.mx/servicios/LicitacionesEstatales/ui/dependencia.aspx?i=64"
    s = soup_of(url)
    items=[]
    for a in s.select("a[href]"):
        href = a.get("href","")
        text = normspace(a.get_text(" ", strip=True))
        if not text: continue
        if ("convocatoria" in text.lower() or "licitación" in text.lower() or "les-" in text.lower()):
            code = max(CODE_RE.findall(text), key=len) if CODE_RE.findall(text) else None
            doc = href if href.startswith("http") else requests.compat.urljoin(url, href)
            if within_range(None, since, until):
                items.append(Item("AGS/LicitacionesEstatales", "Aguascalientes", code, text[:220], None, url, doc, text))
    return dedup(items)

# --- Scrapers Playwright para sitios dinámicos ---
# Requiere: pip install playwright && playwright install
from typing import Dict
import asyncio
try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    async_playwright = None

async def scrape_puebla_conv_obra_playwright(since, until, download_dir=None) -> List[Item]:
    """
    Usa Playwright para navegar la página de convocatorias de obra pública de Puebla,
    encontrar los links a PDFs y descargarlos (o extraer datos del PDF si se requiere).
    """
    if not _HAS_PLAYWRIGHT:
        raise ImportError("Debes instalar playwright: pip install playwright && playwright install")
    base = "https://licitaciones.puebla.gob.mx/index.php/obra-publica-1/convocatorias-obra-publica"
    items = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto(base)
        # Espera a que cargue la lista de convocatorias
        await page.wait_for_selector("a[href$='.pdf']")
        links = await page.query_selector_all("a[href$='.pdf']")
        for a in links:
            href = await a.get_attribute("href")
            if not href:
                continue
            pdf_url = href if href.startswith("http") else base.rsplit('/', 1)[0] + '/' + href.lstrip('/')
            title = await a.inner_text()
            # Descarga el PDF si se solicita
            if download_dir:
                download = await page.wait_for_event('download', lambda: a.click())
                path = await download.path()
                await download.save_as(f"{download_dir}/{download.suggested_filename}")
            items.append(Item(
                source="Puebla/Conv-Obra-Playwright",
                jurisdiction="Puebla",
                code=None,
                title=title,
                date=None,
                url=base,
                doc_url=pdf_url,
                raw_text=None
            ))
        await browser.close()
    return items

async def scrape_cdmx_finanzas_playwright(since, until, download_dir=None) -> List[Item]:
    """
    Usa Playwright para navegar la página de licitaciones de Finanzas CDMX,
    encontrar los links a PDFs y descargarlos (o extraer datos del PDF si se requiere).
    """
    if not _HAS_PLAYWRIGHT:
        raise ImportError("Debes instalar playwright: pip install playwright && playwright install")
    base = "https://www.finanzas.cdmx.gob.mx/notificaciones/licitaciones"
    items = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto(base)
        await page.wait_for_selector("a[href$='.pdf']")
        links = await page.query_selector_all("a[href$='.pdf']")
        for a in links:
            href = await a.get_attribute("href")
            if not href:
                continue
            pdf_url = href if href.startswith("http") else base.rsplit('/', 1)[0] + '/' + href.lstrip('/')
            title = await a.inner_text()
            if download_dir:
                download = await page.wait_for_event('download', lambda: a.click())
                path = await download.path()
                await download.save_as(f"{download_dir}/{download.suggested_filename}")
            items.append(Item(
                source="CDMX/Finanzas-Playwright",
                jurisdiction="CDMX",
                code=None,
                title=title,
                date=None,
                url=base,
                doc_url=pdf_url,
                raw_text=None
            ))
        await browser.close()
    return items

# --- Ejemplo de uso Playwright ---
# Para ejecutar desde terminal:
# python -c "import asyncio; from sitios-locales-confiables import scrape_puebla_conv_obra_playwright; asyncio.run(scrape_puebla_conv_obra_playwright('2024-02-01', '2025-08-21', download_dir='descargas/'))"
#
# Si quieres extraer datos del PDF, puedes usar PyPDF2 o pdfplumber después de descargar.

# --- Prueba rápida ---
if __name__ == "__main__":
    # Prueba simple: ejecuta todos los scrapers migrados y guarda salida estructurada
    since = "2024-02-01"
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scrapers = [
        ("puebla_conv_obra", scrape_puebla_conv_obra),
        ("jalisco_tree", scrape_jalisco_tree),
        ("cdmx_finanzas", scrape_cdmx_finanzas),
        ("cdmx_salud", scrape_cdmx_salud),
        ("veracruz_siop", scrape_veracruz_siop),
        ("bcs_compranet", scrape_bcs_compranet),
        ("bcs_cea", scrape_cea_bcs),
        ("ags_estatales", scrape_ags_estatales),
    ]
    all_results = []
    for name, fn in scrapers:
        try:
            items = fn(since, until)
            print(f"[OK] {name}: {len(items)} items")
            for it in items:
                all_results.append({
                    "organismo": it.source,
                    "convocatoria": it.title,
                    "clave": it.code,
                    "descripcion": it.raw_text,
                    "fecha": it.date,
                    "url": it.url,
                    "doc_url": it.doc_url
                })
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
    outdir = "out"
    os.makedirs(outdir, exist_ok=True)
    outfile = os.path.join(outdir, "licitaciones_todas.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON estructurado guardado en {outfile}")
