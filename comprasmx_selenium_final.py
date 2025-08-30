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

# Inicializar Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def mine_text_data(text_content, basic_info):
    """Minar datos específicos del texto completo extraído"""
    data = basic_info.copy()
    
    # Patrones de extracción mejorados
    patterns = {
        "codigo_expediente": [
            r"Código del expediente:\s*([^\n]+)",
            r"E-\d{4}-\d{8}"
        ],
        "estatus_detalle": [
            r"Estatus del procedimiento de contratación:\s*([^\n]+)",
            r"Estatus del procedimiento:\s*([^\n]+)"
        ],
        "dependencia_detalle": [
            r"Dependencia o Entidad:\s*([^\n]+)",
        ],
        "unidad_compradora": [
            r"Unidad compradora:\s*([^\n]+)",
        ],
        "nombre_procedimiento": [
            r"Nombre del procedimiento de contratación:\s*([^\n]+)",
        ],
        "descripcion_detallada": [
            r"Descripción detallada del procedimiento de contratación:\s*([^\n]+)",
        ],
        "tipo_procedimiento": [
            r"Tipo de procedimiento de contratación:\s*([^\n]+)",
            r"^([A-ZÁÉÍÓÚÑ\s]+PERSONAS?)\s*$"
        ],
        "fecha_publicacion": [
            r"Fecha y hora de publicación:\s*([^\n]+)",
        ],
        "fecha_apertura": [
            r"Fecha y hora de presentación y apertura de proposiciones:\s*([^\n]+)",
        ],
        "fecha_fallo": [
            r"Fecha y hora del acto del Fallo:\s*([^\n]+)",
        ],
        "importe_estimado": [
            r"Importe estimado[:\s]*([^\n]+)",
            r"Monto[:\s]*([^\n$]+)",
        ],
        "plazo_ejecucion": [
            r"Plazo de ejecucion en dias naturales:\s*([^\n]+)",
        ],
        "entidad_federativa": [
            r"Entidad Federativa donde se llevará a cabo la contratación:\s*([^\n]+)",
        ],
        "caracter_detalle": [
            r"Carácter:\s*([^\n]+)",
        ]
    }
    
    # Extraer usando patrones
    for field, pattern_list in patterns.items():
        value = "N/A"
        for pattern in pattern_list:
            matches = re.findall(pattern, text_content, re.MULTILINE | re.IGNORECASE)
            if matches:
                value = matches[0].strip()
                if value and value != "N/A":
                    break
        data[field] = value
    
    # Extracciones especiales
    # Extraer montos de texto libre
    money_patterns = [
        r'\$\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*pesos',
        r'importe.*?([\d,]+\.?\d*)',
    ]
    
    for pattern in money_patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        if matches and data.get("importe_estimado") == "N/A":
            data["importe_estimado"] = f"${matches[0]}"
            break
    
    return data

