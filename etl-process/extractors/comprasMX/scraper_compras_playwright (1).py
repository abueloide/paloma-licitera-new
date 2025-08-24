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

# Variables globales para control de paginación
captured_responses = []
pagination_info = None

def nombre_archivo(url: str, content_type: str, page_num: int = None) -> Path:
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
    
    # Agregar número de página si se especifica
    if page_num is not None:
        base = f"{base}_page{page_num}"
    
    # extensión por mimetype
    ext = ".json"
    if "pdf" in content_type:
        ext = ".pdf"
    elif "html" in content_type:
        ext = ".html"
    ts = time.strftime("%Y%m%d-%H%M%S")
    return SALIDA / f"{ts}_{base}{ext}"

async def capturar_respuesta(resp):
    global pagination_info, captured_responses
    url = resp.url
    if not ENDPOINT_RE.search(url):
        return
    ctype = (resp.headers or {}).get("content-type", "").lower()
    try:
        if "application/json" in ctype or "json" in ctype:
            data = await resp.json()
            
            # Detectar información de paginación en expedientes
            if "expedientes" in url and data.get("success") and data.get("data"):
                for item in data["data"]:
                    if "paginacion" in item and item["paginacion"]:
                        pag_info = item["paginacion"][0]
                        pagination_info = {
                            "total_paginas": pag_info.get("total_paginas", 1),
                            "pagina_actual": pag_info.get("pagina_actual", 1),
                            "total_registros": pag_info.get("total_registros", 0),
                            "registros_pagina": pag_info.get("registros_pagina", 100)
                        }
                        print(f"[PAGINACIÓN] Detectada: {pagination_info['total_registros']} registros en {pagination_info['total_paginas']} páginas")
            
            # Almacenar respuesta capturada
            captured_responses.append({
                "url": url,
                "data": data,
                "timestamp": time.time()
            })
            
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

async def navegar_a_pagina(page, numero_pagina):
    """
    Navega a una página específica de los expedientes.
    """
    try:
        print(f"[INFO] Navegando a página {numero_pagina}...")
        
        # Buscar el campo de entrada de página o controles de paginación
        # Primero intentar buscar un input de número de página
        page_input = None
        try:
            # Buscar input que contenga el número de página actual
            page_input = await page.locator('input[type="number"]').first.wait_for(timeout=3000)
        except:
            try:
                # Buscar input con valor numérico
                page_input = await page.locator('input').filter(has_text=re.compile(r'^\d+$')).first.wait_for(timeout=3000)
            except:
                pass
        
        if page_input and await page_input.is_visible():
            # Limpiar y escribir el número de página
            await page_input.clear()
            await page_input.fill(str(numero_pagina))
            await page_input.press("Enter")
            print(f"[OK] Página {numero_pagina} solicitada via input")
        else:
            # Intentar buscar enlaces de paginación
            # Buscar enlace con el número de página
            page_link = None
            try:
                page_link = await page.get_by_text(str(numero_pagina), exact=True).first.wait_for(timeout=3000)
                if await page_link.is_visible():
                    await page_link.click()
                    print(f"[OK] Página {numero_pagina} solicitada via enlace")
            except:
                # Como último recurso, buscar botón "Siguiente" repetidamente
                for _ in range(numero_pagina - 1):
                    try:
                        next_btn = await page.get_by_text("Siguiente", exact=False).first.wait_for(timeout=2000)
                        if await next_btn.is_visible() and await next_btn.is_enabled():
                            await next_btn.click()
                            await page.wait_for_timeout(2000)
                        else:
                            break
                    except:
                        break
                print(f"[OK] Navegación secuencial a página {numero_pagina}")
        
        # Esperar a que se carguen los nuevos datos
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] No se pudo navegar a la página {numero_pagina}: {e}")
        return False

async def solicitar_pagina_por_api(page, numero_pagina):
    """
    Solicita una página específica manipulando directamente la API.
    """
    try:
        print(f"[API] Solicitando página {numero_pagina} via JavaScript...")
        
        # Inyectar JavaScript para solicitar la página específica
        script = f"""
        // Buscar función de paginación en el contexto global
        if (typeof window.cargarPagina === 'function') {{
            window.cargarPagina({numero_pagina});
        }} else if (typeof window.buscarExpedientes === 'function') {{
            window.buscarExpedientes({{ pagina: {numero_pagina} }});
        }} else if (window.angular) {{
            // Intentar con AngularJS si está disponible
            var scope = window.angular.element(document.body).scope();
            if (scope && scope.paginacion) {{
                scope.paginacion.paginaActual = {numero_pagina};
                scope.$apply();
            }}
        }} else {{
            // Disparar evento personalizado
            window.dispatchEvent(new CustomEvent('cambiarPagina', {{ detail: {numero_pagina} }}));
        }}
        """
        
        await page.evaluate(script)
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] No se pudo solicitar página {numero_pagina} via API: {e}")
        return False

async def main(headless: bool = True, espera_ms: int = 15000):
    global pagination_info, captured_responses
    
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

        # Intentar navegar a la sección de expedientes
        print(">>> Buscando sección de expedientes...")
        try:
            for texto in ("EXPEDIENTES", "Licitaciones", "Búsqueda", "Procedimientos"):
                try:
                    el = await page.get_by_text(texto, exact=False).first.wait_for(timeout=3000)
                    if await el.is_visible():
                        await el.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(5000)
                        print(f"[OK] Navegado a sección: {texto}")
                        break
                except:
                    continue
        except Exception:
            print("[INFO] No se encontraron enlaces de navegación específicos")

        # Esperar a capturar la primera página y detectar paginación
        await page.wait_for_timeout(5000)
        
        # Si se detectó información de paginación, navegar a todas las páginas
        if pagination_info and pagination_info["total_paginas"] > 1:
            total_paginas = pagination_info["total_paginas"]
            print(f">>> Iniciando captura de {total_paginas} páginas...")
            
            # Ya tenemos la página 1, ahora capturar las restantes
            for num_pagina in range(2, total_paginas + 1):
                print(f"\n>>> Procesando página {num_pagina}/{total_paginas}")
                
                # Intentar múltiples métodos de navegación
                exito = False
                
                # Método 1: Navegación por UI
                if not exito:
                    exito = await navegar_a_pagina(page, num_pagina)
                
                # Método 2: API JavaScript
                if not exito:
                    exito = await solicitar_pagina_por_api(page, num_pagina)
                
                if exito:
                    # Esperar a que se capturen las nuevas respuestas
                    await page.wait_for_timeout(3000)
                    print(f"[OK] Página {num_pagina} procesada")
                else:
                    print(f"[WARN] No se pudo procesar página {num_pagina}")
                
                # Pequeña pausa entre requests para no sobrecargar el servidor
                await page.wait_for_timeout(1000)
        
        else:
            print("[INFO] No se detectó información de paginación o solo hay 1 página")

        # Espera final para capturar cualquier respuesta pendiente
        await page.wait_for_timeout(5000)
        
        # Resumen final
        total_responses = len(captured_responses)
        expedientes_responses = len([r for r in captured_responses if "expedientes" in r["url"]])
        
        print(f"\n>>> RESUMEN DE CAPTURA:")
        print(f"Total respuestas capturadas: {total_responses}")
        print(f"Respuestas de expedientes: {expedientes_responses}")
        if pagination_info:
            print(f"Registros esperados: {pagination_info['total_registros']}")
            print(f"Páginas esperadas: {pagination_info['total_paginas']}")

        await browser.close()

if __name__ == "__main__":
    # Headless por defecto (no requiere X server)
    asyncio.run(main(headless=True))