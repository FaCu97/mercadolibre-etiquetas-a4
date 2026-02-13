import json
import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys # Necesario para borrar inputs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
load_dotenv()
USUARIO = os.getenv("CIANBOX_USER")
PASSWORD = os.getenv("CIANBOX_PASS")
URL_LOGIN = os.getenv("URL_LOGIN")
ARCHIVO_JSON = "lote_cianbox.json"

# ==============================================================================
# 1. CONSTANTES JS (MEJORADAS PARA EVITAR "UNDEFINED")
# ==============================================================================
JS_BUSCAR_PROVEEDOR = """
    var callback = arguments[arguments.length - 1];
    var termino = arguments[0];
    
    fetch("/equipstore/modules/pv_proveedores/acomplete.php", {
        headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest' },
        body: "userlevel=1&userid=5&rrhh=1&sec=pv_compras&box=alta&bsearch=" + encodeURIComponent(termino),
        method: "POST", credentials: "include"
    }).then(r => r.text()).then(html => {
        var div = document.createElement('div'); div.innerHTML = html;
        var fila = div.querySelector('tr[rel]');
        if (fila) {
            var data = JSON.parse(fila.getAttribute('rel').replace(/&quot;/g, '"'));
            
            // Asignar ID Oculto
            var inputHidden = document.querySelector('input[name="id_proveedor"]');
            if (inputHidden) inputHidden.value = data.id;

            // Asignar Nombre Visual (Con chequeo de nulos)
            var inputVisual = document.querySelector('input.fc.required[autocomplete="no_auto"]');
            if (inputVisual) {
                // Usamos nombre, razon social o el termino de busqueda si todo falla
                inputVisual.value = data.nombre || data.razon_social || termino;
                inputVisual.dispatchEvent(new Event('input', { bubbles: true }));
            }
            callback("OK");
        } else { callback("ERROR"); }
    }).catch(e => callback("EXCEPTION: " + e));
"""

JS_BUSCAR_PRODUCTO = """
    var callback = arguments[arguments.length - 1];
    var codigo = arguments[0];
    
    fetch("/equipstore/modules/pv_productos/acomplete.php", {
        headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest' },
        body: "id_usuario=5&incluye_insumos=1&id_moneda=1&cotizacion=1&userid=5&userlevel=1&sec=pv_compras&box=alta&bsearch=" + encodeURIComponent(codigo),
        method: "POST", credentials: "include"
    }).then(r => r.text()).then(html => {
        var match = html.match(/rel="([^"]+)"/) || html.match(/rel='([^']+)'/);
        if (match && match[1]) {
            var data = JSON.parse(match[1].replace(/&quot;/g, '"'));
            
            // Asignar ID
            var inputId = document.querySelector('input[name="add_id_producto"]');
            if (inputId) inputId.value = data.id;
            
            // Asignar Nombre Visual (Evitar Undefined)
            var inputNombre = document.querySelector('.box_main_field');
            if(inputNombre) {
                // Si data.nombre es null, ponemos el código para que no quede feo
                inputNombre.value = data.nombre || codigo; 
                inputNombre.dispatchEvent(new Event('input', { bubbles: true }));
            }
            callback("OK");
        } else { callback("ERROR"); }
    }).catch(e => callback("EXCEPTION: " + e));
"""

# ==============================================================================
# 2. SELECTORES Y MAPEOS
# ==============================================================================
MAPEO_COMPROBANTES = { "FACTURA": "1", "NOTA DE CREDITO": "5", "NOTA DE DEBITO": "6", "REMITO": "7" }
MAPEO_LETRAS = { "A": "1", "B": "2", "C": "3", "M": "4", "E": "8" }

SELECTORES = {
    "login_user": (By.NAME, "user"),
    "login_pass": (By.NAME, "password"),
    "login_btn":  (By.TAG_NAME, "button"),
    
    # Navegación
    "tab_compras": (By.CSS_SELECTOR, "a[rel='pv_compras']"),
    "btn_alta":    (By.CSS_SELECTOR, "a[rel='alta']"),

    # Formulario
    "select_tipo":   (By.NAME, "id_comprobante"),
    "select_letra":  (By.NAME, "id_tipo"),
    "fecha":   (By.NAME, "fecha_comprobante"),
    "pv":      (By.NAME, "punto_venta"),
    "numero":  (By.NAME, "numero"),
    "cant":    (By.NAME, "add_cantidad"),
    "precio":  (By.NAME, "add_precio_unitario"),
    "btn_add": (By.ID, "add_producto"),
    "guardar": (By.CSS_SELECTOR, "input[value='Aceptar y Nueva']"),
    #IIBB
    "tab_percepciones": (By.CSS_SELECTOR, "a[rel='percepcion']"),
    "select_provincia": (By.NAME, "add_percepcion"),
    "monto_percepcion": (By.NAME, "add_monto"),
    "btn_add_percepcion": (By.ID, "add_impuesto") # Confirmar si este es el ID del botón "+" de percepciones
}

