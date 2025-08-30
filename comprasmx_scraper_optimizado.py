#!/usr/bin/env python3
"""
ComprasMX Scraper Optimizado con Claude Haiku
Versión mejorada que usa técnicas robustas para extracción de UUIDs
y Claude Haiku para estructurar los datos extraídos.
"""

import time
import json
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import anthropic
import os
from typing import Dict, List, Optional, Tuple

class ComprasMXScraperOptimizado:
    def __init__(self, anthropic_api_key: str = None):
        """
        Inicializar el scraper optimizado
        
        Args:
            anthropic_api_key: Clave de API de Anthropic (opcional, usa variable de entorno)
        """
        self.base_url = "https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/busqueda-procedimientos"
        self.driver = None
        self.wait = None
        
        # Configurar cliente de Anthropic
        api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            print("✅ Cliente de Claude configurado")
        else:
            self.anthropic_client = None
            print("⚠️  Clave de Anthropic no configurada - funcionará sin IA")
        
        # Estadísticas
        self.stats = {
            'total_procesadas': 0,
            'uuids_exitosos': 0,
            'datos_completos': 0,
            'errores': 0
        }

    def configurar_driver(self, headless: bool = True) -> None:
        """Configurar el driver de Chrome con opciones optimizadas"""
        print("🔧 Configurando driver de Chrome...")
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Opciones para mejor rendimiento y estabilidad
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        
        # User agent para evitar detección
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
        print("✅ Driver configurado exitosamente")

    def navegar_a_sitio(self) -> None:
        """Navegar al sitio de ComprasMX y esperar a que cargue"""
        print("🌐 Navegando a ComprasMX...")
        
        self.driver.get(self.base_url)
        time.sleep(3)
        
        # Esperar a que aparezca la tabla
        try:
            tabla = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p-table"))
            )
            print("✅ Página cargada exitosamente")
            
            # Scroll para asegurar que todo esté cargado
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
        except TimeoutException:
            print("❌ Error: La página no cargó correctamente")
            raise

    def extraer_uuids_mejorado(self, limite: int = 100) -> List[Dict]:
        """
        Extrae UUIDs usando múltiples técnicas robustas
        
        Args:
            limite: Número máximo de registros a procesar
            
        Returns:
            Lista de diccionarios con información básica y UUIDs
        """
        print(f"🔍 Iniciando extracción de UUIDs (límite: {limite})...")
        licitaciones = []
        
        for indice in range(limite):
            try:
                print(f"[{indice + 1}/{limite}] Extrayendo UUID...")
                
                # Encontrar la fila usando múltiples selectores
                fila = self._encontrar_fila_por_indice(indice)
                if not fila:
                    print(f"    ❌ No se pudo encontrar la fila {indice + 1}")
                    continue
                
                # Extraer información básica de la fila
                info_basica = self._extraer_info_basica_fila(fila)
                if not info_basica:
                    print(f"    ❌ No se pudo extraer información básica")
                    continue
                
                print(f"    📄 {info_basica.get('numero_identificacion', 'N/A')}: {info_basica.get('titulo', 'N/A')[:60]}...")
                
                # Intentar extraer UUID con múltiples métodos
                uuid = self._extraer_uuid_robusto(fila, indice)
                
                if uuid:
                    print(f"    🔑 UUID: {uuid}")
                    info_basica['uuid'] = uuid
                    info_basica['url_detalle'] = f"https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/{uuid}/procedimiento"
                    licitaciones.append(info_basica)
                    self.stats['uuids_exitosos'] += 1
                else:
                    print(f"    ❌ Error extrayendo UUID de fila {indice + 1}")
                
                self.stats['total_procesadas'] += 1
                
                # Pequeña pausa entre extracciones
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    ❌ Error general en fila {indice + 1}: {str(e)[:100]}")
                self.stats['errores'] += 1
                continue
        
        print(f"\n✅ EXTRACCIÓN DE UUIDs COMPLETADA")
        print(f"📊 Total procesadas: {self.stats['total_procesadas']}")
        print(f"🔑 UUIDs exitosos: {self.stats['uuids_exitosos']}/{self.stats['total_procesadas']} ({(self.stats['uuids_exitosos']/max(self.stats['total_procesadas'], 1))*100:.1f}%)")
        
        return licitaciones

    def _encontrar_fila_por_indice(self, indice: int):
        """Encuentra una fila usando múltiples selectores"""
        selectores = [
            f"p-table tbody tr:nth-child({indice + 1})",
            f"tbody tr:nth-child({indice + 1})",
            f"table tbody tr:nth-child({indice + 1})",
            f"[role='row']:nth-child({indice + 1})"
        ]
        
        for selector in selectores:
            try:
                elementos = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elementos:
                    return elementos[0]
            except:
                continue
        
        return None

    def _extraer_info_basica_fila(self, fila) -> Optional[Dict]:
        """Extrae información básica de una fila de la tabla"""
        try:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) < 5:
                return None
            
            return {
                'numero_identificacion': celdas[0].text.strip(),
                'caracter': celdas[1].text.strip(),
                'titulo': celdas[2].text.strip(),
                'dependencia': celdas[3].text.strip(),
                'estatus': celdas[4].text.strip(),
            }
        except Exception:
            return None

    def _extraer_uuid_robusto(self, fila, indice: int) -> Optional[str]:
        """
        Extrae UUID usando múltiples técnicas robustas
        
        Métodos:
        1. Click directo en la celda ID
        2. Click con JavaScript
        3. Click con ActionChains
        4. Scroll y click
        """
        metodos = [
            self._metodo_click_directo,
            self._metodo_javascript_click,
            self._metodo_action_chains,
            self._metodo_scroll_click
        ]
        
        for i, metodo in enumerate(metodos, 1):
            try:
                print(f"        🔄 Probando método {i}...")
                uuid = metodo(fila, indice)
                if uuid:
                    print(f"        ✅ Método {i} exitoso")
                    return uuid
            except Exception as e:
                print(f"        ❌ Método {i} falló: {str(e)[:50]}...")
                continue
        
        return None

    def _metodo_click_directo(self, fila, indice: int) -> Optional[str]:
        """Método 1: Click directo en la primera celda"""
        celda_id = fila.find_element(By.TAG_NAME, "td")
        celda_id.click()
        return self._obtener_uuid_de_url()

    def _metodo_javascript_click(self, fila, indice: int) -> Optional[str]:
        """Método 2: Click usando JavaScript"""
        celda_id = fila.find_element(By.TAG_NAME, "td")
        self.driver.execute_script("arguments[0].click();", celda_id)
        return self._obtener_uuid_de_url()

    def _metodo_action_chains(self, fila, indice: int) -> Optional[str]:
        """Método 3: Click usando ActionChains"""
        celda_id = fila.find_element(By.TAG_NAME, "td")
        actions = ActionChains(self.driver)
        actions.move_to_element(celda_id).click().perform()
        return self._obtener_uuid_de_url()

    def _metodo_scroll_click(self, fila, indice: int) -> Optional[str]:
        """Método 4: Scroll hasta el elemento y click"""
        # Scroll hasta que la fila esté visible
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", fila)
        time.sleep(0.5)
        
        # Intentar scroll hacia arriba para evitar elementos superpuestos
        self.driver.execute_script("window.scrollBy(0, -100);")
        time.sleep(0.3)
        
        celda_id = fila.find_element(By.TAG_NAME, "td")
        
        # Click usando coordenadas específicas
        try:
            # Obtener dimensiones del elemento
            location = celda_id.location_once_scrolled_into_view
            size = celda_id.size
            
            # Click en el centro-derecha de la celda
            actions = ActionChains(self.driver)
            actions.move_to_element_with_offset(
                celda_id, 
                size['width'] * 0.7,  # 70% hacia la derecha
                size['height'] * 0.5   # Centro vertical
            ).click().perform()
            
            return self._obtener_uuid_de_url()
        except:
            # Fallback: click simple
            celda_id.click()
            return self._obtener_uuid_de_url()

    def _obtener_uuid_de_url(self) -> Optional[str]:
        """Extrae el UUID de la URL actual después del click"""
        time.sleep(1)  # Esperar a que cambie la URL
        
        url_actual = self.driver.current_url
        
        # Buscar UUID en la URL usando regex
        patron = r'/detalle/([a-f0-9-]{36})/procedimiento'
        match = re.search(patron, url_actual)
        
        if match:
            uuid = match.group(1)
            # Volver a la página principal
            self.driver.back()
            time.sleep(1)
            return uuid
        
        return None

    def scraping_detallado_con_ia(self, licitaciones: List[Dict]) -> List[Dict]:
        """
        Realiza scraping detallado usando IA para estructurar los datos
        
        Args:
            licitaciones: Lista de licitaciones con UUIDs
            
        Returns:
            Lista de licitaciones con datos completos y estructurados
        """
        print(f"\n🎯 FUNCIÓN 2: Scraping detallado con IA de {len(licitaciones)} licitaciones...")
        
        datos_completos = []
        
        for i, licitacion in enumerate(licitaciones, 1):
            try:
                print(f"\n[{i}/{len(licitaciones)}] Scraping UUID: {licitacion['uuid']}")
                
                # Navegar a la página de detalle
                url_detalle = licitacion['url_detalle']
                print(f"    🔗 URL: {url_detalle}")
                
                self.driver.get(url_detalle)
                time.sleep(3)
                
                # Extraer texto completo
                texto_completo = self._extraer_texto_completo()
                print(f"    📄 Extrayendo texto completo con document.body.textContent...")
                print(f"    ✅ Texto extraído: {len(texto_completo)} caracteres")
                
                # Procesar con IA si está disponible
                if self.anthropic_client and texto_completo:
                    datos_estructurados = self._procesar_con_ia(texto_completo)
                    if datos_estructurados:
                        print(f"    🤖 IA procesó exitosamente los datos")
                        # Combinar datos básicos con datos de IA
                        licitacion.update(datos_estructurados)
                    else:
                        print(f"    ⚠️  IA no pudo procesar, usando extracción básica")
                        # Fallback a extracción básica
                        campos_basicos = self._extraer_campos_basicos(texto_completo)
                        licitacion.update(campos_basicos)
                else:
                    # Extracción básica sin IA
                    campos_basicos = self._extraer_campos_basicos(texto_completo)
                    licitacion.update(campos_basicos)
                
                # Agregar metadatos
                licitacion['texto_completo'] = texto_completo
                licitacion['fecha_scraping'] = datetime.now().isoformat()
                
                datos_completos.append(licitacion)
                self.stats['datos_completos'] += 1
                
                print(f"    ✅ Scraping completado")
                
            except Exception as e:
                print(f"    ❌ Error en scraping detallado: {str(e)[:100]}")
                self.stats['errores'] += 1
                continue
        
        return datos_completos

    def _extraer_texto_completo(self) -> str:
        """Extrae el texto completo de la página"""
        try:
            # Esperar a que cargue el contenido
            time.sleep(2)
            
            # Extraer usando JavaScript para obtener todo el texto
            texto = self.driver.execute_script("return document.body.textContent;")
            return texto.strip() if texto else ""
            
        except Exception:
            return ""

    def _procesar_con_ia(self, texto: str) -> Optional[Dict]:
        """
        Procesa el texto usando Claude Haiku para estructurar los datos
        
        Args:
            texto: Texto completo de la licitación
            
        Returns:
            Diccionario con datos estructurados o None si hay error
        """
        try:
            prompt = f"""
            Analiza el siguiente texto de una licitación de ComprasMX y extrae la información en formato JSON.

            Busca y extrae EXACTAMENTE estos campos:
            - codigo_expediente
            - nombre_procedimiento
            - descripcion_detallada
            - tipo_procedimiento
            - fecha_publicacion
            - fecha_apertura
            - fecha_fallo
            - importe_estimado
            - unidad_compradora
            - entidad_federativa
            - plazo_ejecucion

            REGLAS IMPORTANTES:
            1. Si no encuentras un campo, pon null
            2. Para las fechas, extrae el formato exacto como aparece
            3. Para importes, incluye la moneda si está especificada
            4. Responde SOLO con JSON válido, sin explicaciones

            TEXTO A ANALIZAR:
            {texto[:4000]}  # Limitar para no exceder límites de API

            JSON:
            """
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            # Extraer JSON de la respuesta
            contenido = response.content[0].text.strip()
            
            # Limpiar la respuesta para extraer solo el JSON
            if contenido.startswith('```json'):
                contenido = contenido[7:]
            if contenido.endswith('```'):
                contenido = contenido[:-3]
            
            datos = json.loads(contenido.strip())
            return datos
            
        except Exception as e:
            print(f"    ❌ Error en procesamiento con IA: {str(e)}")
            return None

    def _extraer_campos_basicos(self, texto: str) -> Dict:
        """Extrae campos básicos usando regex como fallback"""
        campos = {}
        
        # Patrones regex para extraer información
        patrones = {
            'codigo_expediente': r'Código del expediente:\s*([^\n]+)',
            'nombre_procedimiento': r'Nombre del procedimiento[^:]*:\s*([^\n]+)',
            'fecha_publicacion': r'Fecha y hora de publicación:\s*([^\n]+)',
            'fecha_apertura': r'Fecha y hora de presentación[^:]*:\s*([^\n]+)',
            'fecha_fallo': r'Fecha y hora del acto del Fallo:\s*([^\n]+)',
            'plazo_ejecucion': r'Plazo de ejecucion[^:]*:\s*([^\n]+)',
            'unidad_compradora': r'Unidad compradora:\s*([^\n]+)',
            'entidad_federativa': r'Entidad Federativa[^:]*:\s*([^\n]+)',
        }
        
        for campo, patron in patrones.items():
            match = re.search(patron, texto, re.IGNORECASE)
            campos[campo] = match.group(1).strip() if match else None
        
        return campos

    def guardar_resultados(self, datos: List[Dict], prefijo: str = "comprasmx_optimizado") -> Tuple[str, str]:
        """Guarda los resultados en CSV y JSON"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Guardar CSV
        archivo_csv = f"{prefijo}_{timestamp}.csv"
        with open(archivo_csv, 'w', newline='', encoding='utf-8') as f:
            if datos:
                writer = csv.DictWriter(f, fieldnames=datos[0].keys())
                writer.writeheader()
                writer.writerows(datos)
        
        # Guardar JSON
        archivo_json = f"{prefijo}_{timestamp}.json"
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        return archivo_csv, archivo_json

    def ejecutar_scraping_completo(self, limite: int = 100, headless: bool = True) -> Dict:
        """
        Ejecuta el proceso completo de scraping
        
        Args:
            limite: Número máximo de registros a procesar
            headless: Si ejecutar en modo headless
            
        Returns:
            Diccionario con estadísticas del proceso
        """
        try:
            print("🚀 INICIANDO SCRAPING OPTIMIZADO DE COMPRASMX")
            print("=" * 60)
            
            # Configurar y navegar
            self.configurar_driver(headless=headless)
            self.navegar_a_sitio()
            
            # Fase 1: Extraer UUIDs
            licitaciones = self.extraer_uuids_mejorado(limite)
            
            if not licitaciones:
                print("❌ No se pudieron extraer UUIDs")
                return self.stats
            
            # Guardar UUIDs
            archivo_uuids_csv, archivo_uuids_json = self.guardar_resultados(
                licitaciones, "comprasmx_uuids_optimizado"
            )
            print(f"💾 UUIDs guardados en: {archivo_uuids_json}")
            
            # Fase 2: Scraping detallado con IA
            datos_completos = self.scraping_detallado_con_ia(licitaciones)
            
            if datos_completos:
                # Guardar datos completos
                archivo_csv, archivo_json = self.guardar_resultados(
                    datos_completos, "comprasmx_datos_optimizado"
                )
                
                print(f"\n🎉 SCRAPING COMPLETADO EXITOSAMENTE!")
                print("=" * 60)
                print(f"📊 ESTADÍSTICAS FINALES:")
                print(f"  📋 Total procesadas: {self.stats['total_procesadas']}")
                print(f"  🔑 UUIDs exitosos: {self.stats['uuids_exitosos']}")
                print(f"  📊 Datos completos: {self.stats['datos_completos']}")
                print(f"  ❌ Errores: {self.stats['errores']}")
                print(f"\n💾 ARCHIVOS GENERADOS:")
                print(f"  📊 CSV: {archivo_csv}")
                print(f"  📋 JSON: {archivo_json}")
            
            return self.stats
            
        except Exception as e:
            print(f"❌ Error general: {str(e)}")
            self.stats['errores'] += 1
            return self.stats
            
        finally:
            if self.driver:
                self.driver.quit()
                print("✅ Driver cerrado correctamente")

def main():
    """Función principal"""
    # Configuración
    LIMITE = 100
    HEADLESS = False  # Cambiar a True para ejecución silenciosa
    
    # Verificar clave de Anthropic
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  Variable de entorno ANTHROPIC_API_KEY no configurada")
        print("   El scraper funcionará sin IA. Para usar IA:")
        print("   export ANTHROPIC_API_KEY='tu_clave_aqui'")
        print()
    
    # Ejecutar scraper
    scraper = ComprasMXScraperOptimizado(anthropic_api_key=api_key)
    resultados = scraper.ejecutar_scraping_completo(
        limite=LIMITE, 
        headless=HEADLESS
    )
    
    print(f"\n📈 Proceso completado con {resultados['uuids_exitosos']} UUIDs exitosos")

if __name__ == "__main__":
    main()