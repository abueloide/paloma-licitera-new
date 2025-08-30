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

try:
    print("🚀 Iniciando scraper ComprasMX con Selenium...")
    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
    
    # Esperar que la página cargue completamente
    print("⏳ Esperando carga completa...")
    time.sleep(15)
    
    # Encontrar todas las filas de licitaciones
    print("📊 Buscando licitaciones...")
    rows = []
    all_rows = driver.find_elements(By.TAG_NAME, "tr")
    
    # Filtrar filas válidas (con datos de licitaciones)
    for row in all_rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            cell_text = cells[1].text.strip()
            if cell_text and len(cell_text) > 5:
                rows.append(row)
    
    print(f"✅ Encontradas {len(rows)} licitaciones")
    
    data = []
    for i, row in enumerate(rows[:20], start=1):  # Procesar 20 licitaciones
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 9:
                continue
            
            # Extraer información básica
            numero_id = cells[1].text.strip()
            caracter = cells[2].text.strip()
            titulo = cells[3].text.strip()
            dependencia = cells[4].text.strip()
            estatus = cells[5].text.strip()
            
            print(f"\n[{i}/20] Procesando: {numero_id}")
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
                try:
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located(
                        (By.XPATH, "//h3[contains(.,'DATOS GENERALES')] | //td[contains(.,'Código del expediente')]")
                    ))
                    
                    # Extraer información detallada
                    expediente = numero_id  # Default
                    estatus_detalle = estatus  # Default
                    dependencia_detalle = dependencia  # Default
                    unidad_compradora = "N/A"
                    nombre_proc = titulo  # Default
                    descripcion_detallada = ""
                    
                    try:
                        expediente = driver.find_element(
                            By.XPATH, "//td[contains(.,'Código del expediente')]/following-sibling::td"
                        ).text.strip()
                    except: pass
                    
                    try:
                        estatus_detalle = driver.find_element(
                            By.XPATH, "//td[contains(.,'Estatus del procedimiento')]/following-sibling::td"
                        ).text.strip()
                    except: pass
                    
                    try:
                        dependencia_detalle = driver.find_element(
                            By.XPATH, "//td[contains(.,'Dependencia o Entidad')]/following-sibling::td"
                        ).text.strip()
                    except: pass
                    
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
                    "codigo_expediente": numero_id,  # CORREGIDO: usar numero_id en lugar de expediente indefinido
                    "hash_uuid": hash_uuid,
                    "caracter": caracter,
                    "dependencia": dependencia_detalle,
                    "unidad_compradora": unidad_compradora,
                    "nombre_procedimiento": nombre_proc,
                    "descripcion_detallada": descripcion_detallada,
                    "estatus": estatus_detalle,
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
                
                # CORREGIDO: Re-localizar filas después de volver (evitar stale elements)
                print("    🔄 Re-localizando elementos...")
                all_rows = driver.find_elements(By.TAG_NAME, "tr")
                rows = []
                for row in all_rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        cell_text = cells[1].text.strip()
                        if cell_text and len(cell_text) > 5:
                            rows.append(row)
                print(f"    ✅ Re-localizadas {len(rows)} filas")
                
            else:
                print("    ❌ No navegó al detalle")
                # Guardar datos básicos
                data.append({
                    "numero_identificacion": numero_id,
                    "codigo_expediente": numero_id,
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
            print(f"    ❌ Error: {e}")
            continue
    
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
        
    else:
        print("⚠️ No se extrajeron datos")

finally:
    driver.quit()
    print("\n✅ Proceso terminado")