MAPEO_PROVINCIAS = {
    "Capital Federal": "2",
    "Ciudad de Buenos Aires": "2",
    "Santa Fe": "3",
    "Córdoba": "4",
    "Tucuman": "6",
    "Misiones": "7",
    "Corrientes": "9",
    "Mendoza": "12",
    "Buenos Aires": "23",
    "Provincia de Buenos Aires": "23"
}

# ==============================================================================
# 3. FUNCIONES DE LIMPIEZA Y ESCRITURA
# ==============================================================================

def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def limpiar_monto_para_input(monto_str):
    """
    Transforma '1.500,50' en '1500,50'.
    Quita puntos de miles para que el input de Cianbox no se confunda.
    """
    if not monto_str: return "0,00"
    # Quitamos los puntos de miles
    limpio = monto_str.replace(".", "")
    return limpio

def click_seguro(driver, selector):
    wait = WebDriverWait(driver, 10)
    try:
        elemento = wait.until(EC.element_to_be_clickable(selector))
        elemento.click()
    except:
        elemento = driver.find_element(*selector)
        driver.execute_script("arguments[0].click();", elemento)

def escribir_seguro(driver, selector, texto):
    """
    Borra el campo agresivamente y escribe el valor limpio.
    """
    elemento = driver.find_element(*selector)
    elemento.click()
    time.sleep(0.1)
    
    # Seleccionar todo y borrar
    elemento.send_keys(Keys.CONTROL + "a")
    elemento.send_keys(Keys.BACK_SPACE)
    
    # Escribimos el valor limpio (sin puntos de miles)
    valor_limpio = limpiar_monto_para_input(str(texto))
    elemento.send_keys(valor_limpio)
    
    # Disparamos el evento 'change' saliendo con TAB
    elemento.send_keys(Keys.TAB)
    time.sleep(0.1)

def login(driver):
    print("🔑 Logueando...")
    driver.get(URL_LOGIN)
    time.sleep(2)
    if len(driver.find_elements(*SELECTORES["login_user"])) > 0:
        driver.find_element(*SELECTORES["login_user"]).send_keys(USUARIO)
        driver.find_element(*SELECTORES["login_pass"]).send_keys(PASSWORD)
        driver.find_element(*SELECTORES["login_btn"]).click()
        time.sleep(2)
    else:
        print("   ✅ Ya estabas logueado.")

def navegar_una_sola_vez(driver):
    """Navega al formulario de alta UNA VEZ al principio."""
    wait = WebDriverWait(driver, 10)
    print("📍 Navegando al formulario inicial...")
    
    # Click Pestaña
    try:
        wait.until(EC.element_to_be_clickable(SELECTORES["tab_compras"])).click()
    except:
        driver.execute_script("document.querySelector(\"a[rel='pv_compras']\").click();")
    
    time.sleep(1.5)

    # Click Botón Alta
    try:
        wait.until(EC.element_to_be_clickable(SELECTORES["btn_alta"])).click()
    except:
        driver.execute_script("document.querySelector(\"a[rel='alta']\").click();")

    # Esperar carga
    wait.until(EC.presence_of_element_located(SELECTORES["fecha"]))
    print("✅ Formulario listo. Iniciando bucle de carga...")


