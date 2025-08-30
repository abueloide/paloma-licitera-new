from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Inicializar Chrome en modo headless
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)

try:
    print("🔍 Analizando estructura de ComprasMX...")
    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")
    
    # Esperar que la página cargue
    time.sleep(10)
    
    print("📊 Buscando tablas...")
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"Encontradas {len(tables)} tablas")
    
    for i, table in enumerate(tables):
        print(f"\n--- TABLA {i+1} ---")
        try:
            # Buscar filas
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"Filas encontradas: {len(rows)}")
            
            # Analizar primeras 3 filas
            for j, row in enumerate(rows[:3]):
                cells = row.find_elements(By.TAG_NAME, "td")
                print(f"  Fila {j+1}: {len(cells)} celdas")
                
                for k, cell in enumerate(cells):
                    text = cell.text.strip()[:50]  # Primeros 50 caracteres
                    has_link = len(cell.find_elements(By.TAG_NAME, "a")) > 0
                    print(f"    Celda {k+1}: '{text}' {'(con enlace)' if has_link else ''}")
        except Exception as e:
            print(f"Error analizando tabla {i+1}: {e}")
    
    # Buscar específicamente tabla PrimeNG
    print("\n🔍 Buscando tabla PrimeNG específica...")
    try:
        prime_table = driver.find_element(By.CSS_SELECTOR, "table.p-datatable-table")
        print("✅ Tabla PrimeNG encontrada")
        
        tbody = prime_table.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        print(f"Filas en tbody PrimeNG: {len(rows)}")
        
        if rows:
            first_row = rows[0]
            cells = first_row.find_elements(By.TAG_NAME, "td")
            print(f"Primera fila tiene {len(cells)} celdas:")
            
            for i, cell in enumerate(cells):
                text = cell.text.strip()[:50]
                links = cell.find_elements(By.TAG_NAME, "a")
                print(f"  Celda {i+1}: '{text}' - Enlaces: {len(links)}")
                
                if links:
                    for link in links:
                        href = link.get_attribute("href")
                        link_text = link.text.strip()[:30]
                        print(f"    -> Enlace: '{link_text}' -> {href}")
                        
    except Exception as e:
        print(f"❌ No se encontró tabla PrimeNG: {e}")
    
finally:
    driver.quit()
    print("\n🏁 Análisis completado")