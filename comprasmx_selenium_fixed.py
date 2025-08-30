from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
import re

# Inicializar Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def get_current_rows():
    """Función para obtener filas válidas de licitaciones"""
    all_rows = driver.find_elements(By.TAG_NAME, "tr")
    valid_rows = []
    for row in all_rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            cell_text = cells[1].text.strip()
            if cell_text and len(cell_text) > 5:
                valid_rows.append(row)
    return valid_rows

try:
    print("🚀 Iniciando scraper ComprasMX con Selenium...")
    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
    
    # Esperar que la página cargue completamente
    print("⏳ Esperando carga completa...")
    time.sleep(15)
    
    # Obtener filas iniciales
    print("📊 Buscando licitaciones...")
    rows = get_current_rows()
    print(f"✅ Encontradas {len(rows)} licitaciones")
    
    data = []
    processed_ids = set()  # Para evitar duplicados
    max_to_process = 10    # Procesar solo 10 para prueba
    
    i = 0
    while i < min(len(rows), max_to_process):
        try:
            # Re-obtener filas frescas cada vez para evitar stale elements
            current_rows = get_current_rows()
            
            if i >= len(current_rows):
                print(f"    ⚠️ No hay más filas disponibles (índice {i} >= {len(current_rows)})")
                break
                
            row = current_rows[i]
            cells = row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) < 9:
                i += 1
                continue
            
            # Extraer información básica
            numero_id = cells[1].text.strip()
            
            # Verificar si ya procesamos este ID
            if numero_id in processed_ids:
                i += 1
                continue
                
            processed_ids.add(numero_id)
            
            caracter = cells[2].text.strip()
            titulo = cells[3].text.strip()
            dependencia = cells[4].text.strip()
            estatus = cells[5].text.strip()
            
            print(f"\n[{len(data)+1}] Procesando: {numero_id}")
            print(f"    └─ {titulo[:50]}...")
            
            # Click en el código de expediente
            print("    🔄 Haciendo click...")
            cells[1].click()
            time.sleep(8)  # Esperar navegación
            
            current_url = driver.current_url
            
            # Verificar si navegó al detalle
            if "/detalle/" in current_url:
                print("    ✅ Navegó al detalle")
                
                # Extraer hash UUID
                hash_match = re.search(r'/detalle/([a-f0-9]{32})/', current_url)
                hash_uuid = hash_match.group(1) if hash_match else "N/A"
                if hash_uuid != "N/A":
                    print(f"    🔑 Hash UUID: {hash_uuid}")
                
                # Esperar datos generales
                descripcion_detallada = ""
                unidad_compradora = "N/A"
                nombre_proc = titulo
                
                try:
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located(
                        (By.XPATH, "//h3[contains(.,'DATOS GENERALES')] | //td[contains(.,'Código del expediente')]")
                    ))
                    
                    try:
                        unidad_compradora = driver.find_element(
                            By.XPATH, "//td[contains(.,'Unidad compradora')]/following-sibling::td"
                        ).text.strip()
                    except: pass
                    
                    try:
                        nombre_proc = driver.find_element(
                            By.XPATH, "//td[contains(.,'Nombre del procedimiento') | contains(.,'Descripción')]/following-sibling::td"
                        ).text.strip()
                    except: pass
                    
                    try:
                        descripcion_detallada = driver.find_element(
                            By.XPATH, "//td[contains(.,'Descripción detallada del procedimiento')]/following-sibling::td"
                        ).text.strip()
                    except: pass
                    
                    print(f"    📝 Descripción: {len(descripcion_detallada)} caracteres")
                    
                except Exception as e:
                    print(f"    ⚠️ Error extrayendo datos: {e}")
                
                # Guardar datos
                data.append({
                    "numero_identificacion": numero_id,
                    "hash_uuid": hash_uuid,
                    "caracter": caracter,
                    "dependencia": dependencia,
                    "unidad_compradora": unidad_compradora,
                    "nombre_procedimiento": nombre_proc,
                    "descripcion_detallada": descripcion_detallada,
                    "estatus": estatus,
                    "url_detalle": current_url
                })
                print(f"    ✅ Datos guardados")
                
                # Volver al listado
                print("    ⬅️ Regresando...")
                driver.back()
                WebDriverWait(driver, 15).until(EC.presence_of_element_located(
                    (By.TAG_NAME, "table")
                ))
                time.sleep(3)
                
            else:
                print("    ❌ No navegó al detalle")
                # Guardar datos básicos
                data.append({
                    "numero_identificacion": numero_id,
                    "hash_uuid": "N/A",
                    "caracter": caracter,
                    "dependencia": dependencia,
                    "unidad_compradora": "N/A",
                    "nombre_procedimiento": titulo,
                    "descripcion_detallada": "",
                    "estatus": estatus,
                    "url_detalle": "No accesible"
                })
                
        except Exception as e:
            print(f"    ❌ Error procesando índice {i}: {e}")
        
        # Avanzar al siguiente elemento
        i += 1
    
    # Guardar resultados
    if data:
        df = pd.DataFrame(data)
        df.to_csv("comprasmx_selenium_completo.csv", index=False)
        
        # Estadísticas
        hash_exitosos = len([d for d in data if d["hash_uuid"] != "N/A"])
        print(f"\n🎉 ¡SCRAPING COMPLETADO!")
        print(f"📊 Total procesadas: {len(data)}")
        print(f"🔑 Con hash UUID: {hash_exitosos} ({hash_exitosos/len(data)*100:.1f}%)")
        print(f"📁 Guardado en: comprasmx_selenium_completo.csv")
        
        # Mostrar algunos resultados
        print("\n📋 Primeros resultados:")
        for i, item in enumerate(data[:3], 1):
            print(f"  {i}. {item['numero_identificacion']} - Hash: {item['hash_uuid'][:8]}... - {len(item['descripcion_detallada'])} chars")
        
    else:
        print("⚠️ No se extrajeron datos")

finally:
    driver.quit()
    print("\n✅ Proceso terminado")