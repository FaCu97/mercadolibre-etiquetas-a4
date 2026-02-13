import pdfplumber
import re
import json
import os
import shutil
import csv
from datetime import datetime
import glob

# ==============================================================================
# 1. CONFIGURACIÓN GENERAL
# ==============================================================================
CARPETA_BASE = os.getcwd()
DIR_ENTRADA = os.path.join(CARPETA_BASE, "01_pendientes")
DIR_SALIDA_OK = os.path.join(CARPETA_BASE, "02_procesados")
DIR_SALIDA_ERROR = os.path.join(CARPETA_BASE, "03_errores")
DIR_LOGS = os.path.join(CARPETA_BASE, "logs")
ARCHIVO_JSON_FINAL = os.path.join(CARPETA_BASE, "lote_cianbox.json")
ARCHIVO_LOG_CSV = os.path.join(DIR_LOGS, "audit_log.csv")

# Tolerancia para diferencias de redondeo (en pesos)
TOLERANCIA = 0.09 

# ==============================================================================
# 2. HERRAMIENTAS DE LOGGING Y ARCHIVOS
# ==============================================================================
def inicializar_carpetas():
    for d in [DIR_ENTRADA, DIR_SALIDA_OK, DIR_SALIDA_ERROR, DIR_LOGS]:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"📁 Carpeta creada: {d}")

    # Crear CSV si no existe
    if not os.path.exists(ARCHIVO_LOG_CSV):
        with open(ARCHIVO_LOG_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha", "Archivo", "Proveedor", "Tipo", "Numero", "Estado", "Motivo", "Diferencia"])

def registrar_log(archivo, proveedor, tipo, numero, estado, motivo, diferencia="0.00"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"   📝 Log: {estado} - {motivo}")
    with open(ARCHIVO_LOG_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, archivo, proveedor, tipo, numero, estado, motivo, diferencia])

def mover_archivo(ruta_origen, carpeta_destino):
    nombre_archivo = os.path.basename(ruta_origen)
    destino = os.path.join(carpeta_destino, nombre_archivo)
    
    # Si ya existe, le agregamos un timestamp para no sobrescribir
    if os.path.exists(destino):
        base, ext = os.path.splitext(nombre_archivo)
        timestamp = datetime.now().strftime("%H%M%S")
        destino = os.path.join(carpeta_destino, f"{base}_{timestamp}{ext}")
        
    shutil.move(ruta_origen, destino)

# ==============================================================================
# 3. EL PARSER (LÓGICA DE EXTRACCIÓN - BASE V12)
# ==============================================================================
def str_to_float(precio_str):
    if not precio_str: return 0.0
    clean = re.sub(r'[^\d,]', '', precio_str).replace('.', '')
    try: return float(clean.replace(',', '.'))
    except ValueError: return 0.0

def float_to_str(valor_float):
    return "{:,.2f}".format(valor_float).replace(",", "X").replace(".", ",").replace("X", ".")

def extraer_valor_por_columna(words, palabra_clave, margen_vertical=60):
    candidatos = [w for w in words if palabra_clave in w['text']]
    if not candidatos: return "0,00", ""
    header = candidatos[-1]
    
    x_min, x_max = header['x0'] - 25, header['x1'] + 25
    y_min, y_max = header['bottom'], header['bottom'] + margen_vertical
    
    valores = []
    for w in words:
        mid_x = (w['x0'] + w['x1']) / 2
        if x_min < mid_x < x_max and y_min < w['top'] < y_max:
            if re.search(r'\d+,\d{2}', w['text']): valores.append(w['text'])
    
    valor_final = valores[0] if valores else "0,00"
    valor_final = valor_final.strip() # Aseguramos que no haya espacios en blanco

    palabras_derecha = [w['text'] for w in words if abs(w['top'] - header['top']) < 4 and w['x0'] > header['x1']]
    contexto = " ".join(palabras_derecha).split("TOTAL")[0].strip()
    return valor_final, contexto

