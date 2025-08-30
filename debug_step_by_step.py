from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Configurar Chrome con más tiempo de espera
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 30)  # Aumentar timeout

try:
    print("🚀 Navegando a ComprasMX...")
    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
    
    print("⏳ Esperando que la página cargue completamente...")
    time.sleep(15)  # Esperar más tiempo
    
    print("🔍 Estado de la página:")
    print(f"URL actual: {driver.current_url}")
    print(f"Título: {driver.title}")
    
    # Intentar diferentes selectores para encontrar las filas
    print("\n📊 Probando diferentes selectores para filas...")
    
    # Método 1: Selector original
    try:
        tabla1 = driver.find_element(By.CSS_SELECTOR, "table.p-datatable-table tbody")
        rows1 = tabla1.find_elements(By.CSS_SELECTOR, "tr")
        print(f"Método 1 (table.p-datatable-table tbody tr): {len(rows1)} filas")
    except Exception as e:
        print(f"Método 1 falló: {e}")
        rows1 = []
    
    # Método 2: Más genérico
    try:
        rows2 = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"Método 2 (table tbody tr): {len(rows2)} filas")
    except Exception as e:
        print(f"Método 2 falló: {e}")
        rows2 = []
    
    # Método 3: Solo tr
    try:
        rows3 = driver.find_elements(By.TAG_NAME, "tr")
        print(f"Método 3 (tr): {len(rows3)} filas")
        # Filtrar filas con contenido relevante
        rows3_filtered = []
        for row in rows3:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 2:
                cell_text = cells[1].text.strip()
                if cell_text and len(cell_text) > 5:
                    rows3_filtered.append(row)
        print(f"Método 3 filtrado: {len(rows3_filtered)} filas con datos")
    except Exception as e:
        print(f"Método 3 falló: {e}")
        rows3_filtered = []
    
    # Usar el método que más filas encontró
    best_rows = []
    if rows3_filtered:
        best_rows = rows3_filtered
        print(f"✅ Usando método 3 filtrado: {len(best_rows)} filas")
    elif rows1:
        best_rows = rows1
        print(f"✅ Usando método 1: {len(best_rows)} filas")
    elif rows2:
        best_rows = rows2
        print(f"✅ Usando método 2: {len(best_rows)} filas")
    
    if best_rows:
        print(f"\n🎯 Probando click en la primera fila...")
        first_row = best_rows[0]
        cells = first_row.find_elements(By.TAG_NAME, "td")
        
        if len(cells) >= 2:
            codigo = cells[1].text.strip()
            print(f"Código a procesar: '{codigo}'")
            
            print("🔄 Haciendo click...")
            cells[1].click()
            
            # Esperar y verificar navegación
            time.sleep(8)
            new_url = driver.current_url
            print(f"URL después del click: {new_url}")
            
            if "/detalle/" in new_url:
                print("✅ ¡ÉXITO! Navegó al detalle")
                
                # Buscar datos generales
                try:
                    datos_generales = wait.until(EC.presence_of_element_located(
                        (By.XPATH, "//h3[contains(.,'DATOS GENERALES')] | //td[contains(.,'Código del expediente')]")
                    ), timeout=15)
                    print("✅ Datos generales encontrados")
                    
                    # Extraer hash de la URL
                    import re
                    hash_match = re.search(r'/detalle/([a-f0-9]{32})/', new_url)
                    if hash_match:
                        hash_uuid = hash_match.group(1)
                        print(f"🔑 Hash UUID extraído: {hash_uuid}")
                    
                except Exception as e:
                    print(f"❌ Error buscando datos generales: {e}")
            else:
                print("❌ No navegó al detalle")
        else:
            print("❌ No se encontraron suficientes celdas")
    else:
        print("❌ No se encontraron filas válidas")

finally:
    driver.quit()
    print("\n🏁 Debug completado")