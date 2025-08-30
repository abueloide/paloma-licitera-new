#!/usr/bin/env python3
"""
ComprasMX Scraper con Claude Haiku - SIMPLIFICADO
Solo extrae UUIDs y usa Haiku para procesar
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
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import anthropic
import os
from typing import Dict, List, Optional, Tuple

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv no instalado, usando variables de entorno del sistema")

class ComprasMXScraperSimple:
    def __init__(self):
        """Inicializar scraper simple"""
        self.base_url = "https://comprasmx.buengobierno.gob.mx/sitiopublico/#"  # URL CORRECTA
        self.driver = None
        self.wait = None
        
        # Configurar cliente de Anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            print("✅ Cliente de Claude configurado")
        else:
            self.anthropic_client = None
            print("❌ REQUIERE CLAVE DE ANTHROPIC")
            exit(1)

    def configurar_driver(self) -> None:
        """Configurar driver simple"""
        print("🔧 Configurando driver...")
        
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Comentado para debug
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1200,800")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)  # Más tiempo
        print("✅ Driver configurado")

    def extraer_uuid_simple(self, indice: int) -> Optional[Dict]:
        """Extrae UUID de una fila específica usando el método que funcionó"""
        try:
            # Encontrar todas las filas
            filas = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            if indice >= len(filas):
                return None
            
            fila = filas[indice]
            
            # Extraer información básica
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) < 5:
                return None
            
            info = {
                'numero_identificacion': celdas[0].text.strip(),
                'caracter': celdas[1].text.strip(),
                'titulo': celdas[2].text.strip(),
                'dependencia': celdas[3].text.strip(),
                'estatus': celdas[4].text.strip(),
            }
            
            print(f"📄 {info['numero_identificacion']}: {info['titulo'][:60]}...")
            
            # Click en la primera celda para obtener UUID
            try:
                celdas[0].click()
                time.sleep(2)
                
                # Obtener UUID de la URL
                url_actual = self.driver.current_url
                match = re.search(r'/detalle/([a-f0-9-]{36})/procedimiento', url_actual)
                
                if match:
                    uuid = match.group(1)
                    print(f"🔑 UUID: {uuid}")
                    
                    info['uuid'] = uuid
                    info['url_detalle'] = f"https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/{uuid}/procedimiento"
                    
                    # Regresar a la lista
                    self.driver.back()
                    time.sleep(2)
                    
                    return info
                else:
                    print("❌ UUID no encontrado en URL")
                    self.driver.back()
                    time.sleep(1)
                    return None
                    
            except Exception as e:
                print(f"❌ Error en click: {str(e)[:50]}")
                return None
                
        except Exception as e:
            print(f"❌ Error general: {str(e)[:50]}")
            return None

    def extraer_uuids(self, limite: int = 10) -> List[Dict]:
        """Extrae UUIDs usando el método simple que funcionó"""
        print(f"🔍 Extrayendo UUIDs (límite: {limite})...")
        
        # Navegar al sitio principal
        self.driver.get(self.base_url)
        time.sleep(3)
        
        # Click en "Búsqueda de Procedimientos" 
        try:
            print("📍 Buscando enlace 'Búsqueda de Procedimientos'...")
            
            # Intentar diferentes formas de encontrar el enlace
            selectores = [
                (By.LINK_TEXT, "Búsqueda de Procedimientos"),
                (By.PARTIAL_LINK_TEXT, "Búsqueda"),
                (By.PARTIAL_LINK_TEXT, "Procedimientos"),
                (By.CSS_SELECTOR, "a[href*='busqueda-procedimientos']"),
                (By.XPATH, "//a[contains(text(), 'Búsqueda')]"),
                (By.XPATH, "//a[contains(text(), 'Procedimientos')]")
            ]
            
            enlace = None
            for selector_type, selector_value in selectores:
                try:
                    enlace = self.wait.until(EC.element_to_be_clickable((selector_type, selector_value)))
                    print(f"✅ Encontrado con selector: {selector_type} = {selector_value}")
        
        licitaciones = []
        for i in range(limite):
            print(f"[{i+1}/{limite}] Extrayendo...")
            
            licitacion = self.extraer_uuid_simple(i)
            if licitacion:
                licitaciones.append(licitacion)
            
            time.sleep(1)  # Pausa entre extracciones
        
        print(f"✅ Extraídos {len(licitaciones)} UUIDs")
        return licitaciones

    def procesar_con_haiku(self, url: str) -> Optional[Dict]:
        """Procesa URL con Claude Haiku"""
        try:
            prompt = f"""
