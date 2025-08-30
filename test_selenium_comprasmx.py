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

driver.get("https://comprasmx.buengobierno.gob.mx/sitiopublico/#/")

# Esperar a que aparezca la tabla de anuncios vigentes
tabla = wait.until(EC.presence_of_element_located(
    (By.CSS_SELECTOR, "table tbody")))
rows = tabla.find_elements(By.CSS_SELECTOR, "tr")

data = []
for i, row in enumerate(rows, start=1):
    # tomar la columna 2 (número de identificación)
    link_elem = row.find_elements(By.TAG_NAME, "td")[1].find_element(By.TAG_NAME, "a")
    numero_id = link_elem.text.strip()
    href = link_elem.get_attribute("href")

    # abrir la ficha en una nueva pestaña
    driver.execute_script("window.open(arguments[0]);", href)
    driver.switch_to.window(driver.window_handles[-1])

    # esperar a que carguen los datos generales
    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//h3[contains(.,'DATOS GENERALES')]")))

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

    # (Opcional) Descargar anexos:
    # desplácese a la sección de ANEXOS y haga clic en cada fila para descargar los archivos
    # anexos_tabla = driver.find_element(By.XPATH, "//h3[contains(.,'ANEXOS')]/following::table[1]")
    # ... iterar y descargar ...

    # Cerrar la pestaña de la ficha y volver a la tabla principal
    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    # Pausa opcional para no saturar el servidor
    time.sleep(0.5)

# Exportar a CSV
df = pd.DataFrame(data)
df.to_csv("procedimientos_detalle.csv", index=False)
driver.quit()