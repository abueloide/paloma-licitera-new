import asyncio, os, re, json, hashlib, time
from pathlib import Path
from urllib.parse import urlparse, parse_qsl
from playwright.async_api import async_playwright

# Directorio de salida ajustado para integración ETL
# Busca el directorio data/raw/comprasmx desde la raíz del proyecto
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # ../../../
SALIDA = project_root / "data" / "raw" / "comprasmx"
SALIDA.mkdir(parents=True, exist_ok=True)

print(f"[INFO] Scraper ComprasMX - Guardando archivos en: {SALIDA.absolute()}")

# Filtros de endpoints relevantes
ENDPOINT_PATTERNS = [
    r"/whitney/sitiopublico/expedientes(\?|/)",
    r"/whitney/sitiopublico/.+?/reqeconomicos(\?|/|$)",
    r"/whitney/sitiopublico/.+?/anexos(\?|/|$)",
    r"/whitney/sitiopublico/catalogos$",
]

ENDPOINT_RE = re.compile("|".join(ENDPOINT_PATTERNS))

def nombre_archivo(url: str, content_type: str) -> Path:
    """
    Genera un nombre estable y legible por URL + query.
    """
    u = urlparse(url)
    base = u.path.strip("/").replace("/", "_")
    if not base:
        base = "root"
    if u.query:
        # normaliza orden de parámetros para no duplicar
        q = "&".join(sorted([f"{k}={v}" for k, v in parse_qsl(u.query)]))
        h = hashlib.sha1(q.encode("utf-8")).hexdigest()[:10]
        base = f"{base}_{h}"
    # extensión por mimetype
    ext = ".json"
    if "pdf" in content_type:
        ext = ".pdf"
    elif "html" in content_type:
        ext = ".html"
    ts = time.strftime("%Y%m%d-%H%M%S")
    return SALIDA / f"{ts}_{base}{ext}"

async def capturar_respuesta(resp):
    url = resp.url
    if not ENDPOINT_RE.search(url):
        return
    ctype = (resp.headers or {}).get("content-type", "").lower()
    try:
        if "application/json" in ctype or "json" in ctype:
            data = await resp.json()
            ruta = nombre_archivo(url, ctype)
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[OK] JSON guardado: {ruta.name} <- {url}")
        else:
            # por si algún adjunto/reg descarga no es JSON
            body = await resp.body()
            ruta = nombre_archivo(url, ctype)
            with open(ruta, "wb") as f:
                f.write(body)
            print(f"[OK] Binario guardado: {ruta.name} <- {url} ({ctype or 'octet-stream'})")
    except Exception as e:
        print(f"[WARN] No pude guardar {url}: {e}")

async def main(headless: bool = True, espera_ms: int = 15000):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/118 Safari/537.36"),
            locale="es-MX",
        )
        page = await context.new_page()

        # Hook de respuestas
        page.on("response", lambda r: asyncio.create_task(capturar_respuesta(r)))

        print(">>> Abriendo sitio público de ComprasMX…")
        await page.goto("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/", wait_until="domcontentloaded")

        # Da tiempo a que la SPA cargue, resuelva reCAPTCHA invisible y dispare los XHR
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(espera_ms)

        # (Opcional) intenta navegar dentro para provocar más XHR si la portada no trae lista
        # Algunas implementaciones cargan listados al entrar a una vista específica.
        # Si en tu UI existe un link/tab a "Expedientes" o similar, intenta click:
        try:
            # ejemplos de selectores tentativos (ajústalos si ves que existen):
            for texto in ("EXPEDIENTES", "Licitaciones", "Búsqueda", "Procedimientos"):
                el = await page.get_by_text(texto, exact=False).first
                if await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(5000)
                    break
        except Exception:
            pass

        # Espera adicional para capturar llamadas posteriores (detalles, anexos, reqeconómicos)
        await page.wait_for_timeout(5000)

        await browser.close()

if __name__ == "__main__":
    # Headless por defecto (no requiere X server)
    asyncio.run(main(headless=True))