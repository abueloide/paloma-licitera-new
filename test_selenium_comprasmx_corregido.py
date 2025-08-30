from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time

# Inicializar Chrome en modo headless (sin ventana) con driver automático
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)

try:
    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
    
    # Esperar a que aparezca la tabla PrimeNG específica
    tabla = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "table.p-datatable-table tbody")))
    rows = tabla.find_elements(By.CSS_SELECTOR, "tr")
    
    print(f"🎯 Encontradas {len(rows)} licitaciones")
    
    data = []
    for i, row in enumerate(rows[:5], start=1):  # Probar solo 5 primeras para debug
        try:
            # Obtener todas las celdas
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 9:
                continue
            
            # Extraer información básica de la fila
            numero_id = cells[1].text.strip()  # Columna 2: Código de expediente
            caracter = cells[2].text.strip()   # Columna 3: Nacional/Internacional
            titulo = cells[3].text.strip()     # Columna 4: Título
            dependencia = cells[4].text.strip() # Columna 5: Dependencia/Unidad
            estatus = cells[5].text.strip()    # Columna 6: Estatus
            
            print(f"\n[{i}/5] Procesando: {numero_id}")
            print(f"    └─ {titulo[:50]}...")
            
            # CORREGIDO: Click en la celda del código (no buscar enlace <a>)
            print(f"    🔄 Haciendo click en código de expediente...")
            cells[1].click()  # Click directo en la celda
            
            # Esperar navegación (la URL debería cambiar)
            time.sleep(5)
            
            current_url = driver.current_url
            print(f"    🌐 URL actual: {current_url}")
            
            # Verificar si navegó al detalle
            if "/detalle/" in current_url:
                print(f"    ✅ Navegó al detalle exitosamente")
                
                # Esperar que carguen los datos generales
                try:
                    wait.until(EC.presence_of_element_located(
                        (By.XPATH, "//h3[contains(.,'DATOS GENERALES')] | //td[contains(.,'Código del expediente')]")),
                        timeout=15)
                    print(f"    ✅ Datos generales cargados")
                    
                    # Extraer campos usando selectores más robustos
                    try:
                        expediente = driver.find_element(
                            By.XPATH, "//td[contains(.,'Código del expediente')]/following-sibling::td"
                        ).text.strip()
                    except:
                        expediente = numero_id  # Fallback
                    
                    try:
                        estatus_detalle = driver.find_element(
                            By.XPATH, "//td[contains(.,'Estatus del procedimiento')]/following-sibling::td"
                        ).text.strip()
                    except:
                        estatus_detalle = estatus  # Fallback
                    
                    try:
                        dependencia_detalle = driver.find_element(
                            By.XPATH, "//td[contains(.,'Dependencia o Entidad')]/following-sibling::td"
                        ).text.strip()
                    except:
                        dependencia_detalle = dependencia  # Fallback
                    
                    try:
                        unidad_compradora = driver.find_element(
                            By.XPATH, "//td[contains(.,'Unidad compradora')]/following-sibling::td"
                        ).text.strip()
                    except:
                        unidad_compradora = "N/A"
                    
                    try:
                        nombre_proc = driver.find_element(
                            By.XPATH, "//td[contains(.,'Nombre del procedimiento') | contains(.,'Descripción')]/following-sibling::td"
                        ).text.strip()
                    except:
                        nombre_proc = titulo  # Fallback
                    
                    # Guardar datos
                    data.append({
                        "numero_identificacion": numero_id,
                        "codigo_expediente": expediente,
                        "caracter": caracter,
                        "dependencia": dependencia_detalle,
                        "unidad_compradora": unidad_compradora,
                        "nombre_procedimiento": nombre_proc,
                        "estatus": estatus_detalle,
                        "url_detalle": current_url
                    })
                    print(f"    ✅ Datos extraídos y guardados")
                    
                except Exception as e:
                    print(f"    ❌ Error extrayendo datos del detalle: {e}")
                
                # Volver al listado
                print(f"    ⬅️ Volviendo al listado...")
                driver.back()
                
                # Esperar que vuelva al listado
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "table.p-datatable-table tbody")))
                time.sleep(2)
                print(f"    ✅ De vuelta en el listado")
                
            else:
                print(f"    ❌ No navegó al detalle - URL sin cambios")
                # Guardar información básica
                data.append({
                    "numero_identificacion": numero_id,
                    "codigo_expediente": numero_id,
                    "caracter": caracter,
                    "dependencia": dependencia,
                    "unidad_compradora": "N/A",
                    "nombre_procedimiento": titulo,
                    "estatus": estatus,
                    "url_detalle": "No accesible"
                })
                
        except Exception as e:
            print(f"    ❌ Error procesando fila {i}: {e}")
    
    # Exportar resultados
    if data:
        df = pd.DataFrame(data)
        df.to_csv("procedimientos_detalle_corregido.csv", index=False)
        print(f"\n🎉 ¡Éxito! {len(data)} procedimientos extraídos y guardados en CSV")
    else:
        print(f"\n⚠️ No se extrajeron datos")

finally:
    driver.quit()