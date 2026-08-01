import json
import time
import os
from dotenv import load_dotenv
from selenium import webdriver
import csv
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys # Necesario para borrar inputs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# --- CONFIGURACIÓN ---
load_dotenv()
USUARIO = os.getenv("CIANBOX_USER")
PASSWORD = os.getenv("CIANBOX_PASS")
URL_LOGIN = os.getenv("URL_LOGIN")

ARCHIVO_JSON = "lote_cianbox.json"
CARPETA_BASE = os.getcwd()
DIR_LOGS = os.path.join(CARPETA_BASE, "logs")
DIR_PROCESADOS = os.path.join(CARPETA_BASE, "02_procesados")
DIR_ERRORES = os.path.join(CARPETA_BASE, "03_errores")
ARCHIVO_LOG_CSV = os.path.join(DIR_LOGS, "audit_log.csv")
ARCHIVO_PROCESADAS_CSV = os.path.join(DIR_LOGS, "procesadas.csv")
ARCHIVO_ERRORES_CSV = os.path.join(DIR_LOGS, "errores.csv")

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
            if (inputHidden) {
                inputHidden.value = data.id;
                inputHidden.dispatchEvent(new Event('input', { bubbles: true }));
                inputHidden.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery) {
                    window.jQuery(inputHidden).change();
                    window.jQuery(inputHidden).trigger('change');
                }
            }

            // Asignar Nombre Visual (Con chequeo de nulos)
            var inputVisual = document.querySelector('input.fc.required[autocomplete="no_auto"]');
            if (inputVisual) {
                // Usamos nombre, razon social o el termino de busqueda si todo falla
                inputVisual.value = data.nombre || data.razon_social || termino;
                inputVisual.dispatchEvent(new Event('input', { bubbles: true }));
                inputVisual.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery) {
                    window.jQuery(inputVisual).change();
                    window.jQuery(inputVisual).trigger('change');
                }
            }
            callback("OK");
        } else { callback("ERROR"); }
    }).catch(e => callback("EXCEPTION: " + e));
"""

JS_BUSCAR_PRODUCTO = """
    var callback = arguments[arguments.length - 1];
    var codigo = arguments[0];
    var codigoNorm = codigo.trim().toUpperCase();
    
    fetch("/equipstore/modules/pv_productos/acomplete.php", {
        headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest' },
        body: "id_usuario=5&incluye_insumos=1&id_moneda=1&cotizacion=1&userid=5&userlevel=1&sec=pv_compras&box=alta&bsearch=" + encodeURIComponent(codigo),
        method: "POST", credentials: "include"
    }).then(r => r.text()).then(html => {
        // Creamos un elemento temporal para parsear la tabla de resultados
        var div = document.createElement('div');
        div.innerHTML = html;
        var filas = div.querySelectorAll('tr[rel]');
        var encontrado = null;
 
        // Iteramos sobre los resultados para buscar coincidencia exacta
        for (var i = 0; i < filas.length; i++) {
            try {
                var jsonRaw = filas[i].getAttribute('rel').replace(/&quot;/g, '"');
                var data = JSON.parse(jsonRaw);
                var desc = (data.desc || "").toUpperCase();
                var codInterno = (data.adicional && data.adicional.codigo_interno) ? data.adicional.codigo_interno.toString().toUpperCase() : "";
                
                // CRITERIOS DE COINCIDENCIA:
                // 1. El código está entre corchetes en la descripción: "[CODIGO]"
                // 2. Coincidencia exacta con codigo interno
                if (desc.includes("[" + codigoNorm + "]") || codInterno === codigoNorm) {
                    encontrado = data;
                    break; // Encontramos el exacto, dejamos de buscar
                }
            } catch(e) { continue; }
        }
 
        if (encontrado) {
            // Asignar ID
            var inputId = document.querySelector('input[name="add_id_producto"]');
            if (inputId) {
                inputId.value = encontrado.id;
                inputId.dispatchEvent(new Event('input', { bubbles: true }));
                inputId.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery) {
                    window.jQuery(inputId).change();
                    window.jQuery(inputId).trigger('change');
                }
            }
            
            // Asignar Nombre Visual
            var inputNombre = document.querySelector('.box_main_field');
            var nombreFinal = encontrado.nombre || codigo;
            if(inputNombre) {
                inputNombre.value = nombreFinal; 
                inputNombre.dispatchEvent(new Event('input', { bubbles: true }));
                inputNombre.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery) {
                    window.jQuery(inputNombre).change();
                    window.jQuery(inputNombre).trigger('change');
                }
            }
            var descLimpia = (encontrado.desc || "").replace(/\\|/g, " ");
            callback("OK|" + nombreFinal + "|" + descLimpia);
        } else { 
            // Si no se encuentra coincidencia exacta, limpiamos el ID para evitar asociaciones erróneas
            var inputId = document.querySelector('input[name="add_id_producto"]');
            if (inputId) {
                inputId.value = "0";
                inputId.dispatchEvent(new Event('input', { bubbles: true }));
                inputId.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery) {
                    window.jQuery(inputId).change();
                    window.jQuery(inputId).trigger('change');
                }
            }
            callback("NOT_FOUND"); 
        }
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
    "select_stock":  (By.NAME, "recibida"),
    "select_contribuyente": (By.NAME, "id_contribuyente"),
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
    "btn_add_percepcion": (By.ID, "add_impuesto"),
    "btn_cerrar_ventana": (By.CSS_SELECTOR, "a.close[alt='Cerrar']"), # Botón 'X' del modal principal
    "btn_aceptar_confirmacion": (By.CSS_SELECTOR, "a.accept"), # Botón 'Aceptar' de la ventana de confirmación
    "notificacion_error": (By.CSS_SELECTOR, "div.windowNtf")
}