def procesar_archivo_individual(ruta_pdf):
    # Retorna: (DatosJSON, ErrorMsg)
    # Si ErrorMsg es None, significa que salió OK.
    
    nombre_archivo = os.path.basename(ruta_pdf)
    
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            page = pdf.pages[0]
            full_text = page.extract_text() or ""
            
            # --- HEADER ---
            header_text = page.crop((0, 0, page.width, 250)).extract_text().upper()
            if "CREDITO" in header_text: tipo = "NOTA DE CREDITO"
            elif "DEBITO" in header_text: tipo = "NOTA DE DEBITO"
            else: tipo = "FACTURA"

            letra = "X"
            match_letra = re.search(r'(?:^|\n)\s*([ABCE])\s*(?:$|\n)', header_text)
            if match_letra: letra = match_letra.group(1)
            elif " A " in header_text: letra = "A"

            datos = {
                "cabecera": {
                    "proveedor": "CROMOSOL", "tipo": tipo, "letra": letra,
                    "fecha": "HOY", "puntoVenta": "0000", "numero": "00000000",
                    "total": "0,00", "percepciones_iibb": []
                },
                "productos": []
            }

            m_f = re.search(r'FECHA:\s*(\d{2}-\d{2}-\d{4})', full_text)
            if m_f: datos["cabecera"]["fecha"] = m_f.group(1).replace('-', '/')
            
            m_n = re.search(r'(\d{4})-(\d{8})', full_text)
            if m_n: 
                datos["cabecera"]["puntoVenta"] = m_n.group(1)
                datos["cabecera"]["numero"] = m_n.group(2)
            else:
                return None, "No se encontró el número de comprobante"

            # --- PIE DE PÁGINA ---
            pie = page.crop((0, page.height * 0.65, page.width, page.height))
            words_pie = pie.extract_words()
            
            val_neto_str, _ = extraer_valor_por_columna(words_pie, "NETO")
            if val_neto_str == "0,00": val_neto_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL")
            val_iva_str, _ = extraer_valor_por_columna(words_pie, "I.V.A.")
            val_total_str, _ = extraer_valor_por_columna(words_pie, "TOTAL")
            
            # Extraer la cadena de la percepción de IIBB
            val_iibb_str_extracted, jur_iibb = extraer_valor_por_columna(words_pie, "IIBB")
            # Convertir el valor de IIBB a flotante para una comparación numérica precisa
            monto_iibb_float = str_to_float(val_iibb_str_extracted)

            # Solo añadir la percepción si su valor numérico es distinto de cero
            if monto_iibb_float != 0.0:
                 if not jur_iibb: 
                    if "Capital" in [w['text'] for w in words_pie]: jur_iibb = "Capital Federal"
                 datos["cabecera"]["percepciones_iibb"].append({
                    "jurisdiccion": jur_iibb if jur_iibb else "Capital Federal",
                    "monto": float_to_str(monto_iibb_float) # Almacenar en formato canónico
                })
            
            datos["cabecera"]["total"] = val_total_str

            # --- PRODUCTOS Y VALIDACIÓN ---
            words = page.extract_words()
            top_y = 0; bottom_y = page.height
            for w in words:
                if w['text'] == "ARTICULO": top_y = w['top'] - 5
                if "SUBTOTAL" in w['text']: bottom_y = w['top']
            
            if top_y > 0: page_prod = page.crop((0, top_y, page.width, bottom_y))
            else: page_prod = page

            cortes = [10, 46, 88, 460, 535, 600]
            settings = {"vertical_strategy": "explicit", "explicit_vertical_lines": cortes, "horizontal_strategy": "text", "snap_tolerance": 3}
            tabla = page_prod.extract_table(table_settings=settings)

            suma_productos = 0.0
            if tabla:
                for fila in tabla:
                    if not fila or len(fila) < 4: continue
                    if not fila[3] or not re.search(r'\d', fila[3]): continue
                    try:
                        cod = fila[1].replace('\n', '').strip().split(' ')[0]
                        desc = fila[2].replace('\n', ' ').strip()
                        cant_float = float(fila[0].split(',')[0].strip())
                        precio_float = str_to_float(fila[3])
                        
                        linea_total = round(cant_float * precio_float, 2)
                        suma_productos = round(suma_productos + linea_total, 2)

                        datos["productos"].append({
                            "codigo": cod, "descripcion": desc, "cantidad": str(int(cant_float)),
                            "precio": fila[3], "iva": "21.00", "descuento": "0,00"
                        })
                    except: pass
            
            # --- CHEQUEO TOLERANCIA ---
            f_neto = str_to_float(val_neto_str)
            diff_prod = abs(suma_productos - f_neto)
            
            if diff_prod > TOLERANCIA:
                msg = f"Error Suma Productos. Calc: {suma_productos} vs Neto: {f_neto} (Diff: {diff_prod:.2f})"
                return datos, msg # Devolvemos datos para log, pero con mensaje de error

            f_total_leido = str_to_float(val_total_str)
            f_iva = str_to_float(val_iva_str)
            
            # Usar el valor flotante de la percepción de IIBB ya calculado
            total_calc = round(f_neto + f_iva + monto_iibb_float, 2)
            diff_total = abs(total_calc - f_total_leido)

            if diff_total > TOLERANCIA:
                msg = f"Error Suma Fiscal. Calc: {total_calc} vs Total PDF: {f_total_leido} (Diff: {diff_total:.2f})"
                return datos, msg

            return datos, None # None = Sin errores

    except Exception as e:
        return None, f"Excepción de Python: {str(e)}"

# ==============================================================================
# 4. ORQUESTADOR PRINCIPAL
# ==============================================================================
def ejecutar_lote():
    inicializar_carpetas()
    
    archivos = glob.glob(os.path.join(DIR_ENTRADA, "*.pdf"))
    print(f"\n🚀 Iniciando procesamiento de {len(archivos)} archivos en '{DIR_ENTRADA}'...")
    
    lote_exitoso = []

    for ruta in archivos:
        nombre = os.path.basename(ruta)
        print(f"\n📄 Analizando: {nombre}")
        
        datos, error = procesar_archivo_individual(ruta)
        
        # Datos básicos para el log (aunque falle)
        prov = "CROMOSOL"
        tipo = datos["cabecera"]["tipo"] if datos else "?"
        nro = datos["cabecera"]["numero"] if datos else "?"

        if error:
            print(f"   ❌ RECHAZADO: {error}")
            mover_archivo(ruta, DIR_SALIDA_ERROR)
            registrar_log(nombre, prov, tipo, nro, "ERROR", error)
        else:
            print(f"   ✅ APROBADO")
            lote_exitoso.append(datos)
            mover_archivo(ruta, DIR_SALIDA_OK)
            registrar_log(nombre, prov, tipo, nro, "OK", "Procesado correctamente")

    # Guardar JSON Final
    if lote_exitoso:
        with open(ARCHIVO_JSON_FINAL, 'w', encoding='utf-8') as f:
            json.dump(lote_exitoso, f, indent=4, ensure_ascii=False)
        print(f"\n✨ Proceso terminado. {len(lote_exitoso)} facturas listas en '{ARCHIVO_JSON_FINAL}'")
    else:
        print("\n⚠️ No se generaron facturas exitosas.")

if __name__ == "__main__":
    ejecutar_lote()