import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
load_dotenv()
USUARIO = os.getenv("CIANBOX_USER")
PASSWORD = os.getenv("CIANBOX_PASS")
URL_LOGIN = os.getenv("URL_LOGIN")

SELECTORES = {
    "login_user": (By.NAME, "user"),
    "login_pass": (By.NAME, "password"),
    "login_btn":  (By.TAG_NAME, "button"),
    "tab_compras": (By.CSS_SELECTOR, "a[rel='pv_compras']"),
    # Botón Eliminar dentro de la ficha de la compra
    "btn_eliminar": (By.CSS_SELECTOR, "input[type='submit'][value='Eliminar']"),
    # Botón de confirmación en el modal (según tu descripción: <a href="#" class="accept">Eliminar</a>)
    "btn_confirmar": (By.CSS_SELECTOR, "a.accept"),
}

def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def login(driver):
    print("🔑 Logueando...")
    driver.get(URL_LOGIN)
    time.sleep(1.5)
    if len(driver.find_elements(*SELECTORES["login_user"])) > 0:
        driver.find_element(*SELECTORES["login_user"]).send_keys(USUARIO)
        driver.find_element(*SELECTORES["login_pass"]).send_keys(PASSWORD)
        driver.find_element(*SELECTORES["login_btn"]).click()
        time.sleep(1.5)
    else:
        print("   ✅ Ya estabas logueado.")

def eliminar_facturas(driver, cantidad_a_eliminar):
    wait = WebDriverWait(driver, 10)
    
    print("📍 Navegando a Compras...")
    try:
        wait.until(EC.element_to_be_clickable(SELECTORES["tab_compras"])).click()
    except:
        driver.execute_script("document.querySelector(\"a[rel='pv_compras']\").click();")
    
    # Esperar a que cargue la tabla inicial
    time.sleep(3)

    for i in range(cantidad_a_eliminar):
        print(f"\n🗑️ [Intento {i+1}/{cantidad_a_eliminar}] Eliminando factura...")
        
        try:
            # 1. Seleccionar la primera fila de la tabla
            # Buscamos todos los TR. Generalmente el primero (índice 0) es el encabezado,
            # así que intentamos hacer clic en el segundo (índice 1).
            filas = driver.find_elements(By.TAG_NAME, "tr")
            
            fila_a_clickear = None
            if len(filas) > 1:
                fila_a_clickear = filas[1]
            else:
                print("⚠️ No se encontraron más filas en la tabla. ¿Lista vacía?")
                break

            # Hacemos clic en la fila para abrir el detalle
            fila_a_clickear.click()
            
            # 2. Esperar y hacer clic en el botón Eliminar
            btn_eliminar = wait.until(EC.element_to_be_clickable(SELECTORES["btn_eliminar"]))
            btn_eliminar.click()
            print("   ⚠️ Botón Eliminar presionado.")

            # 3. Confirmar en el modal
            # Esperamos que aparezca el modal y el botón aceptar/eliminar
            btn_confirmar = wait.until(EC.element_to_be_clickable(SELECTORES["btn_confirmar"]))
            btn_confirmar.click()
            print("   ✅ Confirmación aceptada.")

            # 4. Esperar recarga de la lista
            # Al eliminar, el sistema suele volver a la lista. Esperamos que la tabla reaparezca.
            time.sleep(1.5) 
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
            time.sleep(1) # Un respiro extra para asegurar que el DOM esté estable

        except Exception as e:
            print(f"❌ Error al eliminar en iteración {i+1}: {e}")
            # Si falla (ej. no cargó la página), intentamos volver atrás para no romper el bucle
            try:
                driver.back()
                time.sleep(2)
            except:
                pass
            continue

if __name__ == "__main__":
    driver = iniciar_driver()
    try:
        login(driver)
        eliminar_facturas(driver, 200) # Configurado para 200 facturas
        print("\n✨ Proceso de eliminación finalizado.")
    except Exception as e:
        print(f"❌ Error Fatal: {e}")
    finally:
        input("Presiona Enter para cerrar el navegador...")
        driver.quit()