Analiza esta página web de una licitación mexicana y extrae los datos en JSON limpio:

URL: {url}

Extrae EXACTAMENTE estos campos (si no encuentras algo, pon null):

{{
  "codigo_expediente": "código del expediente",
  "nombre_procedimiento": "nombre del procedimiento",
  "descripcion_detallada": "descripción completa",
  "tipo_procedimiento": "tipo (licitación pública, invitación, etc.)",
  "fecha_publicacion": "fecha de publicación",
  "fecha_apertura": "fecha de apertura",
  "fecha_fallo": "fecha del fallo",
  "importe_estimado": "monto estimado",
  "unidad_compradora": "unidad compradora",
  "entidad_federativa": "entidad federativa",
  "plazo_ejecucion": "plazo en días",
  "moneda": "moneda",
  "ubicacion_trabajos": "dónde se realizarán los trabajos"
}}

Responde SOLO JSON válido, sin explicaciones.
"""
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            contenido = response.content[0].text.strip()
            
            # Limpiar JSON
            if contenido.startswith('```json'):
                contenido = contenido[7:-3]
            elif contenido.startswith('```'):
                contenido = contenido[3:-3]
            
            return json.loads(contenido.strip())
            
        except Exception as e:
            print(f"❌ Error Haiku: {str(e)}")
            return None

    def procesar_licitaciones(self, licitaciones: List[Dict]) -> List[Dict]:
        """Procesa las licitaciones con Haiku"""
        print(f"\n🤖 Procesando {len(licitaciones)} licitaciones con Claude...")
        
        datos_completos = []
        
        for i, licitacion in enumerate(licitaciones, 1):
            print(f"[{i}/{len(licitaciones)}] {licitacion['uuid']}")
            
            # Procesar con Haiku
            datos_haiku = self.procesar_con_haiku(licitacion['url_detalle'])
            
            if datos_haiku:
                licitacion.update(datos_haiku)
                licitacion['metodo_extraccion'] = 'claude_haiku'
                print("✅ Procesado con Haiku")
            else:
                licitacion['metodo_extraccion'] = 'basico'
                print("⚠️  Solo datos básicos")
            
            licitacion['fecha_scraping'] = datetime.now().isoformat()
            datos_completos.append(licitacion)
            
            time.sleep(2)  # Pausa entre requests
        
        return datos_completos

    def guardar_resultados(self, datos: List[Dict]) -> Tuple[str, str]:
        """Guarda resultados"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        archivo_csv = f"comprasmx_haiku_{timestamp}.csv"
        archivo_json = f"comprasmx_haiku_{timestamp}.json"
        
        # CSV
        with open(archivo_csv, 'w', newline='', encoding='utf-8') as f:
            if datos:
                writer = csv.DictWriter(f, fieldnames=datos[0].keys())
                writer.writeheader()
                writer.writerows(datos)
        
        # JSON
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        return archivo_csv, archivo_json

    def ejecutar(self, limite: int = 10) -> None:
        """Ejecuta el proceso completo"""
        print("🚀 SCRAPER SIMPLE CON HAIKU")
        print("=" * 50)
        
        try:
            self.configurar_driver()
            
            # Fase 1: Extraer UUIDs
            licitaciones = self.extraer_uuids(limite)
            
            if not licitaciones:
                print("❌ No se extrajeron UUIDs")
                return
            
            # Cerrar Selenium
            self.driver.quit()
            print("✅ Selenium cerrado")
            
            # Fase 2: Procesar con Haiku
            datos_completos = self.procesar_licitaciones(licitaciones)
            
            # Guardar
            archivo_csv, archivo_json = self.guardar_resultados(datos_completos)
            
            print(f"\n🎉 COMPLETADO!")
            print(f"📊 Procesadas: {len(datos_completos)}")
            print(f"📁 CSV: {archivo_csv}")
            print(f"📁 JSON: {archivo_json}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

def main():
    scraper = ComprasMXScraperSimple()
    scraper.ejecutar(limite=5)  # Solo 5 para probar

if __name__ == "__main__":
    main()