def extract_uuids_from_listing():
    """Fase 1: Extraer todos los UUIDs de la página principal con reintentos"""
    print("🚀 FASE 1: Extrayendo UUIDs de la página principal...")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"📡 Intento {attempt + 1}/{max_retries} - Cargando página principal...")
            driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
            
            # Esperar carga más robusta
            print("⏳ Esperando carga completa...")
            time.sleep(20)  # Más tiempo para cargar
            
            # Verificar que la tabla esté presente
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Encontrar filas
            print("📊 Buscando licitaciones...")
            all_rows = driver.find_elements(By.TAG_NAME, "tr")
            
            valid_rows = []
            for row in all_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 5:  # Asegurar que tenga suficientes columnas
                    cell_text = cells[1].text.strip()
                    if cell_text and len(cell_text) > 5 and not cell_text.lower().startswith("número"):
                        valid_rows.append(row)
            
            print(f"✅ Encontradas {len(valid_rows)} licitaciones válidas")
            
            if len(valid_rows) > 0:
                break
            else:
                print(f"⚠️ Intento {attempt + 1} falló - No se encontraron filas válidas")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    
        except Exception as e:
            print(f"❌ Error en intento {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(15)
    
    if not valid_rows:
        print("❌ No se pudieron encontrar licitaciones después de todos los intentos")
        return []
    
    # Extraer UUIDs con estrategia mejorada
    licitaciones_info = []
    processed_count = 0
    
    # Procesar de 10 en 10 para evitar problemas de memoria
    batch_size = 10
    total_rows = len(valid_rows)
    
    for batch_start in range(0, total_rows, batch_size):
        batch_end = min(batch_start + batch_size, total_rows)
        print(f"\n📦 Procesando lote {batch_start//batch_size + 1}: filas {batch_start+1} a {batch_end}")
        
        # Recargar página para cada lote
        if batch_start > 0:
            print("🔄 Recargando página para nuevo lote...")
            driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
            time.sleep(20)
            
            # Re-localizar filas
            all_rows = driver.find_elements(By.TAG_NAME, "tr")
            valid_rows = []
            for row in all_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 5:
                    cell_text = cells[1].text.strip()
                    if cell_text and len(cell_text) > 5 and not cell_text.lower().startswith("número"):
                        valid_rows.append(row)
        
        # Procesar el lote actual
        for i in range(batch_start, batch_end):
            if i >= len(valid_rows):
                break
                
            row = valid_rows[i]
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 5:
                    continue
                
                # Extraer información básica
                numero_id = cells[1].text.strip()
                caracter = cells[2].text.strip()
                titulo = cells[3].text.strip()
                dependencia = cells[4].text.strip()
                estatus = cells[5].text.strip() if len(cells) > 5 else "N/A"
                
                print(f"\n[{processed_count+1}/{total_rows}] Procesando: {numero_id}")
                print(f"    📄 {titulo[:50]}...")
                
                # Click más seguro
                driver.execute_script("arguments[0].scrollIntoView(true);", cells[1])
                time.sleep(2)
                cells[1].click()
                
                # Esperar navegación
                print("    ⏳ Esperando navegación...")
                time.sleep(10)
                
                current_url = driver.current_url
                
                # Extraer UUID
                hash_uuid = "N/A"
                if "/detalle/" in current_url:
                    hash_match = re.search(r'/detalle/([a-f0-9]{32})/', current_url)
                    if hash_match:
                        hash_uuid = hash_match.group(1)
                        print(f"    🔑 UUID extraído: {hash_uuid}")
                    else:
                        print("    ❌ No se pudo extraer UUID de la URL")
                
                # Guardar información
                licitaciones_info.append({
                    "numero_identificacion": numero_id,
                    "caracter": caracter,
                    "titulo_basico": titulo,
                    "dependencia_basica": dependencia,
                    "estatus_basico": estatus,
                    "hash_uuid": hash_uuid,
                    "url_directa": f"https://comprasmx.buengobierno.gob.mx/sitiopublico/#/sitiopublico/detalle/{hash_uuid}/procedimiento" if hash_uuid != "N/A" else "N/A"
                })
                
                processed_count += 1
                
                # Regresar solo si no es el último del lote
                if i < batch_end - 1 and "/detalle/" in current_url:
                    print("    ⬅️ Regresando al listado...")
                    driver.back()
                    time.sleep(8)
                    
                    # Verificar que regresamos correctamente
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.TAG_NAME, "table"))
                    )
                    
                    # Re-localizar filas para el siguiente elemento
                    all_rows = driver.find_elements(By.TAG_NAME, "tr")
                    valid_rows = []
                    for row in all_rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 5:
                            cell_text = cells[1].text.strip()
                            if cell_text and len(cell_text) > 5 and not cell_text.lower().startswith("número"):
                                valid_rows.append(row)
                
            except Exception as e:
                print(f"    ❌ Error procesando fila {i+1}: {e}")
                processed_count += 1
                continue
    
    # Guardar UUIDs extraídos
    with open("comprasmx_uuids_extraidos.json", "w", encoding="utf-8") as f:
        json.dump(licitaciones_info, f, ensure_ascii=False, indent=2)
    
    uuids_exitosos = len([info for info in licitaciones_info if info["hash_uuid"] != "N/A"])
    print(f"\n✅ FASE 1 COMPLETADA")
    print(f"📊 Total procesadas: {len(licitaciones_info)}")
    print(f"🔑 UUIDs extraídos: {uuids_exitosos} ({uuids_exitosos/len(licitaciones_info)*100:.1f}%)")
    print(f"💾 Guardado en: comprasmx_uuids_extraidos.json")
    
    return licitaciones_info

