import asyncio, os, re, json, hashlib, time, zipfile
from pathlib import Path
from urllib.parse import urlparse, parse_qsl
from playwright.async_api import async_playwright

# Usar ruta absoluta para guardar en el lugar correcto
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Subir hasta la raíz del proyecto
SALIDA = BASE_DIR / "data" / "raw" / "tianguis"
SALIDA.mkdir(parents=True, exist_ok=True)

print(f">>> Los archivos se guardarán en: {SALIDA.absolute()}")

# Patrones para interceptar las respuestas relevantes
ENDPOINT_PATTERNS = [
    r"/livewire/message/search-component",
    r"/livewire/download",  # Posible endpoint de descarga
    r"\.csv$",
    r"\.json$",
    r"\.zip$",  # Para detectar ZIPs
    r"/export",
    r"/download",
]

ENDPOINT_RE = re.compile("|".join(ENDPOINT_PATTERNS))

def nombre_archivo(url: str, content_type: str, response_data=None) -> Path:
    """Genera nombre único basado en URL y contenido"""
    u = urlparse(url)
    base = u.path.strip("/").replace("/", "_")
    if not base:
        base = "data"
    
    # Si hay query params, incluirlos en el hash
    if u.query:
        q = "&".join(sorted([f"{k}={v}" for k, v in parse_qsl(u.query)]))
        h = hashlib.sha1(q.encode("utf-8")).hexdigest()[:10]
        base = f"{base}_{h}"
    
    # Determinar extensión
    ext = ".json"
    if "pdf" in content_type:
        ext = ".pdf"
    elif "excel" in content_type or "spreadsheet" in content_type:
        ext = ".xlsx"
    elif "csv" in content_type or "text/csv" in content_type:
        ext = ".csv"
    elif "zip" in content_type:
        ext = ".zip"
    
    ts = time.strftime("%Y%m%d-%H%M%S")
    return SALIDA / f"{ts}_{base}{ext}"

def descomprimir_zip(archivo_zip: Path):
    """Descomprime un archivo ZIP"""
    try:
        print(f">>> Descomprimiendo {archivo_zip.name}...")
        
        with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
            # Listar contenido
            archivos = zip_ref.namelist()
            print(f"    -> Contiene {len(archivos)} archivo(s)")
            
            # Extraer todo en la misma carpeta
            zip_ref.extractall(SALIDA)
            
            # Mostrar archivos extraídos
            for archivo in archivos:
                print(f"    -> Extraído: {archivo}")
        
        # Opcional: eliminar el ZIP original después de extraer
        # archivo_zip.unlink()
        # print(f"    -> ZIP original eliminado")
        
    except Exception as e:
        print(f"[ERROR] Al descomprimir {archivo_zip.name}: {e}")

async def capturar_respuesta(resp):
    """Intercepta y guarda las respuestas relevantes"""
    url = resp.url
    
    # Capturar TODAS las respuestas de Livewire para análisis
    if "/livewire/" in url or ENDPOINT_RE.search(url):
        ctype = (resp.headers or {}).get("content-type", "").lower()
        
        try:
            # Para CSV
            if "text/csv" in ctype or "csv" in ctype or url.endswith('.csv'):
                body = await resp.body()
                if len(body) > 0:
                    ruta = nombre_archivo(url, ctype)
                    with open(ruta, "wb") as f:
                        f.write(body)
                    print(f"[OK] CSV capturado: {ruta.name} ({len(body)} bytes)")
                    
            elif "application/json" in ctype or "json" in ctype:
                data = await resp.json()
                
                # Verificar si la respuesta contiene datos de contrataciones
                if isinstance(data, dict):
                    # Buscar indicadores de datos relevantes
                    if any(key in str(data).lower() for key in ['contrat', 'licitac', 'compra', 'download', 'export']):
                        ruta = nombre_archivo(url, ctype, data)
                        with open(ruta, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"[OK] Datos capturados: {ruta.name}")
                        
                        # Si hay URL de descarga directa en la respuesta
                        if 'download_url' in str(data) or 'file_url' in str(data):
                            print(f"    -> Contiene URL de descarga directa")
                            # Extraer y guardar la URL
                            urls_file = SALIDA / "urls_descarga.txt"
                            with open(urls_file, "a") as f:
                                f.write(f"{url}\n")
                                
            else:
                # Para archivos binarios (PDF, Excel, ZIP, etc.)
                body = await resp.body()
                if len(body) > 1000:  # Solo guardar si tiene contenido sustancial
                    ruta = nombre_archivo(url, ctype)
                    with open(ruta, "wb") as f:
                        f.write(body)
                    print(f"[OK] Archivo binario guardado: {ruta.name} ({len(body)} bytes)")
                    
        except Exception as e:
            # Solo mostrar error si es relevante
            if "livewire/message" in url:
                print(f"[INFO] Respuesta Livewire no procesable: {e}")

