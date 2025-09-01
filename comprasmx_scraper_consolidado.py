#!/usr/bin/env python3
"""
ComprasMX Scraper Consolidado - Versión Simplificada
====================================================

OBJETIVO:
1. Extraer UUIDs de ComprasMX usando window.location.href (método real)
2. Ir a cada licitación individual y extraer texto completo
3. Usar Claude Haiku para estructurar datos específicos
4. Output: JSON estructurado

SIMPLIFICADO: UN SOLO método de extracción - el que funciona realmente
BASADO EN: ComprasMX_v2Claude.py que usa window.location.href

Autor: Claude + Usuario
Versión: 2.0 - Método único window.location.href
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
    texto_completo: str
    # Campos extraídos por Haiku
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

class ComprasMXScraperSimplificado:
    """
    Scraper simplificado para ComprasMX
    USA UN SOLO MÉTODO: window.location.href después del click
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
        """Navegar al sitio principal y esperar que cargue la tabla"""
        logger.info(f"🌐 Navegando a ComprasMX: {self.base_url}")
        
        try:
            self.driver.get(self.base_url)
            time.sleep(8)  # Espera inicial
            
            # Verificar que la tabla esté presente
            tabla_presente = self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            if tabla_presente:
                logger.info("✅ Sitio cargado exitosamente")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error cargando sitio: {e}")
        
        return False

    def obtener_filas_validas(self) -> List:
        """Obtener filas válidas de la tabla principal"""
        try:
            all_rows = self.driver.find_elements(By.TAG_NAME, "tr")
            filas_validas = []
            
            for row in all_rows:
                celdas = row.find_elements(By.TAG_NAME, "td")
                if len(celdas) >= 5:  # Verificar columnas suficientes
                    texto_primera_celda = celdas[0].text.strip()
                    # Filtrar filas de header y vacías
                    if (texto_primera_celda and 
                        len(texto_primera_celda) > 3 and 
                        not texto_primera_celda.lower().startswith(("número", "no.", "#"))):
                        filas_validas.append(row)
            
            logger.info(f"📊 Encontradas {len(filas_validas)} filas válidas de licitaciones")
            return filas_validas
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo filas: {e}")
            return []

    def extraer_uuid_fila(self, fila, indice: int) -> Optional[LicitacionUUID]:
        """
        Extraer UUID de una fila usando SOLO window.location.href
        MÉTODO ÚNICO - como en ComprasMX_v2Claude.py
        """
        try:
            # Extraer información básica de la fila
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) < 5:
                return None
            
            info_basica = {
                'numero_identificacion': celdas[0].text.strip(),
                'caracter': celdas[1].text.strip(),
                'titulo': celdas[2].text.strip(),
                'dependencia': celdas[3].text.strip(),
                'estatus': celdas[4].text.strip(),
            }
            
            logger.debug(f"[{indice+1}] {info_basica['numero_identificacion']}: {info_basica['titulo'][:50]}...")
            
            # MÉTODO ÚNICO: Click y capturar window.location.href
            uuid_extraido = self._extraer_uuid_window_location(celdas[0])
            
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

    def _extraer_uuid_window_location(self, celda_objetivo) -> Optional[str]:
        """
        MÉTODO ÚNICO: Click y usar window.location.href para obtener UUID real
        Basado en el método funcional de ComprasMX_v2Claude.py
        """
        try:
            logger.debug("    🔄 Click y captura window.location.href...")
            
            # 1. HACER CLICK EN LA CELDA
            celda_objetivo.click()
            time.sleep(3)  # Esperar navegación
            
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
                    time.sleep(2)
                    return uuid
                else:
                    logger.debug("    ❌ No se encontró UUID en la URL")
            else:
                logger.debug("    ❌ URL no navega a detalle")
            
            # Si llegamos aquí, algo falló - regresar si es posible
            if "/detalle/" in url_completa_real:
                self.driver.back()
                time.sleep(1)
            
            return None
            
        except Exception as e:
            logger.debug(f"    ❌ Error en extracción UUID: {e}")
            # Intentar regresar en caso de error
            try:
                current_url = self.driver.execute_script("return window.location.href;")
                if "/detalle/" in current_url:
                    self.driver.back()
                    time.sleep(1)
            except:
                pass
            return None

    def extraer_todas_uuids(self, limite: int = 10) -> List[LicitacionUUID]:
        """
        Extraer UUIDs de todas las licitaciones usando método único
        """
        logger.info(f"🔍 Iniciando extracción de UUIDs (límite: {limite})")
        logger.info("🎯 MÉTODO ÚNICO: window.location.href después de click")
        
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
            logger.info(f"[{i+1}/{len(filas_a_procesar)}] Extrayendo UUID...")
            
            # Re-obtener filas frescas para evitar stale elements
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

    def procesar_licitacion_con_haiku(self, licitacion: LicitacionUUID) -> LicitacionCompleta:
        """
        Procesar una licitación individual:
        1. Navegar a URL de detalle
        2. Extraer texto completo con document.body.textContent
        3. Enviar a Claude Haiku para estructurar datos
        """
        logger.info(f"🤖 Procesando {licitacion.uuid} con Haiku...")
        
        # Crear objeto de respuesta
        resultado = LicitacionCompleta(
            uuid=licitacion.uuid,
            numero_identificacion=licitacion.numero_identificacion,
            titulo_basico=licitacion.titulo,
            url_detalle=licitacion.url_detalle,
            texto_completo="",
            fecha_scraping=datetime.now().isoformat()
        )
        
        try:
            # Navegar a la página de detalle
            logger.debug(f"    🔗 Navegando a: {licitacion.url_detalle}")
            self.driver.get(licitacion.url_detalle)
            
            # Esperar que cargue el contenido
            time.sleep(8)  # Tiempo suficiente para carga completa
            
            # Extraer texto completo usando document.body.textContent
            logger.debug("    📄 Extrayendo texto completo...")
            texto_completo = self.driver.execute_script("return document.body.textContent;")
            
            if not texto_completo or len(texto_completo.strip()) < 500:
                logger.warning("    ⚠️  Texto insuficiente, esperando más tiempo...")
                time.sleep(5)
                texto_completo = self.driver.execute_script("return document.body.textContent;")
            
            resultado.texto_completo = texto_completo.strip() if texto_completo else ""
            logger.debug(f"    ✅ Texto extraído: {len(resultado.texto_completo)} caracteres")
            
            # Procesar con Haiku si está disponible
            if self.anthropic_client and resultado.texto_completo:
                datos_haiku = self._procesar_con_haiku(resultado.texto_completo)
                if datos_haiku:
                    # Asignar datos extraídos por Haiku
                    resultado.numero_procedimiento_contratacion = datos_haiku.get('numero_procedimiento_contratacion')
                    resultado.dependencia_entidad = datos_haiku.get('dependencia_entidad')
                    resultado.ramo = datos_haiku.get('ramo')
                    resultado.unidad_compradora = datos_haiku.get('unidad_compradora')
                    resultado.referencia_control_interno = datos_haiku.get('referencia_control_interno')
                    resultado.nombre_procedimiento_contratacion = datos_haiku.get('nombre_procedimiento_contratacion')
                    resultado.descripcion_detallada = datos_haiku.get('descripcion_detallada')
                    resultado.ley_soporte_normativo = datos_haiku.get('ley_soporte_normativo')
                    resultado.tipo_procedimiento_contratacion = datos_haiku.get('tipo_procedimiento_contratacion')
                    resultado.entidad_federativa_contratacion = datos_haiku.get('entidad_federativa_contratacion')
                    resultado.fecha_publicacion = datos_haiku.get('fecha_publicacion')
                    resultado.fecha_apertura_proposiciones = datos_haiku.get('fecha_apertura_proposiciones')
                    resultado.fecha_junta_aclaraciones = datos_haiku.get('fecha_junta_aclaraciones')
                    
                    resultado.procesado_haiku = True
                    self.stats['procesadas_con_haiku'] += 1
                    logger.info("    🤖 ✅ Procesado exitosamente con Haiku")
                else:
                    resultado.error_haiku = "Error procesando con Haiku"
                    logger.warning("    🤖 ❌ Error procesando con Haiku")
            else:
                resultado.error_haiku = "Haiku no configurado o texto insuficiente"
                logger.warning("    🤖 ⚠️  Haiku no disponible")
            
            self.stats['licitaciones_procesadas'] += 1
            return resultado
            
        except Exception as e:
            logger.error(f"    ❌ Error procesando licitación: {e}")
            resultado.error_haiku = str(e)
            self.stats['errores'] += 1
            return resultado

    def _procesar_con_haiku(self, texto: str) -> Optional[Dict]:
        """
        Enviar texto a Claude Haiku para extraer datos estructurados
        """
        try:
            # Limitar texto para evitar límites de API
            texto_limitado = texto[:6000] if len(texto) > 6000 else texto
            
            prompt = f"""
Analiza el siguiente texto de una licitación de ComprasMX y extrae EXACTAMENTE la siguiente información en formato JSON.

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

    def procesar_todas_licitaciones(self, licitaciones: List[LicitacionUUID]) -> List[LicitacionCompleta]:
        """
        Procesar todas las licitaciones con Haiku
        """
        logger.info(f"🤖 Iniciando procesamiento de {len(licitaciones)} licitaciones con Haiku")
        
        resultados = []
        
        for i, licitacion in enumerate(licitaciones, 1):
            logger.info(f"[{i}/{len(licitaciones)}] Procesando {licitacion.numero_identificacion}")
            
            resultado = self.procesar_licitacion_con_haiku(licitacion)
            resultados.append(resultado)
            
            # Pausa entre requests para no sobrecargar
            time.sleep(2)
        
        return resultados

    def guardar_resultados_json(self, resultados: List[LicitacionCompleta], archivo: str = None) -> str:
        """Guardar resultados en formato JSON"""
        if not archivo:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            archivo = f"comprasmx_simplificado_{timestamp}.json"
        
        # Convertir dataclasses a dict para JSON
        datos_json = []
        for resultado in resultados:
            datos_json.append({
                'uuid': resultado.uuid,
                'numero_identificacion': resultado.numero_identificacion,
                'titulo_basico': resultado.titulo_basico,
                'url_detalle': resultado.url_detalle,
                'texto_completo': resultado.texto_completo,
                'numero_procedimiento_contratacion': resultado.numero_procedimiento_contratacion,
                'dependencia_entidad': resultado.dependencia_entidad,
                'ramo': resultado.ramo,
                'unidad_compradora': resultado.unidad_compradora,
                'referencia_control_interno': resultado.referencia_control_interno,
                'nombre_procedimiento_contratacion': resultado.nombre_procedimiento_contratacion,
                'descripcion_detallada': resultado.descripcion_detallada,
                'ley_soporte_normativo': resultado.ley_soporte_normativo,
                'tipo_procedimiento_contratacion': resultado.tipo_procedimiento_contratacion,
                'entidad_federativa_contratacion': resultado.entidad_federativa_contratacion,
                'fecha_publicacion': resultado.fecha_publicacion,
                'fecha_apertura_proposiciones': resultado.fecha_apertura_proposiciones,
                'fecha_junta_aclaraciones': resultado.fecha_junta_aclaraciones,
                'fecha_scraping': resultado.fecha_scraping,
                'procesado_haiku': resultado.procesado_haiku,
                'error_haiku': resultado.error_haiku
            })
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Resultados guardados en: {archivo}")
        return archivo

    def ejecutar_proceso_completo(self, limite: int = 1) -> Dict:
        """
        Ejecutar proceso completo: extracción de UUIDs + procesamiento con Haiku
        
        Args:
            limite: Número de licitaciones a procesar (para primera iteración)
            
        Returns:
            Dict con estadísticas y resultados
        """
        logger.info("🚀 INICIANDO SCRAPER SIMPLIFICADO COMPRASMX")
        logger.info("🎯 MÉTODO ÚNICO: window.location.href")
        logger.info("=" * 60)
        
        try:
            # Configurar driver
            self.configurar_driver()
            
            # Fase 1: Extraer UUIDs
            logger.info("\n📋 FASE 1: EXTRACCIÓN DE UUIDs CON MÉTODO ÚNICO")
            licitaciones_uuid = self.extraer_todas_uuids(limite=limite)
            
            if not licitaciones_uuid:
                logger.error("❌ No se extrajeron UUIDs")
                return {"error": "No se extrajeron UUIDs", "stats": self.stats}
            
            # Fase 2: Procesamiento con Haiku
            logger.info(f"\n🤖 FASE 2: PROCESAMIENTO CON HAIKU")
            resultados = self.procesar_todas_licitaciones(licitaciones_uuid)
            
            # Guardar resultados
            archivo_json = self.guardar_resultados_json(resultados)
            
            # Estadísticas finales
            logger.info(f"\n🎉 PROCESO COMPLETADO EXITOSAMENTE!")
            logger.info("=" * 60)
            logger.info(f"📊 ESTADÍSTICAS FINALES:")
            logger.info(f"  📋 Total intentos: {self.stats['total_intentos']}")
            logger.info(f"  🔑 UUIDs extraídos: {self.stats['uuids_extraidos']}")
            logger.info(f"  📊 Licitaciones procesadas: {self.stats['licitaciones_procesadas']}")
            logger.info(f"  🤖 Procesadas con Haiku: {self.stats['procesadas_con_haiku']}")
            logger.info(f"  ❌ Errores: {self.stats['errores']}")
            logger.info(f"  💾 Archivo generado: {archivo_json}")
            
            return {
                "success": True,
                "archivo_generado": archivo_json,
                "resultados": resultados,
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
    Función principal para ejecutar el scraper simplificado
    """
    # Configuración
    LIMITE = 1  # Solo 1 para primera iteración de prueba
    HEADLESS = False  # False para ver qué está pasando
    
    # Verificar clave de Anthropic desde .env
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        logger.error("❌ ANTHROPIC_API_KEY no configurada correctamente en .env")
        logger.error("   1. Copia .env.example a .env: cp .env.example .env")
        logger.error("   2. Edita .env y pon tu clave real de Anthropic")
        logger.error("   3. Asegúrate que no sea 'your_api_key_here'")
        return
    
    print(f"✅ ANTHROPIC_API_KEY cargada desde .env: {api_key[:10]}...")
    
    # Ejecutar scraper simplificado
    scraper = ComprasMXScraperSimplificado(headless=HEADLESS, anthropic_api_key=api_key)
    resultado = scraper.ejecutar_proceso_completo(limite=LIMITE)
    
    if resultado.get("success"):
        print(f"\n✅ SCRAPER SIMPLIFICADO COMPLETADO EXITOSAMENTE")
        print(f"🎯 MÉTODO ÚNICO: window.location.href funcionó correctamente")
        print(f"📁 Archivo JSON generado: {resultado['archivo_generado']}")
        print(f"📊 UUIDs procesados: {resultado['stats']['uuids_extraidos']}")
        print(f"🤖 Procesados con Haiku: {resultado['stats']['procesadas_con_haiku']}")
        
        # Mostrar ejemplo de resultado
        if resultado['resultados']:
            primer_resultado = resultado['resultados'][0]
            print(f"\n📋 EJEMPLO DE RESULTADO:")
            print(f"  UUID: {primer_resultado.uuid}")
            print(f"  Título: {primer_resultado.titulo_basico[:100]}...")
            print(f"  Procesado con Haiku: {primer_resultado.procesado_haiku}")
            if primer_resultado.procesado_haiku:
                print(f"  Nombre procedimiento: {primer_resultado.nombre_procedimiento_contratacion}")
                print(f"  Dependencia: {primer_resultado.dependencia_entidad}")
    else:
        print(f"❌ ERROR: {resultado.get('error')}")

if __name__ == "__main__":
    main()
