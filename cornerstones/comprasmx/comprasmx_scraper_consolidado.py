#!/usr/bin/env python3
"""
ComprasMX Scraper Consolidado - Versión Funcional
=================================================

OBJETIVO:
1. Extraer UUIDs de ComprasMX usando window.location.href DESPUÉS DEL CLICK
2. Ir a cada licitación individual y extraer texto completo
3. Usar Claude Haiku para estructurar datos específicos
4. Output: JSON estructurado SIN texto completo (archivo más liviano)

MÉTODO COMPROBADO: Click + window.location.href (como ComprasMX_v2Claude.py)
CONFIRMADO: ¡¡¡FUNCIONA!!! El click es obligatorio para obtener UUIDs reales

Autor: Claude + Usuario
Versión: 2.3 - FUNCIONAL - JSON sin texto completo
"""

import time
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️  python-dotenv no instalado, usando variables de entorno del sistema")
    print("   Para instalar: pip install python-dotenv")

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Anthropic import
import anthropic

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LicitacionUUID:
    """Estructura para licitación con UUID extraída"""
    uuid: str
    numero_identificacion: str
    caracter: str
    titulo: str
    dependencia: str
    estatus: str
    url_detalle: str

@dataclass
class LicitacionCompleta:
    """Estructura para licitación procesada con Haiku"""
    uuid: str
    numero_identificacion: str
    titulo_basico: str
    url_detalle: str
    # Campos extraídos por Haiku - SIN texto_completo para archivo más liviano
    numero_procedimiento_contratacion: Optional[str] = None
    dependencia_entidad: Optional[str] = None
    ramo: Optional[str] = None
    unidad_compradora: Optional[str] = None
    referencia_control_interno: Optional[str] = None
    nombre_procedimiento_contratacion: Optional[str] = None
    descripcion_detallada: Optional[str] = None
    ley_soporte_normativo: Optional[str] = None
    tipo_procedimiento_contratacion: Optional[str] = None
    entidad_federativa_contratacion: Optional[str] = None
    fecha_publicacion: Optional[str] = None
    fecha_apertura_proposiciones: Optional[str] = None
    fecha_junta_aclaraciones: Optional[str] = None
    # Metadata
    fecha_scraping: str = ""
    procesado_haiku: bool = False
    error_haiku: Optional[str] = None