MAPEO_PROVINCIAS = {
    "Capital Federal": "2",
    "Ciudad de Buenos Aires": "2",
    "C.A.B.A.": "2",
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
    # --- MODO HEADLESS (Descomentar para ejecutar en segundo plano) ---
    # options.add_argument("--headless")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1920,1080") # Necesario para evitar errores de renderizado
    return webdriver.Chrome(options=options)

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

def escribir_teclado(driver, selector, texto):
    """
    Escribe el valor simulando pulsaciones de teclado físicamente.
    Útil para campos con máscaras de entrada (como la fecha) o inputs con autocompletar.
    """
    elemento = driver.find_element(*selector)
    elemento.click()
    time.sleep(0.05)
    elemento.send_keys(Keys.CONTROL + "a")
    elemento.send_keys(Keys.BACK_SPACE)
    valor_limpio = limpiar_monto_para_input(str(texto))
    elemento.send_keys(valor_limpio)
    elemento.send_keys(Keys.TAB)
    time.sleep(0.05)

def escribir_seguro(driver, selector, texto):
    """
    Escribe el valor limpio utilizando JavaScript para velocidad extrema y confiabilidad.
    """
    elemento = driver.find_element(*selector)
    valor_limpio = limpiar_monto_para_input(str(texto))
    driver.execute_script(
        "arguments[0].value = arguments[1]; "
        "arguments[0].dispatchEvent(new Event('input', { bubbles: true })); "
        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
        elemento, valor_limpio
    )

def reiniciar_modal(driver):
    """Cierra el modal actual y vuelve a abrir el formulario de Alta."""
    print("      🔄 Reiniciando formulario...")
    wait = WebDriverWait(driver, 10)
    
    # 1. Intentar cerrar la ventana principal (el modal de carga)
    try:
        click_seguro(driver, SELECTORES["btn_cerrar_ventana"])
    except Exception as e:
        # Fallback si el click_seguro falla (ej. elemento no clickeable)
        try:
            driver.execute_script("document.querySelector('a.close[alt=\"Cerrar\"]').click();")
        except Exception as e2:
            print(f"         ⚠️ Fallback para cerrar ventana principal falló: {e2}")
    
    # 2. Esperar y hacer clic en el botón 'Aceptar' de la ventana de confirmación
    try:
        confirm_wait = WebDriverWait(driver, 3)
        aceptar_btn = confirm_wait.until(EC.element_to_be_clickable(SELECTORES["btn_aceptar_confirmacion"]))
        aceptar_btn.click()
        confirm_wait.until(EC.staleness_of(aceptar_btn))
        print("         ✅ Confirmación de cierre aceptada.")
    except:
        print("         ℹ️ No se detectó ventana de confirmación de cierre o no fue necesaria.")
    
    # Esperar que el modal principal se haya cerrado (btn_cerrar_ventana invisible)
    try:
        wait.until(EC.invisibility_of_element_located(SELECTORES["btn_cerrar_ventana"]))
    except:
        pass
        
    click_seguro(driver, SELECTORES["btn_alta"])
    
    # Esperar a que el formulario cargue
    wait.until(EC.presence_of_element_located(SELECTORES["fecha"]))
    print("         ✅ Formulario de alta reabierto.")

def inicializar_log_selenium():
    """Asegura que la carpeta de logs y el archivo CSV existan."""
    if not os.path.exists(DIR_LOGS):
        os.makedirs(DIR_LOGS)
    
    for archivo in [ARCHIVO_LOG_CSV, ARCHIVO_PROCESADAS_CSV, ARCHIVO_ERRORES_CSV]:
        if not os.path.exists(archivo):
            with open(archivo, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Fecha", "Archivo", "Proveedor", "Tipo", "Numero", "Estado", "Motivo", "Diferencia"])

def calcular_similitud_palabras(pdf_desc, cian_desc):
    """Calcula el porcentaje de palabras clave del PDF que coinciden con las de Cianbox."""
    def obtener_palabras(texto):
        if not texto:
            return set()
        # Limpiar texto: caracteres alfanuméricos en mayúsculas
        limpio = "".join(c if c.isalnum() or c.isspace() else " " for c in texto.upper())
        # Quedarse con palabras significativas de más de 2 caracteres
        return {w for w in limpio.split() if len(w) > 2}

    palabras_pdf = obtener_palabras(pdf_desc)
    palabras_cian = obtener_palabras(cian_desc)
    
    if not palabras_pdf:
        return 1.0  # Sin descripción en el PDF, no contrastamos
        
    coincidencias = palabras_pdf.intersection(palabras_cian)
    return len(coincidencias) / len(palabras_pdf)

def registrar_log_selenium(cabecera_data, estado, motivo, diferencia="0.00"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    archivo_ref = f"Selenium_Carga_{cabecera_data.get('proveedor', 'N/A')}_{cabecera_data.get('numero', 'N/A')}"
    row = [timestamp, archivo_ref, cabecera_data.get('proveedor', 'N/A'), cabecera_data.get('tipo', 'N/A'), cabecera_data.get('numero', 'N/A'), estado, motivo, diferencia]
    
    if estado in ["OK", "CARGA_EXITOSA"]:
        target = ARCHIVO_PROCESADAS_CSV
    elif "ERROR" in estado or "RECHAZADO" in estado:
        target = ARCHIVO_ERRORES_CSV
    else:
        target = ARCHIVO_LOG_CSV

    with open(target, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)

def login(driver):
    print("🔑 Logueando...")
    driver.get(URL_LOGIN)
    wait = WebDriverWait(driver, 10)
    try:
        user_input = wait.until(EC.presence_of_element_located(SELECTORES["login_user"]))
        user_input.send_keys(USUARIO)
        driver.find_element(*SELECTORES["login_pass"]).send_keys(PASSWORD)
        driver.find_element(*SELECTORES["login_btn"]).click()
        wait.until(EC.presence_of_element_located(SELECTORES["tab_compras"]))
    except:
        if len(driver.find_elements(*SELECTORES["login_user"])) == 0:
            print("   ✅ Ya estabas logueado.")
        else:
            raise Exception("No se pudo iniciar sesión ni verificar estado logueado.")

def asegurar_sucursal(driver, sucursal_nombre):
    """Verifica la sucursal activa en la esquina superior derecha y la cambia si es necesario."""
    sucursal_nombre = sucursal_nombre.upper().strip()
    print(f"🏢 Verificando sucursal activa (requerida: {sucursal_nombre})...")
    
    JS_CHECK_SUCURSAL = """
        const el = document.querySelector('a.selected_sucursal') || document.querySelector('a[alt="elegir_sucursal"]');
        if (el) {
            const txt = el.innerText.toUpperCase().trim();
            if (txt === arguments[0]) {
                return "OK";
            }
        }
        return "OTRA_SUCURSAL";
    """
    
    try:
        status = driver.execute_script(JS_CHECK_SUCURSAL, sucursal_nombre)
        if status == "OK":
            print(f"   ✅ Sucursal activa correcta: {sucursal_nombre}")
            return "ALREADY_OK"
    except Exception as e:
        print(f"   ⚠️ Error al verificar sucursal: {e}")
        
    print(f"   ⚠️ Sucursal incorrecta o no detectada. Cambiando a {sucursal_nombre}...")
    
    # 2. Hacer clic en el selector de sucursal
    JS_CLICK_SUCURSAL_HEADER = """
        const el = document.querySelector('a.selected_sucursal') || document.querySelector('a[alt="elegir_sucursal"]');
        if (el) {
            el.click();
            return "CLICKED";
        }
        return "NOT_FOUND";
    """
    
    try:
        clicked = driver.execute_script(JS_CLICK_SUCURSAL_HEADER)
        if clicked == "NOT_FOUND":
            print("   ❌ Error: No se pudo encontrar el selector de sucursal en el header.")
            return "FAILED"
    except Exception as e:
        print(f"   ❌ Error al hacer clic en el selector de sucursal: {e}")
        return "FAILED"
        
    # Esperar a que la ventana de selección de sucursal esté visible
    time.sleep(1.5)
    
    # 3. Seleccionar la sucursal y hacer clic en Aceptar en el modal
    JS_SELECCIONAR_Y_ACEPTAR = """
        const target = arguments[0];
        const labels = document.querySelectorAll('#rec_sucursales label');
        let found = false;
        for (let label of labels) {
            const txt = label.innerText.toUpperCase().trim();
            if (txt.startsWith(target)) {
                const input = label.querySelector('input[type="radio"]');
                if (input) {
                    input.click();
                    found = true;
                    break;
                }
            }
        }
        
        if (!found) return "SUCURSAL_NOT_FOUND_IN_MODAL";
        
        const botones = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a.accept, a.btn, .button'));
        for (let btn of botones) {
            const txt = (btn.textContent || btn.value || "").trim().toUpperCase();
            if (txt === "ACEPTAR" || txt.includes("ACEPTAR") || txt.includes("SAVE") || txt.includes("GUARDAR")) {
                btn.click();
                return "OK";
            }
        }
        return "ACCEPT_BUTTON_NOT_FOUND";
    """
    
    try:
        res = driver.execute_script(JS_SELECCIONAR_Y_ACEPTAR, sucursal_nombre)
        if res == "OK":
            print(f"   🏢 Sucursal cambiada a {sucursal_nombre}. Esperando recarga...")
            time.sleep(3)  # Esperar a que la página recargue con la nueva sucursal
            return "CHANGED"
        else:
            print(f"   ❌ Error al cambiar sucursal en el modal: {res}")
            return "FAILED"
    except Exception as e:
        print(f"   ❌ Fallo al ejecutar la selección de sucursal: {e}")
        return "FAILED"

def navegar_una_sola_vez(driver):
    """Navega al formulario de alta UNA VEZ al principio."""
    wait = WebDriverWait(driver, 10)
    print("📍 Navegando al formulario inicial...")
    
    try:
        wait.until(EC.element_to_be_clickable(SELECTORES["tab_compras"])).click()
    except:
        driver.execute_script("document.querySelector(\"a[rel='pv_compras']\").click();")
    
    try:
        wait.until(EC.element_to_be_clickable(SELECTORES["btn_alta"])).click()
    except:
        driver.execute_script("document.querySelector(\"a[rel='alta']\").click();")

    wait.until(EC.presence_of_element_located(SELECTORES["fecha"]))
    print("✅ Formulario listo. Iniciando bucle de carga...")

def cargar_historial_cargas_exitosas():
    """
    Lee procesadas.csv y retorna un set con las claves de facturas ya cargadas en Cianbox.
    Clave: PROVEEDOR_TIPO_NUMERO
    """
    historial = set()
    if not os.path.exists(ARCHIVO_PROCESADAS_CSV):
        return historial

    try:
        with open(ARCHIVO_PROCESADAS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Saltar encabezado
            for row in reader:
                if len(row) < 6: continue
                # Estructura: Fecha, Archivo, Proveedor, Tipo, Numero, Estado, ...
                prov, tipo, nro, estado = row[2], row[3], row[4], row[5]
                
                # Solo nos importa si ya fue cargada exitosamente en Cianbox
                if estado == "CARGA_EXITOSA":
                    key = f"{prov.strip().upper()}_{tipo.strip().upper()}_{nro.strip()}"
                    historial.add(key)
        print(f"📚 Historial de cargas: {len(historial)} comprobantes ya subidos.")
    except Exception as e:
        print(f"⚠️ Error leyendo historial de cargas: {e}")
    
    return historial

def procesar_lote(driver):
    if not os.path.exists(ARCHIVO_JSON): return
    with open(ARCHIVO_JSON, 'r', encoding='utf-8') as f:
        facturas = json.load(f)

    wait = WebDriverWait(driver, 10)
    inicializar_log_selenium() # Inicializar el log al inicio del procesamiento del lote
    
    # --- NUEVO: Cargar historial para evitar duplicados ---
    historial_cargadas = cargar_historial_cargas_exitosas()

    # --- PASO 1: NAVEGACIÓN INICIAL (FUERA DEL BUCLE) ---
    navegar_una_sola_vez(driver)

    # --- PASO 2: BUCLE DE CARGA ---
    for i, factura in enumerate(facturas):
        cab = factura["cabecera"]
        
        # --- CHEQUEO DE DUPLICADOS LOCAL ---
        key = f"{cab['proveedor'].strip().upper()}_{cab['tipo'].strip().upper()}_{cab['numero'].strip()}"
        if key in historial_cargadas:
            print(f"⏭️ SALTADO: {cab['numero']} (Ya figura como CARGA_EXITOSA)")
            continue
            
        print(f"\n📄 [{i+1}/{len(facturas)}] Procesando: {cab['numero']}")
        intentos = 3
        for intento in range(intentos):
            try:

                # --- SELECCIONAR SUCURSAL SEGÚN CONTRIBUYENTE ---
                id_contribuyente = str(cab.get("id_contribuyente", "0"))
                sucursal_req = "1318 SRL" if id_contribuyente == "1" else "AV. WARNES 1318"

                status_sucursal = asegurar_sucursal(driver, sucursal_req)
                if status_sucursal == "FAILED":
                    print(f"   ❌ No se pudo establecer la sucursal {sucursal_req}. Saltando factura.")
                    break
                elif status_sucursal == "CHANGED":
                    # Si cambió de sucursal, la página se recargó y cerró el modal. Reabrimos.
                    navegar_una_sola_vez(driver)

                # A. PROVEEDOR (JS)
                wait.until(EC.presence_of_element_located((By.NAME, "id_proveedor")))
                res_prov = driver.execute_async_script(JS_BUSCAR_PROVEEDOR, cab["proveedor"])
                if "ERROR" in res_prov:
                    print("   ❌ Proveedor no encontrado.")
                    registrar_log_selenium(cab, "ERROR_PROVEEDOR", "Proveedor no encontrado en Cianbox.")
                    break

                # B. CABECERA
                # Tip: Como es "Nueva Compra", los campos están limpios, pero por seguridad limpiamos igual
                # Ajuste Máscara: Cianbox tiene el '20' fijo (ej: __/__/20__). Enviamos ddmmyy (180226).
                fecha_dt = datetime.strptime(cab["fecha"], "%d/%m/%Y")
                fecha_formateada = fecha_dt.strftime("%d%m%y")
                escribir_teclado(driver, SELECTORES["fecha"], fecha_formateada)
                escribir_teclado(driver, SELECTORES["pv"], cab["puntoVenta"])
                escribir_teclado(driver, SELECTORES["numero"], cab["numero"])

                # Selects
                val_tipo = MAPEO_COMPROBANTES.get(cab["tipo"].upper(), "1") 
                val_letra = MAPEO_LETRAS.get(cab["letra"].upper(), "1")     
                Select(driver.find_element(*SELECTORES["select_tipo"])).select_by_value(val_tipo)
                Select(driver.find_element(*SELECTORES["select_letra"])).select_by_value(val_letra)

                # Select Contribuyente
                val_contribuyente = str(cab.get("id_contribuyente", "0"))
                Select(driver.find_element(*SELECTORES["select_contribuyente"])).select_by_value(val_contribuyente)

                # Pausa para asegurar que el cambio de tipo de comprobante no resetee el campo de stock
                time.sleep(0.5)

                # Control de Stock (NC Financieras vs Devolución Mercadería)
                mueve_stock = cab.get("mueve_stock", True)
                print(f"      📦 Configuración de Stock: {'MUEVE STOCK (toda_sr)' if mueve_stock else 'NO MUEVE STOCK (no_stock)'}")

                select_stock = Select(driver.find_element(*SELECTORES["select_stock"]))
                if not mueve_stock:
                    select_stock.select_by_value("no_stock")
                else:
                    # Default: Mueve stock (toda_sr = En su totalidad, SIN Remito)
                    select_stock.select_by_value("toda_sr")

                # C. PRODUCTOS
                mismatch_detectado = False
                detalle_mismatch = ""
                for prod in factura["productos"]:
                    # 1. Buscar y Asignar ID (JS)
                    res_prod = driver.execute_async_script(JS_BUSCAR_PRODUCTO, prod["codigo"])

                    if "NOT_FOUND" in res_prod or "ERROR" in res_prod:
                        # CASO: No existe o no coincide exactamente.
                        # Estrategia: Cargar como ítem de texto (sin ID asociado)
                        print(f"   ⚠️ Item {prod['codigo']} no vinculado (Carga Genérica).")
                        registrar_log_selenium(cab, "ITEM_GENERICO", f"Código '{prod['codigo']}' cargado sin vincular a stock.")

                        # Escribimos manualmente la descripción del PDF en el input visual
                        desc_manual = f"{prod['codigo']} {prod['descripcion']}"
                        escribir_teclado(driver, (By.CSS_SELECTOR, ".box_main_field"), desc_manual)

                    else:
                        # CASO: Encontrado y vinculado
                        parts = res_prod.split("|")
                        nombre_prod_cian = parts[1] if len(parts) > 1 else "S/D"
                        desc_prod_cian = parts[2] if len(parts) > 2 else ""

                        # Calcular similitud de descripción para alertar discrepancias de código (ej. choques de EANs o códigos cortos)
                        similitud = calcular_similitud_palabras(prod["descripcion"], desc_prod_cian or nombre_prod_cian)
                        if similitud == 0.0:
                            mismatch_detectado = True
                            detalle_mismatch = f"Código {prod['codigo']}: PDF '{prod['descripcion']}' vs Cianbox '{nombre_prod_cian} {desc_prod_cian}'"
                            break  # Abortar carga de productos de esta factura de inmediato
                        elif nombre_prod_cian != prod['codigo']:
                            registrar_log_selenium(cab, "PRODUCTO_OK", f"Código PDF: {prod['codigo']} -> Cianbox: {nombre_prod_cian}")

                    # 2. Cantidad y Precio
                    escribir_seguro(driver, SELECTORES["cant"], prod["cantidad"])
                    precio_limpio = limpiar_monto_para_input(prod["precio"])
                    escribir_seguro(driver, SELECTORES["precio"], precio_limpio)

                    # 3. Agregar
                    driver.find_element(*SELECTORES["btn_add"]).click()

                    # Esperar a que se añada el producto (por ejemplo, que el input visual se vacíe al agregarse)
                    try:
                        WebDriverWait(driver, 3, poll_frequency=0.1).until(
                            lambda d: d.find_element(By.CSS_SELECTOR, ".box_main_field").get_attribute("value") == ""
                        )
                    except:
                        time.sleep(0.1)

                # Si detectamos un producto sospechoso, cancelamos y movemos el PDF a la carpeta de errores
                if mismatch_detectado:
                    print(f"   ❌ RECHAZADO EN CARGA (PRODUCTO SOSPECHOSO): {detalle_mismatch}")
                    registrar_log_selenium(cab, "RECHAZADO_SOSPECHOSO", f"Rechazado en carga por sospecha de producto incorrecto: {detalle_mismatch}")

                    # Mover el archivo PDF de 02_procesados a 03_errores
                    nombre_pdf = cab.get("archivo")
                    if nombre_pdf:
                        ruta_ok = os.path.join(DIR_PROCESADOS, nombre_pdf)
                        ruta_error = os.path.join(DIR_ERRORES, nombre_pdf)
                        if os.path.exists(ruta_ok):
                            try:
                                os.rename(ruta_ok, ruta_error)
                                print(f"      📁 PDF movido de procesados a errores: {nombre_pdf}")
                            except Exception as file_err:
                                print(f"      ⚠️ No se pudo mover el PDF: {file_err}")

                    # Limpiar formulario/modal para poder seguir con la siguiente factura
                    reiniciar_modal(driver)
                    break

                # --- DETECCIÓN DE DUPLICADOS ---
                # Lo hago después de la carga de productos para darle tiempo al AJAX de Cianbox para validar
                try:
                    div_dup = driver.find_elements(By.ID, "mb_duplicated")
                    if div_dup and div_dup[0].is_displayed():
                        texto_error = div_dup[0].text.replace("\n", " ").strip()
                        print(f"   ⛔ DUPLICADA: {texto_error}")
                        registrar_log_selenium(cab, "DUPLICADO", texto_error)
                        reiniciar_modal(driver)
                        break
                except Exception:
                    pass
                if div_dup and div_dup[0].is_displayed():
                    texto_error = div_dup[0].text.replace("\n", " ").strip()
                    print(f"   ⛔ DUPLICADA: {texto_error}")
                    registrar_log_selenium(cab, "DUPLICADO", texto_error)
                    reiniciar_modal(driver)
                    break

                # PERCEPCIONES (Versión Reforzada)
                if cab.get("percepciones_iibb"):
                    print("   ⚖️ Entrando a pestaña Percepciones...")
                    click_seguro(driver, SELECTORES["tab_percepciones"])
                    wait.until(EC.element_to_be_clickable(SELECTORES["select_provincia"]))

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
                        try:
                            driver.find_element(*SELECTORES["btn_add_percepcion"]).click()
                        except:
                            driver.execute_script("document.getElementById('add_impuesto').click();")

                        # Esperar a que el campo de monto de percepción se limpie
                        try:
                            WebDriverWait(driver, 2, poll_frequency=0.1).until(
                                lambda d: d.find_element(*SELECTORES["monto_percepcion"]).get_attribute("value") == ""
                            )
                        except:
                            time.sleep(0.1)

                    print(f"      ✅ Item de IIBB agregado.")

                # Re-asegurar la opción de stock elegida justo antes de guardar (por si algún AJAX la reseteó)
                try:
                    select_stock = Select(driver.find_element(*SELECTORES["select_stock"]))
                    if not mueve_stock:
                        select_stock.select_by_value("no_stock")
                    else:
                        select_stock.select_by_value("toda_sr")
                except Exception as stock_err:
                    print(f"      ⚠️ No se pudo re-confirmar el tipo de stock: {stock_err}")

                # E. GUARDAR Y PREPARAR SIGUIENTE
                if "1139887" in str(cab.get("numero", "")):
                    print("\n⚠️ PAUSA DE REVISIÓN ACTIVADA PARA FACTURA 1139887.")
                    print("   Por favor, revisa todos los campos en el navegador.")
                    input("   Presiona [ENTER] en esta terminal para continuar con el guardado...")

                old_fecha_el = driver.find_element(*SELECTORES["fecha"])
                print("💾 Guardando...")
                driver.find_element(*SELECTORES["guardar"]).click()

                # Esperar a que ocurra una de tres cosas:
                # 1. Aparezca la ventana de duplicado
                # 2. Aparezca la notificación de error
                # 3. La fecha anterior quede obsoleta (staleness, indicando guardado exitoso y refresco de página)
                print("   ⏳ Esperando confirmación de guardado...")
                try:
                    WebDriverWait(driver, 5, poll_frequency=0.1).until(
                        lambda d: len(d.find_elements(By.ID, "mb_duplicated")) > 0 or 
                                  len(d.find_elements(*SELECTORES["notificacion_error"])) > 0 or
                                  EC.staleness_of(old_fecha_el)(d)
                    )
                except:
                    pass
                try:
                    div_dup = driver.find_elements(By.ID, "mb_duplicated")
                    if div_dup and div_dup[0].is_displayed():
                        texto_error = div_dup[0].text.replace("\n", " ").strip()
                        print(f"   ⛔ DUPLICADA: {texto_error}")
                        registrar_log_selenium(cab, "DUPLICADO", texto_error)
                        reiniciar_modal(driver)
                        break
                except Exception:
                    pass

                try:
                    ntf = driver.find_elements(*SELECTORES["notificacion_error"])
                    if ntf and ntf[0].is_displayed() and "Faltan campos" in ntf[0].text:
                        print("   ❌ ERROR AL GUARDAR: Faltan campos requeridos.")
                        registrar_log_selenium(cab, "ERROR_GUARDADO", "Faltan campos requeridos al intentar guardar.")
                        reiniciar_modal(driver)
                        break
                except Exception:
                    pass
                # Si el elemento no quedó obsoleto por alguna razón, forzar la espera
                try:
                    if not EC.staleness_of(old_fecha_el)(driver):
                        WebDriverWait(driver, 3, poll_frequency=0.1).until(EC.staleness_of(old_fecha_el))
                except:
                    pass

                # Esperar el nuevo formulario limpio
                wait.until(EC.presence_of_element_located(SELECTORES["fecha"]))
                wait.until(lambda d: d.find_element(*SELECTORES["numero"]).get_attribute("value") == "")
                print("✅ Guardado. Formulario listo para la siguiente.")
                registrar_log_selenium(cab, "CARGA_EXITOSA", "Carga confirmada en Cianbox")

                break
            except Exception as e:
                if intento < intentos - 1:
                    print(f"   ⚠️ Intento {intento+1}/{intentos} falló para factura {cab['numero']}: {e}. Reintentando...")
                    try:
                        reiniciar_modal(driver)
                    except Exception as reset_err:
                        print(f"      ⚠️ Error al reiniciar formulario: {reset_err}. Refrescando...")
                        try:
                            driver.refresh()
                            time.sleep(2)
                            navegar_una_sola_vez(driver)
                        except:
                            pass
                else:
                    print(f"   ❌ Factura {cab['numero']} falló tras {intentos} intentos. Pasando a la siguiente.")
                    registrar_log_selenium(cab, "ERROR_SELENIUM", str(e))
                    try:
                        reiniciar_modal(driver)
                    except:
                        pass

if __name__ == "__main__":
    driver = iniciar_driver()
    try:
        login(driver)
        procesar_lote(driver)
        print("\n✨ Fin del proceso.")
    except Exception as e:
        print(f"❌ Error Fatal: {e}")
    finally:
        # Pausa la ejecución y mantiene el navegador abierto para depuración
        input("Presiona Enter para cerrar el navegador y finalizar el script...")
        driver.quit()