async def main(headless: bool = True):
    """
    Scraper principal - headless=True para ejecutar sin ventana visible
    """
    async with async_playwright() as p:
        print(">>> Iniciando navegador en modo headless...")
        browser = await p.chromium.launch(
            headless=headless,  # True = sin ventana visible
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security"  # Para evitar CORS en descargas
            ]
        )
        
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/139.0.0.0 Safari/537.36"),
            locale="es-MX",
            accept_downloads=True,  # Importante para manejar descargas
        )
        
        page = await context.new_page()
        
        # Interceptar TODAS las respuestas
        page.on("response", lambda r: asyncio.create_task(capturar_respuesta(r)))
        
        # También interceptar descargas directas
        page.on("download", lambda download: asyncio.create_task(
            manejar_descarga(download)
        ))
        
        print(">>> Navegando a Tianguis Digital CDMX...")
        await page.goto(
            "https://datosabiertostianguisdigital.cdmx.gob.mx/busqueda",
            wait_until="networkidle",
            timeout=30000
        )
        
        # Esperar que cargue completamente
        await page.wait_for_timeout(5000)
        
        try:
            print(">>> Buscando botón 'Descargar todo'...")
            
            # Intentar diferentes selectores para el botón
            download_button = None
            for selector in [
                "button:has-text('Descargar todo')",
                "text=/Descargar.*todo/i",
                "[wire\\:click*='download']",
                "button[x-data*='download']",
                "button:has-text('Descargar')",
                "[aria-label*='Descargar']"
            ]:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        download_button = elements[0]
                        print(f"    -> Botón encontrado: {selector}")
                        break
                except:
                    continue
            
            if download_button:
                await download_button.click()
                print("    -> Click en 'Descargar todo'")
                
                # Esperar que aparezca el modal/popup
                await page.wait_for_timeout(2000)
                
                # Buscar y clickear CSV en el modal
                print(">>> Buscando opción CSV en el modal...")
                
                # El modal podría estar en un div con role="dialog" o similar
                for selector in [
                    # Selectores específicos para CSV
                    "[role='dialog'] button:has-text('CSV')",
                    ".modal button:has-text('CSV')",
                    "[x-show] button:has-text('CSV')",
                    "[wire\\:click*='csv']",
                    "text=/^CSV$/i",  # Texto exacto CSV
                    "button:has-text('CSV')",
                    "a:has-text('CSV')",
                    "[data-format='csv']",
                    "[data-type='csv']",
                    # Selectores más genéricos
                    "button:text-is('CSV')",
                    "*:has-text('CSV'):clickable"
                ]:
                    try:
                        csv_option = page.locator(selector).first
                        if await csv_option.is_visible():
                            await csv_option.click()
                            print(f"    -> Click en CSV con: {selector}")
                            break
                    except:
                        continue
                
                # Esperar respuesta después del click
                await page.wait_for_timeout(10000)
                
            else:
                print("[WARN] No se encontró el botón de descarga")
                
                # Plan B: Intentar provocar la descarga via JavaScript
                print(">>> Intentando trigger via JavaScript...")
                await page.evaluate("""
                    // Buscar componente Livewire y triggear evento para CSV
                    if (window.Livewire) {
                        const component = window.Livewire.first();
                        if (component) {
                            component.call('downloadAll', 'csv');
                            console.log('Livewire CSV download triggered');
                        }
                    }
                """)
                await page.wait_for_timeout(10000)
                
        except Exception as e:
            print(f"[ERROR] Durante interacción: {e}")
        
        # Espera final para capturar cualquier respuesta tardía
        print(">>> Esperando respuestas finales...")
        await page.wait_for_timeout(5000)
        
        await browser.close()
        
        # Buscar y descomprimir cualquier archivo ZIP descargado
        print("\n>>> Verificando archivos ZIP descargados...")
        zips_encontrados = list(SALIDA.glob("*.zip"))
        if zips_encontrados:
            for archivo_zip in zips_encontrados:
                descomprimir_zip(archivo_zip)
        else:
            print("    -> No se encontraron archivos ZIP")
            
        print(f"\n>>> Proceso completado. Archivos en: {SALIDA.absolute()}")
        
        # Resumen final
        archivos_guardados = list(SALIDA.glob("*"))
        print(f">>> Total de archivos guardados: {len(archivos_guardados)}")
        for archivo in archivos_guardados[-5:]:  # Mostrar últimos 5
            print(f"    - {archivo.name}")

async def manejar_descarga(download):
    """Maneja descargas directas del navegador"""
    try:
        filename = download.suggested_filename
        path = SALIDA / filename
        await download.save_as(path)
        print(f"[OK] Descarga directa guardada: {filename}")
        
        # Si es un ZIP, descomprimirlo
        if filename.lower().endswith('.zip'):
            descomprimir_zip(path)
            
    except Exception as e:
        print(f"[ERROR] Al guardar descarga: {e}")

if __name__ == "__main__":
    # Ejecutar en modo headless (sin ventana)
    asyncio.run(main(headless=True))