def extract_detailed_data(licitaciones_info):
    """Fase 2: Visitar cada URL directa y minar datos del texto"""
    print(f"\n🚀 FASE 2: Minando datos detallados de {len(licitaciones_info)} licitaciones...")
    
    detailed_data = []
    
    # Filtrar solo las que tienen UUID válido
    valid_licitaciones = [info for info in licitaciones_info if info["hash_uuid"] != "N/A"]
    print(f"📍 Procesando {len(valid_licitaciones)} licitaciones con UUID válido")
    
    for i, info in enumerate(valid_licitaciones, start=1):
        try:
            uuid = info["hash_uuid"]
            direct_url = info["url_directa"]
            
            print(f"\n[{i}/{len(valid_licitaciones)}] Minando UUID: {uuid}")
            print(f"    🔗 URL: {direct_url}")
            
            # Navegar directamente
            driver.get(direct_url)
            time.sleep(15)  # Más tiempo para cargar completamente
            
            # Esperar contenido crítico
            try:
                WebDriverWait(driver, 25).until(
                    lambda driver: len(driver.find_element(By.TAG_NAME, "body").text) > 1000
                )
                print("    ✅ Contenido cargado completamente")
            except:
                print("    ⚠️ Timeout, pero continuando con el contenido disponible")
            
            # Extraer texto completo
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"    📄 Texto extraído: {len(page_text)} caracteres")
            
            # Minar datos específicos del texto
            mined_data = mine_text_data(page_text, info)
            mined_data["texto_completo"] = page_text
            
            # Contar campos extraídos exitosamente
            fields_extracted = len([v for k, v in mined_data.items() 
                                 if k.startswith(('codigo_', 'estatus_', 'dependencia_', 
                                                'unidad_', 'nombre_', 'descripcion_', 
                                                'tipo_', 'fecha_', 'importe_', 'plazo_')) 
                                 and v != "N/A"])
            
            print(f"    ⛏️  Campos minados: {fields_extracted}")
            
            detailed_data.append(mined_data)
            print(f"    ✅ Datos guardados")
            
            # Breve pausa entre requests
            time.sleep(3)
            
        except Exception as e:
            print(f"    ❌ Error minando {info.get('numero_identificacion', 'N/A')}: {e}")
            # Guardar datos básicos en caso de error
            error_data = info.copy()
            error_data["error"] = str(e)
            error_data["texto_completo"] = ""
            detailed_data.append(error_data)
            continue
    
    return detailed_data

try:
    # FASE 1: Extraer UUIDs
    licitaciones_info = extract_uuids_from_listing()
    
    if not licitaciones_info:
        print("❌ No se extrajeron UUIDs. Terminando.")
        exit(1)
    
    # FASE 2: Minar datos detallados
    detailed_data = extract_detailed_data(licitaciones_info)
    
    # Guardar resultados finales
    if detailed_data:
        # CSV para análisis
        df = pd.DataFrame(detailed_data)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        csv_filename = f"comprasmx_minado_completo_{timestamp}.csv"
        df.to_csv(csv_filename, index=False, encoding="utf-8")
        
        # JSON para mayor detalle
        json_filename = f"comprasmx_minado_completo_{timestamp}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(detailed_data, f, ensure_ascii=False, indent=2)
        
        # Estadísticas finales
        total_procesadas = len(detailed_data)
        con_codigo = len([d for d in detailed_data if d.get("codigo_expediente", "N/A") != "N/A"])
        con_descripcion = len([d for d in detailed_data if d.get("descripcion_detallada", "N/A") != "N/A"])
        con_fechas = len([d for d in detailed_data if d.get("fecha_publicacion", "N/A") != "N/A"])
        con_importes = len([d for d in detailed_data if d.get("importe_estimado", "N/A") != "N/A"])
        
        print(f"\n🎉 ¡MINADO COMPLETADO!")
        print(f"📊 Total procesadas: {total_procesadas}")
        print(f"🔢 Con código expediente: {con_codigo} ({con_codigo/total_procesadas*100:.1f}%)")
        print(f"📝 Con descripción detallada: {con_descripcion} ({con_descripcion/total_procesadas*100:.1f}%)")
        print(f"📅 Con fechas: {con_fechas} ({con_fechas/total_procesadas*100:.1f}%)")
        print(f"💰 Con importes: {con_importes} ({con_importes/total_procesadas*100:.1f}%)")
        print(f"💾 Guardado en:")
        print(f"    📊 CSV: {csv_filename}")
        print(f"    📋 JSON: {json_filename}")
        
    else:
        print("⚠️ No se minaron datos detallados")

except Exception as e:
    print(f"❌ Error crítico: {e}")
    
finally:
    driver.quit()
    print("\n✅ Proceso de minado terminado")