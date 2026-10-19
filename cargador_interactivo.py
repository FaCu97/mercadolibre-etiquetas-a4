import sys
import time
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Factura, Proveedor
from cargador_selenium import iniciar_driver, login, navegar_una_sola_vez, procesar_lote_en_memoria

# We'll monkey patch procesar_lote_en_memoria or write our own loop.
# Let's import what we need.
from cargador_selenium import (
    asegurar_sucursal, JS_SET_PROVEEDOR_DIRECTO, JS_BUSCAR_PROVEEDOR, 
    escribir_teclado, SELECTORES, MAPEO_COMPROBANTES, MAPEO_LETRAS,
    reiniciar_modal, JS_BUSCAR_PRODUCTO, escribir_seguro, limpiar_monto_para_input, MAPEO_PROVINCIAS, click_seguro
)
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

def procesar_interactivo():
    db = SessionLocal()
    # Filter pending invoices in range
    query = db.query(Factura).filter_by(estado="PENDIENTE_CARGA")
    facturas = query.all()
    if not facturas:
        print("No hay facturas pendientes.")
        return

    # Convert models to dict as in cargador_selenium.py
    lote_facturas = []
    for f in facturas:
        tipo_full = f.tipo_comprobante.upper() if f.tipo_comprobante else "FACTURA A"
        parts = tipo_full.rsplit(" ", 1)
        tipo_str = parts[0] if len(parts) > 1 else "FACTURA"
        letra_str = parts[1] if len(parts) > 1 else "A"
        percepciones_list = []
        if f.percepciones and f.percepciones > 0:
            percepciones_list.append({
                "jurisdiccion": "Capital Federal",
                "monto": str(f.percepciones).replace(".", ",")
            })
        lote_facturas.append({
            "_sql_id": f.id,
            "_cuit": getattr(f, "cuit_receptor", ""),
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
                "mueve_stock": f.mueve_stock if f.mueve_stock is not None else True,
                "id_contribuyente": "1" if getattr(f, "cuit_receptor", "") == "30719342457" else "0"
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

    import os
    os.environ["HEADLESS"] = "false" # Ensure user sees it
    driver = iniciar_driver()
    try:
        login(driver)
        wait = WebDriverWait(driver, 10)
        navegar_una_sola_vez(driver)
        
        auto_all = False
        stop_on_other_cuit = False
        stop_cuit = ""
        
        for i, factura in enumerate(lote_facturas):
            # Ensure browser session is alive
            if not getattr(driver, 'session_id', None):
                print("⚠️ Session lost, restarting browser...")
                driver = iniciar_driver()
                login(driver)
                navegar_una_sola_vez(driver)
            cab = factura["cabecera"]
            print(f"\n📄 [{i+1}/{len(lote_facturas)}] Procesando Carga: {cab['numero']}")
            
            # --- Sucursal ---
            id_contribuyente = str(cab.get("id_contribuyente", "0"))
            sucursal_req = "1318 SRL" if id_contribuyente == "1" else "AV. WARNES 1318"
            status_sucursal = asegurar_sucursal(driver, sucursal_req)
            if status_sucursal == "CHANGED":
                navegar_una_sola_vez(driver)
                
            # --- Proveedor ---
            # --- Proveedor ---
            try:
                wait.until(EC.presence_of_element_located((By.NAME, "id_proveedor")))
            except Exception as e:
                print("⚠️ Timeout waiting for provider field, reloading form...")
                navegar_una_sola_vez(driver)
                wait.until(EC.presence_of_element_located((By.NAME, "id_proveedor")))
            id_cian = cab.get("id_cianbox")
            nom_cian = cab.get("nombre_cianbox") or cab.get("proveedor")
            if id_cian:
                driver.execute_async_script(JS_SET_PROVEEDOR_DIRECTO, str(id_cian), str(nom_cian))
            else:
                driver.execute_async_script(JS_BUSCAR_PROVEEDOR, cab["proveedor"])
                
            # --- Cabecera ---
            fecha_dt = datetime.strptime(cab["fecha"], "%d/%m/%Y") if "/" in cab["fecha"] else datetime.now()
            fecha_formateada = fecha_dt.strftime("%d%m%y")
            escribir_teclado(driver, SELECTORES["fecha"], fecha_formateada)
            escribir_teclado(driver, SELECTORES["pv"], cab["puntoVenta"])
            escribir_teclado(driver, SELECTORES["numero"], cab["numero"])
            
            val_tipo = MAPEO_COMPROBANTES.get(cab["tipo"].upper(), "1")
            val_letra = MAPEO_LETRAS.get(cab["letra"].upper(), "1")
            Select(driver.find_element(*SELECTORES["select_tipo"])).select_by_value(val_tipo)
            Select(driver.find_element(*SELECTORES["select_letra"])).select_by_value(val_letra)
            
            try:
                Select(driver.find_element(*SELECTORES["select_contribuyente"])).select_by_value(id_contribuyente)
            except:
                pass
                
            mueve_stock = cab.get("mueve_stock", True)
            opt_stock = "toda_sr" if mueve_stock else "no_stock"
            try:
                Select(driver.find_element(*SELECTORES["select_stock"])).select_by_value(opt_stock)
            except:
                pass
            time.sleep(0.6)
            
            # --- Productos ---
            for prod in factura["productos"]:
                res_prod = driver.execute_async_script(JS_BUSCAR_PRODUCTO, prod["codigo"])
                if "NOT_FOUND" in str(res_prod) or "ERROR" in str(res_prod):
                    desc_manual = f"{prod['codigo']} {prod['descripcion']}"
                    escribir_teclado(driver, (By.CSS_SELECTOR, ".box_main_field"), desc_manual)
                    iva_val = "1.2100" if "21" in str(prod.get("iva", "21.00")) else ("1.1050" if "10.5" in str(prod.get("iva", "")) else "1.0000")
                    try:
                        Select(driver.find_element(By.NAME, "add_alicuota_iva")).select_by_value(iva_val)
                    except:
                        pass
                
                escribir_seguro(driver, SELECTORES["cant"], prod["cantidad"])
                precio_limpio = limpiar_monto_para_input(prod["precio"])
                escribir_seguro(driver, SELECTORES["precio"], precio_limpio)
                click_seguro(driver, SELECTORES["btn_add"])
                try:
                    WebDriverWait(driver, 3, poll_frequency=0.1).until(
                        lambda d: d.find_element(By.CSS_SELECTOR, ".box_main_field").get_attribute("value") == ""
                    )
                except:
                    time.sleep(0.2)
                    
            if cab.get("percepciones_iibb"):
                try:
                    click_seguro(driver, SELECTORES["tab_percepciones"])
                    wait.until(EC.element_to_be_clickable(SELECTORES["select_provincia"]))
                    for perc in cab["percepciones_iibb"]:
                        jurisdiccion = perc.get("jurisdiccion", "Capital Federal")
                        monto = str(perc["monto"])
                        id_prov = MAPEO_PROVINCIAS.get(jurisdiccion, "23")
                        Select(driver.find_element(*SELECTORES["select_provincia"])).select_by_value(id_prov)
                        escribir_seguro(driver, SELECTORES["monto_percepcion"], monto)
                        try:
                            driver.find_element(*SELECTORES["btn_add_percepcion"]).click()
                        except:
                            driver.execute_script("document.getElementById('add_impuesto').click();")
                        time.sleep(0.3)
                except:
                    pass
            
            # --- Interactive Pause ---
            if auto_all and stop_on_other_cuit and factura.get('_cuit') == stop_cuit:
                auto_all = False
                print(f"--- DETENIDO por cambio de CUIT a {stop_cuit} ---")

            if not auto_all:
                print(f"\n--- REVISIÓN REQUERIDA para Factura {cab['numero']} ---")
                print("Por favor revise Chrome. La factura está cargada pero NO guardada.")
                ans = input("Escriba 'ok' (continuar), 'all' (todas), 'skip' (omitir), o 'all_until_other' (todas hasta otro cuit): ").strip().lower()
                if ans == 'all':
                    auto_all = True
                    stop_on_other_cuit = False
                elif ans == 'all_until_other':
                    auto_all = True
                    stop_on_other_cuit = True
                    stop_cuit = "30719342457" if factura.get('_cuit') == "20173327324" else "20173327324"
                elif ans == 'skip':
                    print("Omitiendo...")
                    reiniciar_modal(driver)
                    continue
                    
            click_seguro(driver, SELECTORES["guardar"])
            time.sleep(2)
            
            # Check for dup
            div_dup = driver.find_elements(By.ID, "mb_duplicated")
            es_duplicado = False
            if div_dup and any(d.is_displayed() for d in div_dup):
                es_duplicado = True
            
            if es_duplicado:
                print("Factura Duplicada en Cianbox!")
                reiniciar_modal(driver)
                
            # Update DB state to CARGADA_CIANBOX
            f_rec = db.query(Factura).get(factura["_sql_id"])
            if f_rec:
                f_rec.estado = "CARGADA_CIANBOX"
                db.commit()
                
    finally:
        driver.quit()
        db.close()

if __name__ == "__main__":
    procesar_interactivo()
