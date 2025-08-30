from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
import re
import json
from datetime import datetime

class ComprasMXScraper:
    def __init__(self):
        """Inicializar el scraper con configuración optimizada"""
        self.setup_driver()
        
    def setup_driver(self):
        """Configurar Chrome driver"""
        print("🚀 Configurando Chrome driver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✅ Driver configurado correctamente")

    def extraer_uuids_tabla_principal(self):
        """
        FUNCIÓN 1: Extraer todos los UUIDs de la tabla principal de licitaciones
        Retorna lista de diccionarios con información básica + UUID
        """
        print("\n🎯 FUNCIÓN 1: Extrayendo UUIDs de tabla principal...")
        
        url_principal = "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/"
        max_intentos = 3
        
        for intento in range(max_intentos):
            try:
                print(f"📡 Intento {intento + 1}/{max_intentos} - Cargando página principal...")
                self.driver.get(url_principal)
                
                # Esperar que la tabla cargue completamente
                print("⏳ Esperando carga de tabla...")
                time.sleep(15)
                
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                # Obtener todas las filas válidas
                filas = self.driver.find_elements(By.TAG_NAME, "tr")
                filas_validas = []
                
                for fila in filas:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) >= 5:  # Verificar que tenga columnas suficientes
                        texto_celda = celdas[1].text.strip()
                        # Filtrar filas de encabezado
                        if texto_celda and len(texto_celda) > 3 and not texto_celda.lower().startswith("número"):
                            filas_validas.append(fila)
                
                print(f"✅ Encontradas {len(filas_validas)} licitaciones en la tabla")
                
                if len(filas_validas) > 0:
                    break
                else:
                    print(f"⚠️ No se encontraron filas válidas en intento {intento + 1}")
                    
            except Exception as e:
                print(f"❌ Error en intento {intento + 1}: {e}")
                if intento < max_intentos - 1:
                    time.sleep(10)
        
        if not filas_validas:
            print("❌ No se pudieron obtener filas de la tabla")
            return []
        
        # Extraer UUIDs navegando a cada detalle
        licitaciones = []
        total_filas = len(filas_validas)
        
        for i, fila in enumerate(filas_validas):
            try:
                print(f"\n[{i+1}/{total_filas}] Extrayendo UUID...")
                
                # Obtener información básica de la fila
                celdas = fila.find_elements(By.TAG_NAME, "td")
                numero_id = celdas[1].text.strip()
                caracter = celdas[2].text.strip()
                titulo = celdas[3].text.strip()
                dependencia = celdas[4].text.strip()
                estatus = celdas[5].text.strip() if len(celdas) > 5 else "N/A"
                
                print(f"    📄 {numero_id}: {titulo[:40]}...")
                
                # Click en la celda del número para navegar al detalle
                self.driver.execute_script("arguments[0].scrollIntoView(true);", celdas[1])
                time.sleep(1)
                celdas[1].click()
                
                # Esperar navegación
                time.sleep(8)
                
                # Extraer UUID de la URL
                url_actual = self.driver.current_url
                uuid_extraido = "N/A"
                
                if "/detalle/" in url_actual:
                    match_uuid = re.search(r'/detalle/([a-f0-9]{32})/', url_actual)
                    if match_uuid:
                        uuid_extraido = match_uuid.group(1)
                        print(f"    🔑 UUID: {uuid_extraido}")
                    else:
                        print("    ❌ No se pudo extraer UUID de URL")
                else:
                    print("    ❌ No se navegó a página de detalle")
                
                # Guardar información
                licitacion_info = {
                    "numero_identificacion": numero_id,
                    "caracter": caracter,
                    "titulo": titulo,
                    "dependencia": dependencia,
                    "estatus": estatus,
                    "uuid": uuid_extraido,
                    "url_detalle": f"https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/{uuid_extraido}/procedimiento" if uuid_extraido != "N/A" else "N/A"
                }
                licitaciones.append(licitacion_info)
                
                # Regresar a la tabla principal (solo si no es el último elemento)
                if i < total_filas - 1:
                    print("    ⬅️ Regresando a tabla principal...")
                    self.driver.back()
                    time.sleep(5)
                    
                    # Verificar que regresamos correctamente
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.TAG_NAME, "table"))
                    )
                    
                    # Re-localizar filas para siguiente iteración
                    filas = self.driver.find_elements(By.TAG_NAME, "tr")
                    filas_validas = []
                    for fila in filas:
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        if len(celdas) >= 5:
                            texto_celda = celdas[1].text.strip()
                            if texto_celda and len(texto_celda) > 3 and not texto_celda.lower().startswith("número"):
                                filas_validas.append(fila)
                
            except Exception as e:
                print(f"    ❌ Error extrayendo UUID de fila {i+1}: {e}")
                # Guardar información parcial en caso de error
                licitacion_info = {
                    "numero_identificacion": numero_id if 'numero_id' in locals() else "ERROR",
                    "caracter": caracter if 'caracter' in locals() else "ERROR",
                    "titulo": titulo if 'titulo' in locals() else "ERROR",
                    "dependencia": dependencia if 'dependencia' in locals() else "ERROR",
                    "estatus": estatus if 'estatus' in locals() else "ERROR",
                    "uuid": "ERROR",
                    "url_detalle": "ERROR",
                    "error": str(e)
                }
                licitaciones.append(licitacion_info)
                continue
        
        # Guardar UUIDs extraídos
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archivo_uuids = f"comprasmx_uuids_{timestamp}.json"
        
        with open(archivo_uuids, "w", encoding="utf-8") as f:
            json.dump(licitaciones, f, ensure_ascii=False, indent=2)
        
        uuids_exitosos = len([l for l in licitaciones if l["uuid"] != "N/A" and l["uuid"] != "ERROR"])
        
        print(f"\n✅ EXTRACCIÓN DE UUIDs COMPLETADA")
        print(f"📊 Total procesadas: {len(licitaciones)}")
        print(f"🔑 UUIDs exitosos: {uuids_exitosos}/{len(licitaciones)} ({uuids_exitosos/len(licitaciones)*100:.1f}%)")
        print(f"💾 Guardado en: {archivo_uuids}")
        
        return licitaciones

    def scraping_detalle_por_uuid(self, lista_licitaciones):
        """
        FUNCIÓN 2: Hacer scraping detallado de cada licitación usando URL directa
        Usa document.body.textContent para obtener todo el texto de la página
        """
        print(f"\n🎯 FUNCIÓN 2: Scraping detallado de {len(lista_licitaciones)} licitaciones...")
        
        # Filtrar solo las que tienen UUID válido
        licitaciones_validas = [l for l in lista_licitaciones if l["uuid"] not in ["N/A", "ERROR"]]
        print(f"📍 Procesando {len(licitaciones_validas)} licitaciones con UUID válido")
        
        datos_detallados = []
        
        for i, licitacion in enumerate(licitaciones_validas, start=1):
            try:
                uuid = licitacion["uuid"]
                url_detalle = licitacion["url_detalle"]
                
                print(f"\n[{i}/{len(licitaciones_validas)}] Scraping UUID: {uuid}")
                print(f"    🔗 URL: {url_detalle}")
                
                # Navegar directamente a la página de detalle
                self.driver.get(url_detalle)
                
                # Esperar carga inicial
                time.sleep(12)
                
                # Usar document.body.textContent para obtener TODO el texto
                print("    📄 Extrayendo texto completo con document.body.textContent...")
                texto_completo = self.driver.execute_script("return document.body.textContent;")
                
                if not texto_completo or len(texto_completo) < 500:
                    print("    ⚠️ Texto insuficiente, esperando más tiempo...")
                    time.sleep(10)
                    texto_completo = self.driver.execute_script("return document.body.textContent;")
                
                print(f"    ✅ Texto extraído: {len(texto_completo)} caracteres")
                
                # Extraer datos específicos del texto usando regex
                datos_extraidos = self.extraer_datos_del_texto(texto_completo)
                
                # Combinar información básica con datos extraídos
                licitacion_completa = {
                    **licitacion,  # Información básica de la tabla
                    **datos_extraidos,  # Datos extraídos del texto
                    "texto_completo": texto_completo,
                    "fecha_scraping": datetime.now().isoformat()
                }
                
                datos_detallados.append(licitacion_completa)
                
                # Contar campos exitosos
                campos_extraidos = len([v for k, v in datos_extraidos.items() if v not in ["N/A", "", None]])
                print(f"    ⛏️  Campos extraídos: {campos_extraidos}")
                print(f"    ✅ Scraping completado")
                
                # Pausa entre requests
                time.sleep(3)
                
            except Exception as e:
                print(f"    ❌ Error en scraping de {licitacion.get('numero_identificacion', 'N/A')}: {e}")
                # Guardar datos básicos aunque falle el scraping
                licitacion_error = {
                    **licitacion,
                    "texto_completo": "",
                    "error_scraping": str(e),
                    "fecha_scraping": datetime.now().isoformat()
                }
                datos_detallados.append(licitacion_error)
                continue
        
        return datos_detallados

    def extraer_datos_del_texto(self, texto):
        """
        Extraer datos específicos del texto completo usando patrones regex
        """
        datos = {}
        
        # Patrones para extraer información específica
        patrones = {
            "codigo_expediente": [
                r"Código del expediente[:\s]*([^\n\r]+)",
                r"E-\d{4}-\d{8}"
            ],
            "nombre_procedimiento": [
                r"Nombre del procedimiento de contratación[:\s]*([^\n\r]+)",
                r"Nombre del procedimiento[:\s]*([^\n\r]+)"
            ],
            "descripcion_detallada": [
                r"Descripción detallada del procedimiento[:\s]*([^\n\r]+)",
            ],
            "tipo_procedimiento": [
                r"Tipo de procedimiento[:\s]*([^\n\r]+)",
            ],
            "fecha_publicacion": [
                r"Fecha y hora de publicación[:\s]*([^\n\r]+)",
            ],
            "fecha_apertura": [
                r"Fecha y hora de presentación y apertura[:\s]*([^\n\r]+)",
            ],
            "fecha_fallo": [
                r"Fecha y hora del acto del Fallo[:\s]*([^\n\r]+)",
            ],
            "importe_estimado": [
                r"Importe estimado[:\s]*([^\n\r]+)",
                r"Monto[:\s]*([^\n\r$]+)",
                r'\$\s*([\d,]+\.?\d*)',
            ],
            "unidad_compradora": [
                r"Unidad compradora[:\s]*([^\n\r]+)",
            ],
            "entidad_federativa": [
                r"Entidad Federativa[:\s]*([^\n\r]+)",
            ],
            "plazo_ejecucion": [
                r"Plazo de ejecucion[:\s]*([^\n\r]+)",
            ]
        }
        
        # Aplicar cada patrón
        for campo, lista_patrones in patrones.items():
            valor = "N/A"
            for patron in lista_patrones:
                coincidencias = re.findall(patron, texto, re.MULTILINE | re.IGNORECASE)
                if coincidencias:
                    valor = coincidencias[0].strip()
                    if valor and valor != "N/A":
                        break
            datos[campo] = valor
        
        return datos

    def ejecutar_scraping_completo(self):
        """
        Ejecutar el proceso completo: extracción de UUIDs + scraping detallado
        """
        print("🚀 INICIANDO SCRAPING COMPLETO DE COMPRAS MX")
        print("=" * 60)
        
        try:
            # FUNCIÓN 1: Extraer UUIDs
            lista_licitaciones = self.extraer_uuids_tabla_principal()
            
            if not lista_licitaciones:
                print("❌ No se extrajeron UUIDs. Finalizando.")
                return None
            
            # FUNCIÓN 2: Scraping detallado
            datos_completos = self.scraping_detalle_por_uuid(lista_licitaciones)
            
            if datos_completos:
                # Guardar resultados finales
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                
                # CSV para análisis
                df = pd.DataFrame(datos_completos)
                archivo_csv = f"comprasmx_datos_completos_{timestamp}.csv"
                df.to_csv(archivo_csv, index=False, encoding="utf-8")
                
                # JSON para datos completos
                archivo_json = f"comprasmx_datos_completos_{timestamp}.json"
                with open(archivo_json, "w", encoding="utf-8") as f:
                    json.dump(datos_completos, f, ensure_ascii=False, indent=2)
                
                # Estadísticas finales
                self.mostrar_estadisticas_finales(datos_completos, archivo_csv, archivo_json)
                
                return datos_completos
            else:
                print("⚠️ No se obtuvieron datos detallados")
                return None
                
        except Exception as e:
            print(f"❌ Error crítico en scraping: {e}")
            return None
        
        finally:
            self.cerrar()

    def mostrar_estadisticas_finales(self, datos, archivo_csv, archivo_json):
        """Mostrar estadísticas del scraping realizado"""
        total = len(datos)
        con_codigo = len([d for d in datos if d.get("codigo_expediente", "N/A") != "N/A"])
        con_descripcion = len([d for d in datos if d.get("descripcion_detallada", "N/A") != "N/A"])
        con_fechas = len([d for d in datos if d.get("fecha_publicacion", "N/A") != "N/A"])
        con_importes = len([d for d in datos if d.get("importe_estimado", "N/A") != "N/A"])
        
        print(f"\n🎉 SCRAPING COMPLETADO EXITOSAMENTE!")
        print("=" * 60)
        print(f"📊 ESTADÍSTICAS FINALES:")
        print(f"  📋 Total procesadas: {total}")
        print(f"  🔢 Con código expediente: {con_codigo} ({con_codigo/total*100:.1f}%)")
        print(f"  📝 Con descripción: {con_descripcion} ({con_descripcion/total*100:.1f}%)")
        print(f"  📅 Con fechas: {con_fechas} ({con_fechas/total*100:.1f}%)")
        print(f"  💰 Con importes: {con_importes} ({con_importes/total*100:.1f}%)")
        print(f"\n💾 ARCHIVOS GENERADOS:")
        print(f"  📊 CSV: {archivo_csv}")
        print(f"  📋 JSON: {archivo_json}")

    def cerrar(self):
        """Cerrar el driver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("\n✅ Driver cerrado correctamente")

# Ejecución principal
if __name__ == "__main__":
    scraper = ComprasMXScraper()
    try:
        datos = scraper.ejecutar_scraping_completo()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
    finally:
        scraper.cerrar()