def procesar_lote(driver):
    if not os.path.exists(ARCHIVO_JSON): return
    with open(ARCHIVO_JSON, 'r', encoding='utf-8') as f:
        facturas = json.load(f)

    wait = WebDriverWait(driver, 10)

    # --- PASO 1: NAVEGACIÓN INICIAL (FUERA DEL BUCLE) ---
    navegar_una_sola_vez(driver)

    # --- PASO 2: BUCLE DE CARGA ---
    for i, factura in enumerate(facturas):
        cab = factura["cabecera"]
        print(f"\n📄 [{i+1}/{len(facturas)}] Procesando: {cab['numero']}")

        try:
            # A. CABECERA
            # Tip: Como es "Nueva Compra", los campos están limpios, pero por seguridad limpiamos igual
            escribir_seguro(driver, SELECTORES["fecha"], cab["fecha"])
            escribir_seguro(driver, SELECTORES["pv"], cab["puntoVenta"])
            escribir_seguro(driver, SELECTORES["numero"], cab["numero"])

            # Selects
            val_tipo = MAPEO_COMPROBANTES.get(cab["tipo"].upper(), "1") 
            val_letra = MAPEO_LETRAS.get(cab["letra"].upper(), "1")     
            Select(driver.find_element(*SELECTORES["select_tipo"])).select_by_value(val_tipo)
            Select(driver.find_element(*SELECTORES["select_letra"])).select_by_value(val_letra)

            # B. PROVEEDOR (JS)
            res_prov = driver.execute_async_script(JS_BUSCAR_PROVEEDOR, cab["proveedor"])
            if "ERROR" in res_prov:
                print("   ❌ Proveedor no encontrado.")
                continue

            # C. PRODUCTOS
            for prod in factura["productos"]:
                # 1. Buscar y Asignar ID (JS)
                res_prod = driver.execute_async_script(JS_BUSCAR_PRODUCTO, prod["codigo"])
                if "ERROR" in res_prod:
                    print(f"   ⚠️ Item {prod['codigo']} no encontrado.")
                    continue
                
                # 2. Cantidad y Precio (Ahora con limpieza de miles)
                escribir_seguro(driver, SELECTORES["cant"], prod["cantidad"])
                # Limpiamos el precio antes de mandarlo
                precio_limpio = limpiar_monto_para_input(prod["precio"])
                escribir_seguro(driver, SELECTORES["precio"], precio_limpio)
                
                # 3. Agregar
                driver.find_element(*SELECTORES["btn_add"]).click()
                
                # Esperar que baje a la tabla (buscando el botón de borrar del renglón o pausa simple)
                time.sleep(0.8)

            # PERCEPCIONES (Versión Reforzada)
            if cab.get("percepciones_iibb"):
                print("   ⚖️ Entrando a pestaña Percepciones...")
                click_seguro(driver, SELECTORES["tab_percepciones"])
                time.sleep(0.8) # Espera a que la pestaña se active visualmente

                for perc in cab["percepciones_iibb"]:
                    jurisdiccion = perc["jurisdiccion"]
                    monto = str(perc["monto"]) # Aseguramos que sea string
                    
                    id_prov = MAPEO_PROVINCIAS.get(jurisdiccion, "23")
                    print(f"      📍 Cargando {jurisdiccion} (ID {id_prov}): ${monto}")

                    # Seleccionar Provincia
                    Select(driver.find_element(*SELECTORES["select_provincia"])).select_by_value(id_prov)
                    
                    # Cargar Monto con limpieza extrema
                    campo_monto = driver.find_element(*SELECTORES["monto_percepcion"])
                    
                    # Enviamos el monto sin puntos de miles
                    monto_limpio = limpiar_monto_para_input(monto)
                    campo_monto.send_keys(monto_limpio)
                    
                    # 4. Click en Agregar (el "+" de percepciones)
                    # Si el ID no es 'add_impuesto', suele ser el botón que está al lado del input de monto
                    try:
                        driver.find_element(*SELECTORES["btn_add_percepcion"]).click()
                    except:
                        # Fallback: a veces el botón se llama igual que el de productos o similar
                        driver.execute_script("document.getElementById('add_impuesto').click();")
                    time.sleep(0.1)

                print(f"      ✅ Item de IIBB agregado.")
                time.sleep(0.4) # Pausa para que el renglón aparezca en la lista
            # E. GUARDAR Y PREPARAR SIGUIENTE
            print("💾 Guardando...")
            driver.find_element(*SELECTORES["guardar"]).click()
            
            # ESPERA CRÍTICA:
            # Al guardar, la página se recarga o limpia los campos.
            # Esperamos que el campo fecha vuelva a aparecer o esté listo.
            time.sleep(3) 
            wait.until(EC.presence_of_element_located(SELECTORES["fecha"]))
            print("✅ Guardado. Formulario listo para la siguiente.")

        except Exception as e:
            print(f"🔥 Error en factura {cab['numero']}: {e}")
            # Si falla, quizás quedó a mitad de camino. 
            # Podrías intentar recargar la página: driver.refresh()
            time.sleep(5)

if __name__ == "__main__":
    driver = iniciar_driver()
    try:
        login(driver)
        procesar_lote(driver)
        print("\n✨ Fin del proceso.")
    except Exception as e:
        print(f"❌ Error Fatal: {e}")
    finally:
        # driver.quit()
        pass