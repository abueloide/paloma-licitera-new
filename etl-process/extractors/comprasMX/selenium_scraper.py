#!/usr/bin/env python3
"""
Scraper ComprasMX usando Selenium - Código sugerido por el usuario
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime

# Configuración de directorios
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # ../../../
SALIDA = project_root / "data" / "raw" / "comprasmx"
SALIDA.mkdir(parents=True, exist_ok=True)

print(f"[INFO] Selenium Scraper ComprasMX - Guardando archivos en: {SALIDA.absolute()}")

def main():
    # Inicializar Chrome en modo headless (sin ventana)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")

    # Esperar a que aparezca la tabla de anuncios vigentes
    tabla = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "table tbody")))
    rows = tabla.find_elements(By.CSS_SELECTOR, "tr")

    print(f"✅ Tabla encontrada con {len(rows)} filas")

    data = []
    for i, row in enumerate(rows, start=1):
        try:
            print(f"\n[{i}/{len(rows)}] Procesando fila...")
            
            # tomar la columna 2 (número de identificación)
            link_elem = row.find_elements(By.TAG_NAME, "td")[1].find_element(By.TAG_NAME, "a")
            numero_id = link_elem.text.strip()
            href = link_elem.get_attribute("href")
            
            print(f"    📋 Número ID: {numero_id}")
            print(f"    🔗 URL: {href}")

            # abrir la ficha en una nueva pestaña
            driver.execute_script("window.open(arguments[0]);", href)
            driver.switch_to.window(driver.window_handles[-1])

            # esperar a que carguen los datos generales
            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//h3[contains(.,'DATOS GENERALES')]")))
            
            print(f"    ✅ Página de detalle cargada")

            # Extraer campos importantes (ajuste los selectores según la estructura exacta)
            expediente = driver.find_element(
                By.XPATH, "//td[contains(.,'Código del expediente')]/following-sibling::td"
            ).text.strip()
            estatus = driver.find_element(
                By.XPATH, "//td[contains(.,'Estatus del procedimiento')]/following-sibling::td"
            ).text.strip()
            dependencia = driver.find_element(
                By.XPATH, "//td[contains(.,'Dependencia o Entidad')]/following-sibling::td"
            ).text.strip()
            rama = driver.find_element(
                By.XPATH, "//td[contains(.,'Ramo')]/following-sibling::td"
            ).text.strip()
            unidad_compradora = driver.find_element(
                By.XPATH, "//td[contains(.,'Unidad compradora')]/following-sibling::td"
            ).text.strip()
            nombre_proc = driver.find_element(
                By.XPATH, "//td[contains(.,'Nombre del procedimiento')]/following-sibling::td"
            ).text.strip()

            print(f"    📝 Datos extraídos:")
            print(f"        - Expediente: {expediente}")
            print(f"        - Estatus: {estatus}")
            print(f"        - Dependencia: {dependencia[:50]}...")
            print(f"        - Procedimiento: {nombre_proc[:50]}...")

            # Guardar datos
            data.append({
                "numero_identificacion": numero_id,
                "codigo_expediente": expediente,
                "dependencia": dependencia,
                "rama": rama,
                "unidad_compradora": unidad_compradora,
                "nombre_procedimiento": nombre_proc,
                "estatus": estatus,
                "url_detalle": href
            })

            # Cerrar la pestaña de la ficha y volver a la tabla principal
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            print(f"    ✅ Detalle procesado correctamente")

            # Pausa opcional para no saturar el servidor
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    ❌ Error procesando fila {i}: {e}")
            
            # Intentar volver a la ventana principal si hay error
            try:
                if len(driver.window_handles) > 1:
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass
            
            continue

    # Guardar resultados
    print(f"\n💾 Guardando {len(data)} registros...")
    
    # Exportar a CSV
    df = pd.DataFrame(data)
    csv_path = SALIDA / f"procedimientos_detalle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(csv_path, index=False)
    print(f"✅ CSV guardado: {csv_path}")
    
    # También guardar como JSON
    json_path = SALIDA / f"procedimientos_detalle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON guardado: {json_path}")
    
    # Mostrar estadísticas
    print(f"\n📊 ESTADÍSTICAS FINALES:")
    print(f"✓ Registros procesados: {len(data)}")
    print(f"✓ Archivos guardados en: {SALIDA}")
    
    driver.quit()

if __name__ == "__main__":
    main()