class ComprasMXScraperFuncional:
    """
    Scraper funcional para ComprasMX
    MÉTODO COMPROBADO: Click + window.location.href
    """

    def __init__(self, headless: bool = True, anthropic_api_key: str = None):
        self.base_url = "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/"
        self.driver = None
        self.wait = None
        self.headless = headless
        
        # Configurar cliente Anthropic
        api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        if api_key and api_key.strip() and api_key != 'your_api_key_here':
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            logger.info("✅ Cliente Claude Haiku configurado desde .env")
        else:
            self.anthropic_client = None
            logger.warning("⚠️  Haiku no configurado - scraper funcionará sin IA")
        
        # Estadísticas
        self.stats = {
            'total_intentos': 0,
            'uuids_extraidos': 0,
            'licitaciones_procesadas': 0,
            'procesadas_con_haiku': 0,
            'errores': 0
        }

    def configurar_driver(self) -> None:
        """Configurar driver Chrome con opciones optimizadas"""
        logger.info("🔧 Configurando driver Chrome...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Opciones optimizadas
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        
        # User agent para evitar detección
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("✅ Driver Chrome configurado exitosamente")
        except Exception as e:
            logger.error(f"❌ Error configurando driver: {e}")
            raise

    def navegar_sitio_principal(self) -> bool:
        """Navegar al sitio principal y esperar que cargue la tabla dinámica"""
        logger.info(f"🌐 Navegando a ComprasMX: {self.base_url}")
        
        try:
            self.driver.get(self.base_url)
            
            # Esperar que se cargue la tabla dinámica
            logger.info("⏳ Esperando carga dinámica de la tabla...")
            table_body = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
            )
            
            # Espera adicional para estabilizar
            time.sleep(8)
            
            logger.info("✅ Tabla dinámica cargada exitosamente")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error cargando sitio: {e}")
        
        return False

    def obtener_filas_validas(self) -> List:
        """Obtener filas válidas de la tabla principal"""
        try:
            table_body = self.driver.find_element(By.CSS_SELECTOR, "table tbody")
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            
            filas_validas = []
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 2:  # Al menos 2 columnas
                    # Verificar que la segunda columna tenga contenido (número de licitación)
                    texto_segunda_columna = cols[1].text.strip()
                    if texto_segunda_columna and len(texto_segunda_columna) > 3:
                        filas_validas.append(row)
            
            logger.info(f"📊 Encontradas {len(filas_validas)} filas válidas de licitaciones")
            return filas_validas
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo filas: {e}")
            return []

    def extraer_uuid_fila(self, fila, indice: int) -> Optional[LicitacionUUID]:
        """
        Extraer UUID de una fila usando CLICK + window.location.href
        MÉTODO COMPROBADO que funciona
        """
        try:
            # Obtener celdas de la fila
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) < 2:
                return None
            
            # Extraer información básica de las celdas disponibles
            info_basica = {}
            try:
                info_basica['numero_identificacion'] = celdas[1].text.strip()  # Segunda columna
                info_basica['caracter'] = celdas[2].text.strip() if len(celdas) > 2 else ""
                info_basica['titulo'] = celdas[3].text.strip() if len(celdas) > 3 else ""
                info_basica['dependencia'] = celdas[4].text.strip() if len(celdas) > 4 else ""
                info_basica['estatus'] = celdas[5].text.strip() if len(celdas) > 5 else ""
            except Exception as e:
                logger.debug(f"    ⚠️ Error extrayendo info básica: {e}")
                info_basica = {
                    'numero_identificacion': celdas[1].text.strip() if len(celdas) > 1 else 'N/A',
                    'caracter': 'N/A', 
                    'titulo': 'N/A',
                    'dependencia': 'N/A',
                    'estatus': 'N/A'
                }
            
            logger.debug(f"[{indice+1}] {info_basica['numero_identificacion']}: {info_basica['titulo'][:50]}...")
            
            # MÉTODO FUNCIONAL: Click + window.location.href
            uuid_extraido = self._extraer_uuid_con_click(celdas[1])
            
            if uuid_extraido:
                return LicitacionUUID(
                    uuid=uuid_extraido,
                    numero_identificacion=info_basica['numero_identificacion'],
                    caracter=info_basica['caracter'],
                    titulo=info_basica['titulo'],
                    dependencia=info_basica['dependencia'],
                    estatus=info_basica['estatus'],
                    url_detalle=f"https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/{uuid_extraido}/procedimiento"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo UUID de fila {indice+1}: {e}")
            return None

    def _extraer_uuid_con_click(self, celda_objetivo) -> Optional[str]:
        """
        MÉTODO FUNCIONAL: Click + window.location.href para obtener UUID real
        Basado en el método que funciona de ComprasMX_v2Claude.py
        """
        try:
            logger.debug("    🔄 Click + window.location.href...")
            
            # 1. HACER CLICK EN LA CELDA (segunda columna)
            celda_objetivo.click()
            time.sleep(4)  # Esperar navegación
            
            # 2. CAPTURAR URL REAL USANDO window.location.href
            url_completa_real = self.driver.execute_script("return window.location.href;")
            logger.debug(f"    🌐 URL capturada: {url_completa_real}")
            
            # 3. EXTRAER UUID DEL PATRÓN DE URL
            if "/detalle/" in url_completa_real:
                patron = r'/detalle/([a-f0-9]{32})/'
                match = re.search(patron, url_completa_real)
                
                if match:
                    uuid = match.group(1)
                    logger.debug(f"    🔑 UUID extraído: {uuid}")
                    
                    # 4. REGRESAR AL LISTADO
                    self.driver.back()
                    time.sleep(3)  # Esperar a que se cargue el listado
                    
                    # 5. ESPERAR QUE LA TABLA SE RECARGUE
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody")))
                    time.sleep(1)
                    
                    return uuid
                else:
                    logger.debug("    ❌ No se encontró UUID en la URL")
            else:
                logger.debug("    ❌ URL no navega a detalle")
            
            # Si llegamos aquí, algo falló - intentar regresar
            current_url = self.driver.execute_script("return window.location.href;")
            if "/detalle/" in current_url:
                self.driver.back()
                time.sleep(2)
            
            return None
            
        except Exception as e:
            logger.debug(f"    ❌ Error en extracción UUID: {e}")
            # Intentar regresar en caso de error
            try:
                current_url = self.driver.execute_script("return window.location.href;")
                if "/detalle/" in current_url:
                    self.driver.back()
                    time.sleep(2)
            except:
                # Si todo falla, navegar directamente al listado
                self.driver.get(self.base_url)
                time.sleep(5)
            return None

    def extraer_todas_uuids(self, limite: int = 10) -> List[LicitacionUUID]:
        """
        Extraer UUIDs usando método funcional con click
        """
        logger.info(f"🔍 Iniciando extracción de UUIDs (límite: {limite})")
        logger.info("🎯 MÉTODO FUNCIONAL: Click + window.location.href")
        
        if not self.navegar_sitio_principal():
            return []
        
        filas_validas = self.obtener_filas_validas()
        if not filas_validas:
            return []
        
        # Limitar filas a procesar
        filas_a_procesar = filas_validas[:limite]
        logger.info(f"📋 Procesando {len(filas_a_procesar)} licitaciones")
        
        licitaciones_con_uuid = []
        
        for i, fila in enumerate(filas_a_procesar):
            self.stats['total_intentos'] += 1
            logger.info(f"[{i+1}/{len(filas_a_procesar)}] Extrayendo UUID con click...")
            
            # Re-obtener filas frescas después de navegación
            if i > 0:
                time.sleep(1)
                filas_actuales = self.obtener_filas_validas()
                if i < len(filas_actuales):
                    fila = filas_actuales[i]
                else:
                    logger.warning(f"Fila {i+1} ya no disponible, continuando...")
                    continue
            
            licitacion = self.extraer_uuid_fila(fila, i)
            
            if licitacion:
                licitaciones_con_uuid.append(licitacion)
                self.stats['uuids_extraidos'] += 1
                logger.info(f"    ✅ UUID extraído: {licitacion.uuid}")
            else:
                self.stats['errores'] += 1
                logger.warning(f"    ❌ No se pudo extraer UUID")
            
            # Pausa entre extracciones
            time.sleep(1)
        
        logger.info(f"✅ Extracción completada: {len(licitaciones_con_uuid)}/{len(filas_a_procesar)} UUIDs exitosos")
        return licitaciones_con_uuid

    def _procesar_con_haiku(self, texto: str) -> Optional[Dict]:
        """
        Enviar texto a Claude Haiku para extraer datos estructurados
        """
        try:
            # Limitar texto para evitar límites de API
            texto_limitado = texto[:6000] if len(texto) > 6000 else texto
            
            prompt = f"""Analiza el siguiente texto de una licitación de ComprasMX y extrae EXACTAMENTE la siguiente información en formato JSON.

CAMPOS A EXTRAER:
1. numero_procedimiento_contratacion
2. dependencia_entidad 
3. ramo
4. unidad_compradora
5. referencia_control_interno (Referencia / Numero de control interno)
6. nombre_procedimiento_contratacion
7. descripcion_detallada (Descripción detallada del procedimiento de contratación)
8. ley_soporte_normativo (Ley/Soporte normativo que rige la contratación)
9. tipo_procedimiento_contratacion (Tipo de procedimiento de contratación)
10. entidad_federativa_contratacion (Entidad Federativa donde se llevará a cabo la contratación)
11. fecha_publicacion (Fecha y hora de publicación)
12. fecha_apertura_proposiciones (Fecha y hora de presentación y apertura de proposiciones)
13. fecha_junta_aclaraciones (Fecha y hora de junta de aclaraciones, "N/A" si no existe)

REGLAS IMPORTANTES:
- Si no encuentras un campo, pon null
- Para fechas, extrae el formato exacto como aparece
- Responde SOLO con JSON válido, sin explicaciones, sin ```json, sin texto adicional
- El JSON debe ser parseable directamente

TEXTO A ANALIZAR:
{texto_limitado}
"""
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            contenido = response.content[0].text.strip()
            
            # Limpiar respuesta
            if contenido.startswith('```json'):
                contenido = contenido[7:]
            if contenido.endswith('```'):
                contenido = contenido[:-3]
            
            # Parsear JSON
            datos_extraidos = json.loads(contenido.strip())
            return datos_extraidos
            
        except Exception as e:
            logger.error(f"❌ Error en Haiku: {e}")
            return None

    def ejecutar_proceso_completo(self, limite: int = 1) -> Dict:
        """
        Ejecutar proceso completo: extracción con click + procesamiento con Haiku
        """
        logger.info("🚀 INICIANDO SCRAPER FUNCIONAL COMPRASMX")
        logger.info("🎯 MÉTODO FUNCIONAL: Click + window.location.href")
        logger.info("📦 ARCHIVO OPTIMIZADO: Sin texto_completo")
        logger.info("=" * 60)
        
        try:
            # Configurar driver
            self.configurar_driver()
            
            # Fase 1: Extraer UUIDs con click
            logger.info("\n📋 FASE 1: EXTRACCIÓN DE UUIDs CON CLICK")
            licitaciones_uuid = self.extraer_todas_uuids(limite=limite)
            
            if not licitaciones_uuid:
                logger.error("❌ No se extrajeron UUIDs")
                return {"error": "No se extrajeron UUIDs", "stats": self.stats}
            
            # Guardar resultados
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            archivo_json = f"comprasmx_funcional_{timestamp}.json"
            
            # Convertir dataclasses a dict para JSON - SIN texto_completo
            datos_json = []
            for resultado in licitaciones_uuid:
                datos_json.append({
                    'uuid': resultado.uuid,
                    'numero_identificacion': resultado.numero_identificacion,
                    'caracter': resultado.caracter,
                    'titulo_basico': resultado.titulo,
                    'dependencia': resultado.dependencia,
                    'estatus': resultado.estatus,
                    'url_detalle': resultado.url_detalle,
                    'fecha_scraping': datetime.now().isoformat(),
                    'procesado_haiku': False,
                    'fuente': 'ComprasMX'
                })
            
            with open(archivo_json, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_procesamiento': datetime.now().isoformat(),
                    'total_licitaciones': len(datos_json),
                    'procesado_con_haiku': False,
                    'fuente': 'ComprasMX',
                    'licitaciones': datos_json
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Resultados guardados en: {archivo_json}")
            
            # Estadísticas finales
            logger.info(f"\n🎉 PROCESO COMPLETADO EXITOSAMENTE!")
            logger.info("=" * 60)
            logger.info(f"📊 ESTADÍSTICAS FINALES:")
            logger.info(f"  🔑 UUIDs extraídos: {self.stats['uuids_extraidos']}")
            logger.info(f"  ❌ Errores: {self.stats['errores']}")
            logger.info(f"  💾 Archivo generado: {archivo_json}")
            
            return {
                "success": True,
                "archivo_generado": archivo_json,
                "resultados": datos_json,
                "stats": self.stats
            }
            
        except Exception as e:
            logger.error(f"❌ Error crítico: {e}")
            return {"error": str(e), "stats": self.stats}
        
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("✅ Driver cerrado correctamente")

def main():
    """
    Función principal para ejecutar el scraper funcional
    """
    # Configuración
    LIMITE = 5  # Probar con 5 licitaciones
    HEADLESS = False  # False para ver qué está pasando
    
    # Verificar clave de Anthropic desde .env
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        logger.warning("⚠️ ANTHROPIC_API_KEY no configurada, continuando sin IA")
    else:
        logger.info(f"✅ ANTHROPIC_API_KEY cargada: {api_key[:10]}...")
    
    # Ejecutar scraper funcional
    scraper = ComprasMXScraperFuncional(headless=HEADLESS, anthropic_api_key=api_key)
    resultado = scraper.ejecutar_proceso_completo(limite=LIMITE)
    
    if resultado.get("success"):
        print(f"\n✅ SCRAPER FUNCIONAL COMPLETADO EXITOSAMENTE")
        print(f"📁 Archivo JSON generado: {resultado['archivo_generado']}")
        print(f"📊 UUIDs procesados: {resultado['stats']['uuids_extraidos']}")
    else:
        print(f"❌ ERROR: {resultado.get('error')}")

if __name__ == "__main__":
    main()
