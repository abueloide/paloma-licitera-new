#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper unificado para TODOS los sitios solicitados (cámaras, medios, periódicos,
estatales/municipales de licitaciones). Sin dummies: solo devuelve lo que el HTML
expone realmente. Incluye:
- Modo confirmación (--confirm-only) o límite por sitio (--max-per-source N)
- Fallback SSL (https -> http) ante SSLError
- Scrapers especializados para portales clave
- Scraper genérico heurístico para el resto (palabras clave + PDFs)

Salida homogénea (JSONL/CSV):
  {"source","jurisdiction","code","title","date","url","doc_url","raw_text"}
"""

import re, os, sys, json, argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Callable, Optional, Iterable, Tuple
from datetime import datetime, timezone

import requests
from requests.exceptions import SSLError, RequestException
from bs4 import BeautifulSoup
 # Tenacity es opcional; si no está instalado, usamos un backoff simple
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    _HAS_TENACITY = True
except Exception:
    _HAS_TENACITY = False
    import time
    def retry(func=None, *, stop=None, wait=None, retry=None):
        """Decorador de reintentos mínimo (4 intentos, backoff exponencial 1->2->4->8s)."""
        def decorator(f):
            def wrapped(*args, **kwargs):
                attempts = 4
                delay = 1.0
                for i in range(attempts):
                    try:
                        return f(*args, **kwargs)
                    except requests.exceptions.RequestException:
                        if i == attempts - 1:
                            raise
                        time.sleep(delay)
                        delay = delay * 2 if delay < 8 else 8
            return wrapped
        return decorator if func is None else decorator(func)
    def stop_after_attempt(n):
        return None
    def wait_exponential(multiplier=1, min=1, max=8):
        return None
    def retry_if_exception_type(types):
        return None
 # dateparser es opcional; si no está, usamos un parser básico para ES
try:
    import dateparser as _dateparser
    _HAS_DATEPARSER = True
except Exception:
    _HAS_DATEPARSER = False
    _dateparser = None
try:
    import pandas as pd
    _HAS_PANDAS = True
except Exception:
    _HAS_PANDAS = False
    pd = None
    import csv

# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}

DEFAULT_SINCE = "2024-02-01"
DEFAULT_UNTIL = datetime.now(timezone.utc).strftime("%Y-%m-%d")

DATEPARSER_KW = {"languages": ["es", "en"], "settings": {"DATE_ORDER": "DMY"}}

PDF_RE  = re.compile(r"\.pdf($|\?)", re.I)
# Conjuntos de códigos usuales en MX
CODE_RE = re.compile(
    r"\b(?:SPFA|LPN|LP|LPE|LPI|LA|IA|AC|DGAS|SAF|GEP|GESAL|PLEJ|SCEM|SMOV|ADQ|"
    r"LPNSC|LPLSC|HCES|SACMEX|SOBSE|LES|LO|LPEJ|LPE\-|DGAP|PJENL|ASCM|LPEF|LPEM)[A-Z0-9/\-\._]*\b",
    re.I
)
MONTHS_SHORT = "ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic"

# Regex para montos (pesos, millones, etc)
AMOUNT_RE = re.compile(r"(\$\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\$\s?\d+(?:[.,]\d{2})?\s*(?:mxn|m\.n\.)?|\b\d+(?:[.,]\d{3})*(?:[.,]\d{2})?\s*(?:mdp|millones)\b)", re.I)

BASE_KEYWORDS = ["licit", "convoc", "obra", "adquis", "contrat", "bases", "acta", "obras públicas", "licitación"]

# ---------------------------------------------------------
# Utilidades de red / parseo
# ---------------------------------------------------------

class HardFail(Exception): ...
class NotFound(Exception): ...

@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=8),
       retry=retry_if_exception_type((RequestException,)))
def _fetch(url: str, method: str = "GET", **kw) -> requests.Response:
    kw.setdefault("headers", HEADERS)
    kw.setdefault("timeout", 25)
    resp = requests.request(method, url, **kw)
    resp.raise_for_status()
    return resp

def fetch(url: str, method: str = "GET", **kw) -> requests.Response:
    """
    Fetch robusto:
    1) intenta tal cual (https con verify=True)
    2) si hay SSLError y es https:// -> reintenta en http://
    3) si sigue fallando (o si no era https), último intento con verify=False
    4) si hay otros RequestException, intenta verify=False como último recurso
    """
    try:
        return _fetch(url, method=method, **kw)
    except SSLError:
        if url.startswith("https://"):
            url_http = "http://" + url[len("https://"):]
            try:
                return _fetch(url_http, method=method, **kw)
            except Exception:
                pass
        kw_loose = dict(kw)
        kw_loose["verify"] = False
        return _fetch(url, method=method, **kw_loose)
    except RequestException:
        kw_loose = dict(kw)
        kw_loose["verify"] = False
        return _fetch(url, method=method, **kw_loose)

def soup_of(url: str, **kw) -> BeautifulSoup:
    r = fetch(url, **kw)
    return BeautifulSoup(r.text, "lxml")

def normspace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

# Extraer monto de texto (si lo hay, sin inventar)
def extract_amount(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = AMOUNT_RE.search(text)
    return m.group(1).strip() if m else None

def parse_date_any(s: str) -> Optional[str]:
    if not s:
        return None
    if _HAS_DATEPARSER:
        dt = _dateparser.parse(s, **DATEPARSER_KW)
        return dt.strftime("%Y-%m-%d") if dt else None
    # Fallback manual sin dateparser
    txt = s.strip().lower()
    # 1) dd/mm/yyyy
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", txt)
    if m:
        d, mth, y = map(int, m.groups())
        if 1 <= mth <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mth:02d}-{d:02d}"
    # 2) d mes yyyy (ene, enero, feb, febrero, ...)
    MONTH_MAP = {
        'ene':1,'enero':1,'feb':2,'febrero':2,'mar':3,'marzo':3,'abr':4,'abril':4,
        'may':5,'mayo':5,'jun':6,'junio':6,'jul':7,'julio':7,'ago':8,'agosto':8,
        'sep':9,'sept':9,'septiembre':9,'oct':10,'octubre':10,'nov':11,'noviembre':11,
        'dic':12,'diciembre':12
    }
    m2 = re.search(r"\b(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})\b", txt)
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

# ---------------------------------------------------------
# Modelo de salida
# ---------------------------------------------------------

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

def emit(items: Iterable[Item], out_jsonl: Optional[str], out_csv: Optional[str]):
    rows = [asdict(x) for x in items]
    if out_jsonl:
        out_dir = os.path.dirname(out_jsonl)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(out_jsonl, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if out_csv:
        out_dir = os.path.dirname(out_csv)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        if _HAS_PANDAS:
            pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8")
        else:
            # Fallback sin pandas
            fieldnames = ["source","jurisdiction","code","title","date","url","doc_url","raw_text"]
            with open(out_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow({k: (r.get(k) if r.get(k) is not None else "") for k in fieldnames})

def dedup(items: List[Item]) -> List[Item]:
    seen=set(); out=[]
    for it in items:
        k = (it.source, it.code, it.doc_url or it.url)
        if k in seen: continue
        seen.add(k); out.append(it)
    return out

# ---------------------------------------------------------
# Scrapers especializados (mejor señal por sitio)
# ---------------------------------------------------------

# (Eliminados: puebla_conv_obra, jalisco_tree, cdmx_finanzas, cdmx_salud, veracruz_siop, eluniversal_tag, elsiglo_obras, bcs_compranet, bcs_cea, ags_estatales)

# ---------------------------------------------------------
# Scraper genérico
# ---------------------------------------------------------

def generic_scrape(url: str, source_name: str, jurisdiction: str,
                   since: str, until: str, keywords: Optional[List[str]] = None) -> List[Item]:
    """
    Heurístico simple y robusto:
    - Lee la página
    - Busca <a> cuyo texto o href contenga palabras clave o PDFs
    - Extrae (code|title|date) si se ve en texto cercano
    """
    kwords = [k.lower() for k in (keywords or BASE_KEYWORDS)]
    s = soup_of(url)
    items=[]
    anchors = s.select("a[href]")
    for a in anchors:
        href = a.get("href","")
        label = normspace(a.get_text(" ", strip=True))
        if not href: 
            continue
        href_full = href if href.startswith("http") else requests.compat.urljoin(url, href)
        test_text = (label + " " + href).lower()
        if any(kw in test_text for kw in kwords) or PDF_RE.search(href):
            # fecha aproximada en el contenedor
            date = None
            parent = a.find_parent()
            if parent:
                around = normspace(parent.get_text(" ", strip=True))
                # fechas dd/mm/yyyy o "19 jul 2025"
                m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", around)
                if m:
                    date = parse_date_any(m.group(1))
                else:
                    m2 = re.search(r"\b(\d{1,2}\s+(?:%s)\s+\d{4})\b" % MONTHS_SHORT, around, re.I)
                    date = parse_date_any(m2.group(1)) if m2 else None
            code = max(CODE_RE.findall(label), key=len) if CODE_RE.findall(label) else None
            title = label if label else href_full
            if within_range(date, since, until):
                items.append(Item(source_name, jurisdiction, code, title[:220], date, url, href_full, None))
    return dedup(items)

# ---------------------------------------------------------
# Registro de fuentes
# ---------------------------------------------------------

# Mapa de sitios con scraper especializado (id -> función)
SPECIALIZED: Dict[str, Callable[[str, str], List[Item]]] = {
    # ...otros scrapers especializados si los hay...
}

# Sitios genéricos (id, jurisdicción, url, [keywords opcionales])
GENERIC_SITES: List[Tuple[str, str, str, List[str]]] = [
    # Cámaras de construcción
    ("cmic_nacional", "Nacional", "https://www.cmic.org/", ["observatorio","licit","convoc"]),
    ("cmic_edomex", "Edomex", "https://cmicedomex.com.mx/", ["licit","convoc","obra"]),
    ("cmic_cdmx", "CDMX", "https://cmiccdmx.org/", ["licit","convoc","obra"]),
    ("cmic_nuevoleon", "Nuevo León", "https://www.cmicnuevoleon.com/", ["licit","convoc","obra"]),
    ("cmic_tamaulipas", "Tamaulipas", "https://cmictamaulipas.org.mx/", ["licit","convoc","obra"]),
    # Revistas especializadas
    ("inmobiliare", "Nacional", "https://inmobiliare.com/", ["licit","convoc","obra","constru"]),
    ("obras_expansion", "Nacional", "https://obras.expansion.mx/", ["licit","convoc","obra","infra"]),
    ("t21", "Nacional", "https://t21.com.mx/", ["licit","convoc","aduana","logística","infra"]),
    # Periódicos confirmados
    ("elfinanciero", "Nacional", "https://www.elfinanciero.com.mx/", ["licit","convoc","obra","contrat"]),
    ("milenio", "Nacional", "https://www.milenio.com/", ["licit","convoc","obra","contrat"]),
    # Periódicos regionales
    ("eldiariodechihuahua", "Chihuahua", "https://www.eldiariodechihuahua.mx/", ["licit","convoc","obra"]),
    ("elimparcial", "Baja California", "https://www.elimparcial.com/", ["licit","convoc","obra"]),
    ("diariodequeretaro", "Querétaro", "https://www.diariodequeretaro.com.mx/", ["licit","convoc","obra"]),
    ("eloccidental", "Jalisco", "https://www.eloccidental.com.mx/", ["licit","convoc","obra"]),
    ("lavozdemichoacan", "Michoacán", "https://www.lavozdemichoacan.com.mx/", ["licit","convoc","obra"]),
    ("tribunacampeche", "Campeche", "https://tribunacampeche.com/", ["licit","convoc","obra"]),
    # Aguascalientes (resto)
    ("ags_sop", "Aguascalientes", "https://eservicios2.aguascalientes.gob.mx/sop/appsWEBSOP/UI/licitacionesVigentes/", BASE_KEYWORDS),
    ("ags_sae", "Aguascalientes", "https://eservicios2.aguascalientes.gob.mx/sae/hoysecompra/", BASE_KEYWORDS),
    ("ags_fiscalia", "Aguascalientes", "https://www.fiscalia-aguascalientes.gob.mx/Proveedores.aspx", BASE_KEYWORDS),
    ("ags_issea", "Aguascalientes", "https://www.issea.gob.mx/licitaciones.aspx", BASE_KEYWORDS),
    ("ags_poderjudicial", "Aguascalientes", "http://www.poderjudicialags.gob.mx/Micrositio/UT/ContratosYLisitaciones", BASE_KEYWORDS),
    ("ags_ayuntamiento", "Aguascalientes", "https://www.ags.gob.mx/cont.aspx?p=1917", BASE_KEYWORDS),
    ("ags_epagos", "Aguascalientes", "https://epagosmunicipio.ags.gob.mx/Inicio.aspx", BASE_KEYWORDS),
    ("jesusmaria_mun", "Aguascalientes", "http://www.jesusmaria.gob.mx/", BASE_KEYWORDS),
    ("inegi_vendele", "Nacional", "https://www.inegi.org.mx/app/vendelealinegi/consulta/consulta/expediente/?p=121", BASE_KEYWORDS),
    ("conagua_consulta", "Nacional", "https://app.conagua.gob.mx/consultalicitacion.aspx", BASE_KEYWORDS),
    # Baja California
    ("bc_piab", "Baja California", "https://tramites.ebajacalifornia.gob.mx/Compras/Licitaciones", BASE_KEYWORDS),
    ("bc_portal_compras", "Baja California", "https://compras.ebajacalifornia.gob.mx/", BASE_KEYWORDS),
    # Tijuana (municipal)
    ("tijuana_om", "Tijuana, BC", "https://www.tijuana.gob.mx/dependencias/OM/index.aspx", BASE_KEYWORDS),
    ("tijuana_cespt", "Tijuana, BC", "https://www.cespt.gob.mx/TransLicConv/Licitaciones.aspx", BASE_KEYWORDS),
    ("tijuana_tesoreria", "Tijuana, BC", "http://www.tijuana.gob.mx/dependencias/tesoreria/licitaciones.aspx", BASE_KEYWORDS),
    ("tijuana_doium", "Tijuana, BC", "https://www.tijuana.gob.mx/dependencias/sdue/doium/", BASE_KEYWORDS),
    # Baja California Sur (además de especializados)
    ("bcs_compranet_portal", "BCS", "http://compranet.bcs.gob.mx/app/portal", BASE_KEYWORDS),
    ("pjbc_licit", "BCS", "https://transparencia.pjbc.gob.mx/paginas/ConcursosLicitacion.aspx", BASE_KEYWORDS),
    ("tribunal_bcs", "BCS", "https://tribunalbcs.gob.mx/seccion.php?CONTENIDO=Convocatorias+a+Licitaciones+Publicas&id=644", BASE_KEYWORDS),
    # CDMX (federales presentes + dependencias locales adicionales)
    ("ine_licitaciones", "Federal (CDMX)", "https://ine.mx/licitaciones-contrataciones-presenciales/", BASE_KEYWORDS),
    ("issfam", "Federal (CDMX)", "https://www.gob.mx/issfam/documentos/licitaciones-e-invitaciones-2025", BASE_KEYWORDS),
    ("secgob_cdmx", "CDMX", "https://www.secgob.cdmx.gob.mx/convocatorias/licitaciones", BASE_KEYWORDS),
    ("fgj_cdmx", "CDMX", "https://www.fgjcdmx.gob.mx/micrositios/licitaciones", BASE_KEYWORDS),
    ("ascm_cdmx", "CDMX", "http://ascm.gob.mx/index.php/licitaciones-publicas/", BASE_KEYWORDS),
    ("sectei_cdmx", "CDMX", "https://www.sectei.cdmx.gob.mx/administracion/licitaciones-publicas-2020", BASE_KEYWORDS),
    ("sobse_cdmx", "CDMX", "https://www.obras.cdmx.gob.mx/convocatorias/licitaciones", BASE_KEYWORDS),
    ("metro_cdmx", "CDMX", "https://www.metro.cdmx.gob.mx/acerca-del-metro/mas-informacion/licitaciones", BASE_KEYWORDS),
    ("congreso_cdmx", "CDMX", "https://www.congresocdmx.gob.mx/licitaciones-314-1.html", BASE_KEYWORDS),
    ("procesos_cdmx", "CDMX", "https://procesos.finanzas.cdmx.gob.mx/licitaciones/index.php", BASE_KEYWORDS),
    ("alcaldia_cuauhtemoc_hist", "CDMX", "https://historico.alcaldiacuauhtemoc.mx/licitaciones-publicas/", BASE_KEYWORDS),
    ("icat_cdmx", "CDMX", "https://icat.cdmx.gob.mx/instituto/licitaciones", BASE_KEYWORDS),
    # Estado de México
    ("transparenciafiscal_edomex", "Edomex", "https://transparenciafiscal.edomex.gob.mx/convocatorias_licitaciones", BASE_KEYWORDS),
    ("junta_caminos_edomex", "Edomex", "https://jcem.edomex.gob.mx/convocatorias_licitaciones", BASE_KEYWORDS),
    ("secogem_edomex", "Edomex", "https://portal.secogem.gob.mx/convocatorias-obra-publica", BASE_KEYWORDS),
    ("ieem_edomex", "Edomex", "https://www.ieem.org.mx/procedimientos-de-adquisicion/licitaciones.html", BASE_KEYWORDS),
    # Jalisco (resto)
    ("siop_jalisco_page", "Jalisco", "https://siop.jalisco.gob.mx/contratacion/licitaciones-publicas", BASE_KEYWORDS),
    ("transparencia_info_jal", "Jalisco", "https://transparencia.info.jalisco.gob.mx/transparencia/informacion-fundamental/5320", BASE_KEYWORDS),
    ("administracion_jal", "Jalisco", "https://administracion.jalisco.gob.mx/licitaciones", BASE_KEYWORDS),
    ("dif_jal", "Jalisco", "https://difjalisco.gob.mx/compras-publico", BASE_KEYWORDS),
    ("congreso_jal", "Jalisco", "https://www.congresojal.gob.mx/licitaciones", BASE_KEYWORDS),
    ("gdl_2024", "Guadalajara, Jal", "https://transparencia.guadalajara.gob.mx/licitaciones2024", BASE_KEYWORDS),
    ("gdl_2025", "Guadalajara, Jal", "https://transparencia.guadalajara.gob.mx/licitaciones2025", BASE_KEYWORDS),
    ("zapopan", "Zapopan, Jal", "https://www.zapopan.gob.mx/transparencia/articulo-8/concursos-y-licitaciones/", BASE_KEYWORDS),
    # Nuevo León
    ("nl_licit_publicas", "Nuevo León", "https://www.nl.gob.mx/es/licitaciones-publicas", BASE_KEYWORDS),
    ("secop_nl", "Nuevo León", "https://secop.nl.gob.mx/lic-pub-concluidas.html", BASE_KEYWORDS),
    ("nl_calendario", "Nuevo León", "https://www.nl.gob.mx/es/calendariodelicitaciones", BASE_KEYWORDS),
    ("nl_dependencias", "Nuevo León", "https://nl.gob.mx/es/licitaciones-dependencias-centrales", BASE_KEYWORDS),
    ("pjenl_licitaciones", "Nuevo León (PJ)", "https://www.pjenl.gob.mx/LicitacionesPublicas/", BASE_KEYWORDS),
    ("pjenl_sistema", "Nuevo León (PJ)", "https://www.pjenl.gob.mx/SistemaIntegralAdquisiciones/", BASE_KEYWORDS),
    ("monterrey_adquisiciones", "Monterrey, NL", "https://portal.monterrey.gob.mx/transparencia/adquisiciones_obrapublica.html", BASE_KEYWORDS),
    # Ojo: León es GTO (el listado original lo puso bajo NL); se respeta URL y se marca jurisdicción correcta
    ("leon_gto_obrapublica", "León, Gto", "https://apps.leon.gob.mx/aplicaciones/licitaciones/obrapublica/", BASE_KEYWORDS),
    # Veracruz (además del especializado)
    ("sefiplan_ver", "Veracruz", "http://www.veracruz.gob.mx/finanzas/transparencia-abrogada/transparencia-fiscal/licitaciones/", BASE_KEYWORDS),
    ("ssp_ver", "Veracruz", "https://www.veracruz.gob.mx/seguridad/licitaciones-publicas/", BASE_KEYWORDS),
    ("dif_ver", "Veracruz", "https://www.difver.gob.mx/transparencia_pro_tax/licitaciones_pro/", BASE_KEYWORDS),
    ("sedesol_ver", "Veracruz", "https://www.veracruz.gob.mx/desarrollosocial/procesos-de-licitaciones-publicas/", BASE_KEYWORDS),
    ("fiscalia_ver", "Veracruz", "http://fiscaliaveracruz.gob.mx/adquisiciones/", BASE_KEYWORDS),
    ("veracruz_municipio", "Veracruz, Ver", "http://transparencia.veracruzmunicipio.gob.mx/xiv-licitaciones/", BASE_KEYWORDS),
    # Puebla (además del especializado)
    ("puebla_portal", "Puebla", "https://licitaciones.puebla.gob.mx/", BASE_KEYWORDS),
    ("puebla_conv_adq", "Puebla", "https://licitaciones.puebla.gob.mx/index.php/aquisiciones-bienes-y-servicios/convocatorias-aquisiciones-bienes-y-servicios", BASE_KEYWORDS),
    ("pj_puebla", "Puebla (PJ)", "https://pjpuebla.gob.mx/licitaciones", BASE_KEYWORDS),
    ("iee_puebla", "Puebla", "https://www.ieepuebla.org.mx/categorias.php?Categoria=licitacionespublicas18", BASE_KEYWORDS),
    ("memorias_puebla_capital", "Puebla (Municipio)", "https://memorias.pueblacapital.gob.mx/ayuntamiento/item/3791-licitacion-publica", BASE_KEYWORDS),
    ("cmic_puebla", "Puebla (CMIC)", "https://www.cmicpuebla.org/licitaciones", BASE_KEYWORDS),
    # Sinaloa
    ("compranet_sinaloa", "Sinaloa", "https://compranet.sinaloa.gob.mx/secretaria-de-administracion-y-finanzas-ges", BASE_KEYWORDS),
    ("congreso_sinaloa", "Sinaloa", "https://www.congresosinaloa.gob.mx/licitaciones/", BASE_KEYWORDS),
    ("ceaip_sinaloa", "Sinaloa", "https://www.ceaipsinaloa.org.mx/licitaciones/", BASE_KEYWORDS),
    ("salud_sinaloa", "Sinaloa", "https://saludsinaloa.gob.mx/index.php/licitaciones/", BASE_KEYWORDS),
    ("cesavesin_sinaloa", "Sinaloa", "https://www.cesavesin.mx/convocatorias/", BASE_KEYWORDS),
    ("cpc_sinaloa", "Sinaloa (CPC)", "https://www.cpcsinaloa.org.mx/comites-de-obra-publica", BASE_KEYWORDS),
    # Otros estados
    ("oaxaca_admon", "Oaxaca", "https://www.oaxaca.gob.mx/administracion/licitaciones/", BASE_KEYWORDS),
    # Chihuahua (Cuauhtémoc municipio) — ya repetido arriba en CDMX sección, pero aquí lo dejamos correcto
    ("cuauhtemoc_chih", "Cuauhtémoc, Chih", "http://licitaciones.municipiocuauhtemoc.gob.mx/", BASE_KEYWORDS),
    #MIIIA
    #https://www.miaa.mx/LicitacionesObra
    #https://www.miaa.mx/LicitacionesCompra
    #https://www.miaa.mx/Invitaciones
    
]

# ---------------------------------------------------------
# Motor
# ---------------------------------------------------------

# Diccionario final de scrapers (especializados + genéricos)
SCRAPERS: Dict[str, Callable[[str, str], List[Item]]] = {}
SCRAPERS.update(SPECIALIZED)

# Envolver sitios genéricos en funciones “runner” (evita cierre tardío)
def _make_generic_runner(u: str, s: str, j: str, k: List[str]) -> Callable[[str, str], List[Item]]:
    def runner(since: str, until: str) -> List[Item]:
        return generic_scrape(u, s, j, since, until, k)
    return runner

for site_id, juris, url, kws in GENERIC_SITES:
    SCRAPERS[site_id] = _make_generic_runner(url, site_id, juris, kws)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=str, default="all",
                    help="coma-separado o 'all'. opciones: " + ",".join(SCRAPERS.keys()))
    ap.add_argument("--since", type=str, default=DEFAULT_SINCE)
    ap.add_argument("--until", type=str, default=DEFAULT_UNTIL)
    ap.add_argument("--out", type=str, default=None, help="ruta JSONL")
    ap.add_argument("--csv", type=str, default=None, help="ruta CSV")
    ap.add_argument("--confirm-only", action="store_true",
                    help="emite solo 1 ítem por fuente (confirmación de descarga)")
    ap.add_argument("--max-per-source", type=int, default=None,
                    help="límite de ítems por fuente (si se usa, ignora confirm-only)")
    ap.add_argument("--json", type=str, default=None, help="ruta JSON resumen por sitio (incluye errores y conteos)")
    ap.add_argument("--per-site-max", type=int, default=10, help="máximo de registros por sitio (default 10)")
    args = ap.parse_args()

    since = args.since
    until = args.until
    sources = list(SCRAPERS.keys()) if args.sources=="all" else [s.strip() for s in args.sources.split(",")]

    # Control de límite
    limit = 1 if args.confirm_only and not args.max_per_source else args.max_per_source
    per_site_limit = args.per_site_max

    all_items=[]
    per_site_results = []  # para JSON resumen
    failures = []
    for src in sources:
        if src not in SCRAPERS:
            print(f"[WARN] fuente desconocida: {src}", file=sys.stderr)
            per_site_results.append({"sitio": src, "items": [], "count": 0, "error": "Fuente desconocida"})
            continue
        mode = " (confirm-only)" if args.confirm_only and not args.max_per_source else (f" (max={limit})" if limit else "")
        print(f"[INFO] scraping {src}{mode}…", file=sys.stderr)
        try:
            items = SCRAPERS[src](since, until)

            # Máximo por sitio (siempre activo)
            if per_site_limit is not None:
                items = items[:per_site_limit]
            # Si además definiste límite general por fuente (confirm-only / max-per-source)
            if limit:
                items = items[:limit]

            print(f"[OK] {src}: {len(items)} items", file=sys.stderr)
            all_items.extend(items)

            # Mapear al formato pedido
            mapped = []
            for it in items:
                monto = extract_amount(((it.raw_text or "") + " " + (it.title or "")).strip())
                vinculo = it.doc_url or it.url
                mapped.append({
                    "Organismo": it.source,
                    "localidad": it.jurisdiction,
                    "Proyecto": it.title,
                    "Vínculo": vinculo,
                    "Monto": monto
                })

            per_site_results.append({
                "sitio": src,
                "items": mapped,
                "count": len(mapped)
            })

        except Exception as e:
            err = f"{e.__class__.__name__}: {e}"
            print(f"[FAIL] {src}: {err}", file=sys.stderr)
            failures.append({"sitio": src, "error": err})
            # Registrar sitio con 0 para que quede explícito que no se pudo
            per_site_results.append({"sitio": src, "items": [], "count": 0, "error": err})

    if not args.out and not args.csv and not args.json:
        args.out = "out/licitaciones.jsonl"

    all_items = dedup(all_items)

    if args.json:
        summary = {
            "since": since,
            "until": until,
            "fuentes": per_site_results
        }
        out_dir = os.path.dirname(args.json)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"[OK] json resumen -> {args.json}", file=sys.stderr)

    emit(all_items, args.out, args.csv)
    print(f"[DONE] total: {len(all_items)}", file=sys.stderr)

if __name__ == "__main__":
    main()