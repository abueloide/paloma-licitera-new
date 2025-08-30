#!/usr/bin/env python3
"""
Debug del scraper Selenium para ver la estructura real de la tabla
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def debug_table_structure():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")

    # Esperar a que aparezca la tabla
    print("🔍 Buscando tabla...")
    
    # Intentar diferentes selectores
    selectores = [
        "table tbody",
        "table.p-datatable-table tbody",
        "table tr",
        ".p-datatable tbody"
    ]
    
    tabla = None
    for selector in selectores:
        try:
            tabla = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            print(f"✅ Tabla encontrada con selector: {selector}")
            break
        except:
            print(f"❌ No encontrada con: {selector}")
    
    if not tabla:
        print("❌ No se encontró ninguna tabla")
        driver.quit()
        return
    
    # Buscar filas
    rows = tabla.find_elements(By.CSS_SELECTOR, "tr")
    print(f"🔍 Filas encontradas: {len(rows)}")
    
    # Analizar cada fila
    for i, row in enumerate(rows[:5], 1):  # Solo las primeras 5 filas
        print(f"\n--- FILA {i} ---")
        
        # Ver el HTML completo de la fila
        html = row.get_attribute('outerHTML')
        print(f"HTML: {html[:200]}...")
        
        # Ver celdas
        celdas = row.find_elements(By.TAG_NAME, "td")
        print(f"Número de celdas: {len(celdas)}")
        
        for j, celda in enumerate(celdas):
            texto = celda.text.strip()
            print(f"  Celda {j}: '{texto[:50]}...' ")
            
            # Buscar enlaces en cada celda
            enlaces = celda.find_elements(By.TAG_NAME, "a")
            if enlaces:
                for enlace in enlaces:
                    href = enlace.get_attribute("href")
                    texto_enlace = enlace.text.strip()
                    print(f"    🔗 Enlace: '{texto_enlace}' -> {href}")

    driver.quit()

if __name__ == "__main__":
    debug_table_structure()