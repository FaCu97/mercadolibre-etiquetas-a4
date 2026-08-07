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

CARPETA_BASE = os.getcwd()
DIR_COMPROBANTES = os.path.join(CARPETA_BASE, "comprobantes")


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
            callback("OK");
        } else { callback("ERROR"); }
    }).catch(e => callback("EXCEPTION: " + e));
"""

JS_SET_PROVEEDOR_DIRECTO = """
    var callback = arguments[arguments.length - 1];
    var idProveedor = arguments[0];
    var nombreProveedor = arguments[1];

    try {
        var inputHidden = document.querySelector('input[name="id_proveedor"]');
        if (inputHidden) {
            inputHidden.value = idProveedor;
            inputHidden.dispatchEvent(new Event('input', { bubbles: true }));
            inputHidden.dispatchEvent(new Event('change', { bubbles: true }));
            if (window.jQuery) {
                window.jQuery(inputHidden).change();
                window.jQuery(inputHidden).trigger('change');
            }
        }

        var inputVisual = document.querySelector('#acomp_proveedores input[type="text"]');
        if (!inputVisual) {
            inputVisual = document.querySelector('input.fc.required[autocomplete="no_auto"]');
        }
        if (inputVisual) {
            inputVisual.value = nombreProveedor;
            inputVisual.dispatchEvent(new Event('input', { bubbles: true }));
            inputVisual.dispatchEvent(new Event('change', { bubbles: true }));
            if (window.jQuery) {
                window.jQuery(inputVisual).change();
                window.jQuery(inputVisual).trigger('change');
            }
        }
        callback("OK");
    } catch(e) {
        callback("EXCEPTION: " + e);
    }
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
    
    # Permitir modo visible (GUI) si HEADLESS se pasa como 'false' o '0'
    use_headless = os.getenv("HEADLESS", "true").lower() in ["true", "1", "yes"]
    if use_headless:
        options.add_argument("--headless=new")
        
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin

    if os.path.exists(chromedriver_path):
        from selenium.webdriver.chrome.service import Service
        service = Service(executable_path=chromedriver_path)
        return webdriver.Chrome(service=service, options=options)

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
    Escribe el valor de forma segura esperando que el elemento sea interactuable,
    con fallback por JavaScript en caso de overlays flotantes de notificación.
    """
    wait = WebDriverWait(driver, 5)
    try:
        elemento = wait.until(EC.element_to_be_clickable(selector))
        elemento.click()
        time.sleep(0.05)
        elemento.send_keys(Keys.CONTROL + "a")
        elemento.send_keys(Keys.BACK_SPACE)
        valor_limpio = limpiar_monto_para_input(str(texto))
        elemento.send_keys(valor_limpio)
        elemento.send_keys(Keys.TAB)
    except Exception:
        # Fallback silencioso por JS si hay un cartel flotante sobre el campo
        elemento = driver.find_element(*selector)
        valor_limpio = limpiar_monto_para_input(str(texto))
        driver.execute_script(
            "arguments[0].focus(); "
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true })); "
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
            elemento, valor_limpio
        )
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


def cargar_facturas_cianbox(proveedor_filtro: str = None, factura_id: int = None, factura_ids: list = None):
    """
    Función de entrada expuesta para el Orquestador/Scheduler.
    Lee facturas pendientes desde SQLite e inyecta en Cianbox usando Selenium.
    """
    from sqlalchemy.orm import Session
    from db.database import SessionLocal
    from db.models import Factura, Proveedor, ProcesoLog
    from datetime import datetime

    db: Session = SessionLocal()
    try:
        query = db.query(Factura).filter_by(estado="PENDIENTE_CARGA")
        
        if factura_ids:
            query = query.filter(Factura.id.in_(factura_ids))
        elif factura_id:
            query = query.filter_by(id=factura_id)
        elif proveedor_filtro:
            prov = db.query(Proveedor).filter(Proveedor.nombre.ilike(f"%{proveedor_filtro}%")).first()
            if prov:
                query = query.filter_by(proveedor_id=prov.id)
            else:
                print(f"⚠️ No se encontró el proveedor '{proveedor_filtro}' en SQLite.")
                return

        facturas = query.all()

        if not facturas:
            print("ℹ️ No hay facturas pendientes de carga en SQLite.")
            return

        print(f"🚀 Iniciando carga Selenium para {len(facturas)} factura(s) pendiente(s)...")

        # Convertir modelos SQLAlchemy a lote dict esperado por procesar_lote
        lote_facturas = []
        for f in facturas:
            tipo_full = f.tipo_comprobante.upper() if f.tipo_comprobante else "FACTURA A"
            parts = tipo_full.rsplit(" ", 1)
            tipo_str = parts[0] if len(parts) > 1 else "FACTURA"
            letra_str = parts[1] if len(parts) > 1 else "A"

            # Reconstruir lista de percepciones
            percepciones_list = []
            if f.percepciones and f.percepciones > 0:
                percepciones_list.append({
                    "jurisdiccion": "Capital Federal",  # Valor por defecto
                    "monto": str(f.percepciones).replace(".", ",")
                })

            lote_facturas.append({
                "_sql_id": f.id,
                "cabecera": {
                    "proveedor": f.proveedor.nombre if f.proveedor else "CROMOSOL",
                    "id_cianbox": f.proveedor.id_cianbox if (f.proveedor and f.proveedor.id_cianbox) else None,
                    "nombre_cianbox": f.proveedor.nombre_cianbox if (f.proveedor and f.proveedor.nombre_cianbox) else (f.proveedor.nombre if f.proveedor else "CROMOSOL"),
                    "tipo": tipo_str,
                    "letra": letra_str,
                    "fecha": f.fecha_emision or datetime.now().strftime("%d/%m/%Y"),
                    "puntoVenta": f.numero_comprobante.split("-")[0] if "-" in f.numero_comprobante else "0000",
                    "numero": f.numero_comprobante.split("-")[1] if "-" in f.numero_comprobante else f.numero_comprobante,
                    "total": str(f.total).replace(".", ","),
                    "percepciones_iibb": percepciones_list,
                    "mueve_stock": True
                },

                "productos": [
                    {
                        "codigo": item.codigo or "",
                        "descripcion": item.descripcion,
                        "cantidad": str(int(item.cantidad)),
                        "precio": str(item.precio_unitario).replace(".", ","),
                        "iva": "21.00",
                        "descuento": "0,00"
                    } for item in f.items
                ]
            })


        driver = iniciar_driver()
        try:
            login(driver)
            procesar_lote_desde_sql(driver, lote_facturas, db)
        finally:
            driver.quit()

    finally:
        db.close()

def procesar_lote_desde_sql(driver, facturas_lote, db):
    """Ejecuta la carga invocando el procesador de lotes validado de Selenium."""
    procesar_lote_en_memoria(driver, facturas_lote, db)


def procesar_lote_en_memoria(driver, facturas, db=None):
    """Procesa una lista de facturas en memoria usando toda la lógica original de sucursal, JS_BUSCAR_PRODUCTO, carga genérica y notificaciones."""

    wait = WebDriverWait(driver, 10)
    navegar_una_sola_vez(driver)

    for i, factura in enumerate(facturas):
        cab = factura["cabecera"]
        print(f"\n📄 [{i+1}/{len(facturas)}] Procesando Carga en Cianbox: {cab['numero']}")
        intentos = 3
        for intento in range(intentos):
            try:
                # 1. Sucursal
                id_contribuyente = str(cab.get("id_contribuyente", "0"))
                sucursal_req = "1318 SRL" if id_contribuyente == "1" else "AV. WARNES 1318"
                status_sucursal = asegurar_sucursal(driver, sucursal_req)
                if status_sucursal == "CHANGED":
                    navegar_una_sola_vez(driver)

                # 2. Proveedor (Inyección directa por id_cianbox si existe, o búsqueda de fallback)
                wait.until(EC.presence_of_element_located((By.NAME, "id_proveedor")))
                id_cian = cab.get("id_cianbox")
                nom_cian = cab.get("nombre_cianbox") or cab.get("proveedor")
                
                if id_cian:
                    print(f"   🏢 Inyectando proveedor directo por ID Cianbox ({id_cian} - {nom_cian})...")
                    res_prov = driver.execute_async_script(JS_SET_PROVEEDOR_DIRECTO, str(id_cian), str(nom_cian))
                else:
                    print(f"   🔍 Buscando proveedor vía AJAX (Fallback): '{cab['proveedor']}'...")
                    res_prov = driver.execute_async_script(JS_BUSCAR_PROVEEDOR, cab["proveedor"])

                if "ERROR" in str(res_prov):
                    print("   ❌ Proveedor no encontrado.")
                    break



                # 3. Cabecera
                fecha_dt = datetime.strptime(cab["fecha"], "%d/%m/%Y") if "/" in cab["fecha"] else datetime.now()
                fecha_formateada = fecha_dt.strftime("%d%m%y")
                escribir_teclado(driver, SELECTORES["fecha"], fecha_formateada)
                escribir_teclado(driver, SELECTORES["pv"], cab["puntoVenta"])
                escribir_teclado(driver, SELECTORES["numero"], cab["numero"])

                val_tipo = MAPEO_COMPROBANTES.get(cab["tipo"].upper(), "1")
                val_letra = MAPEO_LETRAS.get(cab["letra"].upper(), "1")
                Select(driver.find_element(*SELECTORES["select_tipo"])).select_by_value(val_tipo)
                Select(driver.find_element(*SELECTORES["select_letra"])).select_by_value(val_letra)

                time.sleep(0.6)

                # --- VALIDACIÓN TEMPRANA DE DUPLICADO (DESPUÉS DE INGRESAR NÚMERO/COMPROBANTE) ---
                div_dup_early = driver.find_elements(By.ID, "mb_duplicated")
                if div_dup_early:
                    style_attr = div_dup_early[0].get_attribute("style") or ""
                    # Si el style no es display:none o si el texto del div no está vacío y es visible
                    if "display: none" not in style_attr and "display:none" not in style_attr and div_dup_early[0].text.strip():
                        texto_dup_early = div_dup_early[0].text.replace("\n", " ").strip()
                        print(f"   ⛔ Factura Duplicada en Cianbox (Detectada al tipear número): {texto_dup_early}")
                        reiniciar_modal(driver)
                        
                        sql_id = factura.get("_sql_id")
                        if sql_id and db:
                            from db.models import Factura, ProcesoLog
                            f_rec = db.query(Factura).get(sql_id)
                            if f_rec:
                                f_rec.estado = "CARGADA_CIANBOX"
                                f_rec.motivo_error = f"Comprobante duplicado en Cianbox: {texto_dup_early}"
                                log = ProcesoLog(
                                    factura_id=f_rec.id,
                                    nivel="WARNING",
                                    mensaje=f"Comprobante omitido por duplicidad detectada en cabecera: {texto_dup_early}"
                                )
                                db.add(log)
                                db.commit()
                        break


                # 4. Productos (Manejo de items vinculados vs no vinculados/genéricos)
                for prod in factura["productos"]:
                    res_prod = driver.execute_async_script(JS_BUSCAR_PRODUCTO, prod["codigo"])
                    if "NOT_FOUND" in str(res_prod) or "ERROR" in str(res_prod):
                        # CASO: Producto no encontrado en stock Cianbox -> Carga genérica manual
                        desc_manual = f"{prod['codigo']} {prod['descripcion']}"
                        escribir_teclado(driver, (By.CSS_SELECTOR, ".box_main_field"), desc_manual)
                    
                    escribir_seguro(driver, SELECTORES["cant"], prod["cantidad"])
                    precio_limpio = limpiar_monto_para_input(prod["precio"])
                    escribir_seguro(driver, SELECTORES["precio"], precio_limpio)
                    driver.find_element(*SELECTORES["btn_add"]).click()

                    try:
                        WebDriverWait(driver, 3, poll_frequency=0.1).until(
                            lambda d: d.find_element(By.CSS_SELECTOR, ".box_main_field").get_attribute("value") == ""
                        )
                    except:
                        time.sleep(0.2)

                # 4.5. PERCEPCIONES DE IIBB
                if cab.get("percepciones_iibb"):
                    print("      📍 Intentando cargar percepciones de IIBB...")
                    try:
                        click_seguro(driver, SELECTORES["tab_percepciones"])
                        wait.until(EC.element_to_be_clickable(SELECTORES["select_provincia"]))

                        for perc in cab["percepciones_iibb"]:
                            jurisdiccion = perc.get("jurisdiccion", "Capital Federal")
                            monto = str(perc["monto"])
                            id_prov = MAPEO_PROVINCIAS.get(jurisdiccion, "23")
                            print(f"      📍 Percepción IIBB {jurisdiccion} (ID {id_prov}): ${monto}")

                            Select(driver.find_element(*SELECTORES["select_provincia"])).select_by_value(id_prov)
                            campo_monto = driver.find_element(*SELECTORES["monto_percepcion"])
                            monto_limpio = limpiar_monto_para_input(monto)
                            campo_monto.send_keys(monto_limpio)

                            try:
                                driver.find_element(*SELECTORES["btn_add_percepcion"]).click()
                            except:
                                driver.execute_script("document.getElementById('add_impuesto').click();")

                            time.sleep(0.3)
                        print("      ✅ Percepciones de IIBB agregadas.")
                    except Exception as perc_err:
                        print(f"      ⚠️ No se pudo cargar percepción IIBB: {perc_err}")

                # 5. Guardar
                old_fecha_el = driver.find_element(*SELECTORES["fecha"])
                driver.find_element(*SELECTORES["guardar"]).click()

                # Esperar 4 segundos a que Cianbox responda y procese la solicitud
                time.sleep(2)
                
                # Verificar exhaustivamente si apareció la ventana de duplicado en Cianbox
                div_dup = driver.find_elements(By.ID, "mb_duplicated")
                modales_flotantes = driver.find_elements(By.CSS_SELECTOR, "div.mb_window, div.windowNtf, div.mb_title")
                
                es_duplicado = False
                texto_dup = "Comprobante ya registrado en Cianbox"

                if div_dup and any(d.is_displayed() for d in div_dup):
                    es_duplicado = True
                    texto_dup = div_dup[0].text.replace("\n", " ").strip()
                else:
                    for mod in modales_flotantes:
                        try:
                            if mod.is_displayed() and "duplicad" in mod.text.lower():
                                es_duplicado = True
                                texto_dup = mod.text.replace("\n", " ").strip()
                                break
                        except:
                            pass

                if es_duplicado:
                    print(f"   ⛔ Factura Duplicada en Cianbox: {texto_dup}")
                    reiniciar_modal(driver)
                    
                    sql_id = factura.get("_sql_id")
                    if sql_id and db:
                        from db.models import Factura, ProcesoLog
                        f_rec = db.query(Factura).get(sql_id)
                        if f_rec:
                            f_rec.estado = "CARGADA_CIANBOX"
                            f_rec.motivo_error = f"Comprobante duplicado en Cianbox: {texto_dup}"
                            log = ProcesoLog(
                                factura_id=f_rec.id,
                                nivel="WARNING",
                                mensaje=f"Comprobante omitido por duplicidad en Cianbox: {texto_dup}"
                            )
                            db.add(log)
                            db.commit()
                    break

                # Confirmación de guardado real
                print(f"✅ Factura {cab['numero']} cargada exitosamente.")
                sql_id = factura.get("_sql_id")
                if sql_id and db:
                    from db.models import Factura, ProcesoLog
                    f_rec = db.query(Factura).get(sql_id)
                    if f_rec:
                        f_rec.estado = "CARGADA_CIANBOX"
                        f_rec.motivo_error = None
                        f_rec.fecha_procesamiento = datetime.utcnow()
                        log = ProcesoLog(
                            factura_id=f_rec.id,
                            nivel="INFO",
                            mensaje="Inyección desatendida en Cianbox completada exitosamente vía Selenium."
                        )
                        db.add(log)
                        db.commit()
                break


            except Exception as e:
                if intento < intentos - 1:
                    print(f"   ⚠️ Sincronizando interfaz (Intento {intento+1}/{intentos})... Reintentando formulario.")
                    try:
                        reiniciar_modal(driver)
                    except:
                        pass
                else:
                    print(f"❌ Error final en carga Selenium para {cab['numero']}: {e}")